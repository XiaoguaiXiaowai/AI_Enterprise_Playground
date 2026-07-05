from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config.settings import get_settings
from app.models.mcp import McpServer, McpToolCall
from app.modules.context.service import log_event
from app.modules.hitl.errors import HitlPendingError
from app.modules.hitl.service import create_mcp_tool_call_request, mark_executed
from app.modules.mcp.transports.stdio import StdioMcpTransport
from app.modules.mcp.transports.streamable_http import StreamableHttpMcpTransport


def _loads_json(value: str) -> dict:
    try:
        data = json.loads(value or "{}")
        if isinstance(data, dict):
            return data
        return {}
    except Exception:
        return {}


def _dumps_json(value: dict) -> str:
    return json.dumps(value or {}, ensure_ascii=False, separators=(",", ":"))


def _requires_hitl_approval(*, server: McpServer, tool_name: str) -> tuple[bool, str | None]:
    config = _loads_json(server.config_json)
    if bool(config.get("requires_approval")):
        reason = config.get("approval_reason")
        return True, str(reason) if reason else None
    name = (tool_name or "").lower()
    if any(x in name for x in ["write", "delete", "remove", "exec", "update", "patch", "post", "put"]):
        return True, "high_risk_tool"
    if server.server_type in {"github", "browser"}:
        return True, "high_risk_server"
    return False, None


def create_server(
    db: Session,
    *,
    user_id: int,
    name: str,
    transport: str,
    server_type: str,
    config: dict,
) -> McpServer:
    server = McpServer(
        user_id=user_id,
        name=name,
        transport=transport,
        server_type=server_type,
        config_json=_dumps_json(config),
        is_enabled=True,
    )
    db.add(server)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ValueError("server_name_already_exists")
    db.refresh(server)
    return server


def list_servers(db: Session, *, user_id: int) -> list[McpServer]:
    stmt = select(McpServer).where(McpServer.user_id == user_id).order_by(McpServer.id.desc())
    return list(db.execute(stmt).scalars().all())


def get_server(db: Session, *, user_id: int, server_id: int) -> McpServer | None:
    server = db.get(McpServer, server_id)
    if not server or server.user_id != user_id:
        return None
    return server


def delete_server(db: Session, *, user_id: int, server_id: int) -> bool:
    server = get_server(db, user_id=user_id, server_id=server_id)
    if not server:
        return False
    db.delete(server)
    db.commit()
    return True


async def list_tools(
    db: Session,
    *,
    user_id: int,
    server_id: int,
) -> list[dict]:
    server = get_server(db, user_id=user_id, server_id=server_id)
    if not server or not server.is_enabled:
        raise ValueError("server_not_found")
    result, _ = await _call_mcp(db, user_id=user_id, server=server, method="tools/list", params={}, request_id=None)
    tools = result.get("tools")
    if isinstance(tools, list):
        return [t for t in tools if isinstance(t, dict)]
    return []


async def call_tool(
    db: Session,
    *,
    user_id: int,
    server_id: int,
    tool_name: str,
    arguments: dict,
    request_id: str | None,
    bypass_hitl: bool = False,
    hitl_request_id: int | None = None,
) -> dict:
    server = get_server(db, user_id=user_id, server_id=server_id)
    if not server or not server.is_enabled:
        raise ValueError("server_not_found")
    if not bypass_hitl:
        required, reason = _requires_hitl_approval(server=server, tool_name=tool_name)
        if required:
            req = create_mcp_tool_call_request(
                db,
                user_id=user_id,
                request_id=request_id,
                server_id=server.id,
                tool_name=tool_name,
                arguments=arguments or {},
                reason=reason,
            )
            raise HitlPendingError(req.id)
    try:
        result, call_id = await _call_mcp(
            db,
            user_id=user_id,
            server=server,
            method="tools/call",
            params={"name": tool_name, "arguments": arguments or {}},
            request_id=request_id,
            tool_name=tool_name,
            input_payload={"arguments": arguments or {}},
        )
        if hitl_request_id is not None:
            mark_executed(
                db,
                hitl_request_id=hitl_request_id,
                execution_status="ok",
                result=result,
                error=None,
                tool_call_id=call_id,
            )
        return result
    except Exception as e:
        if hitl_request_id is not None:
            try:
                mark_executed(
                    db,
                    hitl_request_id=hitl_request_id,
                    execution_status="error",
                    result=None,
                    error=str(e),
                    tool_call_id=None,
                )
            except Exception:
                pass
        raise


def list_tool_calls(db: Session, *, user_id: int, limit: int = 50) -> list[McpToolCall]:
    stmt = select(McpToolCall).where(McpToolCall.user_id == user_id).order_by(McpToolCall.id.desc()).limit(limit)
    return list(db.execute(stmt).scalars().all())


async def _call_mcp(
    db: Session,
    *,
    user_id: int,
    server: McpServer,
    method: str,
    params: dict,
    request_id: str | None,
    tool_name: str | None = None,
    input_payload: dict | None = None,
) -> tuple[dict, int]:
    settings = get_settings()
    config = _loads_json(server.config_json)

    call = McpToolCall(
        user_id=user_id,
        server_id=server.id,
        request_id=request_id,
        tool_name=tool_name or method,
        status="ok",
        input_json=_dumps_json(input_payload or params or {}),
        output_json="{}",
        duration_ms=0,
    )
    db.add(call)
    db.commit()
    db.refresh(call)

    try:
        result, duration_ms = await _request_via_transport(
            transport=server.transport,
            config=config,
            method=method,
            params={
                **params,
                "clientInfo": {"name": settings.app_name, "version": settings.version},
                "protocolVersion": "2025-11-25",
            }
            if method == "initialize"
            else params,
        )
        call.duration_ms = duration_ms
        call.output_json = _dumps_json(result if isinstance(result, dict) else {"result": result})
        db.add(call)
        db.commit()
        if request_id:
            log_event(
                db,
                request_id=request_id,
                user_id=user_id,
                event_type="mcp_tool_call",
                data={"server_id": server.id, "name": server.name, "transport": server.transport, "method": method, "tool_name": tool_name},
            )
        out = result if isinstance(result, dict) else {"result": result}
        return out, int(call.id)
    except Exception as e:
        call.status = "error"
        call.error_message = str(e)
        call.output_json = "{}"
        db.add(call)
        db.commit()
        if request_id:
            log_event(
                db,
                request_id=request_id,
                user_id=user_id,
                event_type="mcp_tool_call_failed",
                data={"server_id": server.id, "name": server.name, "transport": server.transport, "method": method, "tool_name": tool_name, "error": str(e)},
            )
        raise


async def _request_via_transport(*, transport: str, config: dict, method: str, params: dict) -> tuple[dict, int]:
    settings = get_settings()
    init_params = {
        "protocolVersion": "2025-11-25",
        "clientInfo": {"name": settings.app_name, "version": settings.version},
        "capabilities": {"tools": {}},
    }
    t = (transport or "").lower()
    if t == "stdio":
        command = config.get("command")
        if not isinstance(command, list) or not all(isinstance(x, str) and x for x in command):
            raise ValueError("invalid_stdio_command")
        env = config.get("env")
        if env is not None and not isinstance(env, dict):
            raise ValueError("invalid_stdio_env")
        cwd = config.get("cwd")
        if cwd is not None and not isinstance(cwd, str):
            raise ValueError("invalid_stdio_cwd")
        async with StdioMcpTransport(command=command, env={k: str(v) for k, v in (env or {}).items()}, cwd=cwd) as tr:
            await tr.request(method="initialize", params=init_params)
            return await tr.timed_request(method=method, params=params)

    if t in {"http", "streamable_http", "streamable-http", "sse"}:
        url = config.get("url")
        if not isinstance(url, str) or not url:
            raise ValueError("invalid_http_url")
        headers = config.get("headers")
        if headers is not None and not isinstance(headers, dict):
            raise ValueError("invalid_http_headers")
        async with StreamableHttpMcpTransport(url=url, headers={k: str(v) for k, v in (headers or {}).items()}) as tr:
            await tr.request(method="initialize", params=init_params)
            return await tr.timed_request(method=method, params=params)

    raise ValueError("unsupported_transport")
