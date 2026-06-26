import enum


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
