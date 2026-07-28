from sqlalchemy import Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin
from app.models.enums import ListingType, pg_enum


class Property(Base, TimestampMixin):
    __tablename__ = "properties"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    location: Mapped[str] = mapped_column(String(255), nullable=False)
    bhk: Mapped[int] = mapped_column(Integer, nullable=False)
    # How the property is offered. SALE => `price` is the total; RENT/LEASE =>
    # `rent_pm` is the monthly amount (and `price` is null).
    listing_type: Mapped[ListingType] = mapped_column(
        pg_enum(ListingType, "listing_type"),
        nullable=False,
        default=ListingType.SALE,
    )
    price: Mapped[int | None] = mapped_column(Integer)      # total INR (sale)
    rent_pm: Mapped[int | None] = mapped_column(Integer)    # monthly INR (rent/lease)
    area_sqft: Mapped[int | None] = mapped_column(Integer)
    description: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        # Supports the parameterized property-search query (type, location, bhk).
        Index(
            "ix_properties_type_location_bhk",
            "listing_type", "location", "bhk",
        ),
    )
