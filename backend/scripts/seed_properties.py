"""Seed demo property inventory (idempotent — skips if any properties exist).

Generates a realistic, deterministic catalogue across major Indian metros so the
qualifier agent has broad inventory to match against (and realistic no-match
cases). Deterministic on purpose: no randomness, so reruns are reproducible and
the "skip if already seeded" guard stays meaningful.

Run inside the backend container:
    python -m scripts.seed_properties
"""
from sqlalchemy import select

from app.db.sync_session import SyncSessionLocal
from app.models.enums import ListingType
from app.models.property import Property

LAKH = 100_000
CRORE = 100 * LAKH

# Per-city catalogue. Each area carries a base 1BHK price (INR) reflecting that
# micro-market; larger configs scale off it. Ordered roughly premium → value.
# (city, [(area, base_1bhk_price), ...])
CITIES = [
    ("Bangalore", [
        ("Indiranagar", 65 * LAKH),
        ("HSR Layout", 60 * LAKH),
        ("Whitefield", 45 * LAKH),
        ("Sarjapur Road", 48 * LAKH),
        ("Electronic City", 40 * LAKH),
    ]),
    ("Mumbai", [
        ("Bandra West", int(2.2 * CRORE)),
        ("Powai", int(1.1 * CRORE)),
        ("Andheri West", 95 * LAKH),
        ("Thane West", 60 * LAKH),
        ("Navi Mumbai", 55 * LAKH),
    ]),
    ("Delhi", [
        ("Dwarka", 70 * LAKH),
        ("Saket", 90 * LAKH),
        ("Rohini", 55 * LAKH),
    ]),
    ("Gurgaon", [
        ("Golf Course Road", int(1.0 * CRORE)),
        ("Sohna Road", 60 * LAKH),
        ("Sector 62", 55 * LAKH),
    ]),
    ("Noida", [
        ("Sector 50", 65 * LAKH),
        ("Sector 137", 48 * LAKH),
        ("Greater Noida West", 38 * LAKH),
    ]),
    ("Pune", [
        ("Kharadi", 55 * LAKH),
        ("Hinjewadi", 45 * LAKH),
        ("Wakad", 42 * LAKH),
        ("Baner", 60 * LAKH),
    ]),
    ("Hyderabad", [
        ("Jubilee Hills", 85 * LAKH),
        ("Gachibowli", 55 * LAKH),
        ("Kondapur", 48 * LAKH),
        ("Tellapur", 42 * LAKH),
    ]),
    ("Chennai", [
        ("Adyar", 80 * LAKH),
        ("OMR", 45 * LAKH),
        ("Anna Nagar", 65 * LAKH),
        ("Velachery", 55 * LAKH),
    ]),
    ("Kolkata", [
        ("Ballygunge", 60 * LAKH),
        ("Salt Lake", 45 * LAKH),
        ("New Town", 38 * LAKH),
    ]),
]

# Config scaling off the area's base 1BHK price. (bhk, price_multiplier,
# area_sqft, label, descriptor)
CONFIGS = [
    (1, 1.00, 640, "1BHK", "Compact {bhk} in {area}, {city} — ideal first home or rental."),
    (2, 1.55, 1080, "2BHK", "Well-planned {bhk} in {area}, {city} with balcony and covered parking."),
    (2, 1.75, 1220, "2BHK", "Premium {bhk} in {area}, {city} — corner unit, park-facing block."),
    (3, 2.30, 1580, "3BHK", "Spacious {bhk} in {area}, {city} with modular kitchen and two parkings."),
    (3, 2.70, 1780, "3BHK", "High-floor {bhk} in {area}, {city} with city views and premium fittings."),
    (4, 3.60, 2600, "4BHK", "Expansive {bhk} in {area}, {city} — servant room, private terrace."),
]

# Rotating naming pool so titles read like real projects, deterministically.
NAMES = [
    "Sunrise Residency", "Green Meadows", "Lakeview Heights", "Metro Park",
    "Heritage Court", "Skyline Towers", "Palm Grove", "Riverdale",
    "Urban Nest", "Orchid Enclave", "Sea Breeze", "Marine Crest",
    "Golf Green", "Cyber Greens", "Capital Court", "Tech Ridge",
    "Riverwood", "Green Vista", "Jubilee Court", "Marina Vista",
    "Signature One", "Emerald Bay", "Silver Oak", "Maple Woods",
    "Crown Plaza", "Serene Gardens", "Horizon", "The Address",
]

AMENITIES = [
    "Clubhouse, gym and swimming pool.",
    "24x7 security with power backup and covered parking.",
    "Landscaped podium, kids' play area and jogging track.",
    "Rooftop lounge, EV charging and visitor parking.",
    "Gated community with retail plaza and daycare.",
]


# Rough gross rental yield used to derive a realistic monthly rent from a sale
# value (~3.5% annual is typical for Indian residential). Lease priced a touch
# below rent.
RENT_YIELD_ANNUAL = 0.035
LEASE_FACTOR = 0.92


def _round_sale(price: int) -> int:
    """Round to a tidy figure — nearest lakh below a crore, else nearest 5 lakh."""
    if price < CRORE:
        return round(price / LAKH) * LAKH
    return round(price / (5 * LAKH)) * (5 * LAKH)


def _round_rent(rent: int) -> int:
    """Round monthly rent to the nearest ₹500 for tidy figures."""
    return max(5_000, round(rent / 500) * 500)


def _build() -> list[dict]:
    """Every area yields the full config spread in all three listing types."""
    rows: list[dict] = []
    name_i = 0
    for city, areas in CITIES:
        for area, base in areas:
            for bhk, mult, sqft, label, desc_tmpl in CONFIGS:
                sale = _round_sale(int(base * mult))
                monthly = int(sale * RENT_YIELD_ANNUAL / 12)
                location = f"{area}, {city}"
                base_desc = desc_tmpl.format(bhk=label, area=area, city=city)
                for lt in (ListingType.SALE, ListingType.RENT, ListingType.LEASE):
                    name = NAMES[name_i % len(NAMES)]
                    amenity = AMENITIES[name_i % len(AMENITIES)]
                    name_i += 1
                    if lt == ListingType.SALE:
                        price, rent_pm, verb = sale, None, "for sale"
                    elif lt == ListingType.RENT:
                        price, rent_pm, verb = None, _round_rent(monthly), "for rent"
                    else:
                        price, rent_pm, verb = None, _round_rent(int(monthly * LEASE_FACTOR)), "on lease"
                    rows.append({
                        "title": f"{name} — {label}",
                        "location": location,
                        "bhk": bhk,
                        "listing_type": lt,
                        "price": price,
                        "rent_pm": rent_pm,
                        "area_sqft": sqft,
                        "description": f"{base_desc} Available {verb}. {amenity}",
                    })
    return rows


PROPERTIES = _build()


def main() -> None:
    db = SyncSessionLocal()
    try:
        if db.execute(select(Property.id).limit(1)).first():
            print("Properties already seeded — skipping.")
            return
        for row in PROPERTIES:
            db.add(Property(**row))
        db.commit()
        by_type = {lt.value: sum(1 for r in PROPERTIES if r["listing_type"] == lt)
                   for lt in ListingType}
        print(f"Seeded {len(PROPERTIES)} properties {by_type}.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
