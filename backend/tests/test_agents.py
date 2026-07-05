import sys
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import create_app


def _register_and_login(client: TestClient) -> str:
    email = f"u-{uuid4().hex[:8]}@example.com"
    r = client.post("/auth/register", json={"email": email, "password": "password123"})
    assert r.status_code == 200
    return r.json()["access_token"]


def _register_filesystem_server(client: TestClient, *, headers: dict) -> int:
    name = f"fs-{uuid4().hex[:6]}"
    r = client.post(
        "/mcp/servers",
        headers=headers,
        json={
            "name": name,
            "transport": "stdio",
            "server_type": "filesystem",
            "config": {
                "command": [sys.executable, "-m", "app.mcp_servers.filesystem_server"],
                "env": {"PYTHONPATH": "backend", "MCP_FILESYSTEM_ROOT": "."},
            },
        },
    )
    assert r.status_code == 200
    return r.json()["id"]


def test_agent_run_calls_mcp() -> None:
    client = TestClient(create_app())
    token = _register_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}
    _register_filesystem_server(client, headers=headers)

    r = client.post("/agents/runs", headers=headers, json={"goal": "Read README.md and summarize", "model": "mock"})
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "completed"
    assert "README.md" in (data["output_text"] or "")
    assert data["graph"]["nodes"]
    assert [s["agent"] for s in data["steps"]] == ["planner", "researcher", "coder", "reviewer"]

    r = client.get("/mcp/calls?limit=50", headers=headers)
    assert r.status_code == 200
    assert r.json()

