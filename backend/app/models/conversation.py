from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class Conversation(Base, TimestampMixin):
    """A chat thread.

    Belongs to EITHER a lead (inbound website chat) OR an employee (the
    internal RAG knowledge-base chat) — exactly one of ``lead_id`` /
    ``employee_id`` is set. ``channel`` distinguishes them ("web" for leads,
    "internal" for the employee RAG chat).
    """

    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(primary_key=True)
    lead_id: Mapped[int | None] = mapped_column(
        ForeignKey("leads.id", ondelete="CASCADE"), index=True
    )
    employee_id: Mapped[int | None] = mapped_column(
        ForeignKey("employees.id", ondelete="CASCADE"), index=True
    )
    channel: Mapped[str] = mapped_column(String(50), default="web", nullable=False)
    # Short human-readable label for the thread (e.g. the first question).
    title: Mapped[str | None] = mapped_column(String(255))

    messages: Mapped[list["Message"]] = relationship(  # noqa: F821
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.id",
    )
