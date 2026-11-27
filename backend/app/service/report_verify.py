import base64
import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone
from typing import Any

from app.config import jwt_secret


def _b64u_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64u_decode(text: str) -> bytes:
    pad = "=" * ((4 - len(text) % 4) % 4)
    return base64.urlsafe_b64decode((text + pad).encode("ascii"))


def create_share_token(session_id: int, user_id: int, expires_days: int = 30) -> str:
    """Creates a compact HMAC-SHA256 signed URL-safe token for read-only report verification."""
    exp = int((datetime.now(timezone.utc) + timedelta(days=expires_days)).timestamp())
    payload = json.dumps({"s": int(session_id), "u": int(user_id), "e": exp}, separators=(",", ":")).encode("utf-8")
    p_b64 = _b64u_encode(payload)
    sig = hmac.new(jwt_secret.encode("utf-8"), p_b64.encode("ascii"), hashlib.sha256).digest()
    return f"{p_b64}.{_b64u_encode(sig)}"


def create_batch_share_token(session_ids: list[int], user_id: int, expires_days: int = 30) -> str:
    """Creates a compact HMAC-SHA256 signed token for a multi-session verification bundle."""
    exp = int((datetime.now(timezone.utc) + timedelta(days=expires_days)).timestamp())
    unique_ids = list(dict.fromkeys(int(sid) for sid in session_ids))
    payload = json.dumps({"ids": unique_ids, "u": int(user_id), "e": exp}, separators=(",", ":")).encode("utf-8")
    p_b64 = _b64u_encode(payload)
    sig = hmac.new(jwt_secret.encode("utf-8"), p_b64.encode("ascii"), hashlib.sha256).digest()
    return f"{p_b64}.{_b64u_encode(sig)}"


def verify_share_token(token: str) -> tuple[list[int], int] | None:
    """Verifies signature and expiry of a single or batch share token. Returns (session_ids, user_id) or None."""
    if not token or "." not in token:
        return None
    parts = token.split(".", 1)
    if len(parts) != 2:
        return None
    p_b64, s_b64 = parts
    expected_sig = _b64u_encode(
        hmac.new(jwt_secret.encode("utf-8"), p_b64.encode("ascii"), hashlib.sha256).digest()
    )
    if not hmac.compare_digest(s_b64, expected_sig):
        return None
    try:
        data = json.loads(_b64u_decode(p_b64).decode("utf-8"))
        exp = int(data.get("e", 0))
        if exp < int(datetime.now(timezone.utc).timestamp()):
            return None
        uid = int(data["u"])
        if "ids" in data and isinstance(data["ids"], list):
            ids = [int(x) for x in data["ids"]]
            return (ids, uid) if ids else None
        return [int(data["s"])], uid
    except Exception:
        return None


def compute_integrity_hash(row: Any, segs: list[Any]) -> str:
    """Computes a deterministic SHA-256 tamper-evident digest over session metadata and chunk scores."""
    started_iso = row.started_at.isoformat() if row.started_at else ""
    canonical = {
        "session_id": int(row.id),
        "started_at": started_iso,
        "verdict": str(row.verdict or "real"),
        "fake_count": int(row.fake_count or 0),
        "real_count": int(row.real_count or 0),
        "avg_fake_prob": round(float(row.avg_fake_prob or 0.0), 4),
        "chunks": [
            [int(s.offset_s), bool(s.is_fake), round(float(s.fake_prob or 0.0), 4)]
            for s in segs
        ],
    }
    blob = json.dumps(canonical, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def build_hr_risk_brief(row: Any, segs: list[Any]) -> dict:
    """Generates a deterministic, actionable 2-3 sentence HR Risk Brief from chunk patterns."""
    total = len(segs)
    fake_indices = [int(s.offset_s) for s in segs if s.is_fake]
    fake_count = len(fake_indices)
    avg_pct = round(float(row.avg_fake_prob or 0.0) * 100, 1)
    peak_seg = max(segs, key=lambda s: float(s.fake_prob or 0.0), default=None)
    peak_pct = round(float(peak_seg.fake_prob or 0.0) * 100, 1) if peak_seg else avg_pct
    peak_idx = int(peak_seg.offset_s) if peak_seg else 1

    # Detect longest consecutive AI streak
    max_streak = 0
    cur_streak = 0
    for s in segs:
        if s.is_fake:
            cur_streak += 1
            if cur_streak > max_streak:
                max_streak = cur_streak
        else:
            cur_streak = 0

    if total == 0:
        return {
            "risk_level": "Low",
            "headline": "No audio chunks recorded",
            "summary": "This session contains no analyzed audio segments.",
            "recommendation": "Re-run screening with an active audio input to obtain a full voice assessment.",
        }

    if fake_count == 0:
        return {
            "risk_level": "Low",
            "headline": "Consistent human voice across all chunks",
            "summary": (
                f"All {total} analyzed chunk(s) scored within the authentic human range "
                f"(average AI risk {avg_pct}%, peak {peak_pct}% at Chunk #{peak_idx}). "
                "No synthetic voice anomalies were detected during this session."
            ),
            "recommendation": "No further voice-authenticity follow-up is required based on this screening.",
        }

    if max_streak >= 2 or (fake_count / total) >= 0.5:
        return {
            "risk_level": "High",
            "headline": "Sustained synthetic voice indicators detected",
            "summary": (
                f"{fake_count} of {total} chunk(s) triggered AI voice flags with a peak risk of {peak_pct}% "
                f"at Chunk #{peak_idx} and a maximum consecutive streak of {max_streak} flagged chunk(s). "
                "Sustained synthetic patterns strongly indicate AI voice conversion or TTS playback."
            ),
            "recommendation": "Flag this screening for HR review and request a live on-camera identity re-verification.",
        }

    return {
        "risk_level": "Moderate",
        "headline": "Isolated AI voice spike detected",
        "summary": (
            f"{fake_count} isolated chunk(s) out of {total} crossed the AI risk threshold "
            f"(peak {peak_pct}% at Chunk #{peak_idx}, overall average {avg_pct}%). "
            "Isolated spikes can result from brief synthetic playback, heavy codec compression, or background audio."
        ),
        "recommendation": "Review the highlighted chunk(s) in the timeline and consider a short follow-up call if the spike occurred during key responses.",
    }
