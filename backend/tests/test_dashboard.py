from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import create_app


def test_dashboard_overview() -> None:
    client = TestClient(create_app())
    email = f"u-{uuid4().hex[:8]}@example.com"
    r = client.post("/auth/register", json={"email": email, "password": "password123"})
    assert r.status_code == 200
    token = r.json()["access_token"]

    r = client.get("/dashboard/overview?hours=48&hitl_pending_limit=10&hitl_pending_offset=0", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    data = r.json()
    assert data["health"]["status"] == "ok"
    assert "counts" in data
    assert "recents" in data
    assert "token_usage_24h" in data
    assert data["range"]["hours"] == 48
    assert "failure_rates" in data
    assert "hitl_pending_queue" in data
