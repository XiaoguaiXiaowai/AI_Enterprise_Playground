from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config.settings import get_settings
from app.models.agents import AgentRun
from app.models.audit import AuditLog
from app.models.chat import ChatMessage, ChatSession
from app.models.context import ContextEvent
from app.models.hitl import HitlRequest
from app.models.mcp import McpServer, McpToolCall
from app.models.memory import Memory
from app.models.rag import Chunk, Document


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


def _count(db: Session, stmt) -> int:
    v = db.execute(stmt).scalar_one()
    return int(v or 0)


def _rate(failed: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return float(failed) / float(total)


def get_overview(
    db: Session,
    *,
    user_id: int,
    since: datetime,
    until: datetime,
    hours: int,
    hitl_pending_limit: int,
    hitl_pending_offset: int,
) -> dict:
    settings = get_settings()
    now = _utcnow()

    counts = {
        "chat_sessions": _count(db, select(func.count()).select_from(ChatSession).where(ChatSession.user_id == user_id)),
        "chat_messages": _count(
            db,
            select(func.count())
            .select_from(ChatMessage)
            .join(ChatSession, ChatSession.id == ChatMessage.session_id)
            .where(ChatSession.user_id == user_id),
        ),
        "rag_documents": _count(db, select(func.count()).select_from(Document).where(Document.user_id == user_id)),
        "rag_chunks": _count(
            db,
            select(func.count())
            .select_from(Chunk)
            .join(Document, Document.id == Chunk.document_id)
            .where(Document.user_id == user_id),
        ),
        "memories": _count(db, select(func.count()).select_from(Memory).where(Memory.user_id == user_id)),
        "context_events": _count(db, select(func.count()).select_from(ContextEvent).where(ContextEvent.user_id == user_id)),
        "mcp_servers": _count(db, select(func.count()).select_from(McpServer).where(McpServer.user_id == user_id)),
        "mcp_tool_calls": _count(db, select(func.count()).select_from(McpToolCall).where(McpToolCall.user_id == user_id)),
        "hitl_requests": _count(db, select(func.count()).select_from(HitlRequest).where(HitlRequest.user_id == user_id)),
        "hitl_pending": _count(
            db,
            select(func.count()).select_from(HitlRequest).where(HitlRequest.user_id == user_id).where(HitlRequest.status == "pending"),
        ),
        "agent_runs": _count(db, select(func.count()).select_from(AgentRun).where(AgentRun.user_id == user_id)),
        "audit_logs": _count(db, select(func.count()).select_from(AuditLog).where(AuditLog.user_id == user_id)),
    }

    agent_total = _count(
        db,
        select(func.count())
        .select_from(AgentRun)
        .where(AgentRun.user_id == user_id)
        .where(AgentRun.created_at >= since)
        .where(AgentRun.created_at <= until),
    )
    agent_failed = _count(
        db,
        select(func.count())
        .select_from(AgentRun)
        .where(AgentRun.user_id == user_id)
        .where(AgentRun.created_at >= since)
        .where(AgentRun.created_at <= until)
        .where(AgentRun.status == "failed"),
    )

    mcp_total = _count(
        db,
        select(func.count())
        .select_from(McpToolCall)
        .where(McpToolCall.user_id == user_id)
        .where(McpToolCall.created_at >= since)
        .where(McpToolCall.created_at <= until),
    )
    mcp_failed = _count(
        db,
        select(func.count())
        .select_from(McpToolCall)
        .where(McpToolCall.user_id == user_id)
        .where(McpToolCall.created_at >= since)
        .where(McpToolCall.created_at <= until)
        .where(McpToolCall.status == "error"),
    )

    failure_rates = {
        "agent_runs_total": agent_total,
        "agent_runs_failed": agent_failed,
        "agent_runs_failure_rate": _rate(agent_failed, agent_total),
        "mcp_tool_calls_total": mcp_total,
        "mcp_tool_calls_failed": mcp_failed,
        "mcp_tool_calls_failure_rate": _rate(mcp_failed, mcp_total),
    }

    recent_sessions = list(
        db.execute(
            select(ChatSession).where(ChatSession.user_id == user_id).order_by(ChatSession.id.desc()).limit(5)
        ).scalars()
    )
    recent_runs = list(db.execute(select(AgentRun).where(AgentRun.user_id == user_id).order_by(AgentRun.id.desc()).limit(5)).scalars())
    recent_hitl = list(db.execute(select(HitlRequest).where(HitlRequest.user_id == user_id).order_by(HitlRequest.id.desc()).limit(5)).scalars())
    recent_mcp_calls = list(db.execute(select(McpToolCall).where(McpToolCall.user_id == user_id).order_by(McpToolCall.id.desc()).limit(5)).scalars())
    recent_docs = list(db.execute(select(Document).where(Document.user_id == user_id).order_by(Document.id.desc()).limit(5)).scalars())
    recent_audit = list(db.execute(select(AuditLog).where(AuditLog.user_id == user_id).order_by(AuditLog.id.desc()).limit(5)).scalars())

    token_prompt = 0
    token_response = 0
    msg_events = list(
        db.execute(
            select(ContextEvent)
            .where(ContextEvent.user_id == user_id)
            .where(ContextEvent.event_type == "chat_message")
            .where(ContextEvent.created_at >= since)
            .where(ContextEvent.created_at <= until)
            .order_by(ContextEvent.id.desc())
            .limit(500)
        ).scalars()
    )
    for evt in msg_events:
        data = _loads(evt.data_json)
        token_prompt += int(data.get("approx_prompt_tokens") or 0)
        token_response += int(data.get("approx_response_tokens") or 0)

    recents = {
        "chat_sessions": [
            {"id": s.id, "title": s.title, "created_at": s.created_at.isoformat(), "updated_at": s.updated_at.isoformat()}
            for s in recent_sessions
        ],
        "agent_runs": [
            {"id": r.id, "status": r.status, "goal": r.goal, "created_at": r.created_at.isoformat()}
            for r in recent_runs
        ],
        "hitl_requests": [
            {
                "id": h.id,
                "status": h.status,
                "tool_name": h.tool_name,
                "server_id": h.server_id,
                "created_at": h.created_at.isoformat(),
            }
            for h in recent_hitl
        ],
        "mcp_tool_calls": [
            {"id": c.id, "status": c.status, "tool_name": c.tool_name, "duration_ms": c.duration_ms, "created_at": c.created_at.isoformat()}
            for c in recent_mcp_calls
        ],
        "rag_documents": [{"id": d.id, "filename": d.filename, "status": d.status, "created_at": d.created_at.isoformat()} for d in recent_docs],
        "audit_logs": [
            {"id": a.id, "action": a.action, "target_type": a.target_type, "target_id": a.target_id, "created_at": a.created_at.isoformat()}
            for a in recent_audit
        ],
    }

    hitl_pending_total = _count(
        db,
        select(func.count())
        .select_from(HitlRequest)
        .where(HitlRequest.user_id == user_id)
        .where(HitlRequest.status == "pending"),
    )
    pending_rows = list(
        db.execute(
            select(HitlRequest)
            .where(HitlRequest.user_id == user_id)
            .where(HitlRequest.status == "pending")
            .order_by(HitlRequest.id.asc())
            .limit(hitl_pending_limit)
            .offset(hitl_pending_offset)
        ).scalars()
    )
    hitl_pending_queue = {
        "total": hitl_pending_total,
        "limit": hitl_pending_limit,
        "offset": hitl_pending_offset,
        "items": [
            {
                "id": h.id,
                "created_at": h.created_at.isoformat(),
                "tool_name": h.tool_name,
                "server_id": h.server_id,
                "reason": h.reason,
            }
            for h in pending_rows
        ],
    }

    return {
        "health": {"status": "ok", "version": settings.version, "environment": settings.environment},
        "server_time": now.isoformat(),
        "counts": counts,
        "recents": recents,
        "token_usage_24h": {"prompt_tokens": token_prompt, "response_tokens": token_response, "events": len(msg_events), "hours": hours},
        "range": {"since": since.isoformat(), "until": until.isoformat(), "hours": hours},
        "failure_rates": failure_rates,
        "hitl_pending_queue": hitl_pending_queue,
    }
