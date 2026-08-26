"""employee is_online presence flag

Separates presence from account status. `is_active` becomes purely the admin
enable/disable switch (login blocks inactive accounts); `is_online` tracks
session presence — set false on logout, true on login. Existing employees
default to online=false (no live sessions across a migration).

Revision ID: 0010
Revises: 0009
Create Date: 2026-08-19

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0010"
down_revision: Union[str, None] = "0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "employees",
        sa.Column(
            "is_online",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    op.drop_column("employees", "is_online")
