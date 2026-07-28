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

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.assignment import assign_employee as _assign_employee
from app.agent.scoring import FINANCING, PURPOSES, TIMELINES, score_lead as _score_lead
from app.models.employee import Employee
from app.models.enums import LeadStatus, ListingType
from app.models.lead import Lead
from app.models.property import Property
from app.retrieval import search_documents

logger = logging.getLogger("agent.tools")

# ---------------------------------------------------------------------------
# Executors — each takes (db, lead, **args from the model)
# ---------------------------------------------------------------------------


# Common alternate city spellings → the name used in inventory. Leads type
# "Bengaluru"/"Bombay"/"Gurugram" constantly; the catalogue uses one spelling.
_CITY_ALIASES = {
    "bengaluru": "Bangalore",
    "bengalooru": "Bangalore",
    "bangalooru": "Bangalore",
    "bombay": "Mumbai",
    "gurugram": "Gurgaon",
    "calcutta": "Kolkata",
    "madras": "Chennai",
    "new delhi": "Delhi",
    "ncr": "Delhi",
}


def _normalize_location(location: str) -> str:
    """Map a lead's free-text location onto the catalogue's spelling. Matches the
    whole string or a trailing '<area>, <city>' token, so 'Bengaluru' and
    'Whitefield, Bengaluru' both resolve to 'Bangalore'."""
    raw = location.strip()
    key = raw.lower()
    if key in _CITY_ALIASES:
        return _CITY_ALIASES[key]
    # '<area>, <city>' — normalize just the city part if it's an alias.
    if "," in raw:
        area, _, city = raw.rpartition(",")
        city_key = city.strip().lower()
        if city_key in _CITY_ALIASES:
            return f"{area.strip()}, {_CITY_ALIASES[city_key]}"
    return raw


def _price_col(listing_type: ListingType):
    """The price column that carries meaning for this listing type."""
    return Property.price if listing_type == ListingType.SALE else Property.rent_pm


def _serialize_property(p: Property) -> dict[str, Any]:
    is_sale = p.listing_type == ListingType.SALE
    return {
        "id": p.id,
        "title": p.title,
        "location": p.location,
        "bhk": p.bhk,
        "listing_type": p.listing_type.value,
        # One price field, unit implied by listing_type: total for sale,
        # monthly for rent/lease.
        "price_inr": p.price if is_sale else p.rent_pm,
        "price_unit": "total" if is_sale else "per_month",
        "area_sqft": p.area_sqft,
        "description": p.description,
    }


async def search_properties(
    db: AsyncSession,
    lead: Lead,
    location: str | None = None,
    bhk: int | None = None,
    listing_type: str | None = None,
    min_price: int | None = None,
    max_price: int | None = None,
    limit: int = 3,
) -> dict[str, Any]:
    """Parameterized, indexed property lookup (no vector search, no raw SQL).

    listing_type is 'sale' | 'rent' | 'lease' — defaults to 'sale'. Budget is
    matched against the total price for sale, or the monthly amount for
    rent/lease. If nothing matches within budget, falls back to the closest
    listings by price (same type/location/BHK) and flags the result.
    """
    lt = ListingType(listing_type) if listing_type in {e.value for e in ListingType} \
        else ListingType.SALE
    price_col = _price_col(lt)
    limit = max(1, min(limit, 10))

    base = select(Property).where(Property.listing_type == lt)
    if location:
        base = base.where(Property.location.ilike(f"%{_normalize_location(location)}%"))
    if bhk is not None:
        base = base.where(Property.bhk == bhk)

    # 1) Strict pass — honour the budget.
    stmt = base
    if min_price is not None:
        stmt = stmt.where(price_col >= min_price)
    if max_price is not None:
        stmt = stmt.where(price_col <= max_price)
    result = await db.execute(stmt.order_by(price_col).limit(limit))
    props = list(result.scalars().all())
    if props:
        return {
            "count": len(props),
            "fallback": False,
            "listing_type": lt.value,
            "properties": [_serialize_property(p) for p in props],
        }

    # 2) Nearest-match fallback — drop the budget filter, order by closeness to
    # the requested budget (its midpoint, or whichever bound was given).
    target = None
    if min_price is not None and max_price is not None:
        target = (min_price + max_price) // 2
    elif max_price is not None:
        target = max_price
    elif min_price is not None:
        target = min_price

    order = func.abs(price_col - target) if target is not None else price_col
    result = await db.execute(base.order_by(order).limit(limit))
    near = list(result.scalars().all())
    return {
        "count": len(near),
        "fallback": bool(near),  # these are closest-by-price, not in-budget
        "listing_type": lt.value,
        "properties": [_serialize_property(p) for p in near],
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
    # Silence the AI qualifier — the assigned human now owns this chat. The
    # widget route checks this flag and stops calling the agent. Persisted on
    # the caller's commit (lead is a tracked ORM object; no db.execute needed).
    lead.is_bot_active = False
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
                "Search the property inventory. Call once you know the location, "
                "BHK, and whether the lead wants to buy or rent (budget optional). "
                "For sale, budget is the total price in INR (80 lakh = 8000000). "
                "For rent/lease, budget is the MONTHLY amount in INR (25k = 25000). "
                "If nothing fits the budget, the result comes back with "
                "\"fallback\": true and the closest listings — present those as "
                "near matches, not exact ones."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {"type": "string", "description": "Area/locality/city"},
                    "bhk": {"type": "integer", "description": "Bedrooms, e.g. 2 for 2BHK"},
                    "listing_type": {
                        "type": "string",
                        "enum": ["sale", "rent", "lease"],
                        "description": "Buy=sale, rent, or lease. Default sale.",
                    },
                    "min_price": {
                        "type": "integer",
                        "description": "Min budget INR — total for sale, monthly for rent/lease",
                    },
                    "max_price": {
                        "type": "integer",
                        "description": "Max budget INR — total for sale, monthly for rent/lease",
                    },
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
