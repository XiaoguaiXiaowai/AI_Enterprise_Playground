from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.auth import User
from app.modules.auth.dependencies import get_current_user, get_current_user_optional
from app.modules.context.schemas import ContextEventResponse, ContextEventsResponse, CurrentContextResponse
from app.modules.context.service import list_events, to_public

router = APIRouter(prefix="/context", tags=["context"])


def _sanitize_headers(headers: dict) -> dict:
    out: dict = {}
    for k, v in headers.items():
        lk = k.lower()
        if lk in {"authorization", "cookie"}:
            continue
        out[k] = v
    return out


@router.get("/current", response_model=CurrentContextResponse)
def current(
    request: Request,
    user: User | None = Depends(get_current_user_optional),
) -> CurrentContextResponse:
    return CurrentContextResponse(
        request_id=getattr(request.state, "request_id", "") or "",
        method=request.method,
        path=str(request.url.path),
        user_id=user.id if user else None,
        headers=_sanitize_headers(dict(request.headers)),
        query_params=dict(request.query_params),
    )


@router.get("/events", response_model=ContextEventsResponse)
def events(
    limit: int = 50,
    offset: int = 0,
    event_type: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ContextEventsResponse:
    rows = list_events(db, user_id=user.id, limit=limit, offset=offset, event_type=event_type)
    return ContextEventsResponse(events=[ContextEventResponse(**to_public(r)) for r in rows])

