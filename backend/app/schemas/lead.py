"""Dashboard-facing shapes for leads, followups, and properties."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.enums import AuditAction, LeadStatus, LeadTier


class EmployeeBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str


class LeadSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str | None
    email: str | None
    phone: str | None
    location: str | None
    bhk: int | None
    budget_min: int | None
    budget_max: int | None
    timeline: str | None
    purpose: str | None
    financing: str | None
    score: int | None
    tier: LeadTier | None
    status: LeadStatus
    ad_source: str | None
    assigned_employee: EmployeeBrief | None
    # False once the chat is handed over to a human (AI qualifier silenced).
    is_bot_active: bool
    last_activity_at: datetime
    created_at: datetime


class LeadMessage(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sender: str
    body: str
    created_at: datetime


class FollowupRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    lead_id: int
    draft_body: str
    status: str
    created_at: datetime


class FollowupUpdate(BaseModel):
    draft_body: str = Field(..., min_length=1, max_length=10_000)


class LeadReplyRequest(BaseModel):
    # An employee's message typed into a handed-over widget conversation.
    body: str = Field(..., min_length=1, max_length=2000)


class LeadUpdate(BaseModel):
    """Editable lead fields. All optional — only provided fields change. Every
    change is audited. `assigned_employee_id` is admin-only (enforced in the
    route); owners may edit the rest of their own leads (including tier)."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, max_length=255)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=50)
    location: str | None = Field(default=None, max_length=255)
    bhk: int | None = Field(default=None, ge=0, le=20)
    budget_min: int | None = Field(default=None, ge=0)
    budget_max: int | None = Field(default=None, ge=0)
    timeline: str | None = Field(default=None, max_length=255)
    purpose: str | None = Field(default=None, max_length=255)
    financing: str | None = Field(default=None, max_length=255)
    tier: LeadTier | None = None
    status: LeadStatus | None = None
    assigned_employee_id: int | None = None  # admin-only


class AuditLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    action: AuditAction
    field: str | None
    old_value: str | None
    new_value: str | None
    actor: EmployeeBrief | None
    created_at: datetime


class LeadDetail(LeadSummary):
    messages: list[LeadMessage]
    followups: list[FollowupRead]
    audit: list[AuditLogRead] = []
    # True when the viewer owns this lead or is an admin. When False the viewer
    # is a non-owner employee: they see metadata (incl. who it's assigned to)
    # but the chat transcript, follow-ups and audit are withheld.
    can_edit: bool = True


class PropertyCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    location: str = Field(..., min_length=1, max_length=255)
    bhk: int = Field(..., ge=0, le=20)
    price: int = Field(..., gt=0, description="Absolute INR")
    area_sqft: int | None = Field(default=None, gt=0)
    description: str | None = None


class PropertyRead(PropertyCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
