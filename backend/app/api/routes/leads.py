"""Dashboard endpoints: leads list/detail and follow-up draft workflow.

Follow-up lifecycle: the stall-checker task creates rows with status="draft";
an employee edits (optional) then sends (emails the lead via Resend) or
dismisses. Sending refreshes the lead's last_activity_at so the stall checker
doesn't immediately re-draft.
"""
import html

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_employee
from app.core.email import send_email
from app.db.session import get_db
from app.models.conversation import Conversation
from app.models.employee import Employee
from app.models.enums import LeadStatus, LeadTier, Role
from app.models.followup import Followup
from app.models.lead import Lead
from app.schemas.lead import (
    FollowupRead,
    FollowupUpdate,
    LeadDetail,
    LeadMessage,
    LeadSummary,
)

router = APIRouter(prefix="/leads", tags=["leads"])
followups_router = APIRouter(prefix="/followups", tags=["followups"])


@router.get("", response_model=list[LeadSummary])
async def list_leads(
    tier: LeadTier | None = None,
    lead_status: LeadStatus | None = Query(default=None, alias="status"),
    mine: bool = False,
    db: AsyncSession = Depends(get_db),
    employee: Employee = Depends(get_current_employee),
):
    """All leads, most recently active first. Filter by tier/status, or pass
    ``mine=true`` for only the current employee's assignments."""
    stmt = (
        select(Lead)
        .options(selectinload(Lead.assigned_employee))
        .order_by(Lead.last_activity_at.desc())
    )
    if tier is not None:
        stmt = stmt.where(Lead.tier == tier)
    if lead_status is not None:
        stmt = stmt.where(Lead.status == lead_status)
    if mine:
        stmt = stmt.where(Lead.assigned_employee_id == employee.id)

    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.get("/{lead_id}", response_model=LeadDetail)
async def get_lead(
    lead_id: int,
    db: AsyncSession = Depends(get_db),
    employee: Employee = Depends(get_current_employee),
):
    """One lead with its full widget conversation and follow-up drafts."""
    result = await db.execute(
        select(Lead)
        .where(Lead.id == lead_id)
        .options(selectinload(Lead.assigned_employee))
    )
    lead = result.scalar_one_or_none()
    if lead is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Lead not found")

    convo_result = await db.execute(
        select(Conversation)
        .where(Conversation.lead_id == lead.id, Conversation.channel == "web")
        .options(selectinload(Conversation.messages))
        .order_by(Conversation.id)
    )
    messages = [
        LeadMessage.model_validate(m)
        for convo in convo_result.scalars().all()
        for m in convo.messages
    ]

    fu_result = await db.execute(
        select(Followup).where(Followup.lead_id == lead.id).order_by(Followup.id.desc())
    )
    followups = [FollowupRead.model_validate(f) for f in fu_result.scalars().all()]

    summary = LeadSummary.model_validate(lead)
    return LeadDetail(**summary.model_dump(), messages=messages, followups=followups)


# ---------------------------------------------------------------------------
# Follow-up drafts
# ---------------------------------------------------------------------------


async def _get_followup_for(
    db: AsyncSession, followup_id: int, employee: Employee
) -> tuple[Followup, Lead]:
    """Load a followup + its lead, enforcing that only the assigned employee
    (or an admin) can act on it."""
    result = await db.execute(
        select(Followup, Lead)
        .join(Lead, Lead.id == Followup.lead_id)
        .where(Followup.id == followup_id)
    )
    row = result.first()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Follow-up not found")
    followup, lead = row
    if employee.role != Role.ADMIN and lead.assigned_employee_id != employee.id:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, detail="Not your lead's follow-up"
        )
    return followup, lead


@followups_router.get("", response_model=list[FollowupRead])
async def list_followups(
    followup_status: str | None = Query(default="draft", alias="status"),
    db: AsyncSession = Depends(get_db),
    employee: Employee = Depends(get_current_employee),
):
    """Pending follow-up drafts — admins see all, employees see their leads'."""
    stmt = select(Followup).join(Lead, Lead.id == Followup.lead_id)
    if followup_status:
        stmt = stmt.where(Followup.status == followup_status)
    if employee.role != Role.ADMIN:
        stmt = stmt.where(Lead.assigned_employee_id == employee.id)
    result = await db.execute(stmt.order_by(Followup.id.desc()))
    return list(result.scalars().all())


@followups_router.patch("/{followup_id}", response_model=FollowupRead)
async def edit_followup(
    followup_id: int,
    body: FollowupUpdate,
    db: AsyncSession = Depends(get_db),
    employee: Employee = Depends(get_current_employee),
):
    """Edit a draft before sending."""
    followup, _ = await _get_followup_for(db, followup_id, employee)
    if followup.status != "draft":
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Not an editable draft")
    followup.draft_body = body.draft_body
    await db.commit()
    await db.refresh(followup)
    return followup


@followups_router.post("/{followup_id}/send", response_model=FollowupRead)
async def send_followup(
    followup_id: int,
    db: AsyncSession = Depends(get_db),
    employee: Employee = Depends(get_current_employee),
):
    """Approve & send the draft to the lead's email, then mark it sent."""
    followup, lead = await _get_followup_for(db, followup_id, employee)
    if followup.status != "draft":
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Already handled")
    if not lead.email:
        raise HTTPException(
            status.HTTP_409_CONFLICT, detail="Lead has no email address"
        )

    body_html = html.escape(followup.draft_body).replace("\n", "<br>")
    await send_email(
        to=lead.email,
        subject="Following up on your property search",
        html=f'<div style="font-family:system-ui,sans-serif">{body_html}</div>',
    )

    followup.status = "sent"
    lead.last_activity_at = func.now()
    await db.commit()
    await db.refresh(followup)
    return followup


@followups_router.post("/{followup_id}/dismiss", response_model=FollowupRead)
async def dismiss_followup(
    followup_id: int,
    db: AsyncSession = Depends(get_db),
    employee: Employee = Depends(get_current_employee),
):
    """Discard a draft without sending."""
    followup, _ = await _get_followup_for(db, followup_id, employee)
    if followup.status != "draft":
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Already handled")
    followup.status = "dismissed"
    await db.commit()
    await db.refresh(followup)
    return followup
