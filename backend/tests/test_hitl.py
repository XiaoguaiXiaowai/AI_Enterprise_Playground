import sys
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import create_app


def _register_and_login(client: TestClient) -> str:
    email = f"u-{uuid4().hex[:8]}@example.com"
    r = client.post("/auth/register", json={"email": email, "password": "password123"})
    assert r.status_code == 200
    return r.json()["access_token"]


def test_hitl_mcp_tool_call_resume() -> None:
    client = TestClient(create_app())
    token = _register_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}

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
                "requires_approval": True,
            },
        },
    )
    assert r.status_code == 200
    server_id = r.json()["id"]

    r = client.post(
        f"/mcp/servers/{server_id}/tools/filesystem.read_file",
        headers=headers,
        json={"arguments": {"path": "README.md", "max_bytes": 10000}},
    )
    assert r.status_code == 409
    hitl_request_id = r.json()["detail"]["hitl_request_id"]

    r = client.get(f"/hitl/requests/{hitl_request_id}", headers=headers)
    assert r.status_code == 200
    assert r.json()["status"] == "pending"

    r = client.post(f"/hitl/requests/{hitl_request_id}/approve", headers=headers, json={"reason": "ok"})
    assert r.status_code == 200
    assert r.json()["status"] == "approved"

    r = client.post(f"/hitl/requests/{hitl_request_id}/resume", headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert data["execution_status"] == "ok"
    assert data["executed_at"]
    assert "AI Enterprise Playground" in data["result"]["structured"]["content"]

    r = client.get("/mcp/calls?limit=20", headers=headers)
    assert r.status_code == 200
    assert r.json()

