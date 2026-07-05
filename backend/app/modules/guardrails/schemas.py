from pydantic import BaseModel, Field


class GuardResult(BaseModel):
    name: str
    passed: bool
    score: float = 0.0
    reasons: list[str] = Field(default_factory=list)


class GuardReport(BaseModel):
    passed: bool
    results: list[GuardResult]


class GuardEvaluateRequest(BaseModel):
    text: str = Field(min_length=1)
    stage: str = Field(default="input")


class GuardEvaluateResponse(BaseModel):
    stage: str
    report: GuardReport

