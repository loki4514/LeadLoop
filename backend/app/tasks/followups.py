"""Stalled-lead detection + follow-up drafting (the "no lead goes cold" loop).

Runs on a Celery beat schedule. A lead is *stalled* when it has been qualified/
assigned, we have an email for it, and nothing has happened for STALL_HOURS
(default 48h). For each stalled lead the task drafts a short follow-up email
with the LLM, stores it as a Followup draft for human approval, and notifies
the assigned employee. It never emails the lead directly — a human approves
and sends from the dashboard (POST /followups/{id}/send).

Sync code (Celery worker), mirroring the ingestion task's use of the sync
session.
"""
import asyncio
import logging
from datetime import datetime, timedelta

from sqlalchemy import select

from app.core.celery_app import celery_app
from app.core.config import settings
from app.core.email import send_email
from app.db.sync_session import SyncSessionLocal
from app.llm import get_chat_llm
from app.models.conversation import Conversation
from app.models.employee import Employee
from app.models.enums import LeadStatus
from app.models.followup import Followup
from app.models.lead import Lead
from app.models.message import Message

logger = logging.getLogger("tasks.followups")

_DRAFT_SYSTEM = (
    "You write short, warm follow-up emails for a real-estate team re-engaging "
    "a lead who went quiet. Reference what the lead was looking for. One clear "
    "call to action (reply, or a quick call). 4-6 sentences, no subject line, "
    "no placeholders like [Name] — use the details given or omit them. Sign "
    "off as 'The LeadLoop Team'."
)


def _draft_prompt(lead: Lead, transcript: list[tuple[str, str]]) -> str:
    budget = (
        f"₹{lead.budget_min or '?'}–₹{lead.budget_max or '?'}"
        if (lead.budget_min or lead.budget_max)
        else "not shared"
    )
    convo = "\n".join(f"{sender}: {body}" for sender, body in transcript) or "(none)"
    return (
        "Draft a follow-up email to this lead.\n\n"
        f"Name: {lead.name or 'not shared'}\n"
        f"Looking for: {lead.bhk or '?'}BHK in {lead.location or 'unspecified area'}\n"
        f"Budget (INR): {budget}\n"
        f"Timeline: {lead.timeline or 'not shared'} | Purpose: {lead.purpose or 'not shared'}\n\n"
        f"Recent conversation:\n{convo}\n\n"
        "Write only the email body."
    )


@celery_app.task(name="app.tasks.followups.check_stalled_leads", acks_late=True)
def check_stalled_leads() -> int:
    """Draft follow-ups for stalled leads. Returns how many drafts were created."""
    cutoff = datetime.utcnow() - timedelta(hours=settings.STALL_HOURS)
    db = SyncSessionLocal()
    created = 0
    try:
        # Leads worth chasing: qualified/assigned, reachable, quiet past the
        # cutoff, and without an already-pending draft.
        pending_draft = (
            select(Followup.lead_id).where(Followup.status == "draft").subquery()
        )
        leads = (
            db.execute(
                select(Lead).where(
                    Lead.status.in_([LeadStatus.QUALIFIED, LeadStatus.ASSIGNED]),
                    Lead.email.is_not(None),
                    Lead.last_activity_at < cutoff,
                    Lead.id.not_in(select(pending_draft.c.lead_id)),
                )
            )
            .scalars()
            .all()
        )
        if not leads:
            return 0

        llm = get_chat_llm()
        for lead in leads:
            try:
                transcript = _recent_transcript(db, lead.id)
                body = llm.generate(_DRAFT_SYSTEM, _draft_prompt(lead, transcript))
            except Exception:
                logger.exception("Drafting follow-up failed for lead %s", lead.id)
                continue

            db.add(Followup(lead_id=lead.id, draft_body=body, status="draft"))
            db.commit()
            created += 1
            _notify_employee(db, lead)
        logger.info("Stall check: %s follow-up draft(s) created", created)
        return created
    finally:
        db.close()


def _recent_transcript(db, lead_id: int, limit: int = 10) -> list[tuple[str, str]]:
    rows = db.execute(
        select(Message.sender, Message.body)
        .join(Conversation, Conversation.id == Message.conversation_id)
        .where(Conversation.lead_id == lead_id, Conversation.channel == "web")
        .order_by(Message.id.desc())
        .limit(limit)
    ).all()
    return [(sender.value, body) for sender, body in reversed(rows)]


def _notify_employee(db, lead: Lead) -> None:
    """Ping the assigned employee that a draft is waiting for their approval."""
    if lead.assigned_employee_id is None:
        return
    employee = db.get(Employee, lead.assigned_employee_id)
    if employee is None or not employee.email:
        return
    lead_label = lead.name or lead.email or f"Lead #{lead.id}"
    url = f"{settings.FRONTEND_BASE_URL}/leads/{lead.id}"
    asyncio.run(
        send_email(
            to=employee.email,
            subject=f"Lead going cold: {lead_label} — follow-up draft ready",
            html=(
                '<div style="font-family:system-ui,sans-serif">'
                f"<p>Hi {employee.name},</p>"
                f"<p><strong>{lead_label}</strong> has had no activity for "
                f"{settings.STALL_HOURS} hours. A follow-up email draft is ready "
                "for your review — approve, edit, or dismiss it from the dashboard.</p>"
                f'<p><a href="{url}">Review the draft</a></p>'
                "</div>"
            ),
        )
    )
