from pydantic import BaseModel

class Listing(BaseModel):
    id: int
    url: str
    location: str
    price_sek: int | None
    year: int
    mileage_km: int | None
    make: str
    model: str | None
    model_specification: str | None

def normalize(raw: dict) -> Listing:
    mileage = raw.get("mileage")
    return Listing(
        id=raw["id"],
        url=raw["canonical_url"],
        location=raw["location"],
        price_sek=(raw.get("price") or {}).get("amount"),
        year=raw["year"],
        mileage_km=mileage * 10 if mileage is not None else None,
        make=raw["make"],
        model=raw.get("model"),
        model_specification=raw.get("model_specification"),
    )