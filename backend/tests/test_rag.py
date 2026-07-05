from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import create_app


def _register(client: TestClient) -> str:
    r = client.post("/auth/register", json={"email": f"r-{uuid4().hex[:8]}@example.com", "password": "password123"})
    assert r.status_code == 200
    return r.json()["access_token"]


def test_rag_upload_search_chunk_delete() -> None:
    client = TestClient(create_app())
    token = _register(client)

    content = b"Hello world.\nThis is a test document.\nWe talk about pizza and sushi.\n"
    r = client.post(
        "/rag/upload",
        files={"file": ("doc.txt", content, "text/plain")},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    doc_id = r.json()["document_id"]
    assert r.json()["chunks"] >= 1

    r = client.get("/rag/documents", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert any(d["id"] == doc_id for d in r.json())

    r = client.post(
        "/rag/search",
        json={"query": "pizza", "top_k": 3},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    citations = r.json()["citations"]
    assert len(citations) >= 1
    chunk_id = citations[0]["chunk_id"]

    r = client.get(f"/rag/chunks/{chunk_id}", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert "pizza" in r.json()["content"].lower()

    r = client.post(
        "/rag/answer",
        json={"query": "what do we talk about?", "top_k": 3},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert r.json()["citations"]

    r = client.delete(f"/rag/documents/{doc_id}", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200

