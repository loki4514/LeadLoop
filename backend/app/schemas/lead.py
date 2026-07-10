"""Dashboard-facing shapes for leads, followups, and properties."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import LeadStatus, LeadTier


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


class LeadDetail(LeadSummary):
    messages: list[LeadMessage]
    followups: list[FollowupRead]


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
