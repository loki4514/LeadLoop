"""RAG-grounded chat: retrieve relevant chunks, then have the LLM answer using
only that context, returning the answer plus its source chunks.

This is the "connect RAG + LLM" piece — a simple, stateless single-turn Q&A
over the ingested knowledge base. (Multi-turn history can be layered on later
by threading prior turns into the prompt.)
"""
import asyncio

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.crud import conversation as convo_crud
from app.llm import get_chat_llm
from app.models.enums import MessageSender
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
    employee_id: int,
    k: int | None = None,
    conversation_id: int | None = None,
) -> ChatResponse:
    """Retrieve relevant chunks, generate a grounded answer, and persist the turn.

    The question and answer (with its cited sources) are stored as messages in a
    conversation owned by ``employee_id`` — a new thread when ``conversation_id``
    is None, otherwise the existing thread (which must belong to this employee).
    """
    # Resolve the thread up front so both the question and answer are stored
    # together, even when retrieval finds nothing.
    if conversation_id is None:
        convo = await convo_crud.create_for_employee(db, employee_id, title=question)
    else:
        convo = await convo_crud.get_for_employee(db, conversation_id, employee_id)
        if convo is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found"
            )

    convo_crud.add_message(db, convo.id, MessageSender.EMPLOYEE, question)

    top_k = k or settings.CHAT_TOP_K
    hits = await search_documents(db, question, k=top_k)
    # Drop weak matches so the model isn't fed near-irrelevant context.
    hits = [h for h in hits if h.score >= settings.CHAT_MIN_SCORE]

    if not hits:
        answer = (
            "I don't have any information on that in the knowledge base yet. "
            "Try uploading a relevant document first."
        )
    else:
        llm = get_chat_llm()
        prompt = _build_prompt(question, hits)
        # SDK call is blocking; keep it off the event loop.
        answer = await asyncio.to_thread(llm.generate, _SYSTEM, prompt)

    convo_crud.add_message(
        db,
        convo.id,
        MessageSender.AGENT,
        answer,
        sources=[h.model_dump() for h in hits] or None,
    )
    await db.commit()

    return ChatResponse(
        question=question,
        answer=answer,
        sources=hits,
        conversation_id=convo.id,
    )
