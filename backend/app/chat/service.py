"""RAG-grounded chat: retrieve relevant chunks, then have the LLM answer using
only that context, returning the answer plus its source chunks.

This is the "connect RAG + LLM" piece — a simple, stateless single-turn Q&A
over the ingested knowledge base. (Multi-turn history can be layered on later
by threading prior turns into the prompt.)
"""
import asyncio

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.llm import get_chat_llm
from app.retrieval import search_documents
from app.schemas.chat import ChatResponse
from app.schemas.document import SearchHit

_SYSTEM = (
    "You are a helpful assistant for a real-estate team. Answer the user's "
    "question using ONLY the numbered context passages provided. If the answer "
    "is not contained in the context, say you don't have that information — do "
    "not invent details. Cite the passages you used inline as [1], [2], etc. "
    "Keep answers concise and factual."
)


def _build_prompt(question: str, hits: list[SearchHit]) -> str:
    context = "\n\n".join(
        f"[{i + 1}] (source: {h.filename})\n{h.content}" for i, h in enumerate(hits)
    )
    return (
        f"Context passages:\n{context}\n\n"
        f"Question: {question}\n\n"
        "Answer using only the context above, citing passages as [n]."
    )


async def answer_question(
    db: AsyncSession,
    question: str,
    k: int | None = None,
) -> ChatResponse:
    """Retrieve relevant chunks and generate a grounded answer with sources."""
    top_k = k or settings.CHAT_TOP_K
    hits = await search_documents(db, question, k=top_k)
    # Drop weak matches so the model isn't fed near-irrelevant context.
    hits = [h for h in hits if h.score >= settings.CHAT_MIN_SCORE]

    if not hits:
        return ChatResponse(
            question=question,
            answer=(
                "I don't have any information on that in the knowledge base yet. "
                "Try uploading a relevant document first."
            ),
            sources=[],
        )

    llm = get_chat_llm()
    prompt = _build_prompt(question, hits)
    # SDK call is blocking; keep it off the event loop.
    answer = await asyncio.to_thread(llm.generate, _SYSTEM, prompt)

    return ChatResponse(question=question, answer=answer, sources=hits)
