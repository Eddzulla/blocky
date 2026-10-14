from pydantic import BaseModel

class Listing(BaseModel):
    id: int
    vertical: str
    url: str
    location: str
    price_sek: int | None
    year: int
    mileage_km: int | None
    make: str
    model: str | None
    model_specification: str | None

def normalize(raw: dict, vertical: str) -> Listing:
    mileage = raw.get("mileage")
    return Listing(
        id=raw["id"],
        vertical = vertical,
        url=raw["canonical_url"],
        location=raw["location"],
        price_sek=(raw.get("price") or {}).get("amount"),
        year=raw["year"],
        mileage_km=mileage * 10 if mileage is not None else None,
        make=raw["make"],
        model=raw.get("model"),
        model_specification=raw.get("model_specification"),
    )

def to_listings(raw_ads: list, vertical: str):
    by_id = {ad["id"]: ad for ad in raw_ads}
    return [normalize(ad, vertical) for ad in by_id.values()]