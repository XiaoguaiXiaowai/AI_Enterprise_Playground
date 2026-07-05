import sys
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import create_app


def _register_and_login(client: TestClient) -> str:
    email = f"u-{uuid4().hex[:8]}@example.com"
    r = client.post("/auth/register", json={"email": email, "password": "password123"})
    assert r.status_code == 200
    return r.json()["access_token"]


def test_agent_run_pauses_on_hitl_then_resume_completes() -> None:
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

    r = client.post("/agents/runs", headers=headers, json={"goal": "Read README.md and summarize", "model": "mock"})
    assert r.status_code == 200
    run = r.json()
    assert run["status"] == "paused"
    assert run["waiting_hitl_request_id"]
    hitl_request_id = run["waiting_hitl_request_id"]
    run_id = run["id"]

    r = client.post(f"/hitl/requests/{hitl_request_id}/approve", headers=headers, json={"reason": "ok"})
    assert r.status_code == 200
    assert r.json()["status"] == "approved"

    r = client.post(f"/agents/runs/{run_id}/resume", headers=headers)
    assert r.status_code == 200
    resumed = r.json()
    assert resumed["status"] == "completed"
    assert "README.md" in (resumed["output_text"] or "")
    assert [s["agent"] for s in resumed["steps"]] == ["planner", "researcher", "coder", "reviewer"]

