from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_employee
from app.chat import answer_question
from app.db.session import get_db
from app.models.employee import Employee
from app.schemas.chat import ChatRequest, ChatResponse

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat(
    body: ChatRequest,
    db: AsyncSession = Depends(get_db),
    _: Employee = Depends(get_current_employee),
):
    """Answer a question over the ingested knowledge base (RAG + Gemini).

    Retrieves the most relevant document chunks, then asks the chat LLM to
    answer using only that context. Returns the answer and the source chunks it
    cited.
    """
    return await answer_question(db, body.question, k=body.k)
