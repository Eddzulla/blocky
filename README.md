# blocky

Collects car and motorcycle listings from blocket.se, stores them in PostgreSQL, and shows them in a React frontend.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install blocket-api httpx beautifulsoup4
python blocky.py
```

## Stack

- **Fetching:** [`blocket-api`](https://github.com/dunderrrrrr/blocket_api) (calls blocket.se directly)
- **Database:** PostgreSQL, SQLAlchemy, Alembic
- **API:** FastAPI
- **Frontend:** React + Vite + TypeScript

## Notes

- `search_car()` / `search_mc()` take enum lists: `models=[CarModel.HONDA]`.
- `get_ad()` needs an ad object: `api.get_ad(CarAd(ad["id"]))`.
- Listings are in `results["docs"]`, 50 per page, max 50 pages per query. Split large queries by price range.
- `price` is a dict (`price["amount"]`). `mileage` is in Swedish mil (×10 for km).
- The car endpoint includes used, new and leasing listings. Filter on `sales_form`.
- Don't store personal data: `regno`, `chassis_number`, `coordinates`, seller details.

## Roadmap

1. Fetch listings and save them to JSON
2. Normalize the data with Pydantic
3. Store it in Postgres (upserts and price history)
4. Schedule updates
5. FastAPI endpoints
6. React UI
