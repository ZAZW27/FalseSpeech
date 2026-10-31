import logging

from app.db.base import Base
from app.db.session import engine

from app.db import models  

logger = logging.getLogger(__name__)


def init_db() -> None:
    """Create all tables that do not yet exist."""
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables ensured")