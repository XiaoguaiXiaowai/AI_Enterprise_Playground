from pydantic import BaseModel, Field


class CreateSessionRequest(BaseModel):
    title: str = Field(default="New chat", max_length=200)


class SessionResponse(BaseModel):
    id: int
    title: str


class MessageResponse(BaseModel):
    id: int
    role: str
    content: str
    model: str


class SendMessageRequest(BaseModel):
    content: str = Field(min_length=1)
    model: str = Field(default="mock", max_length=64)


class SendMessageResponse(BaseModel):
    session_id: int
    user_message: MessageResponse
    assistant_message: MessageResponse

