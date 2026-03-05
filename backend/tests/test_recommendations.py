"""
Unit tests for AIRecommendationService recommendation pipeline behavior.
"""

from datetime import date

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

