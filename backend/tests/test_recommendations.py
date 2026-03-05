"""
Unit tests for AIRecommendationService recommendation pipeline behavior.
"""

from datetime import date
from types import SimpleNamespace

from app.models.destination import Destination
from app.models.user import Interest, TravelRequest, TravelStyle, UserPreferences
from app.services.ai_recommendation_service import AIRecommendationService


def _make_destination(dest_id: str, name: str) -> Destination:
    return Destination(
        id=dest_id,
        name=name,
        country="Testland",
        city=name,
        country_code="TS",
        coordinates={"lat": 10.0, "lng": 20.0},
    )


def _make_request(num_recommendations: int = 2) -> TravelRequest:
    return TravelRequest(
        origin="London",
        travel_start=date(2026, 6, 10),
        travel_end=date(2026, 6, 20),
        num_recommendations=num_recommendations,
        user_preferences=UserPreferences(
            budget_daily=150,
            budget_total=2000,
            travel_style=TravelStyle.MODERATE,
            interests=[Interest.CULTURE, Interest.FOOD],
            traveling_with="couple",
        ),
    )


async def test_generate_recommendations_sorts_and_limits(monkeypatch):
    service = AIRecommendationService()
    request = _make_request(num_recommendations=2)
    paris = _make_destination("paris_fr", "Paris")
    tokyo = _make_destination("tokyo_jp", "Tokyo")
    rome = _make_destination("rome_it", "Rome")

    # Force fallback path (no LLM client) and deterministic scoring.
    monkeypatch.setattr(service, "_get_client", lambda: None)

    score_map = {"paris_fr": 92.0, "tokyo_jp": 78.0, "rome_it": 86.0}

    def fake_score(destination, _preferences):
        return {
            "weather": 70,
            "affordability": 75,
            "visa": 85,
            "attractions": 88,
            "events": 60,
            "overall": score_map[destination.id],
        }

    monkeypatch.setattr("app.services.ai_recommendation_service.calculate_destination_score", fake_score)

    results = await service.generate_recommendations(request, [tokyo, paris, rome])

    assert len(results) == 2
    assert [d.id for d in results] == ["paris_fr", "rome_it"]
    assert all(isinstance(d.recommendation_reason, str) and d.recommendation_reason for d in results)


async def test_compare_destinations_returns_empty_without_llm(monkeypatch):
    service = AIRecommendationService()
    monkeypatch.setattr(service, "_get_client", lambda: None)

    request = _make_request()
    d1 = _make_destination("a", "Alpha")
    d2 = _make_destination("b", "Beta")

    comparison = await service.compare_destinations([d1, d2], request.user_preferences)
    assert comparison == ""


async def test_generate_recommendations_uses_llm_batch_when_client_available(monkeypatch):
    service = AIRecommendationService()
    request = _make_request(num_recommendations=2)
    d1 = _make_destination("alpha", "Alpha")
    d2 = _make_destination("beta", "Beta")

    monkeypatch.setattr(service, "_get_client", lambda: object())

    def fake_score(destination, _preferences):
        overall = 90.0 if destination.id == "alpha" else 80.0
        return {
            "weather": 60,
            "affordability": 70,
            "visa": 80,
            "attractions": 75,
            "events": 55,
            "overall": overall,
        }

    async def fake_batch(destinations, _preferences, _dates):
        return [f"AI reason for {d.name}" for d in destinations]

    monkeypatch.setattr("app.services.ai_recommendation_service.calculate_destination_score", fake_score)
    monkeypatch.setattr(service, "_generate_explanations_batch", fake_batch)

    results = await service.generate_recommendations(request, [d2, d1])
    assert [d.id for d in results] == ["alpha", "beta"]
    assert results[0].recommendation_reason == "AI reason for Alpha"
    assert results[1].recommendation_reason == "AI reason for Beta"


async def test_generate_recommendations_falls_back_when_batch_item_is_exception(monkeypatch):
    service = AIRecommendationService()
    request = _make_request(num_recommendations=2)
    d1 = _make_destination("alpha", "Alpha")
    d2 = _make_destination("beta", "Beta")

    monkeypatch.setattr(service, "_get_client", lambda: object())

    def fake_score(destination, _preferences):
        if destination.id == "alpha":
            return {
                "weather": 60,
                "affordability": 70,
                "visa": 80,
                "attractions": 75,
                "events": 55,
                "overall": 90.0,
            }
        return {
            "weather": 65,
            "affordability": 85,  # ensures deterministic fallback reason
            "visa": 70,
            "attractions": 60,
            "events": 40,
            "overall": 80.0,
        }

    async def fake_batch(_destinations, _preferences, _dates):
        return ["AI reason for Alpha", RuntimeError("model timeout")]

    monkeypatch.setattr("app.services.ai_recommendation_service.calculate_destination_score", fake_score)
    monkeypatch.setattr(service, "_generate_explanations_batch", fake_batch)

    results = await service.generate_recommendations(request, [d2, d1])
    assert [d.id for d in results] == ["alpha", "beta"]
    assert results[0].recommendation_reason == "AI reason for Alpha"
    assert isinstance(results[1].recommendation_reason, str)
    assert "Fits perfectly within your $150" in results[1].recommendation_reason


async def test_generate_single_explanation_falls_back_when_llm_raises(monkeypatch):
    service = AIRecommendationService()
    destination = _make_destination("paris_fr", "Paris")
    destination.overall_score = 88
    request = _make_request()

    class FailingCompletions:
        async def create(self, **_kwargs):
            raise RuntimeError("LLM unavailable")

    fake_client = SimpleNamespace(
        chat=SimpleNamespace(completions=FailingCompletions())
    )
    monkeypatch.setattr(service, "_get_client", lambda: fake_client)

    explanation = await service._generate_single_explanation(
        destination,
        request.user_preferences,
        (request.travel_start, request.travel_end),
    )

    assert isinstance(explanation, str)
    assert explanation


async def test_compare_destinations_uses_llm_when_available(monkeypatch):
    service = AIRecommendationService()
    request = _make_request()
    d1 = _make_destination("a", "Alpha")
    d2 = _make_destination("b", "Beta")
    d1.overall_score = 84
    d2.overall_score = 79

    class FakeCompletions:
        async def create(self, **_kwargs):
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content="Alpha is the stronger fit."))],
                usage=None,
            )

    fake_client = SimpleNamespace(chat=SimpleNamespace(completions=FakeCompletions()))
    monkeypatch.setattr(service, "_get_client", lambda: fake_client)

    comparison = await service.compare_destinations([d1, d2], request.user_preferences)
    assert comparison == "Alpha is the stronger fit."
