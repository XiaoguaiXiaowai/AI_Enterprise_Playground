from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def _dumps(obj: dict) -> str:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))


def _resolve_under_root(root: Path, raw: str) -> Path:
    p = Path(raw)
    if not p.is_absolute():
        p = (root / p).resolve()
    else:
        p = p.resolve()
    root_abs = root.resolve()
    if p == root_abs or root_abs in p.parents:
        return p
    raise ValueError("path_outside_root")


def _tool_list_dir(root: Path, args: dict) -> dict:
    raw = str(args.get("path") or ".")
    p = _resolve_under_root(root, raw)
    if not p.exists():
        raise FileNotFoundError("not_found")
    if not p.is_dir():
        raise ValueError("not_a_directory")
    entries = []
    for child in sorted(p.iterdir(), key=lambda x: x.name):
        entries.append({"name": child.name, "is_dir": child.is_dir()})
    return {"path": str(p), "entries": entries}


def _tool_read_file(root: Path, args: dict) -> dict:
    raw = str(args.get("path") or "")
    if not raw:
        raise ValueError("missing_path")
    p = _resolve_under_root(root, raw)
    if not p.exists():
        raise FileNotFoundError("not_found")
    if p.is_dir():
        raise ValueError("is_directory")
    max_bytes = int(args.get("max_bytes") or 200_000)
    data = p.read_bytes()
    truncated = len(data) > max_bytes
    if truncated:
        data = data[:max_bytes]
    try:
        text = data.decode("utf-8")
    except Exception:
        text = data.decode("utf-8", errors="replace")
    return {"path": str(p), "content": text, "truncated": truncated}


TOOLS = {
    "filesystem.list_dir": {
        "description": "List directory entries under a configured root.",
        "inputSchema": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
        },
        "handler": _tool_list_dir,
    },
    "filesystem.read_file": {
        "description": "Read a text file under a configured root.",
        "inputSchema": {
            "type": "object",
            "properties": {"path": {"type": "string"}, "max_bytes": {"type": "integer"}},
            "required": ["path"],
        },
        "handler": _tool_read_file,
    },
}


def main() -> None:
    root = Path(os.environ.get("MCP_FILESYSTEM_ROOT") or ".").resolve()
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
                        "serverInfo": {"name": "filesystem", "version": "0.1.0"},
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
                result = tool["handler"](root, args)
                out = {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {"content": [{"type": "text", "text": _dumps(result)}], "structured": result},
                }
                sys.stdout.write(_dumps(out) + "\n")
                sys.stdout.flush()
                continue
            raise ValueError("method_not_supported")
        except Exception as e:
            out = {
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {"code": -32000, "message": str(e)},
            }
            sys.stdout.write(_dumps(out) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
