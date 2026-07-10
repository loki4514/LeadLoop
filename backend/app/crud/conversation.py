"""Persistence for the internal (employee-owned) RAG chat threads."""
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.conversation import Conversation
from app.models.enums import MessageSender
from app.models.message import Message

# Marks threads created by the internal knowledge-base chat (vs. lead "web" chat).
INTERNAL_CHANNEL = "internal"


async def list_for_employee(
    db: AsyncSession, employee_id: int
) -> list[Conversation]:
    """Employee's internal chat threads, newest first."""
    result = await db.execute(
        select(Conversation)
        .where(
            Conversation.employee_id == employee_id,
            Conversation.channel == INTERNAL_CHANNEL,
        )
        .order_by(Conversation.id.desc())
    )
    return list(result.scalars().all())


async def get_for_employee(
    db: AsyncSession, conversation_id: int, employee_id: int
) -> Conversation | None:
    """Load one thread (with messages) if it belongs to this employee."""
    result = await db.execute(
        select(Conversation)
        .where(
            Conversation.id == conversation_id,
            Conversation.employee_id == employee_id,
            Conversation.channel == INTERNAL_CHANNEL,
        )
        .options(selectinload(Conversation.messages))
    )
    return result.scalar_one_or_none()


async def create_for_employee(
    db: AsyncSession, employee_id: int, title: str
) -> Conversation:
    convo = Conversation(
        employee_id=employee_id,
        channel=INTERNAL_CHANNEL,
        title=title[:255],
    )
    db.add(convo)
    await db.flush()  # assign id without committing (caller commits)
    return convo


def add_message(
    db: AsyncSession,
    conversation_id: int,
    sender: MessageSender,
    body: str,
    sources: list[dict[str, Any]] | None = None,
) -> Message:
    msg = Message(
        conversation_id=conversation_id,
        sender=sender,
        body=body,
        sources=sources,
    )
    db.add(msg)
    return msg
