from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt

from app.config import jwt_secret, jwt_algo, jwt_expires


def create_token_akses(subject: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "iat": now,
        "exp": now + timedelta(minutes=jwt_expires),
    }
    return jwt.encode(payload, jwt_secret, algorithm=jwt_algo)


def decode_token_akses(token: str) -> str | None:
    try:
        payload = jwt.decode(token, jwt_secret, algorithms=[jwt_algo])
    except JWTError:
        return None
    return payload.get("sub")