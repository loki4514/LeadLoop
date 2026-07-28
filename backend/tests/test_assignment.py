"""Tests for deterministic lead -> employee assignment.

Covered: no-employee handling, admin fallback, tier-weighted load balancing, and
the round-robin tiebreak (least-recently-assigned wins, never-assigned beats
everyone). Uses the in-memory `db` fixture from conftest.
"""
from datetime import datetime

import pytest

from app.agent.assignment import assign_employee
from app.models.assignment import Assignment
from app.models.employee import Employee
from app.models.enums import LeadStatus, LeadTier, Role
from app.models.lead import Lead

pytestmark = pytest.mark.asyncio


async def add_employee(db, name, *, role=Role.EMPLOYEE, is_active=True):
    emp = Employee(
        name=name, email=f"{name}@x.com", hashed_password="x",
        role=role, is_active=is_active,
    )
    db.add(emp)
    await db.flush()
    return emp


async def add_lead(db, *, employee_id=None, tier=None, status=LeadStatus.NEW):
    lead = Lead(assigned_employee_id=employee_id, tier=tier, status=status)
    db.add(lead)
    await db.flush()
    return lead


async def record_assignment(db, employee_id, when: datetime):
    db.add(Assignment(lead_id=0, employee_id=employee_id, assigned_at=when))
    await db.flush()


async def test_returns_none_when_no_employees(db):
    lead = await add_lead(db)
    assert await assign_employee(db, lead) is None
    assert lead.assigned_employee_id is None


async def test_skips_inactive_employees(db):
    await add_employee(db, "inactive", is_active=False)
    active = await add_employee(db, "active")
    lead = await add_lead(db)

    chosen = await assign_employee(db, lead)
    assert chosen.id == active.id
    assert lead.assigned_employee_id == active.id
    assert lead.status is LeadStatus.ASSIGNED


async def test_falls_back_to_admin_when_no_plain_employees(db):
    admin = await add_employee(db, "boss", role=Role.ADMIN)
    lead = await add_lead(db)

    chosen = await assign_employee(db, lead)
    assert chosen.id == admin.id


async def test_prefers_employee_role_over_admin(db):
    await add_employee(db, "boss", role=Role.ADMIN)
    emp = await add_employee(db, "rep")
    lead = await add_lead(db)

    chosen = await assign_employee(db, lead)
    assert chosen.id == emp.id


async def test_routes_to_least_loaded(db):
    busy = await add_employee(db, "busy")
    light = await add_employee(db, "light")
    # busy already holds an open HOT lead (weight 3); light holds nothing.
    await add_lead(db, employee_id=busy.id, tier=LeadTier.HOT,
                   status=LeadStatus.ASSIGNED)

    chosen = await assign_employee(db, await add_lead(db))
    assert chosen.id == light.id


async def test_load_is_tier_weighted(db):
    a = await add_employee(db, "a")
    b = await add_employee(db, "b")
    # a: one HOT open lead (weight 3). b: two COLD open leads (weight 2 total).
    await add_lead(db, employee_id=a.id, tier=LeadTier.HOT,
                   status=LeadStatus.ASSIGNED)
    await add_lead(db, employee_id=b.id, tier=LeadTier.COLD,
                   status=LeadStatus.ASSIGNED)
    await add_lead(db, employee_id=b.id, tier=LeadTier.COLD,
                   status=LeadStatus.ASSIGNED)

    # b's load (2) < a's load (3), so b should win despite holding more leads.
    chosen = await assign_employee(db, await add_lead(db))
    assert chosen.id == b.id


async def test_closed_leads_do_not_count_as_load(db):
    a = await add_employee(db, "a")
    b = await add_employee(db, "b")
    # a's only lead is CLOSED, so a's effective load is 0 — a and b tie at 0.
    await add_lead(db, employee_id=a.id, tier=LeadTier.HOT,
                   status=LeadStatus.CLOSED)
    # Break the tie deterministically: b was assigned recently, a never was.
    await record_assignment(db, b.id, datetime(2026, 1, 1))

    chosen = await assign_employee(db, await add_lead(db))
    assert chosen.id == a.id  # never-assigned beats recently-assigned


async def test_roundrobin_least_recently_assigned_wins(db):
    a = await add_employee(db, "a")
    b = await add_employee(db, "b")
    # Equal (zero) load. a assigned longer ago than b -> a is "next up".
    await record_assignment(db, a.id, datetime(2026, 1, 1))
    await record_assignment(db, b.id, datetime(2026, 6, 1))

    chosen = await assign_employee(db, await add_lead(db))
    assert chosen.id == a.id


async def test_assignment_row_is_recorded(db):
    emp = await add_employee(db, "rep")
    lead = await add_lead(db)

    await assign_employee(db, lead)
    await db.flush()

    from sqlalchemy import select
    rows = (await db.execute(
        select(Assignment).where(Assignment.employee_id == emp.id)
    )).scalars().all()
    assert any(r.lead_id == lead.id for r in rows)
