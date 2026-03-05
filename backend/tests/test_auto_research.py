"""
Unit tests for auto research orchestration entry points.
"""

import pytest

from app.services import auto_research_agent as ara


async def test_run_auto_research_sets_progress_callback_and_returns_results(monkeypatch):
    captured = {"callback": None, "preferences": None, "job_id": None}

    class FakeAgent:
        def __init__(self, job_id=None):
            captured["job_id"] = job_id

        def set_progress_callback(self, callback):
            captured["callback"] = callback

        async def research_from_preferences(self, preferences):
            captured["preferences"] = preferences
            return {"status": "ok", "recommendations": [{"destination": "Paris"}]}

    monkeypatch.setattr(ara, "AutoResearchAgent", FakeAgent)

    async def progress_callback(_data):
        return None

    prefs = {"origin": "London", "interests": ["food", "culture"]}
    result = await ara.run_auto_research(
        preferences=prefs,
        job_id="job_123",
        progress_callback=progress_callback,
    )

    assert captured["job_id"] == "job_123"
    assert captured["callback"] is progress_callback
    assert captured["preferences"] == prefs
    assert result["status"] == "ok"
    assert result["recommendations"][0]["destination"] == "Paris"


async def test_run_auto_research_without_callback(monkeypatch):
    state = {"callback_set": False}

    class FakeAgent:
        def __init__(self, job_id=None):
            self.job_id = job_id

        def set_progress_callback(self, callback):
            state["callback_set"] = True

        async def research_from_preferences(self, preferences):
            return {"job_id": self.job_id, "preferences": preferences, "status": "ok"}

    monkeypatch.setattr(ara, "AutoResearchAgent", FakeAgent)

    result = await ara.run_auto_research(
        preferences={"origin": "NYC"},
        job_id="job_no_cb",
    )

    assert result["status"] == "ok"
    assert result["job_id"] == "job_no_cb"
    assert result["preferences"]["origin"] == "NYC"
    assert state["callback_set"] is False


async def test_run_auto_research_propagates_agent_exceptions(monkeypatch):
    class FakeAgent:
        def __init__(self, job_id=None):
            self.job_id = job_id

        def set_progress_callback(self, callback):
            return None

        async def research_from_preferences(self, preferences):
            raise RuntimeError("upstream research failed")

    monkeypatch.setattr(ara, "AutoResearchAgent", FakeAgent)

    with pytest.raises(RuntimeError, match="upstream research failed"):
        await ara.run_auto_research(
            preferences={"origin": "Berlin"},
            job_id="job_fail",
        )
