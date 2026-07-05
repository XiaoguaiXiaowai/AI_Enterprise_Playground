from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.context import ContextEvent


def _dumps(value: dict) -> str:
    return json.dumps(value or {}, ensure_ascii=False, separators=(",", ":"))


def _loads(value: str) -> dict:
    try:
        data = json.loads(value or "{}")
        if isinstance(data, dict):
            return data
        return {}
    except Exception:
        return {}


def log_event(
    db: Session,
    *,
    request_id: str,
    user_id: int | None,
    event_type: str,
    data: dict,
) -> ContextEvent:
    evt = ContextEvent(request_id=request_id, user_id=user_id, event_type=event_type, data_json=_dumps(data))
    db.add(evt)
    db.commit()
    db.refresh(evt)
    return evt


def list_events(
    db: Session,
    *,
    user_id: int,
    limit: int,
    offset: int,
    event_type: str | None,
) -> list[ContextEvent]:
    stmt = select(ContextEvent).where(ContextEvent.user_id == user_id)
    if event_type:
        stmt = stmt.where(ContextEvent.event_type == event_type)
    stmt = stmt.order_by(ContextEvent.id.desc()).limit(limit).offset(offset)
    return list(db.scalars(stmt))


def to_public(evt: ContextEvent) -> dict:
    return {
        "id": evt.id,
        "request_id": evt.request_id,
        "user_id": evt.user_id,
        "event_type": evt.event_type,
        "data": _loads(evt.data_json),
    }

