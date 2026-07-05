from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.auth import User
from app.modules.auth.dependencies import get_current_user
from app.modules.hitl.schemas import HitlDecisionRequest, HitlEditRequest, HitlRequestResponse
from app.modules.hitl.service import decide, edit, get_request, list_requests, to_public
from app.modules.mcp.service import call_tool

router = APIRouter(prefix="/hitl", tags=["hitl"])


@router.get("/requests", response_model=list[HitlRequestResponse])
def list_(
    status_filter: str | None = None,
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[HitlRequestResponse]:
    rows = list_requests(db, user_id=user.id, status=status_filter, limit=limit, offset=offset)
    return [HitlRequestResponse(**to_public(r)) for r in rows]


@router.get("/requests/{hitl_request_id}", response_model=HitlRequestResponse)
def get_(
    hitl_request_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> HitlRequestResponse:
    row = get_request(db, user_id=user.id, hitl_request_id=hitl_request_id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="hitl_request_not_found")
    return HitlRequestResponse(**to_public(row))


@router.post("/requests/{hitl_request_id}/approve", response_model=HitlRequestResponse)
def approve(
    hitl_request_id: int,
    payload: HitlDecisionRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> HitlRequestResponse:
    row = decide(db, user_id=user.id, hitl_request_id=hitl_request_id, action="approve", reason=payload.reason)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="hitl_request_not_found")
    return HitlRequestResponse(**to_public(row))


@router.post("/requests/{hitl_request_id}/reject", response_model=HitlRequestResponse)
def reject(
    hitl_request_id: int,
    payload: HitlDecisionRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> HitlRequestResponse:
    row = decide(db, user_id=user.id, hitl_request_id=hitl_request_id, action="reject", reason=payload.reason)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="hitl_request_not_found")
    return HitlRequestResponse(**to_public(row))


@router.post("/requests/{hitl_request_id}/edit", response_model=HitlRequestResponse)
def edit_(
    hitl_request_id: int,
    payload: HitlEditRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> HitlRequestResponse:
    row = edit(db, user_id=user.id, hitl_request_id=hitl_request_id, arguments=payload.arguments, reason=payload.reason)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="hitl_request_not_found")
    return HitlRequestResponse(**to_public(row))


@router.post("/requests/{hitl_request_id}/resume", response_model=HitlRequestResponse)
async def resume(
    hitl_request_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> HitlRequestResponse:
    row = get_request(db, user_id=user.id, hitl_request_id=hitl_request_id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="hitl_request_not_found")
    if row.status not in {"approved", "edited"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="hitl_request_not_approvable")
    if row.executed_at is not None:
        return HitlRequestResponse(**to_public(row))
    if row.kind != "mcp_tool_call" or not row.server_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="unsupported_hitl_kind")

    try:
        await call_tool(
            db,
            user_id=user.id,
            server_id=row.server_id,
            tool_name=row.tool_name,
            arguments=to_public(row)["arguments"],
            request_id=row.request_id,
            bypass_hitl=True,
            hitl_request_id=row.id,
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"error": "resume_failed", "message": str(e)})

    row = get_request(db, user_id=user.id, hitl_request_id=hitl_request_id)
    return HitlRequestResponse(**to_public(row))

