from fastapi import APIRouter

from app.modules.guardrails.schemas import GuardEvaluateRequest, GuardEvaluateResponse
from app.modules.guardrails.service import evaluate_text

router = APIRouter(prefix="/guardrails", tags=["guardrails"])


@router.post("/evaluate", response_model=GuardEvaluateResponse)
def evaluate(payload: GuardEvaluateRequest) -> GuardEvaluateResponse:
    report = evaluate_text(text=payload.text)
    return GuardEvaluateResponse(stage=payload.stage, report=report)

