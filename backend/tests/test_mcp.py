import sys
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import create_app


def _register_and_login(client: TestClient) -> str:
    email = f"u-{uuid4().hex[:8]}@example.com"
    r = client.post("/auth/register", json={"email": email, "password": "password123"})
    assert r.status_code == 200
    return r.json()["access_token"]


def test_mcp_stdio_filesystem_and_sql() -> None:
    client = TestClient(create_app())
    token = _register_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}

    fs_name = f"fs-{uuid4().hex[:6]}"
    r = client.post(
        "/mcp/servers",
        headers=headers,
        json={
            "name": fs_name,
            "transport": "stdio",
            "server_type": "filesystem",
            "config": {
                "command": [sys.executable, "-m", "app.mcp_servers.filesystem_server"],
                "env": {"PYTHONPATH": "backend", "MCP_FILESYSTEM_ROOT": "."},
            },
        },
    )
    assert r.status_code == 200
    fs_server_id = r.json()["id"]

    r = client.get(f"/mcp/servers/{fs_server_id}/tools", headers=headers)
    assert r.status_code == 200
    tools = {t["name"] for t in r.json()["tools"]}
    assert "filesystem.list_dir" in tools
    assert "filesystem.read_file" in tools

    r = client.post(
        f"/mcp/servers/{fs_server_id}/tools/filesystem.list_dir",
        headers=headers,
        json={"arguments": {"path": "."}},
    )
    assert r.status_code == 200
    structured = r.json()["result"]["structured"]
    assert structured["entries"]

    r = client.post(
        f"/mcp/servers/{fs_server_id}/tools/filesystem.read_file",
        headers=headers,
        json={"arguments": {"path": "README.md", "max_bytes": 50_000}},
    )
    assert r.status_code == 200
    structured = r.json()["result"]["structured"]
    assert "AI Enterprise Playground" in structured["content"]

    sql_name = f"sql-{uuid4().hex[:6]}"
    r = client.post(
        "/mcp/servers",
        headers=headers,
        json={
            "name": sql_name,
            "transport": "stdio",
            "server_type": "sql",
            "config": {
                "command": [sys.executable, "-m", "app.mcp_servers.sql_server"],
                "env": {"PYTHONPATH": "backend", "MCP_DATABASE_URL": "sqlite:///./app.db"},
            },
        },
    )
    assert r.status_code == 200
    sql_server_id = r.json()["id"]

    r = client.get(f"/mcp/servers/{sql_server_id}/tools", headers=headers)
    assert r.status_code == 200
    tools = {t["name"] for t in r.json()["tools"]}
    assert "sql.query" in tools

    r = client.post(
        f"/mcp/servers/{sql_server_id}/tools/sql.query",
        headers=headers,
        json={"arguments": {"sql": "SELECT 1 as x", "limit": 10}},
    )
    assert r.status_code == 200
    structured = r.json()["result"]["structured"]
    assert structured["rows"][0]["x"] == 1

    r = client.get("/mcp/calls?limit=20", headers=headers)
    assert r.status_code == 200
    assert r.json()

