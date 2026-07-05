from fastapi.testclient import TestClient

from app.main import create_app


def test_system_endpoints() -> None:
    client = TestClient(create_app())

    r = client.get("/")
    assert r.status_code == 200
    assert "name" in r.json()
    assert r.headers.get("X-Request-ID")

    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}
    assert r.headers.get("X-Request-ID")

    r = client.get("/version")
    assert r.status_code == 200
    assert "version" in r.json()
    assert r.headers.get("X-Request-ID")

    r = client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_request_id_passthrough() -> None:
    client = TestClient(create_app())
    r = client.get("/health", headers={"X-Request-ID": "rid-123"})
    assert r.status_code == 200
    assert r.headers.get("X-Request-ID") == "rid-123"


def test_rate_limit() -> None:
    client = TestClient(create_app())
    assert client.get("/rate-limited").status_code == 200
    assert client.get("/rate-limited").status_code == 200
    assert client.get("/rate-limited").status_code == 429
