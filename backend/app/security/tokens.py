from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt

from app.config import jwt_secret, jwt_algorithm, jwt_expire_minutes


def create_token_akses(subject: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "iat": now,
        "exp": now + timedelta(minutes=jwt_expire_minutes),
    }
    return jwt.encode(payload, jwt_secret, algorithm=jwt_algorithm)


def decode_token_akses(token: str) -> str | None:
    try:
        payload = jwt.decode(token, jwt_secret, algorithms=[jwt_algorithm])
    except JWTError:
        return None
    return payload.get("sub")