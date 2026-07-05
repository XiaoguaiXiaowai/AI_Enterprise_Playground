from pydantic import BaseModel, Field


class McpServerCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    transport: str = Field(min_length=1, max_length=32)
    server_type: str = Field(min_length=1, max_length=32)
    config: dict = Field(default_factory=dict)


class McpServerResponse(BaseModel):
    id: int
    name: str
    transport: str
    server_type: str
    is_enabled: bool
    config: dict


class McpToolDescriptor(BaseModel):
    name: str
    description: str = ""
    input_schema: dict = Field(default_factory=dict)


class McpToolsListResponse(BaseModel):
    server_id: int
    tools: list[McpToolDescriptor]


class McpToolCallRequest(BaseModel):
    arguments: dict = Field(default_factory=dict)


class McpToolCallResponse(BaseModel):
    server_id: int
    tool_name: str
    result: dict = Field(default_factory=dict)


class McpToolCallAuditResponse(BaseModel):
    id: int
    server_id: int | None
    tool_name: str
    status: str
    duration_ms: int
    error_message: str | None
    request_id: str | None

