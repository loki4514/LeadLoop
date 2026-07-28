from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Integer, String, func, true
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.enums import LeadStatus, LeadTier, pg_enum


class Lead(Base, TimestampMixin):
    __tablename__ = "leads"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str | None] = mapped_column(String(255))
    email: Mapped[str | None] = mapped_column(String(255), index=True)
    phone: Mapped[str | None] = mapped_column(String(50))

    # Qualification answers
    location: Mapped[str | None] = mapped_column(String(255))
    bhk: Mapped[int | None] = mapped_column(Integer)
    budget_min: Mapped[int | None] = mapped_column(Integer)
    budget_max: Mapped[int | None] = mapped_column(Integer)
    timeline: Mapped[str | None] = mapped_column(String(255))
    purpose: Mapped[str | None] = mapped_column(String(255))
    financing: Mapped[str | None] = mapped_column(String(255))

    # Scoring
    score: Mapped[int | None] = mapped_column(Integer)
    tier: Mapped[LeadTier | None] = mapped_column(pg_enum(LeadTier, "lead_tier"))
    status: Mapped[LeadStatus] = mapped_column(
        pg_enum(LeadStatus, "lead_status"), default=LeadStatus.NEW, nullable=False
    )

    ad_source: Mapped[str | None] = mapped_column(String(255))

    assigned_employee_id: Mapped[int | None] = mapped_column(
        ForeignKey("employees.id", ondelete="SET NULL")
    )
    assigned_employee: Mapped["Employee | None"] = relationship(  # noqa: F821
        back_populates="assigned_leads"
    )

    # Human takeover: true while the AI qualifier is handling the chat; flipped
    # false on handover so the agent goes quiet and a person takes over.
    is_bot_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=true()
    )

    last_activity_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), nullable=False
    )
