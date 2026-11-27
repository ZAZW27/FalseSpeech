import os
from dotenv import load_dotenv

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

load_dotenv()

_raw_db_url = (
    os.getenv("DATABASE_URL")
    or os.getenv("NEON_DATABASE_URL")
    or os.getenv("NEON_DATABAES_URL")
    or "postgresql+psycopg://falsespeech:falsespeech_dev@localhost:5432/falsespeech"
).strip()

if _raw_db_url.startswith("postgres://"):
    _raw_db_url = "postgresql+psycopg://" + _raw_db_url[len("postgres://"):]
elif _raw_db_url.startswith("postgresql://"):
    _raw_db_url = "postgresql+psycopg://" + _raw_db_url[len("postgresql://"):]

DATABASE_URL = _raw_db_url

engine = create_engine(
    DATABASE_URL,
    echo=False,
    future=True,
    pool_pre_ping=True,
    pool_recycle=300,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)


def get_db():
    """FastAPI dependency. Yields a database session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()