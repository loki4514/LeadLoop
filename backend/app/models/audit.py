from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.enums import AuditAction, pg_enum

if TYPE_CHECKING:
    from app.models.employee import Employee


class AuditLog(Base, TimestampMixin):
    """A lightweight record of a human action on a lead: who did what, when, and
    (for field changes) the old → new values. Rendered as a timeline on the
    lead-detail page."""

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Nullable so a "deleted" record can outlive the lead it describes (the lead's
    # own audit rows cascade away with it; the delete record detaches to null).
    lead_id: Mapped[int | None] = mapped_column(
        ForeignKey("leads.id", ondelete="SET NULL"), index=True
    )
    # Who performed the action. Nullable + SET NULL so history survives employee
    # deletion (and DELETE actions can outlive nothing, but we keep the actor).
    actor_employee_id: Mapped[int | None] = mapped_column(
        ForeignKey("employees.id", ondelete="SET NULL")
    )
    action: Mapped[AuditAction] = mapped_column(
        pg_enum(AuditAction, "audit_action"), nullable=False
    )
    # The field that changed (e.g. "tier", "assigned_employee_id"); null for
    # whole-record actions like delete.
    field: Mapped[str | None] = mapped_column(String(64))
    old_value: Mapped[str | None] = mapped_column(Text)
    new_value: Mapped[str | None] = mapped_column(Text)

    actor: Mapped["Employee | None"] = relationship()
