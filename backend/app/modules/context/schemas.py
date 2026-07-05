from pydantic import BaseModel, Field


class CurrentContextResponse(BaseModel):
    request_id: str
    method: str | None = None
    path: str | None = None
    user_id: int | None = None
    headers: dict = Field(default_factory=dict)
    query_params: dict = Field(default_factory=dict)


class ContextEventResponse(BaseModel):
    id: int
    request_id: str
    user_id: int | None
    event_type: str
    data: dict


class ContextEventsResponse(BaseModel):
    events: list[ContextEventResponse]

