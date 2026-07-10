from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.document import SearchHit


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=4000)
    # Optional override of how many chunks to retrieve for this question.
    k: int | None = Field(default=None, ge=1, le=20)
    # Continue an existing thread; omit/None starts a new conversation.
    conversation_id: int | None = None


class ChatResponse(BaseModel):
    question: str
    answer: str
    # The retrieved chunks the answer was grounded on (the [n] citations).
    sources: list[SearchHit]
    # The thread this turn was stored in (new or continued).
    conversation_id: int


class ConversationSummary(BaseModel):
    """A row in the history sidebar."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str | None
    created_at: datetime


class MessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sender: str
    body: str
    sources: list[SearchHit] | None = None
    created_at: datetime


class ConversationDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str | None
    created_at: datetime
    messages: list[MessageRead]
