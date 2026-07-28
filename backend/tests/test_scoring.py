"""Tier classification tests for the deterministic lead scorer.

score_lead is a pure function over a Lead's stored answers, so these tests build
Lead instances in memory (no DB session) and assert on score + tier. They pin
both the tier for representative Hot/Warm/Cold profiles and the exact behavior at
the two threshold boundaries.
"""
import pytest

from app.agent.scoring import HOT_THRESHOLD, WARM_THRESHOLD, score_lead
from app.models.enums import LeadTier
from app.models.lead import Lead


def make_lead(**answers) -> Lead:
    """A Lead carrying only the qualification answers score_lead reads.

    SQLAlchemy models can be instantiated without a session; we never persist.
    """
    return Lead(**answers)


# --- Representative profiles per tier -------------------------------------

HOT_CASES = [
    pytest.param(
        dict(
            budget_min=8_000_000, budget_max=12_000_000, timeline="0-3_months",
            purpose="own_use", financing="ready_cash", location="Whitefield",
            bhk=3, email="a@x.com", phone="999",
        ),
        100,
        id="hot-full-profile-cash-now",
    ),
    pytest.param(
        dict(
            budget_max=6_000_000, timeline="3-6_months", purpose="investment",
            financing="loan_approved", location="HSR", bhk=2, phone="888",
        ),
        83,
        id="hot-investor-loan-approved",
    ),
]

WARM_CASES = [
    pytest.param(
        dict(
            budget_max=5_000_000, timeline="6-12_months", purpose="own_use",
            location="Indiranagar", bhk=2,
        ),
        63,
        id="warm-no-contact",
    ),
    pytest.param(
        dict(
            budget_min=3_000_000, timeline="unknown", purpose="exploring",
            financing="not_sure", location="Koramangala", bhk=1, email="w@x.com",
        ),
        52,
        id="warm-exploring-with-contact",
    ),
]

COLD_CASES = [
    pytest.param(dict(email="c@x.com"), 10, id="cold-contact-only"),
    pytest.param(dict(), 0, id="cold-empty"),
]


@pytest.mark.parametrize("answers,expected_score", HOT_CASES)
def test_hot_leads(answers, expected_score):
    score, tier = score_lead(make_lead(**answers))
    assert tier is LeadTier.HOT
    assert score == expected_score


@pytest.mark.parametrize("answers,expected_score", WARM_CASES)
def test_warm_leads(answers, expected_score):
    score, tier = score_lead(make_lead(**answers))
    assert tier is LeadTier.WARM
    assert score == expected_score


@pytest.mark.parametrize("answers,expected_score", COLD_CASES)
def test_cold_leads(answers, expected_score):
    score, tier = score_lead(make_lead(**answers))
    assert tier is LeadTier.COLD
    assert score == expected_score


# --- Threshold boundaries (inclusive lower bound) --------------------------

def test_warm_boundary_is_inclusive():
    # budget 30 + purpose investment 10 == 40 == WARM_THRESHOLD
    score, tier = score_lead(make_lead(budget_max=1, purpose="investment"))
    assert score == WARM_THRESHOLD == 40
    assert tier is LeadTier.WARM


def test_just_below_warm_is_cold():
    # budget 30 + timeline 6-12mo 8 == 38
    score, tier = score_lead(make_lead(budget_max=1, timeline="6-12_months"))
    assert score == 38
    assert tier is LeadTier.COLD


def test_hot_boundary_is_inclusive():
    # budget 30 + timeline 0-3mo 25 + purpose own_use 15 == 70 == HOT_THRESHOLD
    score, tier = score_lead(
        make_lead(budget_max=1, timeline="0-3_months", purpose="own_use")
    )
    assert score == HOT_THRESHOLD == 70
    assert tier is LeadTier.HOT


def test_just_below_hot_is_warm():
    # budget 30 + timeline 25 + financing loan_approved 8 + location 5 == 68
    score, tier = score_lead(
        make_lead(
            budget_max=1, timeline="0-3_months",
            financing="loan_approved", location="X",
        )
    )
    assert score == 68
    assert tier is LeadTier.WARM


def test_score_is_capped_at_100():
    score, _ = score_lead(
        make_lead(
            budget_min=1, budget_max=2, timeline="0-3_months", purpose="own_use",
            financing="ready_cash", location="X", bhk=2, email="e@x.com",
            phone="1",
        )
    )
    assert score == 100


def test_scoring_is_deterministic():
    answers = dict(budget_max=5_000_000, timeline="3-6_months", purpose="own_use")
    first = score_lead(make_lead(**answers))
    second = score_lead(make_lead(**answers))
    assert first == second
