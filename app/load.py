import json
from pathlib import Path

from app.db.base import SessionLocal
from app.db.crud import upsert_listings
from app.models import normalize



def load_file(path: str, vertical: str):
    raw_ads = json.loads(Path(path).read_text(encoding="utf-8"))
    by_id = {ad["id"]: ad for ad in raw_ads}
    return [normalize(ad, vertical) for ad in by_id.values()]


def main():
    cars = load_file("data/cars.json", "car")
    mcs = load_file("data/mcs.json", "mc")

    with SessionLocal() as session:
        upsert_listings(session, cars + mcs)
        session.commit()

    print(f'Upserted {len(cars)} cars and {len(mcs)} motorcycles.')

if __name__ == "__main__":
    main()