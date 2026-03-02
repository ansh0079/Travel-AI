"""
Tests for enhanced chat endpoints and contracts.
"""

from fastapi.testclient import TestClient


class TestChatRoutes:
    def test_chat_message_creates_session(self, client: TestClient):
        response = client.post(
            "/api/v1/chat/message",
            json={"message": "I want a beach trip to Bali on a moderate budget"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data
        assert isinstance(data.get("response"), str)
        assert "extracted_preferences" in data
        assert "is_ready_for_recommendations" in data
        assert "suggestions" in data
        assert "planning_stage" in data

        session_id = data["session_id"]
        session_response = client.get(f"/api/v1/chat/session/{session_id}")
        assert session_response.status_code == 200
        session_data = session_response.json()
        assert session_data["session_id"] == session_id
        assert session_data["message_count"] >= 2
        assert "planning_stage" in session_data
        assert "planning_data" in session_data

    def test_chat_stream_returns_sse_payload(self, client: TestClient):
        response = client.post(
            "/api/v1/chat/message/stream",
            json={"message": "Help me plan a city trip to Tokyo"},
        )
        assert response.status_code == 200
        assert "data:" in response.text

    def test_chat_action_uses_json_body_contract(self, client: TestClient):
        bad_payload = client.post("/api/v1/chat/action", json={"session_id": "abc"})
        assert bad_payload.status_code == 422

        response = client.post(
            "/api/v1/chat/action",
            json={
                "session_id": "missing_session",
                "action_type": "get_weather",
                "params": {"location": "Paris"},
            },
        )
        assert response.status_code == 500
        assert "Session not found" in response.json()["detail"]

    def test_user_bound_session_is_not_accessible_anonymously(
        self, client: TestClient, auth_token: str
    ):
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = client.post(
            "/api/v1/chat/message",
            json={"message": "I am planning a trip to Rome"},
            headers=headers,
        )
        assert response.status_code == 200
        session_id = response.json()["session_id"]

        anonymous_get = client.get(f"/api/v1/chat/session/{session_id}")
        assert anonymous_get.status_code == 403

    def test_pipeline_and_ranking_workflow(self, client: TestClient):
        create = client.post(
            "/api/v1/chat/message",
            json={"message": "I want to travel to Bali from London with budget constraints"},
        )
        assert create.status_code == 200
        session_id = create.json()["session_id"]

        advance = client.post(f"/api/v1/chat/pipeline/{session_id}/advance", json={})
        assert advance.status_code == 200
        assert "planning_stage" in advance.json()

        planning = client.put(
            f"/api/v1/chat/pipeline/{session_id}",
            json={"planning_data": {"shortlist": ["Bali", "Bangkok"]}},
        )
        assert planning.status_code == 200
        assert "planning_data" in planning.json()

        ranking = client.post(
            "/api/v1/chat/recommendations/rank",
            json={
                "session_id": session_id,
                "candidates": ["Bali", "London", "Bangkok"],
                "constraints": {"budget_level": "budget", "visa_preference": "visa_free"},
            },
        )
        assert ranking.status_code == 200
        ranked = ranking.json()["ranked_destinations"]
        assert isinstance(ranked, list)
        assert len(ranked) >= 1
        assert "reasons" in ranked[0]

        feedback = client.post(
            "/api/v1/chat/recommendations/feedback",
            json={"session_id": session_id, "destination": "Bali", "feedback": 1},
        )
        assert feedback.status_code == 200
        assert feedback.json()["destination"] == "Bali"
