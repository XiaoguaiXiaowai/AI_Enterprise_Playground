from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.memory import Memory


def _loads_metadata(value: str) -> dict:
    try:
        data = json.loads(value or "{}")
        if isinstance(data, dict):
            return data
        return {}
    except Exception:
        return {}


def _dumps_metadata(value: dict) -> str:
    return json.dumps(value or {}, ensure_ascii=False, separators=(",", ":"))


def create_memory(
    db: Session,
    *,
    user_id: int,
    namespace: str,
    memory_type: str,
    key: str | None,
    content: str,
    metadata: dict,
    importance: float,
) -> Memory:
    mem = Memory(
        user_id=user_id,
        namespace=namespace,
        memory_type=memory_type,
        key=key,
        content=content,
        metadata_json=_dumps_metadata(metadata),
        importance=importance,
    )
    db.add(mem)
    db.commit()
    db.refresh(mem)
    return mem


def get_memory(db: Session, *, user_id: int, memory_id: int) -> Memory | None:
    mem = db.get(Memory, memory_id)
    if not mem or mem.user_id != user_id:
        return None
    return mem


def update_memory(
    db: Session,
    *,
    user_id: int,
    memory_id: int,
    key: str | None,
    content: str | None,
    metadata: dict | None,
    importance: float | None,
) -> Memory | None:
    mem = get_memory(db, user_id=user_id, memory_id=memory_id)
    if not mem:
        return None
    if key is not None:
        mem.key = key
    if content is not None:
        mem.content = content
    if metadata is not None:
        mem.metadata_json = _dumps_metadata(metadata)
    if importance is not None:
        mem.importance = importance
    db.add(mem)
    db.commit()
    db.refresh(mem)
    return mem


def delete_memory(db: Session, *, user_id: int, memory_id: int) -> bool:
    mem = get_memory(db, user_id=user_id, memory_id=memory_id)
    if not mem:
        return False
    db.delete(mem)
    db.commit()
    return True


def list_memories(
    db: Session,
    *,
    user_id: int,
    namespace: str | None,
    memory_type: str | None,
    limit: int,
    offset: int,
) -> list[Memory]:
    stmt = select(Memory).where(Memory.user_id == user_id)
    if namespace:
        stmt = stmt.where(Memory.namespace == namespace)
    if memory_type:
        stmt = stmt.where(Memory.memory_type == memory_type)
    stmt = stmt.order_by(Memory.updated_at.desc()).limit(limit).offset(offset)
    return list(db.scalars(stmt))


def recall(
    db: Session,
    *,
    user_id: int,
    namespace: str,
    memory_type: str | None,
    query: str,
    limit: int,
) -> list[Memory]:
    stmt = select(Memory).where(Memory.user_id == user_id, Memory.namespace == namespace)
    if memory_type:
        stmt = stmt.where(Memory.memory_type == memory_type)
    candidates = list(db.scalars(stmt.order_by(Memory.updated_at.desc()).limit(200)))
    q = (query or "").strip().lower()
    if not q:
        return candidates[:limit]

    def score(mem: Memory) -> tuple[int, float, int]:
        text = (mem.content or "").lower()
        occ = text.count(q)
        return (occ, mem.importance, mem.id)

    ranked = sorted(candidates, key=score, reverse=True)
    ranked = [m for m in ranked if (m.content or "").lower().count(q) > 0]
    return ranked[:limit]


def to_public(mem: Memory) -> dict:
    return {
        "id": mem.id,
        "namespace": mem.namespace,
        "memory_type": mem.memory_type,
        "key": mem.key,
        "content": mem.content,
        "metadata": _loads_metadata(mem.metadata_json),
        "importance": float(mem.importance),
    }

