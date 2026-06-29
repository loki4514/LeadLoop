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
