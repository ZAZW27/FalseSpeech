import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

from app.db.models import User
from app.db.session import SessionLocal

logger = logging.getLogger(__name__)

_scheduler_task: Optional[asyncio.Task] = None
CHECK_INTERVAL_SECONDS = 3600  # Check every hour


def check_expired_subscriptions(now: Optional[datetime] = None) -> int:
    """
    UC-05 / RF-04: Checks monthly subscribers (pro / pro_max) whose subscription_expires_at
    has passed and automatically downgrades them back to the Free tier (600s quota).
    Returns the number of downgraded users.
    """
    current_time = now or datetime.now(timezone.utc)
    db = SessionLocal()
    downgraded = 0
    try:
        expired_users = (
            db.query(User)
            .filter(
                User.tier.in_(["pro", "pro_max"]),
                User.subscription_expires_at.isnot(None),
                User.subscription_expires_at < current_time,
            )
            .all()
        )
        for user in expired_users:
            old_tier = user.tier
            user.tier = "free"
            user.quota_limit = 600
            user.subscription_expires_at = None
            downgraded += 1
            logger.info(
                f"Subscription expired: downgraded user {user.id} from {old_tier} -> free"
            )
        if downgraded > 0:
            db.commit()
    except Exception as exc:
        logger.error(f"Subscription expiry check failed: {exc}")
        db.rollback()
    finally:
        db.close()
    return downgraded


async def _scheduler_loop() -> None:
    logger.info("Monthly subscription scheduler started.")
    while True:
        try:
            await asyncio.to_thread(check_expired_subscriptions)
        except Exception as exc:
            logger.error(f"Scheduler loop error: {exc}")
        await asyncio.sleep(CHECK_INTERVAL_SECONDS)


def start_subscription_scheduler() -> None:
    global _scheduler_task
    if _scheduler_task is None or _scheduler_task.done():
        _scheduler_task = asyncio.create_task(_scheduler_loop())


async def stop_subscription_scheduler() -> None:
    global _scheduler_task
    if _scheduler_task and not _scheduler_task.done():
        _scheduler_task.cancel()
        try:
            await _scheduler_task
        except asyncio.CancelledError:
            pass
    _scheduler_task = None
