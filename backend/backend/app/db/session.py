import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://falsespeech:falsespeech_dev@localhost:5432/falsespeech",
)

engine = create_engine(DATABASE_URL, echo=False, future=True)

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