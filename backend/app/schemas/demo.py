from typing import Literal

from pydantic import BaseModel, Field


class DemoTurn(BaseModel):
    """One prior turn, echoed back by the client (the demo is stateless)."""

    role: Literal["user", "assistant"]
    content: str = Field(..., max_length=4000)


class DemoChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=1000)
    # Optional override of how many chunks to retrieve for this question.
    k: int | None = Field(default=None, ge=1, le=20)
    # Recent turns, oldest first — used only to resolve follow-up phrasing.
    # Capped so a client can't inflate the prompt (and the bill).
    history: list[DemoTurn] = Field(default_factory=list, max_length=10)


class DemoChatResponse(BaseModel):
    """Deliberately minimal: no sources, filenames, chunk text or scores.

    The demo is public, so nothing about the knowledge base or the retrieval
    internals is exposed — only the prose answer.
    """

    answer: str
    # False when retrieval found nothing usable and the LLM was never called.
    grounded: bool
