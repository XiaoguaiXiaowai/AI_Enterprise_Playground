from pydantic import BaseModel, Field


class AgentRunRequest(BaseModel):
    goal: str = Field(min_length=1)
    model: str = Field(default="mock", max_length=64)


class AgentRunStepResponse(BaseModel):
    id: int
    step_index: int
    agent: str
    status: str
    hitl_request_id: int | None = None
    input: dict = Field(default_factory=dict)
    output: dict = Field(default_factory=dict)
    error_message: str | None


class AgentRunResponse(BaseModel):
    id: int
    goal: str
    model: str
    status: str
    waiting_hitl_request_id: int | None = None
    paused_at: str | None = None
    resumed_at: str | None = None
    output_text: str | None
    error_message: str | None
    graph: dict = Field(default_factory=dict)
    steps: list[AgentRunStepResponse] = Field(default_factory=list)


class AgentRunListItem(BaseModel):
    id: int
    goal: str
    model: str
    status: str
