from pydantic import BaseModel, Field


class UploadResponse(BaseModel):
    document_id: int
    filename: str
    chunks: int


class DocumentResponse(BaseModel):
    id: int
    filename: str
    content_type: str
    status: str


class ChunkResponse(BaseModel):
    id: int
    document_id: int
    chunk_index: int
    page_start: int | None
    page_end: int | None
    content: str


class SearchRequest(BaseModel):
    query: str = Field(min_length=1)
    top_k: int = Field(default=5, ge=1, le=20)
    document_ids: list[int] | None = None


class Citation(BaseModel):
    chunk_id: int
    document_id: int
    page_start: int | None
    page_end: int | None
    snippet: str
    score: float


class SearchResponse(BaseModel):
    query: str
    citations: list[Citation]


class AnswerRequest(BaseModel):
    query: str = Field(min_length=1)
    top_k: int = Field(default=5, ge=1, le=20)


class AnswerResponse(BaseModel):
    query: str
    answer: str
    citations: list[Citation]

