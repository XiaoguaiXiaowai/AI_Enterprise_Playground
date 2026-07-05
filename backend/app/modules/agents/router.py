from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.auth import User
from app.modules.agents.schemas import AgentRunListItem, AgentRunRequest, AgentRunResponse, AgentRunStepResponse
from app.modules.agents.service import get_run, list_runs, list_steps, resume_run, run_agents, to_public_run, to_public_step
from app.modules.auth.dependencies import get_current_user

router = APIRouter(prefix="/agents", tags=["agents"])


@router.post("/runs", response_model=AgentRunResponse)
async def create_run(
    request: Request,
    payload: AgentRunRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AgentRunResponse:
    request_id = getattr(request.state, "request_id", None)
    try:
        run = await run_agents(db, user_id=user.id, request_id=request_id, goal=payload.goal, model=payload.model)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"error": "agent_run_failed", "message": str(e)})
    steps = list_steps(db, user_id=user.id, run_id=run.id) or []
    pub_run = to_public_run(run)
    return AgentRunResponse(
        **pub_run,
        steps=[AgentRunStepResponse(**to_public_step(s)) for s in steps],
    )


@router.get("/runs", response_model=list[AgentRunListItem])
def list_(
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[AgentRunListItem]:
    rows = list_runs(db, user_id=user.id, limit=limit, offset=offset)
    return [AgentRunListItem(id=r.id, goal=r.goal, model=r.model, status=r.status) for r in rows]


@router.get("/runs/{run_id}", response_model=AgentRunResponse)
def get_(
    run_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AgentRunResponse:
    run = get_run(db, user_id=user.id, run_id=run_id)
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="run_not_found")
    steps = list_steps(db, user_id=user.id, run_id=run_id) or []
    pub_run = to_public_run(run)
    return AgentRunResponse(
        **pub_run,
        steps=[AgentRunStepResponse(**to_public_step(s)) for s in steps],
    )


@router.post("/runs/{run_id}/resume", response_model=AgentRunResponse)
async def resume_(
    request: Request,
    run_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AgentRunResponse:
    request_id = getattr(request.state, "request_id", None)
    try:
        run = await resume_run(db, user_id=user.id, request_id=request_id, run_id=run_id)
    except ValueError as e:
        if str(e) == "run_not_found":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="run_not_found")
        if str(e) == "run_not_paused":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="run_not_paused")
        if str(e) == "hitl_request_not_found":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="hitl_request_not_found")
        if str(e) == "hitl_not_approved":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="hitl_not_approved")
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"error": "resume_failed", "message": str(e)})
    steps = list_steps(db, user_id=user.id, run_id=run.id) or []
    pub_run = to_public_run(run)
    return AgentRunResponse(**pub_run, steps=[AgentRunStepResponse(**to_public_step(s)) for s in steps])
