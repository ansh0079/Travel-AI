"""
Minimal smoke coverage for core app availability and chat flow.
"""

from fastapi.testclient import TestClient


def test_health_smoke(client: TestClient):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "healthy"
    assert "timestamp" in payload


def test_chat_smoke_roundtrip(client: TestClient):
    send = client.post(
        "/api/v1/chat/message",
        json={"message": "Plan a short budget trip to Lisbon from London"},
    )
    assert send.status_code == 200
    body = send.json()
    assert "session_id" in body
    assert isinstance(body.get("response"), str)
    assert body["response"]

    session_id = body["session_id"]
    fetch = client.get(f"/api/v1/chat/session/{session_id}")
    assert fetch.status_code == 200
    session = fetch.json()
    assert session["session_id"] == session_id
    assert session["message_count"] >= 2
