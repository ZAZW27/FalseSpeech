from sqlalchemy.orm import Session

from app.db.models import User
from app.security.passwords import hash_pass, verify_pass
from app.security.tokens import create_token_akses


def cari_user_by_email(db: Session, email: str) -> User | None:
    return db.query(User).filter(User.email == email).first()


def cari_user_by_phone(db: Session, phone: str) -> User | None:
    return db.query(User).filter(User.phone == phone).first()


def cari_user_by_email_or_phone(db: Session, ident: str) -> User | None:
    user = cari_user_by_email(db, ident)
    if user is None:
        user = cari_user_by_phone(db, ident)
    return user


def cari_user_by_id(db: Session, user_id: int) -> User | None:
    return db.query(User).filter(User.id == user_id).first()


def daftar_user(
    db: Session,
    name: str,
    email: str,
    phone: str,
    password: str,
) -> User:
    if cari_user_by_email(db, email) is not None:
        raise ValueError("email sudah terdaftar")
    if cari_user_by_phone(db, phone) is not None:
        raise ValueError("nomor telepon sudah terdaftar")

    user = User(
        name=name,
        email=email,
        phone=phone,
        hashed_password=hash_pass(password),
        tier="free",
        quota_used=0,
        quota_limit=600,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def login_user(db: Session, ident: str, password: str) -> str | None:
    user = cari_user_by_email_or_phone(db, ident)
    if user is None:
        return None
    if not verify_pass(password, user.hashed_password):
        return None
    return create_token_akses(str(user.id))