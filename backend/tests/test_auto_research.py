"""
Unit tests for auto research orchestration entry points.
"""

import pytest

from app.services import auto_research_agent as ara


async def test_run_auto_research_sets_progress_callback_and_returns_results(monkeypatch):
    captured = {"callback": None, "preferences": None, "job_id": None, "init_depth": None, "run_depth": None}

    class FakeAgent:
        def __init__(self, job_id=None, depth=None):
            captured["job_id"] = job_id
            captured["init_depth"] = depth

        def set_progress_callback(self, callback):
            captured["callback"] = callback

        async def research_from_preferences(self, preferences, depth=None):
            captured["preferences"] = preferences
            captured["run_depth"] = depth
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
    assert captured["init_depth"] == ara.ResearchDepth.STANDARD
    assert captured["callback"] is progress_callback
    assert captured["preferences"] == prefs
    assert captured["run_depth"] is None
    assert result["status"] == "ok"
    assert result["recommendations"][0]["destination"] == "Paris"


async def test_run_auto_research_without_callback(monkeypatch):
    state = {"callback_set": False}

    class FakeAgent:
        def __init__(self, job_id=None, depth=None):
            self.job_id = job_id
            self.depth = depth

        def set_progress_callback(self, callback):
            state["callback_set"] = True

        async def research_from_preferences(self, preferences, depth=None):
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
        def __init__(self, job_id=None, depth=None):
            self.job_id = job_id

        def set_progress_callback(self, callback):
            return None

        async def research_from_preferences(self, preferences, depth=None):
            raise RuntimeError("upstream research failed")

    monkeypatch.setattr(ara, "AutoResearchAgent", FakeAgent)

    with pytest.raises(RuntimeError, match="upstream research failed"):
        await ara.run_auto_research(
            preferences={"origin": "Berlin"},
            job_id="job_fail",
        )


async def test_run_auto_research_passes_explicit_depth(monkeypatch):
    captured = {"init_depth": None, "run_depth": None}

    class FakeAgent:
        def __init__(self, job_id=None, depth=None):
            captured["init_depth"] = depth

        def set_progress_callback(self, callback):
            return None

        async def research_from_preferences(self, preferences, depth=None):
            captured["run_depth"] = depth
            return {"status": "ok"}

    monkeypatch.setattr(ara, "AutoResearchAgent", FakeAgent)

    result = await ara.run_auto_research(
        preferences={"origin": "NYC"},
        depth=ara.ResearchDepth.DEEP,
    )

    assert result["status"] == "ok"
    assert captured["init_depth"] == ara.ResearchDepth.DEEP
    assert captured["run_depth"] == ara.ResearchDepth.DEEP


def test_suggest_depth_returns_deep_for_long_trips():
    depth = ara.AutoResearchAgent.suggest_depth(
        {
            "travel_start": "2026-06-01",
            "travel_end": "2026-07-01",
            "budget_level": "moderate",
        }
    )
    assert depth == ara.ResearchDepth.DEEP


def test_estimate_total_steps_respects_depth():
    quick = ara.AutoResearchAgent(depth=ara.ResearchDepth.QUICK)
    standard = ara.AutoResearchAgent(depth=ara.ResearchDepth.STANDARD)

    quick_steps = quick._estimate_total_steps(destination_count=2, has_origin=True, needs_suggestion=False)
    standard_steps = standard._estimate_total_steps(destination_count=2, has_origin=True, needs_suggestion=False)

    assert quick_steps > 0
    assert standard_steps > quick_steps
