from uuid import uuid4
from fastapi.testclient import TestClient

from app.main import create_app


def test_register_login_refresh_me() -> None:
    client = TestClient(create_app())

    email = f"u-{uuid4().hex[:8]}@example.com"
    r = client.post("/auth/register", json={"email": email, "password": "password123"})
    assert r.status_code == 200
    tokens = r.json()
    assert tokens["access_token"]
    assert tokens["refresh_token"]

    r = client.get("/auth/me", headers={"Authorization": f"Bearer {tokens['access_token']}"})
    assert r.status_code == 200
    me = r.json()
    assert me["email"] == email
    assert "user" in me["roles"]

    r = client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert r.status_code == 200
    refreshed = r.json()
    assert refreshed["access_token"]
    assert refreshed["refresh_token"]
    assert refreshed["refresh_token"] != tokens["refresh_token"]

    r = client.post("/auth/login", json={"email": email, "password": "password123"})
    assert r.status_code == 200

    r = client.post("/auth/login", json={"email": email, "password": "wrong"})
    assert r.status_code == 401
