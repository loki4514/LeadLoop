from typing import Any

from sqlalchemy import ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.enums import MessageSender, pg_enum


class Message(Base, TimestampMixin):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    sender: Mapped[MessageSender] = mapped_column(
        pg_enum(MessageSender, "message_sender"), nullable=False
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)
    # For agent messages: the RAG source chunks the answer cited (list of
    # SearchHit-shaped dicts). Null for user/employee messages.
    sources: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB)

    conversation: Mapped["Conversation"] = relationship(  # noqa: F821
        back_populates="messages"
    )
