"""
Tests for retention cleanup and auto-research rate limiting.
"""

from datetime import datetime, timedelta, timezone

from app.api import auto_research_routes
from app.config import get_settings
from app.database.models import AnalyticsEvent, PersistedChatSession
from app.services import retention_service


def test_run_retention_cleanup_deletes_expired_and_old_records(db_session, monkeypatch):
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    old_chat = PersistedChatSession(
        session_id="old-chat",
        payload="{}",
        planning_stage="discover",
        updated_at=now - timedelta(days=120),
        expires_at=now - timedelta(days=1),
    )
    fresh_chat = PersistedChatSession(
        session_id="fresh-chat",
        payload="{}",
        planning_stage="discover",
        updated_at=now - timedelta(days=1),
        expires_at=now + timedelta(days=2),
    )
    old_event = AnalyticsEvent(
        event_name="recommendation_accepted",
        created_at=now - timedelta(days=200),
    )
    fresh_event = AnalyticsEvent(
        event_name="recommendation_accepted",
        created_at=now - timedelta(days=1),
    )

    db_session.add_all([old_chat, fresh_chat, old_event, fresh_event])
    db_session.commit()

    # Ensure cleanup uses the test DB session from fixture.
    monkeypatch.setattr(retention_service, "SessionLocal", lambda: db_session)

    settings = get_settings()
    original_chat_days = settings.chat_retention_days
    original_analytics_days = settings.analytics_retention_days
    try:
        settings.chat_retention_days = 30
        settings.analytics_retention_days = 90
        result = retention_service.run_retention_cleanup()
    finally:
        settings.chat_retention_days = original_chat_days
        settings.analytics_retention_days = original_analytics_days

    assert result["deleted_chat_sessions"] >= 1
    assert result["deleted_analytics_events"] >= 1

    remaining_chat_ids = {s.session_id for s in db_session.query(PersistedChatSession).all()}
    assert "old-chat" not in remaining_chat_ids
    assert "fresh-chat" in remaining_chat_ids

    remaining_events = db_session.query(AnalyticsEvent).all()
    assert len(remaining_events) == 1
    assert remaining_events[0].created_at >= now - timedelta(days=2)


def test_auto_research_start_rate_limited(client, monkeypatch):
    async def _noop_run_research_job(*args, **kwargs):
        return None

    # Keep endpoint fast/deterministic.
    monkeypatch.setattr(auto_research_routes, "_run_research_job", _noop_run_research_job)

    payload = {
        "origin": "London",
        "destinations": ["Paris"],
        "travel_start": "2026-06-10",
        "travel_end": "2026-06-15",
        "budget_level": "moderate",
        "interests": ["food"],
    }

    statuses = []
    for _ in range(62):
        response = client.post("/api/v1/auto-research/start", json=payload)
        statuses.append(response.status_code)

    # Limiter is 60/minute; repeated calls should trigger 429.
    assert 429 in statuses
