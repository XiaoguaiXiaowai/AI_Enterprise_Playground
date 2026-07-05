from __future__ import annotations

import json
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.audit import AuditLog
from app.models.hitl import HitlRequest
from app.modules.context.service import log_event


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _loads(value: str) -> dict:
    try:
        data = json.loads(value or "{}")
        if isinstance(data, dict):
            return data
        return {}
    except Exception:
        return {}


def _dumps(value: dict) -> str:
    return json.dumps(value or {}, ensure_ascii=False, separators=(",", ":"))


def _audit(
    db: Session,
    *,
    user_id: int | None,
    request_id: str | None,
    action: str,
    target_type: str,
    target_id: int | None,
    data: dict,
) -> None:
    row = AuditLog(user_id=user_id, request_id=request_id, action=action, target_type=target_type, target_id=target_id, data_json=_dumps(data))
    db.add(row)
    db.commit()


def create_mcp_tool_call_request(
    db: Session,
    *,
    user_id: int,
    request_id: str | None,
    server_id: int,
    tool_name: str,
    arguments: dict,
    reason: str | None,
) -> HitlRequest:
    row = HitlRequest(
        user_id=user_id,
        request_id=request_id,
        kind="mcp_tool_call",
        server_id=server_id,
        tool_name=tool_name,
        arguments_json=_dumps(arguments),
        status="pending",
        reason=reason,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    _audit(
        db,
        user_id=user_id,
        request_id=request_id,
        action="hitl.created",
        target_type="hitl_request",
        target_id=row.id,
        data={"server_id": server_id, "tool_name": tool_name},
    )
    if request_id:
        log_event(
            db,
            request_id=request_id,
            user_id=user_id,
            event_type="hitl_pending",
            data={"hitl_request_id": row.id, "server_id": server_id, "tool_name": tool_name},
        )
    return row


def list_requests(db: Session, *, user_id: int, status: str | None, limit: int, offset: int) -> list[HitlRequest]:
    stmt = select(HitlRequest).where(HitlRequest.user_id == user_id)
    if status:
        stmt = stmt.where(HitlRequest.status == status)
    stmt = stmt.order_by(HitlRequest.id.desc()).limit(limit).offset(offset)
    return list(db.execute(stmt).scalars().all())


def get_request(db: Session, *, user_id: int, hitl_request_id: int) -> HitlRequest | None:
    row = db.get(HitlRequest, hitl_request_id)
    if not row or row.user_id != user_id:
        return None
    return row


def decide(
    db: Session,
    *,
    user_id: int,
    hitl_request_id: int,
    action: str,
    reason: str | None,
) -> HitlRequest | None:
    row = get_request(db, user_id=user_id, hitl_request_id=hitl_request_id)
    if not row:
        return None
    if row.status not in {"pending", "edited"}:
        return row
    if action not in {"approve", "reject"}:
        raise ValueError("invalid_action")

    row.status = "approved" if action == "approve" else "rejected"
    row.decided_by_user_id = user_id
    row.decided_at = _utcnow()
    if reason:
        row.reason = reason
    db.add(row)
    db.commit()
    _audit(
        db,
        user_id=user_id,
        request_id=row.request_id,
        action=f"hitl.{action}",
        target_type="hitl_request",
        target_id=row.id,
        data={"tool_name": row.tool_name, "server_id": row.server_id, "reason": reason},
    )
    if row.request_id:
        log_event(
            db,
            request_id=row.request_id,
            user_id=user_id,
            event_type=f"hitl_{row.status}",
            data={"hitl_request_id": row.id, "tool_name": row.tool_name, "server_id": row.server_id, "reason": reason},
        )
    return row


def edit(
    db: Session,
    *,
    user_id: int,
    hitl_request_id: int,
    arguments: dict,
    reason: str | None,
) -> HitlRequest | None:
    row = get_request(db, user_id=user_id, hitl_request_id=hitl_request_id)
    if not row:
        return None
    if row.status not in {"pending", "edited"}:
        return row
    row.status = "edited"
    row.arguments_json = _dumps(arguments)
    row.decided_by_user_id = user_id
    row.decided_at = _utcnow()
    if reason:
        row.reason = reason
    db.add(row)
    db.commit()
    _audit(
        db,
        user_id=user_id,
        request_id=row.request_id,
        action="hitl.edited",
        target_type="hitl_request",
        target_id=row.id,
        data={"tool_name": row.tool_name, "server_id": row.server_id, "reason": reason},
    )
    if row.request_id:
        log_event(
            db,
            request_id=row.request_id,
            user_id=user_id,
            event_type="hitl_edited",
            data={"hitl_request_id": row.id, "tool_name": row.tool_name, "server_id": row.server_id, "reason": reason},
        )
    return row


def mark_executed(
    db: Session,
    *,
    hitl_request_id: int,
    execution_status: str,
    result: dict | None,
    error: str | None,
    tool_call_id: int | None,
) -> None:
    row = db.get(HitlRequest, hitl_request_id)
    if not row:
        return
    row.executed_at = _utcnow()
    row.execution_status = execution_status
    row.execution_error = error
    row.result_json = _dumps(result or {})
    row.tool_call_id = tool_call_id
    db.add(row)
    db.commit()


def to_public(row: HitlRequest) -> dict:
    return {
        "id": row.id,
        "status": row.status,
        "kind": row.kind,
        "tool_name": row.tool_name,
        "server_id": row.server_id,
        "arguments": _loads(row.arguments_json),
        "reason": row.reason,
        "decided_by_user_id": row.decided_by_user_id,
        "decided_at": row.decided_at.isoformat() if row.decided_at else None,
        "executed_at": row.executed_at.isoformat() if row.executed_at else None,
        "execution_status": row.execution_status,
        "execution_error": row.execution_error,
        "result": _loads(row.result_json),
        "tool_call_id": row.tool_call_id,
    }

