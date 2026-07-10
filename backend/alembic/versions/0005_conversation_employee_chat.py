"""support employee-owned conversations for the internal RAG chat

The internal knowledge-base chat is used by a logged-in employee, not a lead,
so a conversation must be able to belong to EITHER a lead or an employee:

- make ``conversations.lead_id`` nullable,
- add nullable ``conversations.employee_id`` (FK -> employees, ON DELETE CASCADE),
- add ``conversations.title`` for a human-readable thread label,
- add ``messages.sources`` (JSONB) to persist the RAG citations of an answer.

Revision ID: 0005
Revises: 0004
Create Date: 2026-07-09

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("conversations", "lead_id", existing_type=sa.Integer(), nullable=True)
    op.add_column("conversations", sa.Column("employee_id", sa.Integer(), nullable=True))
    op.add_column("conversations", sa.Column("title", sa.String(length=255), nullable=True))
    op.create_index(
        "ix_conversations_employee_id", "conversations", ["employee_id"]
    )
    op.create_foreign_key(
        "fk_conversations_employee_id_employees",
        "conversations",
        "employees",
        ["employee_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.add_column(
        "messages",
        sa.Column("sources", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("messages", "sources")
    op.drop_constraint(
        "fk_conversations_employee_id_employees", "conversations", type_="foreignkey"
    )
    op.drop_index("ix_conversations_employee_id", table_name="conversations")
    op.drop_column("conversations", "title")
    op.drop_column("conversations", "employee_id")
    # Restore NOT NULL. Any employee-owned rows (lead_id IS NULL) would violate
    # this, so remove them first — they belong to the reverted feature.
    op.execute("DELETE FROM conversations WHERE lead_id IS NULL")
    op.alter_column("conversations", "lead_id", existing_type=sa.Integer(), nullable=False)
