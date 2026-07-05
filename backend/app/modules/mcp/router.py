from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.auth import User
from app.modules.auth.dependencies import get_current_user
from app.modules.mcp.schemas import (
    McpServerCreateRequest,
    McpServerResponse,
    McpToolCallAuditResponse,
    McpToolCallRequest,
    McpToolCallResponse,
    McpToolDescriptor,
    McpToolsListResponse,
)
from app.modules.mcp.service import (
    call_tool,
    create_server,
    delete_server,
    list_servers,
    list_tool_calls,
    list_tools,
)

router = APIRouter(prefix="/mcp", tags=["mcp"])


@router.post("/servers", response_model=McpServerResponse)
def create_mcp_server(
    payload: McpServerCreateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> McpServerResponse:
    try:
        server = create_server(
            db,
            user_id=user.id,
            name=payload.name,
            transport=payload.transport,
            server_type=payload.server_type,
            config=payload.config,
        )
    except ValueError as e:
        if str(e) == "server_name_already_exists":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="server_name_already_exists")
        raise
    return McpServerResponse(
        id=server.id,
        name=server.name,
        transport=server.transport,
        server_type=server.server_type,
        is_enabled=server.is_enabled,
        config=payload.config,
    )


@router.get("/servers", response_model=list[McpServerResponse])
def list_mcp_servers(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[McpServerResponse]:
    rows = list_servers(db, user_id=user.id)
    out: list[McpServerResponse] = []
    for s in rows:
        out.append(
            McpServerResponse(
                id=s.id,
                name=s.name,
                transport=s.transport,
                server_type=s.server_type,
                is_enabled=s.is_enabled,
                config={},
            )
        )
    return out


@router.delete("/servers/{server_id}")
def delete_mcp_server(
    server_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    ok = delete_server(db, user_id=user.id, server_id=server_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="server_not_found")
    return {"status": "deleted"}


@router.get("/servers/{server_id}/tools", response_model=McpToolsListResponse)
async def get_tools(
    server_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> McpToolsListResponse:
    try:
        tools = await list_tools(db, user_id=user.id, server_id=server_id)
    except ValueError as e:
        if str(e) == "server_not_found":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="server_not_found")
        raise
    normalized: list[McpToolDescriptor] = []
    for t in tools:
        normalized.append(
            McpToolDescriptor(
                name=str(t.get("name") or ""),
                description=str(t.get("description") or ""),
                input_schema=t.get("inputSchema") if isinstance(t.get("inputSchema"), dict) else {},
            )
        )
    return McpToolsListResponse(server_id=server_id, tools=normalized)


@router.post("/servers/{server_id}/tools/{tool_name}", response_model=McpToolCallResponse)
async def call_tool_endpoint(
    request: Request,
    server_id: int,
    tool_name: str,
    payload: McpToolCallRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> McpToolCallResponse:
    request_id = getattr(request.state, "request_id", None)
    try:
        result = await call_tool(
            db,
            user_id=user.id,
            server_id=server_id,
            tool_name=tool_name,
            arguments=payload.arguments,
            request_id=request_id,
        )
    except ValueError as e:
        if str(e) == "server_not_found":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="server_not_found")
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"error": "mcp_call_failed", "message": str(e)})
    return McpToolCallResponse(server_id=server_id, tool_name=tool_name, result=result if isinstance(result, dict) else {"result": result})


@router.get("/calls", response_model=list[McpToolCallAuditResponse])
def list_calls(
    limit: int = 50,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[McpToolCallAuditResponse]:
    rows = list_tool_calls(db, user_id=user.id, limit=limit)
    out: list[McpToolCallAuditResponse] = []
    for c in rows:
        out.append(
            McpToolCallAuditResponse(
                id=c.id,
                server_id=c.server_id,
                tool_name=c.tool_name,
                status=c.status,
                duration_ms=c.duration_ms,
                error_message=c.error_message,
                request_id=c.request_id,
            )
        )
    return out

