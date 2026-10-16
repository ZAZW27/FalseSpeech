import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.config import target_sr
from app.db.models import DetectionSegmentRow, DetectionSessionRow, User
from app.db.session import SessionLocal
from app.security.tokens import decode_token_akses
from app.service import inference
from app.service.audio import preprocess_audio

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

    logger.info(f"WS connected user={user.id} tier={user.tier} quota={user.quota_used}/{user.quota_limit}")
    _, device_used = inference.get_model()

    session = DetectionSessionRow(
        user_id=user.id,
        fake_count=0,
        real_count=0,
        verdict="real",
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    session_id = session.id

    segment_index = 0
    fake_count = 0
    real_count = 0
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

            if would_be_used > user.quota_limit:
                await websocket.send_text(json.dumps({
                    "error": "quota exceeded",
                    "quota_used": user.quota_used + int(total_audio_seconds),
                    "quota_limit": user.quota_limit,
                }))
                logger.info(f"user {user.id} hit quota, closing session {session_id}")
                break

            ril_prob, fek_prob = inference.inferencing(wav_tensor)
            is_fake = fek_prob > 0.5

            total_audio_seconds += chunk_seconds
            segment_index += 1
            if is_fake:
                fake_count += 1
            else:
                real_count += 1

            seg = DetectionSegmentRow(
                session_id=session_id,
                offset_s=segment_index,
                is_fake=is_fake,
                fake_prob=float(fek_prob),
                real_prob=float(ril_prob),
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
        duration = int((ended - started).total_seconds())

        total = fake_count + real_count
        if total == 0:
            verdict = "real"
        elif fake_count / total >= 0.5:
            verdict = "fake"
        elif fake_count / total <= 0.1:
            verdict = "real"
        else:
            verdict = "mixed"

        try:
            session.ended_at = ended
            session.duration_s = duration
            session.fake_count = fake_count
            session.real_count = real_count
            session.verdict = verdict

            user.quota_used = user.quota_used + int(total_audio_seconds)

            db.commit()
            logger.info(
                f"session {session_id} closed: user={user.id} "
                f"fake={fake_count} real={real_count} verdict={verdict} "
                f"audio_seconds={int(total_audio_seconds)} "
                f"quota={user.quota_used}/{user.quota_limit}"
            )
        except Exception as e:
            logger.error(f"failed to close session: {e}")
        finally:
            db.close()