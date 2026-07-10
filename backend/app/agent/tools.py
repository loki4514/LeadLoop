"""Tools the qualifier agent can call, and their OpenAI function schemas.

Design rules (from the product spec):
- The agent NEVER writes SQL. It extracts structured values from the
  conversation and calls these fixed signatures; Python runs prepared queries.
- score_lead / assign_employee are deterministic Python (see scoring.py /
  assignment.py) — the LLM only decides *when* to call them.
- Every executor returns a JSON-serializable dict that is fed back to the model
  as the tool result.
"""
import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.assignment import assign_employee as _assign_employee
from app.agent.scoring import FINANCING, PURPOSES, TIMELINES, score_lead as _score_lead
from app.models.employee import Employee
from app.models.enums import LeadStatus
from app.models.lead import Lead
from app.models.property import Property
from app.retrieval import search_documents

logger = logging.getLogger("agent.tools")

# ---------------------------------------------------------------------------
# Executors — each takes (db, lead, **args from the model)
# ---------------------------------------------------------------------------


async def search_properties(
    db: AsyncSession,
    lead: Lead,
    location: str | None = None,
    bhk: int | None = None,
    min_price: int | None = None,
    max_price: int | None = None,
    limit: int = 3,
) -> dict[str, Any]:
    """Parameterized, indexed property lookup (no vector search, no raw SQL)."""
    stmt = select(Property)
    if location:
        stmt = stmt.where(Property.location.ilike(f"%{location.strip()}%"))
    if bhk is not None:
        stmt = stmt.where(Property.bhk == bhk)
    if min_price is not None:
        stmt = stmt.where(Property.price >= min_price)
    if max_price is not None:
        stmt = stmt.where(Property.price <= max_price)
    stmt = stmt.order_by(Property.price).limit(max(1, min(limit, 10)))

    result = await db.execute(stmt)
    props = list(result.scalars().all())
    return {
        "count": len(props),
        "properties": [
            {
                "id": p.id,
                "title": p.title,
                "location": p.location,
                "bhk": p.bhk,
                "price_inr": p.price,
                "area_sqft": p.area_sqft,
                "description": p.description,
            }
            for p in props
        ],
    }


async def save_lead_answers(
    db: AsyncSession,
    lead: Lead,
    name: str | None = None,
    location: str | None = None,
    bhk: int | None = None,
    budget_min: int | None = None,
    budget_max: int | None = None,
    timeline: str | None = None,
    purpose: str | None = None,
    financing: str | None = None,
) -> dict[str, Any]:
    """Persist qualification answers onto the lead as the conversation reveals them."""
    if name:
        lead.name = name[:255]
    if location:
        lead.location = location[:255]
    if bhk is not None:
        lead.bhk = bhk
    if budget_min is not None:
        lead.budget_min = budget_min
    if budget_max is not None:
        lead.budget_max = budget_max
    if timeline in TIMELINES:
        lead.timeline = timeline
    if purpose in PURPOSES:
        lead.purpose = purpose
    if financing in FINANCING:
        lead.financing = financing
    if lead.status == LeadStatus.NEW:
        lead.status = LeadStatus.QUALIFYING
    await db.flush()
    return {"saved": True, "known_answers": _lead_state(lead)}


async def capture_contact(
    db: AsyncSession,
    lead: Lead,
    email: str | None = None,
    phone: str | None = None,
    name: str | None = None,
) -> dict[str, Any]:
    """Store the lead's contact details for the callback."""
    if not email and not phone:
        return {"saved": False, "error": "Provide at least an email or a phone number."}
    if email:
        lead.email = email.strip()[:255]
    if phone:
        lead.phone = phone.strip()[:50]
    if name:
        lead.name = name[:255]
    await db.flush()
    return {"saved": True, "email": lead.email, "phone": lead.phone}


async def score_lead(db: AsyncSession, lead: Lead) -> dict[str, Any]:
    """Deterministic rules-based scoring over the stored answers."""
    score, tier = _score_lead(lead)
    lead.score = score
    lead.tier = tier
    if lead.status in (LeadStatus.NEW, LeadStatus.QUALIFYING):
        lead.status = LeadStatus.QUALIFIED
    await db.flush()
    return {"score": score, "tier": tier.value}


async def assign_employee(db: AsyncSession, lead: Lead) -> dict[str, Any]:
    """Deterministic round-robin, priority-weighted assignment. Idempotent —
    an already-assigned lead keeps its owner (no double assignment)."""
    if lead.assigned_employee_id is not None:
        result = await db.execute(
            select(Employee).where(Employee.id == lead.assigned_employee_id)
        )
        existing = result.scalar_one_or_none()
        if existing is not None:
            return {
                "assigned": True,
                "employee_name": existing.name,
                "employee_id": existing.id,
                "note": "already assigned",
            }
    if lead.tier is None:  # scoring is a precondition; run it rather than fail
        await score_lead(db, lead)
    employee = await _assign_employee(db, lead)
    if employee is None:
        return {"assigned": False, "error": "No active employees to assign to."}
    await db.flush()
    return {"assigned": True, "employee_name": employee.name, "employee_id": employee.id}


async def search_knowledge_base(
    db: AsyncSession, lead: Lead, question: str
) -> dict[str, Any]:
    """RAG lookup over the business's uploaded documents (FAQs, brochures...)."""
    hits = await search_documents(db, question, k=4)
    hits = [h for h in hits if h.score >= 0.3]
    return {
        "count": len(hits),
        "passages": [{"source": h.filename, "content": h.content} for h in hits],
    }


async def handover_to_human(
    db: AsyncSession, lead: Lead, reason: str | None = None
) -> dict[str, Any]:
    """Route the conversation to a person; assigns an owner if none yet."""
    if lead.assigned_employee_id is None:
        result = await assign_employee(db, lead)
        if not result.get("assigned"):
            return {"handed_over": False, "error": result.get("error")}
    logger.info("Lead %s handed over to human (reason=%r)", lead.id, reason)
    return {"handed_over": True, "employee_id": lead.assigned_employee_id}


# ---------------------------------------------------------------------------
# OpenAI function schemas — the model-facing contract
# ---------------------------------------------------------------------------

TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "search_properties",
            "description": (
                "Search the property inventory. Call once you know at least the "
                "location and BHK (budget optional). Prices are absolute INR "
                "(e.g. 80 lakh = 8000000, 1.2 crore = 12000000)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {"type": "string", "description": "Area/locality/city"},
                    "bhk": {"type": "integer", "description": "Bedrooms, e.g. 2 for 2BHK"},
                    "min_price": {"type": "integer", "description": "Min budget in INR"},
                    "max_price": {"type": "integer", "description": "Max budget in INR"},
                    "limit": {"type": "integer", "description": "Max results (default 3)"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "save_lead_answers",
            "description": (
                "Persist qualification answers the moment the lead reveals them. "
                "Convert budgets to absolute INR. Map free-text answers onto the "
                "enum values exactly."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "location": {"type": "string"},
                    "bhk": {"type": "integer"},
                    "budget_min": {"type": "integer", "description": "INR"},
                    "budget_max": {"type": "integer", "description": "INR"},
                    "timeline": {"type": "string", "enum": list(TIMELINES)},
                    "purpose": {"type": "string", "enum": list(PURPOSES)},
                    "financing": {"type": "string", "enum": list(FINANCING)},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "capture_contact",
            "description": (
                "Store the lead's email and/or phone for the callback. Call as "
                "soon as they share contact details."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "email": {"type": "string"},
                    "phone": {"type": "string"},
                    "name": {"type": "string"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "score_lead",
            "description": (
                "Score the lead from the answers saved so far (rules-based, "
                "deterministic). Call after the qualification questions are "
                "answered (or the lead stops answering)."
            ),
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "assign_employee",
            "description": (
                "Assign the lead to a team member (deterministic round-robin). "
                "Call after capturing contact details, or when handing over."
            ),
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_knowledge_base",
            "description": (
                "Look up factual questions (amenities, legal/loan process, "
                "project details) in the business's knowledge base. Use before "
                "answering any factual question you are not sure about."
            ),
            "parameters": {
                "type": "object",
                "properties": {"question": {"type": "string"}},
                "required": ["question"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "handover_to_human",
            "description": (
                "Route the chat to a human team member when the lead asks for a "
                "person, is frustrated, or the request is beyond your scope."
            ),
            "parameters": {
                "type": "object",
                "properties": {"reason": {"type": "string"}},
            },
        },
    },
]

# Dispatcher used by the agent loop.
EXECUTORS = {
    "search_properties": search_properties,
    "save_lead_answers": save_lead_answers,
    "capture_contact": capture_contact,
    "score_lead": score_lead,
    "assign_employee": assign_employee,
    "search_knowledge_base": search_knowledge_base,
    "handover_to_human": handover_to_human,
}


def _lead_state(lead: Lead) -> dict[str, Any]:
    """Compact snapshot of what we already know — injected into the system prompt."""
    return {
        "name": lead.name,
        "location": lead.location,
        "bhk": lead.bhk,
        "budget_min": lead.budget_min,
        "budget_max": lead.budget_max,
        "timeline": lead.timeline,
        "purpose": lead.purpose,
        "financing": lead.financing,
        "email": lead.email,
        "phone": lead.phone,
        "score": lead.score,
        "tier": lead.tier.value if lead.tier else None,
        "status": lead.status.value,
    }
