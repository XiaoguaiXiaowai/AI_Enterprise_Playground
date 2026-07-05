from pydantic import BaseModel, Field


class MemoryCreateRequest(BaseModel):
    namespace: str = Field(default="default", max_length=128)
    memory_type: str = Field(default="short", max_length=16)
    key: str | None = Field(default=None, max_length=128)
    content: str = Field(min_length=1)
    metadata: dict = Field(default_factory=dict)
    importance: float = Field(default=0.0, ge=0.0)


class MemoryUpdateRequest(BaseModel):
    key: str | None = Field(default=None, max_length=128)
    content: str | None = Field(default=None, min_length=1)
    metadata: dict | None = None
    importance: float | None = Field(default=None, ge=0.0)


class MemoryResponse(BaseModel):
    id: int
    namespace: str
    memory_type: str
    key: str | None
    content: str
    metadata: dict
    importance: float


class RecallRequest(BaseModel):
    namespace: str = Field(default="default", max_length=128)
    memory_type: str | None = Field(default=None, max_length=16)
    query: str = Field(default="")
    limit: int = Field(default=10, ge=1, le=50)


class RecallResponse(BaseModel):
    namespace: str
    query: str
    memories: list[MemoryResponse]

