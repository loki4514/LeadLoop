"""Deterministic, rules-based lead scoring.

This is intentionally NOT an LLM call. The agent's only job is to normalize the
lead's answers into the enum values below (via the save_lead_answers tool);
scoring itself is a pure function so it is auditable, testable, and never
hallucinates a tier.

Weights follow the product spec: budget is the heaviest qualifier, then
timeline, then purchase purpose, then financing readiness. Contact capture and
basic search criteria add smaller amounts.
"""
from app.models.enums import LeadTier
from app.models.lead import Lead

# Enum values the agent is allowed to produce (also enforced in the tool schema).
TIMELINES = ("0-3_months", "3-6_months", "6-12_months", "12_plus_months", "unknown")
PURPOSES = ("own_use", "investment", "exploring")
FINANCING = ("ready_cash", "loan_approved", "loan_needed", "not_sure")

_TIMELINE_POINTS = {
    "0-3_months": 25,
    "3-6_months": 15,
    "6-12_months": 8,
    "12_plus_months": 3,
    "unknown": 0,
}
_PURPOSE_POINTS = {"own_use": 15, "investment": 10, "exploring": 0}
_FINANCING_POINTS = {
    "ready_cash": 10,
    "loan_approved": 8,
    "loan_needed": 5,
    "not_sure": 2,
}

HOT_THRESHOLD = 70
WARM_THRESHOLD = 40


def score_lead(lead: Lead) -> tuple[int, LeadTier]:
    """Score a lead from its stored qualification answers.

    Returns (score 0-100, tier). Deterministic — same answers, same result.
    """
    score = 0

    # Budget — the biggest serious-vs-browsing signal (max 30).
    if lead.budget_min is not None or lead.budget_max is not None:
        score += 30

    score += _TIMELINE_POINTS.get(lead.timeline or "", 0)  # max 25
    score += _PURPOSE_POINTS.get(lead.purpose or "", 0)  # max 15
    score += _FINANCING_POINTS.get(lead.financing or "", 0)  # max 10

    # Search criteria known — the lead engaged with the funnel (max 10).
    if lead.location:
        score += 5
    if lead.bhk is not None:
        score += 5

    # Reachable — contact details captured (max 10).
    if lead.email or lead.phone:
        score += 10

    score = min(score, 100)
    if score >= HOT_THRESHOLD:
        tier = LeadTier.HOT
    elif score >= WARM_THRESHOLD:
        tier = LeadTier.WARM
    else:
        tier = LeadTier.COLD
    return score, tier
