from pydantic import BaseModel, Field


class DashboardRange(BaseModel):
    since: str
    until: str
    hours: int


class DashboardFailureRates(BaseModel):
    agent_runs_total: int = 0
    agent_runs_failed: int = 0
    agent_runs_failure_rate: float = 0.0

    mcp_tool_calls_total: int = 0
    mcp_tool_calls_failed: int = 0
    mcp_tool_calls_failure_rate: float = 0.0


class HitlPendingItem(BaseModel):
    id: int
    created_at: str
    tool_name: str
    server_id: int | None
    reason: str | None


class HitlPendingQueue(BaseModel):
    total: int = 0
    limit: int = 20
    offset: int = 0
    items: list[HitlPendingItem] = Field(default_factory=list)


class DashboardOverviewResponse(BaseModel):
    health: dict = Field(default_factory=dict)
    server_time: str
    counts: dict[str, int] = Field(default_factory=dict)
    recents: dict[str, list[dict]] = Field(default_factory=dict)
    token_usage_24h: dict = Field(default_factory=dict)
    range: DashboardRange | None = None
    failure_rates: DashboardFailureRates | None = None
    hitl_pending_queue: HitlPendingQueue | None = None
