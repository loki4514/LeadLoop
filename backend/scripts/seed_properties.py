"""Seed demo property inventory (idempotent — skips if any properties exist).

Run inside the backend container:
    python -m scripts.seed_properties
"""
from sqlalchemy import select

from app.db.sync_session import SyncSessionLocal
from app.models.property import Property

LAKH = 100_000
CRORE = 100 * LAKH

PROPERTIES = [
    ("Sunrise Residency — 2BHK", "Whitefield, Bangalore", 2, 78 * LAKH, 1120,
     "East-facing 2BHK with balcony, covered parking, clubhouse and pool. 5 min from ITPL."),
    ("Green Meadows — 2BHK", "Whitefield, Bangalore", 2, 92 * LAKH, 1240,
     "Corner unit in a gated community with gym, kids' play area and 24x7 security."),
    ("Lakeview Heights — 3BHK", "Whitefield, Bangalore", 3, int(1.35 * CRORE), 1680,
     "Lake-facing 3BHK with servant room, two parking slots, premium fittings."),
    ("Metro Park — 1BHK", "Indiranagar, Bangalore", 1, 65 * LAKH, 720,
     "Compact 1BHK, 300m from the metro station. Ideal rental investment."),
    ("Heritage Court — 2BHK", "Indiranagar, Bangalore", 2, int(1.15 * CRORE), 1150,
     "Quiet tree-lined street, renovated interiors, terrace garden access."),
    ("Skyline Towers — 3BHK", "HSR Layout, Bangalore", 3, int(1.6 * CRORE), 1850,
     "High-floor 3BHK with city views, modular kitchen, EV charging."),
    ("Palm Grove — 2BHK", "HSR Layout, Bangalore", 2, 98 * LAKH, 1180,
     "Ready-to-move 2BHK next to 27th Main; park-facing block."),
    ("Riverdale Villas — 4BHK Villa", "Sarjapur Road, Bangalore", 4, int(2.4 * CRORE), 2900,
     "Independent villa with private garden, solar water heating, gated enclave."),
    ("Urban Nest — 1BHK", "Electronic City, Bangalore", 1, 42 * LAKH, 650,
     "Budget-friendly 1BHK near Phase 1 tech parks. High rental demand."),
    ("Orchid Enclave — 3BHK", "Sarjapur Road, Bangalore", 3, int(1.2 * CRORE), 1560,
     "Spacious 3BHK beside an international school; large clubhouse."),
]


def main() -> None:
    db = SyncSessionLocal()
    try:
        if db.execute(select(Property.id).limit(1)).first():
            print("Properties already seeded — skipping.")
            return
        for title, location, bhk, price, area, desc in PROPERTIES:
            db.add(Property(
                title=title, location=location, bhk=bhk, price=price,
                area_sqft=area, description=desc,
            ))
        db.commit()
        print(f"Seeded {len(PROPERTIES)} properties.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
