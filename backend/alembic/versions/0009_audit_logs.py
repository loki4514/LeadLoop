"""audit_logs — lightweight lead change history

Records who did what to a lead (edited / tier_changed / reassigned / deleted),
with old→new values for field changes. Rendered as a timeline on the lead page.

Revision ID: 0009
Revises: 0008
Create Date: 2026-07-24

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0009"
down_revision: Union[str, None] = "0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

AUDIT_ACTION = sa.Enum(
    "edited", "tier_changed", "reassigned", "deleted", name="audit_action"
)


def upgrade() -> None:
    # Let create_table create the enum type inline, exactly once. (An explicit
    # .create() in addition caused a duplicate CREATE TYPE.)
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "lead_id",
            sa.Integer(),
            sa.ForeignKey("leads.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "actor_employee_id",
            sa.Integer(),
            sa.ForeignKey("employees.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("action", AUDIT_ACTION, nullable=False),
        sa.Column("field", sa.String(length=64), nullable=True),
        sa.Column("old_value", sa.Text(), nullable=True),
        sa.Column("new_value", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_audit_logs_lead_id", "audit_logs", ["lead_id"])


def downgrade() -> None:
    op.drop_index("ix_audit_logs_lead_id", table_name="audit_logs")
    op.drop_table("audit_logs")
    AUDIT_ACTION.drop(op.get_bind(), checkfirst=True)
