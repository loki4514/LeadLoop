from pydantic import BaseModel, Field

from app.schemas.document import SearchHit


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=4000)
    # Optional override of how many chunks to retrieve for this question.
    k: int | None = Field(default=None, ge=1, le=20)


class ChatResponse(BaseModel):
    question: str
    answer: str
    # The retrieved chunks the answer was grounded on (the [n] citations).
    sources: list[SearchHit]
