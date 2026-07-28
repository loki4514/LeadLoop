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

from app.api.deps import get_current_employee, get_current_employee_from_query
from app.api.sse import message_stream
from app.core.email import send_email
from app.crud import audit as audit_crud
from app.crud.conversation import add_message
from app.db.session import get_db
from app.models.audit import AuditLog
from app.models.conversation import Conversation
from app.models.employee import Employee
from app.models.enums import AuditAction, LeadStatus, LeadTier, MessageSender, Role
from app.models.followup import Followup
from app.models.lead import Lead
from app.schemas.lead import (
    AuditLogRead,
    FollowupRead,
    FollowupUpdate,
    LeadDetail,
    LeadMessage,
    LeadReplyRequest,
    LeadSummary,
    LeadUpdate,
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

    audit = [
        AuditLogRead.model_validate(a)
        for a in await audit_crud.list_for_lead(db, lead.id)
    ]

    summary = LeadSummary.model_validate(lead)
    return LeadDetail(
        **summary.model_dump(), messages=messages, followups=followups, audit=audit
    )


# ---------------------------------------------------------------------------
# Edit / reassign / delete (with audit trail)
# ---------------------------------------------------------------------------


@router.patch("/{lead_id}", response_model=LeadDetail)
async def update_lead(
    lead_id: int,
    body: LeadUpdate,
    db: AsyncSession = Depends(get_db),
    employee: Employee = Depends(get_current_employee),
):
    """Edit a lead. Owners (or admins) may change detail fields including tier;
    only admins may reassign (`assigned_employee_id`). Every changed field is
    written to the audit trail."""
    lead = await db.get(Lead, lead_id)
    if lead is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Lead not found")

    is_admin = employee.role == Role.ADMIN
    if not is_admin and lead.assigned_employee_id != employee.id:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, detail="This lead is not assigned to you"
        )

    changes = body.model_dump(exclude_unset=True)

    # Reassignment is admin-only.
    if "assigned_employee_id" in changes and not is_admin:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, detail="Only an admin can reassign a lead"
        )

    # Validate a reassignment target if given.
    new_owner_id = changes.get("assigned_employee_id")
    if "assigned_employee_id" in changes and new_owner_id is not None:
        target = await db.get(Employee, new_owner_id)
        if target is None or not target.is_active:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Assignee is not an active employee",
            )

    for field, new_value in changes.items():
        old_value = getattr(lead, field)
        # Enum-typed columns compare by value; skip no-op writes.
        old_cmp = old_value.value if hasattr(old_value, "value") else old_value
        new_cmp = new_value.value if hasattr(new_value, "value") else new_value
        if old_cmp == new_cmp:
            continue

        setattr(lead, field, new_value)

        if field == "assigned_employee_id":
            action = AuditAction.REASSIGNED
        elif field == "tier":
            action = AuditAction.TIER_CHANGED
        else:
            action = AuditAction.EDITED
        audit_crud.record_audit(
            db,
            lead_id=lead.id,
            actor_employee_id=employee.id,
            action=action,
            field=field,
            old_value=old_cmp,
            new_value=new_cmp,
        )

    await db.commit()
    return await get_lead(lead_id, db, employee)


@router.delete("/{lead_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_lead(
    lead_id: int,
    db: AsyncSession = Depends(get_db),
    employee: Employee = Depends(get_current_employee),
):
    """Delete a lead (and its conversation/messages, via cascade). Admin only.

    The audit row is written to a separate committed transaction first, so the
    'deleted' record survives even though the lead's own audit rows cascade
    away with it."""
    if employee.role != Role.ADMIN:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, detail="Only an admin can delete a lead"
        )
    lead = await db.get(Lead, lead_id)
    if lead is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Lead not found")

    label = lead.name or lead.email or lead.phone or "unnamed"
    # Delete the lead; its own audit rows detach to lead_id=null (SET NULL). Add a
    # standalone 'deleted' record (lead_id=null) that survives the deletion.
    await db.delete(lead)
    db.add(
        AuditLog(
            lead_id=None,
            actor_employee_id=employee.id,
            action=AuditAction.DELETED,
            field="lead",
            old_value=f"lead#{lead_id} ({label})",
        )
    )
    await db.commit()


# ---------------------------------------------------------------------------
# Human takeover: employee ⇄ lead live chat
# ---------------------------------------------------------------------------


async def _lead_web_conversation(
    db: AsyncSession, lead_id: int, employee: Employee
) -> tuple[Lead, Conversation]:
    """Load a lead + its web conversation, enforcing that only the assigned
    employee (or an admin) may touch it. Raises 404/403 otherwise."""
    lead = await db.get(Lead, lead_id)
    if lead is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Lead not found")
    if employee.role != Role.ADMIN and lead.assigned_employee_id != employee.id:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, detail="This lead is not assigned to you"
        )
    convo = (
        await db.execute(
            select(Conversation)
            .where(Conversation.lead_id == lead.id, Conversation.channel == "web")
            .order_by(Conversation.id)
        )
    ).scalars().first()
    if convo is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, detail="Lead has no web conversation"
        )
    return lead, convo


@router.post("/{lead_id}/reply", response_model=LeadMessage)
async def reply_to_lead(
    lead_id: int,
    body: LeadReplyRequest,
    db: AsyncSession = Depends(get_db),
    employee: Employee = Depends(get_current_employee),
):
    """Send an employee message into the lead's widget chat.

    Also flips the lead out of bot mode (``is_bot_active=False``) so the AI
    qualifier stays silent — replying here IS the takeover. The lead sees this
    message as part of the same conversation.
    """
    lead, convo = await _lead_web_conversation(db, lead_id, employee)

    msg = add_message(db, convo.id, MessageSender.EMPLOYEE, body.body)
    lead.is_bot_active = False  # replying takes the chat over from the bot
    lead.last_activity_at = func.now()
    await db.commit()
    await db.refresh(msg)
    return LeadMessage.model_validate(msg)


@router.get("/{lead_id}/stream")
async def stream_lead_messages(
    lead_id: int,
    token: str = Query(..., description="Bearer token (EventSource can't set headers)"),
    after: int = Query(0, description="Only stream messages with id > this"),
    db: AsyncSession = Depends(get_db),
    employee: Employee = Depends(get_current_employee_from_query),
):
    """Server-Sent Events stream of new messages in the lead's chat.

    One-way push, plain HTTP. Authenticates via ?token= (EventSource cannot send
    an Authorization header). Polls the DB every couple of seconds and emits any
    message newer than the last one sent; keep-alive comments hold the
    connection open through idle proxies. The browser's EventSource reconnects
    automatically on drop (resuming from the last id via ?after=).
    """
    _lead, convo = await _lead_web_conversation(db, lead_id, employee)
    return message_stream(convo.id, after)


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
