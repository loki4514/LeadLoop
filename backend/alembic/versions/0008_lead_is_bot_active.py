"""lead is_bot_active flag for human takeover

True while the AI qualifier drives the chat; flipped false on handover so the
agent stops replying and a person takes over. Existing leads default to true
(none are mid-handover).

Revision ID: 0008
Revises: 0007
Create Date: 2026-07-17

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0008"
down_revision: Union[str, None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "leads",
        sa.Column(
            "is_bot_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
    )


def downgrade() -> None:
    op.drop_column("leads", "is_bot_active")
