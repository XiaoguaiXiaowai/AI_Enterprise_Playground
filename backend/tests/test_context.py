from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import create_app


def _register(client: TestClient) -> str:
    r = client.post("/auth/register", json={"email": f"c-{uuid4().hex[:8]}@example.com", "password": "password123"})
    assert r.status_code == 200
    return r.json()["access_token"]


def test_context_current_sanitizes_headers_and_has_request_id() -> None:
    client = TestClient(create_app())
    r = client.get("/context/current", headers={"Authorization": "Bearer test", "X-Request-ID": "rid-123"})
    assert r.status_code == 200
    data = r.json()
    assert data["request_id"] == "rid-123"
    assert "authorization" not in {k.lower() for k in data["headers"].keys()}


def test_context_events_list() -> None:
    client = TestClient(create_app())
    token = _register(client)

    r = client.get("/health", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200

    r = client.get("/context/events", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    events = r.json()["events"]
    assert len(events) >= 1
    assert any(e["event_type"] == "http_request" for e in events)

