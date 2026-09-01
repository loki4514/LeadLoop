"""Public (unauthenticated) demo of the real-estate RAG chat.

Same grounded answers as the internal /chat, minus everything internal: no auth,
no persisted threads, and no retrieval details in the response — no filenames,
chunk text, similarity scores, or [n] citation markers. Rate-limited per IP,
since it calls the paid LLM without a login in front of it.
"""
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.chat.demo import answer_demo_question
from app.core.ratelimit import limiter
from app.db.session import get_db
from app.schemas.demo import DemoChatRequest, DemoChatResponse

router = APIRouter(prefix="/demo", tags=["demo"])

SUGGESTIONS = [
    "What are the eligibility criteria for a home loan in India?",
    "How much is stamp duty when buying property?",
    "What documents should a buyer verify before purchase?",
    "What is RERA and how does it protect buyers?",
]


@router.get("/suggestions", response_model=list[str])
async def suggestions() -> list[str]:
    """Starter questions shown on the empty demo screen."""
    return SUGGESTIONS


@router.post("/chat", response_model=DemoChatResponse)
@limiter.limit("15/minute")
async def demo_chat(
    request: Request,
    body: DemoChatRequest,
    db: AsyncSession = Depends(get_db),
):
    """Answer a question strictly from the ingested knowledge base.

    When retrieval turns up nothing above the score threshold the LLM is never
    called and a fixed refusal comes back with ``grounded: false`` — so the demo
    can only ever answer from documents in the database.
    """
    return await answer_demo_question(
        db, body.question, k=body.k, history=body.history
    )
