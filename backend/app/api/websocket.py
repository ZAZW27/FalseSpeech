import json
import logging
from datetime import datetime, timezone
import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.config import target_sr
from app.db.models import DetectionSegmentRow, DetectionSessionRow, User
from app.db.session import SessionLocal
from app.security.tokens import decode_token_akses
from app.service import inference
from app.service.audio import preprocess_audio
from app.service.conn_manager import manager

logger = logging.getLogger(__name__)
router = APIRouter()


def _reset_quota_if_needed(user: User, db):
    now = datetime.now(timezone.utc)
    if user.quota_reset_at is None or user.quota_reset_at.replace(tzinfo=timezone.utc) < now:
        user.quota_used = 0
        user.quota_reset_at = now.replace(hour=23, minute=59, second=59, microsecond=0)
        db.commit()
        logger.info(f"quota reset for user {user.id}, limit={user.quota_limit}")

@router.websocket("/ws/audio")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    token = None

    auth = websocket.headers.get("authorization", "")
    if auth.startswith("Bearer "):
        token = auth[7:]

    if not token:
        token = websocket.query_params.get("token")

    if not token:
        await websocket.close(code=1008, reason="missing token")
        return
    
    sub = decode_token_akses(token)
    if sub is None:
        await websocket.close(code=1008, reason="invalid token")
        return

    db = SessionLocal()
    try:
        user_id = int(sub)
    except (ValueError, TypeError):
        db.close()
        await websocket.close(code=1008, reason="invalid token")
        return

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        db.close()
        await websocket.close(code=1008, reason="user not found")
        return

    _reset_quota_if_needed(user, db)

    if user.quota_used >= user.quota_limit:
        db.close()
        await websocket.close(code=1008, reason="quota exceeded")
        return

    is_connected = await manager.connect(user.id, websocket)
    if not is_connected:
        db.close()
        await websocket.close(code=1008, reason="Multiple concurrent connections are not allowed. Please close other tabs.")
        return

    logger.info(f"WS connected user={user.id} tier={user.tier} quota={user.quota_used}/{user.quota_limit}")
    _, device_used = inference.get_model()

    # Reuse an existing DetectionSessionRow when the client passes ?session_id=<id>,
    # so all chunks recorded in one listening run are grouped under one session!
    req_session_id = websocket.query_params.get("session_id")
    req_source = (websocket.query_params.get("source") or "web").strip().lower()[:32] or "web"
    session = None
    created_new_session = False

    if req_session_id:
        try:
            sid_int = int(req_session_id)
            session = (
                db.query(DetectionSessionRow)
                .filter(
                    DetectionSessionRow.id == sid_int,
                    DetectionSessionRow.user_id == user.id,
                )
                .first()
            )
        except (ValueError, TypeError):
            session = None

    if session is None:
        session = DetectionSessionRow(
            user_id=user.id,
            source=req_source,
            fake_count=0,
            real_count=0,
            verdict="real",
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        created_new_session = True

    session_id = session.id
    existing_seg_count = (
        db.query(DetectionSegmentRow)
        .filter(DetectionSegmentRow.session_id == session_id)
        .count()
    )

    segment_index = existing_seg_count
    new_chunks_count = 0
    total_audio_seconds = 0.0
    started = datetime.now(timezone.utc)

    try:
        while True:
            data = await websocket.receive_bytes()

            if not inference.is_loaded():
                await websocket.send_text(json.dumps({"error": "model ga ready"}))
                continue

            wav_tensor = preprocess_audio(data, target_sr=target_sr, device=device_used)
            if wav_tensor is None:
                await websocket.send_text(json.dumps({"error": "audio ga bisa di-decode"}))
                continue

            chunk_seconds = wav_tensor.shape[1] / target_sr
            would_be_used = user.quota_used + int(total_audio_seconds + chunk_seconds)

            # --- FAIR USAGE POLICY CHECK (LIFETIME) ---
            if user.tier == 'lifetime' and would_be_used > 43200:
                await websocket.send_text(json.dumps({
                    "error": "Fair Usage Policy exceeded. Lifetime users are limited to 12 hours of continuous listening per day.",
                    "quota_used": user.quota_used + int(total_audio_seconds),
                    "quota_limit": 43200,
                }))
                logger.info(f"Lifetime user {user.id} hit FUP limit (43200s), closing session {session_id}")
                break
            # ------------------------------------------

            if would_be_used > user.quota_limit:
                await websocket.send_text(json.dumps({
                    "error": "quota exceeded",
                    "quota_used": user.quota_used + int(total_audio_seconds),
                    "quota_limit": user.quota_limit,
                }))
                logger.info(f"user {user.id} hit quota, closing session {session_id}")
                break

            ril_prob, fek_prob = await inference.enqueue_inference(wav_tensor, user.tier)
            is_fake = fek_prob > 0.5

            total_audio_seconds += chunk_seconds
            segment_index += 1
            new_chunks_count += 1

            seg = DetectionSegmentRow(
                session_id=session_id,
                offset_s=segment_index,
                duration_s=round(float(chunk_seconds), 2),
                is_fake=is_fake,
                fake_prob=float(fek_prob),
                real_prob=float(ril_prob),
                recorded_at=datetime.now(timezone.utc),
            )
            db.add(seg)
            db.commit()

            result = {
                "ril_prob": ril_prob,
                "fek_prob": fek_prob,
                "is_fek": is_fake,
                "session_id": session_id,
                "segment_index": segment_index,
                "quota_used": user.quota_used + int(total_audio_seconds),
                "quota_limit": user.quota_limit,
            }
            await websocket.send_text(json.dumps(result))

    except WebSocketDisconnect:
        logger.info(f"WS disconnected user={user.id} session={session_id}")
    except Exception as e:
        logger.error(f"WS error: {e}", exc_info=True)
        try:
            await websocket.close(code=1011)
        except Exception:
            pass
    finally:
        ended = datetime.now(timezone.utc)
        try:
            all_segs = (
                db.query(DetectionSegmentRow)
                .filter(DetectionSegmentRow.session_id == session_id)
                .all()
            )
            total = len(all_segs)
            if total == 0 and created_new_session:
                # Avoid leaving empty phantom sessions if WS closed before any chunk
                db.delete(session)
                db.commit()
            else:
                fake_count = sum(1 for s in all_segs if s.is_fake)
                real_count = total - fake_count
                avg_fake_prob = (
                    sum(float(s.fake_prob or 0.0) for s in all_segs) / total
                    if total > 0
                    else 0.0
                )
                if total == 0:
                    verdict = "real"
                elif fake_count / total >= 0.5:
                    verdict = "fake"
                elif fake_count / total <= 0.1:
                    verdict = "real"
                else:
                    verdict = "mixed"

                sess_start = session.started_at
                if sess_start and sess_start.tzinfo is None:
                    sess_start = sess_start.replace(tzinfo=timezone.utc)
                wall_duration = int((ended - sess_start).total_seconds()) if sess_start else int((ended - started).total_seconds())
                seg_duration = int(round(sum(float(getattr(s, "duration_s", 0.0) or 0.0) for s in all_segs)))

                session.ended_at = ended
                session.duration_s = max(wall_duration, seg_duration, 1 if total > 0 else 0)
                session.fake_count = fake_count
                session.real_count = real_count
                session.avg_fake_prob = avg_fake_prob
                session.verdict = verdict

                if int(total_audio_seconds) > 0:
                    user.quota_used = user.quota_used + int(total_audio_seconds)
                    user.cycle_quota_used = int(user.cycle_quota_used or 0) + int(total_audio_seconds)

                db.commit()
                logger.info(
                    f"session {session_id} updated: user={user.id} chunks={total} (+{new_chunks_count}) "
                    f"fake={fake_count} real={real_count} avg_fake_prob={avg_fake_prob:.3f} verdict={verdict} "
                    f"audio_seconds={int(total_audio_seconds)} quota={user.quota_used}/{user.quota_limit}"
                )
        except Exception as e:
            logger.error(f"failed to finalize session: {e}")
        finally:
            manager.disconnect(user.id)
            db.close()