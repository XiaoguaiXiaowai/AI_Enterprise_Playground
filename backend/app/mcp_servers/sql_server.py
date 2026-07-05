from __future__ import annotations

import json
import os
import sys

from sqlalchemy import create_engine, text

from app.config.settings import get_settings


def _dumps(obj: dict) -> str:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))


def _is_readonly_sql(sql: str) -> bool:
    s = (sql or "").strip().lower()
    return s.startswith("select") or s.startswith("with") or s.startswith("pragma")


def _tool_query(engine, args: dict) -> dict:
    sql = str(args.get("sql") or "")
    if not sql:
        raise ValueError("missing_sql")
    if not _is_readonly_sql(sql):
        raise ValueError("only_readonly_sql_allowed")
    limit = int(args.get("limit") or 200)
    if limit < 1:
        limit = 1
    if limit > 500:
        limit = 500

    with engine.connect() as conn:
        rs = conn.execute(text(sql))
        cols = list(rs.keys())
        rows = []
        for i, row in enumerate(rs.mappings()):
            if i >= limit:
                break
            rows.append({k: row.get(k) for k in cols})
        return {"columns": cols, "rows": rows, "row_count": len(rows), "limit": limit}


TOOLS = {
    "sql.query": {
        "description": "Run a read-only SQL query against the application database.",
        "inputSchema": {
            "type": "object",
            "properties": {"sql": {"type": "string"}, "limit": {"type": "integer"}},
            "required": ["sql"],
        },
        "handler": _tool_query,
    }
}


def main() -> None:
    url = os.environ.get("MCP_DATABASE_URL") or get_settings().database_url
    engine = create_engine(url, future=True)

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except Exception:
            continue
        if not isinstance(msg, dict):
            continue
        method = msg.get("method")
        msg_id = msg.get("id")
        params = msg.get("params") if isinstance(msg.get("params"), dict) else {}
        if not isinstance(msg_id, int) or not isinstance(method, str):
            continue

        try:
            if method == "initialize":
                out = {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "protocolVersion": str(params.get("protocolVersion") or "unknown"),
                        "serverInfo": {"name": "sql", "version": "0.1.0"},
                        "capabilities": {"tools": {}},
                    },
                }
                sys.stdout.write(_dumps(out) + "\n")
                sys.stdout.flush()
                continue
            if method == "tools/list":
                tools = []
                for name, t in TOOLS.items():
                    tools.append({"name": name, "description": t["description"], "inputSchema": t["inputSchema"]})
                out = {"jsonrpc": "2.0", "id": msg_id, "result": {"tools": tools}}
                sys.stdout.write(_dumps(out) + "\n")
                sys.stdout.flush()
                continue
            if method == "tools/call":
                tool_name = str(params.get("name") or "")
                args = params.get("arguments") if isinstance(params.get("arguments"), dict) else {}
                tool = TOOLS.get(tool_name)
                if not tool:
                    raise ValueError("tool_not_found")
                result = tool["handler"](engine, args)
                out = {"jsonrpc": "2.0", "id": msg_id, "result": {"content": [{"type": "text", "text": _dumps(result)}], "structured": result}}
                sys.stdout.write(_dumps(out) + "\n")
                sys.stdout.flush()
                continue
            raise ValueError("method_not_supported")
        except Exception as e:
            out = {"jsonrpc": "2.0", "id": msg_id, "error": {"code": -32000, "message": str(e)}}
            sys.stdout.write(_dumps(out) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()

