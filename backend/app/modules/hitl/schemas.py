from pydantic import BaseModel, Field


class HitlRequestResponse(BaseModel):
    id: int
    status: str
    kind: str
    tool_name: str
    server_id: int | None
    arguments: dict = Field(default_factory=dict)
    reason: str | None

    decided_by_user_id: int | None
    decided_at: str | None

    executed_at: str | None
    execution_status: str | None
    execution_error: str | None
    result: dict = Field(default_factory=dict)
    tool_call_id: int | None


class HitlDecisionRequest(BaseModel):
    reason: str | None = None


class HitlEditRequest(BaseModel):
    arguments: dict = Field(default_factory=dict)
    reason: str | None = None

