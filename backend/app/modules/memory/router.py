from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.auth import User
from app.modules.auth.dependencies import get_current_user
from app.modules.memory.schemas import (
    MemoryCreateRequest,
    MemoryResponse,
    MemoryUpdateRequest,
    RecallRequest,
    RecallResponse,
)
from app.modules.memory.service import (
    create_memory,
    delete_memory,
    get_memory,
    list_memories,
    recall,
    to_public,
    update_memory,
)

router = APIRouter(prefix="/memory", tags=["memory"])


@router.post("", response_model=MemoryResponse)
def create(
    payload: MemoryCreateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> MemoryResponse:
    mem = create_memory(
        db,
        user_id=user.id,
        namespace=payload.namespace,
        memory_type=payload.memory_type,
        key=payload.key,
        content=payload.content,
        metadata=payload.metadata,
        importance=payload.importance,
    )
    return MemoryResponse(**to_public(mem))


@router.get("", response_model=list[MemoryResponse])
def list_(
    namespace: str | None = None,
    memory_type: str | None = None,
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[MemoryResponse]:
    rows = list_memories(db, user_id=user.id, namespace=namespace, memory_type=memory_type, limit=limit, offset=offset)
    return [MemoryResponse(**to_public(m)) for m in rows]


@router.get("/timeline", response_model=list[MemoryResponse])
def timeline(
    limit: int = 20,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[MemoryResponse]:
    rows = list_memories(db, user_id=user.id, namespace=None, memory_type=None, limit=limit, offset=0)
    return [MemoryResponse(**to_public(m)) for m in rows]


@router.get("/{memory_id}", response_model=MemoryResponse)
def get(
    memory_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> MemoryResponse:
    mem = get_memory(db, user_id=user.id, memory_id=memory_id)
    if not mem:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="memory_not_found")
    return MemoryResponse(**to_public(mem))


@router.patch("/{memory_id}", response_model=MemoryResponse)
def patch(
    memory_id: int,
    payload: MemoryUpdateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> MemoryResponse:
    mem = update_memory(
        db,
        user_id=user.id,
        memory_id=memory_id,
        key=payload.key,
        content=payload.content,
        metadata=payload.metadata,
        importance=payload.importance,
    )
    if not mem:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="memory_not_found")
    return MemoryResponse(**to_public(mem))


@router.delete("/{memory_id}")
def delete(
    memory_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    ok = delete_memory(db, user_id=user.id, memory_id=memory_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="memory_not_found")
    return {"status": "deleted"}


@router.post("/recall", response_model=RecallResponse)
def recall_endpoint(
    payload: RecallRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> RecallResponse:
    rows = recall(
        db,
        user_id=user.id,
        namespace=payload.namespace,
        memory_type=payload.memory_type,
        query=payload.query,
        limit=payload.limit,
    )
    return RecallResponse(namespace=payload.namespace, query=payload.query, memories=[MemoryResponse(**to_public(m)) for m in rows])

