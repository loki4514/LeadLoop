"""Audit-trail persistence for lead changes."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.audit import AuditLog
from app.models.enums import AuditAction


def record_audit(
    db: AsyncSession,
    *,
    lead_id: int,
    actor_employee_id: int | None,
    action: AuditAction,
    field: str | None = None,
    old_value: object | None = None,
    new_value: object | None = None,
) -> AuditLog:
    """Stage an audit row (caller commits). Values are stringified for storage."""
    entry = AuditLog(
        lead_id=lead_id,
        actor_employee_id=actor_employee_id,
        action=action,
        field=field,
        old_value=None if old_value is None else str(old_value),
        new_value=None if new_value is None else str(new_value),
    )
    db.add(entry)
    return entry


async def list_for_lead(db: AsyncSession, lead_id: int) -> list[AuditLog]:
    """Audit history for a lead, newest first, with the actor loaded."""
    result = await db.execute(
        select(AuditLog)
        .where(AuditLog.lead_id == lead_id)
        .options(selectinload(AuditLog.actor))
        .order_by(AuditLog.id.desc())
    )
    return list(result.scalars().all())
