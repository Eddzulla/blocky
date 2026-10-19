import json
from pathlib import Path
from pydantic import ValidationError
from app.models import normalize

car_ads = json.loads(Path("data/cars.json").read_text(encoding="utf-8"))
mc_ads = json.loads(Path("data/mcs.json").read_text(encoding="utf-8"))

car_listings, errors = [], 0
for raw in car_ads:
    try:
        car_listings.append(normalize(raw, "car"))
    except (ValidationError, KeyError) as e:
        errors += 1
        print(raw.get("id"), e)

mc_listings, errors = [], 0

for raw in mc_ads:
    try:
        mc_listings.append(normalize(raw, "mc"))
    except (ValidationError, KeyError) as e:
        errors += 1
        print(raw.get("id"), e)

print(f"{len(car_listings)} ok, {errors} errors")
print(car_listings[0])

print(f"{len(mc_listings)} ok, {errors} errors")
print(mc_listings[0])
