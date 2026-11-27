import logging
from sqlalchemy import text

from app.db.base import Base
from app.db.session import engine

from app.db import models  # noqa: F401

logger = logging.getLogger(__name__)


def init_db() -> None:
    """Create all tables that do not yet exist and ensure incremental columns."""
    Base.metadata.create_all(bind=engine)
    try:
        with engine.begin() as conn:
            conn.execute(
                text(
                    "ALTER TABLE users ADD COLUMN IF NOT EXISTS "
                    "subscription_expires_at TIMESTAMPTZ"
                )
            )
            conn.execute(
                text(
                    "ALTER TABLE users ADD COLUMN IF NOT EXISTS "
                    "balance INTEGER NOT NULL DEFAULT 0"
                )
            )
            conn.execute(
                text(
                    "ALTER TABLE users ADD COLUMN IF NOT EXISTS "
                    "cycle_quota_used INTEGER NOT NULL DEFAULT 0"
                )
            )
            conn.execute(
                text(
                    "ALTER TABLE transactions ADD COLUMN IF NOT EXISTS "
                    "balance_applied INTEGER NOT NULL DEFAULT 0"
                )
            )
            conn.execute(
                text(
                    "ALTER TABLE transactions ADD COLUMN IF NOT EXISTS "
                    "payment_url TEXT"
                )
            )
    except Exception as e:
        logger.warning(f"Incremental column migration skipped: {e}")
    logger.info("Database tables ensured")
