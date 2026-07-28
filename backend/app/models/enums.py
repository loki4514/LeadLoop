import enum

from sqlalchemy import Enum as SAEnum


def pg_enum(enum_cls: type[enum.Enum], name: str) -> SAEnum:
    """Build a SQLAlchemy Enum that stores the enum *value* (lowercase), not the
    member *name*. The Postgres type was created from the values, so we must
    persist values to match."""
    return SAEnum(
        enum_cls,
        name=name,
        values_callable=lambda e: [member.value for member in e],
    )


class Role(str, enum.Enum):
    EMPLOYEE = "employee"
    ADMIN = "admin"


class LeadTier(str, enum.Enum):
    HOT = "hot"
    WARM = "warm"
    COLD = "cold"


class LeadStatus(str, enum.Enum):
    NEW = "new"
    QUALIFYING = "qualifying"
    QUALIFIED = "qualified"
    ASSIGNED = "assigned"
    CLOSED = "closed"


class MessageSender(str, enum.Enum):
    LEAD = "lead"
    AGENT = "agent"
    EMPLOYEE = "employee"


class AuditAction(str, enum.Enum):
    """A recorded change to a lead, for the lightweight audit trail."""

    EDITED = "edited"                # a detail field changed
    TIER_CHANGED = "tier_changed"    # warm/cold/hot set by a human
    REASSIGNED = "reassigned"        # owner changed (admin only)
    DELETED = "deleted"              # lead deleted (admin only)


class ListingType(str, enum.Enum):
    """How a property is offered. Drives which price column is meaningful:
    SALE uses ``price`` (total INR); RENT/LEASE use ``rent_pm`` (monthly INR)."""

    SALE = "sale"
    RENT = "rent"
    LEASE = "lease"


class DocumentStatus(str, enum.Enum):
    PENDING = "pending"        # uploaded, queued for ingestion
    PROCESSING = "processing"  # worker is extracting/embedding
    READY = "ready"            # chunks embedded and stored
    FAILED = "failed"          # ingestion errored (see error field)
