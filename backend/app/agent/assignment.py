"""Deterministic lead → employee assignment.

Load-balanced round-robin, priority-weighted: each employee's current book of
open leads is weighted by tier (hot leads cost more attention than cold ones),
and the new lead goes to the least-loaded active employee. Ties break to whoever
was assigned a lead least recently (the round-robin part), then by id.

Not an LLM call — assignment must be fair, explainable, and reproducible.
"""
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assignment import Assignment
from app.models.employee import Employee
from app.models.enums import LeadStatus, LeadTier, Role
from app.models.lead import Lead

# Attention cost of an open lead by tier; unscored leads count as warm.
_TIER_WEIGHT = {LeadTier.HOT: 3, LeadTier.WARM: 2, LeadTier.COLD: 1}


async def assign_employee(
    db: AsyncSession, lead: Lead, prefer_online: bool = False
) -> Employee | None:
    """Pick the employee for ``lead`` and record the assignment.

    Returns the chosen employee, or None when no active employee exists.
    Updates ``lead.assigned_employee_id`` / ``lead.status`` and inserts an
    Assignment row; the caller commits.

    When ``prefer_online`` is set (used when a lead explicitly asks to talk to a
    human now), online employees are preferred so someone can respond live; if
    none are online it falls back to any active employee (they pick it up later).
    """
    result = await db.execute(
        select(Employee).where(Employee.is_active.is_(True), Employee.role == Role.EMPLOYEE)
    )
    employees = list(result.scalars().all())
    if not employees:
        # Fall back to admins so a one-person shop still gets leads routed.
        result = await db.execute(select(Employee).where(Employee.is_active.is_(True)))
        employees = list(result.scalars().all())
    if not employees:
        return None

    # Prefer online agents for live handovers, but only if at least one is
    # online — otherwise keep the full active pool so the lead still gets an owner.
    if prefer_online:
        online = [e for e in employees if e.is_online]
        if online:
            employees = online

    # Current open (not closed) leads per employee, by tier.
    result = await db.execute(
        select(Lead.assigned_employee_id, Lead.tier, func.count())
        .where(
            Lead.assigned_employee_id.is_not(None),
            Lead.status != LeadStatus.CLOSED,
        )
        .group_by(Lead.assigned_employee_id, Lead.tier)
    )
    load: dict[int, int] = {}
    for employee_id, tier, count in result.all():
        load[employee_id] = load.get(employee_id, 0) + count * _TIER_WEIGHT.get(tier, 2)

    # Most recent assignment time per employee — the round-robin tiebreaker.
    result = await db.execute(
        select(Assignment.employee_id, func.max(Assignment.assigned_at)).group_by(
            Assignment.employee_id
        )
    )
    last_assigned = dict(result.all())

    def sort_key(e: Employee):
        # Least weighted load first; never-assigned beats recently-assigned.
        ts = last_assigned.get(e.id)
        return (load.get(e.id, 0), ts is not None, ts, e.id)

    chosen = min(employees, key=sort_key)

    lead.assigned_employee_id = chosen.id
    lead.status = LeadStatus.ASSIGNED
    db.add(Assignment(lead_id=lead.id, employee_id=chosen.id))
    return chosen
