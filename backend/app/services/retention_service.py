"""
Data retention cleanup utilities for chat sessions and analytics events.
"""

from datetime import datetime, timedelta
import asyncio
from sqlalchemy import and_, or_

from app.config import get_settings
from app.database.connection import SessionLocal
from app.database.models import PersistedChatSession, AnalyticsEvent
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


def run_retention_cleanup() -> dict:
    """
    Delete data older than configured retention windows.
    Returns deletion counters for logging/monitoring.
    """
    settings = get_settings()
    now = datetime.utcnow()
    chat_cutoff = now - timedelta(days=max(1, int(settings.chat_retention_days)))
    analytics_cutoff = now - timedelta(days=max(1, int(settings.analytics_retention_days)))

    db = SessionLocal()
    try:
        chat_filter = or_(
            and_(PersistedChatSession.expires_at.is_not(None), PersistedChatSession.expires_at < now),
            PersistedChatSession.updated_at < chat_cutoff,
        )
        deleted_chat = (
            db.query(PersistedChatSession)
            .filter(chat_filter)
            .delete(synchronize_session=False)
        )

        deleted_analytics = (
            db.query(AnalyticsEvent)
            .filter(AnalyticsEvent.created_at < analytics_cutoff)
            .delete(synchronize_session=False)
        )

        db.commit()
        result = {
            "deleted_chat_sessions": int(deleted_chat or 0),
            "deleted_analytics_events": int(deleted_analytics or 0),
            "chat_cutoff": chat_cutoff.isoformat(),
            "analytics_cutoff": analytics_cutoff.isoformat(),
        }
        logger.info("Retention cleanup complete", **result)
        return result
    except Exception as e:
        db.rollback()
        logger.error("Retention cleanup failed", error=str(e), exc_info=True)
        return {
            "deleted_chat_sessions": 0,
            "deleted_analytics_events": 0,
            "error": str(e),
        }
    finally:
        db.close()


async def periodic_retention_cleanup(interval_hours: int):
    """
    Periodically run retention cleanup until task cancellation.
    """
    interval_seconds = max(1, int(interval_hours)) * 3600
    while True:
        await asyncio.to_thread(run_retention_cleanup)
        await asyncio.sleep(interval_seconds)

