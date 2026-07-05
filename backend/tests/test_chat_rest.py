from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import create_app


def _register_and_login(client: TestClient) -> str:
    email = f"u-{uuid4().hex[:8]}@example.com"
    r = client.post("/auth/register", json={"email": email, "password": "password123"})
    assert r.status_code == 200
    return r.json()["access_token"]


def test_chat_session_and_messages() -> None:
    client = TestClient(create_app())
    token = _register_and_login(client)

    r = client.post(
        "/chat/sessions",
        json={"title": "My chat"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    session_id = r.json()["id"]

    r = client.post(
        f"/chat/sessions/{session_id}/messages",
        json={"content": "hello", "model": "mock"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert r.json()["assistant_message"]["content"].startswith("Echo:")

    r = client.get(f"/chat/sessions/{session_id}/messages", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    msgs = r.json()
    assert len(msgs) == 2
    assert msgs[0]["role"] == "user"
    assert msgs[1]["role"] == "assistant"


def test_chat_versioned_api() -> None:
    client = TestClient(create_app())
    token = _register_and_login(client)
    r = client.post(
        "/api/v1/chat/sessions",
        json={"title": "V1 chat"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200

