"""Public demo chat: the same RAG answer quality as the internal chat, but with
the retrieval machinery hidden.

Two differences from ``app.chat.service``:

* **Nothing is exposed about retrieval.** The answer carries no ``[n]`` citation
  markers and the response has no ``sources`` field, so the caller never sees
  filenames, chunk text, or similarity scores. Retrieval still grounds the
  answer; it just isn't part of the output.
* **No auth and no persistence.** There is no employee to own a thread, so turns
  are stateless — the client passes back the recent history it wants considered.

The grounding guard is stricter than the internal chat's: with no chunk above
the score threshold the LLM is never called at all, so an answer can never come
from the model's own knowledge.
"""
import asyncio
import re

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.llm import get_chat_llm
from app.retrieval import search_documents
from app.schemas.demo import DemoChatResponse, DemoTurn

_SYSTEM = (
    "You are a friendly real-estate assistant. Answer the user's question using "
    "ONLY the numbered context passages provided. If the answer is not contained "
    "in the context, say you don't have that information — never invent details, "
    "and never fall back on knowledge outside the passages.\n\n"
    "Write for an end customer, not an engineer:\n"
    "- Do NOT cite passages. Never write [1], [2], 'passage 3', 'the context "
    "says', 'according to the documents', or mention sources, files or scores.\n"
    "- Just state the facts directly, as if you knew them.\n"
    "- Use short paragraphs or bullets. Keep it concise and factual."
)

# The model still emits a stray "[2]" now and then despite the instruction, so
# citation markers are stripped from the text as a backstop before it goes out.
_CITATION_RE = re.compile(r"\s*\[\d+(?:\s*,\s*\d+)*\]")

# A question longer than this is treated as self-contained for retrieval; below
# it, a follow-up likely leans on the previous turn for its subject.
_STANDALONE_WORDS = 12

NO_CONTEXT_ANSWER = (
    "I can only answer from the documents in this knowledge base, and I don't "
    "have anything on that. Try asking about buying property in India — home "
    "loans, stamp duty, registration, RERA, or the documents to verify before "
    "a purchase."
)


def _strip_citations(answer: str) -> str:
    """Remove any ``[n]`` markers the model emitted despite the instruction."""
    cleaned = _CITATION_RE.sub("", answer)
    # Collapse the double spaces a mid-sentence removal can leave behind.
    return re.sub(r" {2,}", " ", cleaned).strip()


def _build_prompt(question: str, contents: list[str], history: list[DemoTurn]) -> str:
    context = "\n\n".join(f"[{i + 1}] {c}" for i, c in enumerate(contents))
    parts = [f"Context passages:\n{context}"]
    if history:
        prior = "\n".join(
            f"{'User' if t.role == 'user' else 'Assistant'}: {t.content}"
            for t in history
        )
        # History is for resolving follow-ups ("what about for that?"); it must
        # not become a second source of facts.
        parts.append(
            "Earlier in this conversation (for context on what the user is "
            f"referring to — do not treat it as a source of facts):\n{prior}"
        )
    parts.append(
        f"Question: {question}\n\n"
        "Answer using only the context passages. Do not include citation "
        "markers or mention the passages, documents, or sources."
    )
    return "\n\n".join(parts)


def _retrieval_query(question: str, history: list[DemoTurn]) -> str:
    """The text to embed for retrieval.

    A follow-up like "and the registration charges on top of that?" embeds
    poorly on its own — the subject lives in the previous turn, so the nearest
    chunks come back generic. Prepending the last user question restores the
    missing subject and pulls the right chunks. Cheap and deterministic; an LLM
    condensation pass would add a round-trip to every turn.

    Only follow-ups get this treatment: a question long enough to stand alone
    is already a good query, and padding it would dilute the embedding.
    """
    if not history or len(question.split()) > _STANDALONE_WORDS:
        return question
    last_user = next(
        (t.content for t in reversed(history) if t.role == "user"), None
    )
    return f"{last_user} {question}" if last_user else question


async def answer_demo_question(
    db: AsyncSession,
    question: str,
    k: int | None = None,
    history: list[DemoTurn] | None = None,
) -> DemoChatResponse:
    """Answer a public demo question strictly from retrieved document chunks.

    Returns the answer plus ``grounded``, which is False when retrieval found
    nothing usable — in that case the LLM was never called and the answer is the
    fixed refusal.
    """
    history = history or []
    top_k = k or settings.CHAT_TOP_K
    hits = await search_documents(db, _retrieval_query(question, history), k=top_k)
    hits = [h for h in hits if h.score >= settings.DEMO_MIN_SCORE]

    if not hits:
        return DemoChatResponse(answer=NO_CONTEXT_ANSWER, grounded=False)

    llm = get_chat_llm()
    prompt = _build_prompt(question, [h.content for h in hits], history)
    # SDK call is blocking; keep it off the event loop.
    answer = await asyncio.to_thread(llm.generate, _SYSTEM, prompt)

    return DemoChatResponse(answer=_strip_citations(answer), grounded=True)
