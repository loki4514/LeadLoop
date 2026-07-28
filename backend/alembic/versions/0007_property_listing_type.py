"""property listing type (sale/rent/lease) + monthly rent

Adds a listing_type enum and a rent_pm column so inventory can be offered for
sale, rent, or lease. Existing rows are sale listings (their `price` is the
total sale value); rent/lease listings use `rent_pm` (monthly INR) instead.

`price` becomes nullable — rent/lease rows have no sale price.

Revision ID: 0007
Revises: 0006
Create Date: 2026-07-17

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

LISTING_TYPE = sa.Enum("sale", "rent", "lease", name="listing_type")


def upgrade() -> None:
    bind = op.get_bind()
    LISTING_TYPE.create(bind, checkfirst=True)

    op.add_column(
        "properties",
        sa.Column(
            "listing_type",
            LISTING_TYPE,
            nullable=False,
            server_default="sale",  # existing rows are sale listings
        ),
    )
    op.add_column(
        "properties",
        sa.Column("rent_pm", sa.Integer(), nullable=True),
    )
    # Sale price no longer required (rent/lease rows have none).
    op.alter_column("properties", "price", existing_type=sa.Integer(), nullable=True)

    # Swap the old (location, bhk, price) index for a (type, location, bhk) one.
    op.drop_index("ix_properties_location_bhk_price", table_name="properties")
    op.create_index(
        "ix_properties_type_location_bhk",
        "properties",
        ["listing_type", "location", "bhk"],
    )

    # Drop the server_default now that existing rows are backfilled; the model
    # supplies the default for new inserts.
    op.alter_column("properties", "listing_type", server_default=None)


def downgrade() -> None:
    op.drop_index("ix_properties_type_location_bhk", table_name="properties")
    op.create_index(
        "ix_properties_location_bhk_price",
        "properties",
        ["location", "bhk", "price"],
    )
    op.alter_column("properties", "price", existing_type=sa.Integer(), nullable=False)
    op.drop_column("properties", "rent_pm")
    op.drop_column("properties", "listing_type")
    LISTING_TYPE.drop(op.get_bind(), checkfirst=True)
