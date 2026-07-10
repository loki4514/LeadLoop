from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_employee
from app.chat import answer_question
from app.crud import conversation as convo_crud
from app.db.session import get_db
from app.models.employee import Employee
from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    ConversationDetail,
    ConversationSummary,
)

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat(
    body: ChatRequest,
    db: AsyncSession = Depends(get_db),
    employee: Employee = Depends(get_current_employee),
):
    """Answer a question over the ingested knowledge base (RAG + LLM).

    Retrieves the most relevant document chunks, asks the chat LLM to answer
    using only that context, and persists the turn to the employee's
    conversation. Pass ``conversation_id`` to continue a thread; omit it to
    start a new one. Returns the answer, cited sources, and the thread id.
    """
    return await answer_question(
        db,
        body.question,
        employee_id=employee.id,
        k=body.k,
        conversation_id=body.conversation_id,
    )


@router.get("/conversations", response_model=list[ConversationSummary])
async def list_conversations(
    db: AsyncSession = Depends(get_db),
    employee: Employee = Depends(get_current_employee),
):
    """List the current employee's chat threads, newest first."""
    return await convo_crud.list_for_employee(db, employee.id)


@router.get("/conversations/{conversation_id}", response_model=ConversationDetail)
async def get_conversation(
    conversation_id: int,
    db: AsyncSession = Depends(get_db),
    employee: Employee = Depends(get_current_employee),
):
    """Load one of the employee's chat threads with its full message history."""
    convo = await convo_crud.get_for_employee(db, conversation_id, employee.id)
    if convo is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found"
        )
    return convo
