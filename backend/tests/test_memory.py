from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import create_app


def _register(client: TestClient) -> str:
    r = client.post("/auth/register", json={"email": f"m-{uuid4().hex[:8]}@example.com", "password": "password123"})
    assert r.status_code == 200
    return r.json()["access_token"]


def test_memory_crud_and_recall() -> None:
    client = TestClient(create_app())
    token = _register(client)

    r = client.post(
        "/memory",
        json={"namespace": "chat:1", "memory_type": "short", "content": "I like pizza", "metadata": {"source": "test"}},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    mem_id = r.json()["id"]

    r = client.get(f"/memory/{mem_id}", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["metadata"]["source"] == "test"

    r = client.post(
        "/memory/recall",
        json={"namespace": "chat:1", "query": "pizza", "limit": 10},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert len(r.json()["memories"]) == 1

    r = client.patch(
        f"/memory/{mem_id}",
        json={"content": "I like sushi", "importance": 1.0},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert r.json()["content"] == "I like sushi"

    r = client.get("/memory/timeline", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert len(r.json()) >= 1

    r = client.delete(f"/memory/{mem_id}", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200


def test_memory_versioned_api() -> None:
    client = TestClient(create_app())
    token = _register(client)
    r = client.post(
        "/api/v1/memory",
        json={"namespace": "default", "memory_type": "long", "content": "Long term memory"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200

