import json
from pathlib import Path
from pydantic import ValidationError
from app.models import normalize

raw_ads = json.loads(Path("data/cars.json").read_text(encoding="utf-8"))

listings, errors = [], 0
for raw in raw_ads:
    try:
        listings.append(normalize(raw))
    except (ValidationError, KeyError) as e:
        errors += 1
        print(raw.get("id"), e)

print(f"{len(listings)} ok, {errors} errors")
print(listings[0])
