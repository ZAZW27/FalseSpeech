from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.sql import func

from app.db.base import Base

from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    phone = Column(String(20), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)

    tier = Column(String(20), nullable=False, default="free")
    quota_used = Column(Integer, nullable=False, default=0)
    quota_limit = Column(Integer, nullable=False, default=600)
    quota_reset_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

class DetectionSessionRow(Base):
    __tablename__ = "detection_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=True)
    started_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    ended_at = Column(DateTime(timezone=True), nullable=True)
    duration_s = Column(Integer, nullable=False, default=0)
    fake_count = Column(Integer, nullable=False, default=0)
    real_count = Column(Integer, nullable=False, default=0)
    verdict = Column(String(20), nullable=False, default="real")


class DetectionSegmentRow(Base):
    __tablename__ = "detection_segments"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(
        Integer,
        ForeignKey("detection_sessions.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    offset_s = Column(Integer, nullable=False, default=0)
    is_fake = Column(Boolean, nullable=False, default=False)
    fake_prob = Column(Float, nullable=False, default=0.0)
    real_prob = Column(Float, nullable=False, default=0.0)