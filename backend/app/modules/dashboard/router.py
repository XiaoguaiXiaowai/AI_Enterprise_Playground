from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.auth import User
from app.modules.auth.dependencies import get_current_user
from app.modules.dashboard.schemas import DashboardOverviewResponse
from app.modules.dashboard.service import get_overview

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/overview", response_model=DashboardOverviewResponse)
def overview(
    hours: int = 24,
    since: str | None = None,
    until: str | None = None,
    hitl_pending_limit: int = 20,
    hitl_pending_offset: int = 0,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> DashboardOverviewResponse:
    if hours < 1:
        hours = 1
    if hours > 720:
        hours = 720
    if hitl_pending_limit < 1:
        hitl_pending_limit = 1
    if hitl_pending_limit > 100:
        hitl_pending_limit = 100
    if hitl_pending_offset < 0:
        hitl_pending_offset = 0

    now = datetime.now(UTC)
    try:
        until_dt = datetime.fromisoformat(until) if until else now
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_until")
    if until_dt.tzinfo is None:
        until_dt = until_dt.replace(tzinfo=UTC)
    try:
        since_dt = datetime.fromisoformat(since) if since else until_dt - timedelta(hours=hours)
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_since")
    if since_dt.tzinfo is None:
        since_dt = since_dt.replace(tzinfo=UTC)
    if since_dt > until_dt:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_range")

    data = get_overview(
        db,
        user_id=user.id,
        since=since_dt,
        until=until_dt,
        hours=hours,
        hitl_pending_limit=hitl_pending_limit,
        hitl_pending_offset=hitl_pending_offset,
    )
    return DashboardOverviewResponse(**data)
