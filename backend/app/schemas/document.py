from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import DocumentStatus


class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    filename: str
    content_type: str | None
    status: DocumentStatus
    error: str | None
    embedding_provider: str | None
    embedding_model: str | None
    created_at: datetime


class SearchHit(BaseModel):
    document_id: int
    filename: str
    chunk_index: int
    content: str
    score: float  # cosine similarity in [0, 1]; higher is closer


class SearchResponse(BaseModel):
    query: str
    hits: list[SearchHit]
