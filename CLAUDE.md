# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Working with this user

The user is learning and writes the code themselves. **Explain approaches and post code snippets in chat; don't edit project files unless explicitly asked.** Running read-only checks (inspecting `data/*.json`, querying the DB, running tests) to verify their work is welcome.

`PLAN.md` holds the current phase status, design decisions and known issues. Read it before suggesting next steps, and keep it updated when decisions change.

## Commands

Run everything from the project root: `alembic.ini`, `.env` and `docker-compose.yml` live there, and `app` is only importable from there. Running from `app/` gives Alembic's "No 'script_location' key found".

```bash
docker compose up -d                    # Postgres 17 (localhost:5432) + Adminer (localhost:8080)
alembic upgrade head                    # apply migrations
python blocky.py                        # fetch from Blocket → data/cars.json, data/mcs.json
python -m tests.test_normalize          # normalize every saved listing; expects "N ok, 0 errors"
docker compose exec db psql -U blocky -d blocky -c "<sql>"
```

Run modules with `python -m app.x` / `python -m tests.x`, not `python tests/x.py` (which gives `ModuleNotFoundError: app`). There's no pytest suite or linter configured; `tests/test_normalize.py` is a plain script that runs offline against `data/cars.json`.

Schema changes: edit `app/db/models.py` → `alembic revision --autogenerate -m "..."` → review the file in `alembic/versions/` → `alembic upgrade head`. `alembic/env.py` loads `DATABASE_URL` from `.env` and imports `app.db.models` to register the tables on `Base.metadata`.

## Architecture

Pipeline: **fetch → filter → normalize → upsert**, currently split into two commands with JSON files in between.

- `app/fetch.py`: uses the `blocket-api` library, which calls Blocket's internal JSON search endpoints directly (`/mobility/search/api/search/SEARCH_ID_CAR_USED` and `SEARCH_ID_MC_USED`). Results accumulate in module-level lists `car_ads` / `mc_ads`. Queries are capped at 50 pages × 50 results, so `get_cars`/`get_mcs` recursively split the price range when `match_count > 2500`. `fetch_range_*` pages through a range that fits. `save_*` applies `is_excluded` (text match against `EXCLUDE`) in place and writes JSON.
- `app/models.py`: **Pydantic** `Listing` plus `normalize(raw, vertical)`. This is the validation layer.
- `app/db/models.py`: **SQLAlchemy** `Listing` (table `listings`). This is the storage layer. Its column names deliberately match the Pydantic fields.
- `app/db/crud.py`: `upsert_listings` builds a single Postgres `INSERT ... ON CONFLICT (id) DO UPDATE` from `model_dump()` rows. The update set is derived from the dict keys, so a new field needs only the Pydantic field, the SQLAlchemy column and a migration. `first_seen` is set only on insert; `last_seen` is bumped on every upsert.
- `app/db/base.py`: engine, `SessionLocal`, `Base`. Reads `DATABASE_URL` at import time, so importing anything under `app.db` requires `.env`.

There are two classes named `Listing`. Import the table as `from app.db import models as db` (`db.Listing`).

## Blocket data gotchas

- `blocket-api` filters take **lists of enums**: `models=[CarModel.HONDA]`, `locations=[Location.SKANE]`. A bare enum or string raises `'str' object has no attribute 'value'`.
- Results: `res["docs"]` (listings), `res["metadata"]["result_size"]["match_count"]`, `res["metadata"]["paging"]["last"]`.
- `price` is a dict (`price["amount"]`). `mileage` is in Swedish mil (×10 for km) and is missing for many listings.
- `SEARCH_ID_CAR_USED` returns used, new **and** leasing listings; `sales_form` tells them apart.
- Fields such as horsepower and number of owners exist only on the listing page (`/mobility/item/<id>`, as `<dt>`/`<dd>` pairs). `blocket-api`'s `get_ad()` currently returns no specifications because its parser no longer matches the HTML.
- Raw listings include `regno`, `chassis_number` and `coordinates`. These stay in local `data/` (gitignored) and aren't normalized into the DB.
- Blocket's `robots.txt` prohibits automated crawling without permission. Keep request volume small, with delays between requests.

## Environment

`.env` (gitignored) defines `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` (used by docker-compose) and `DATABASE_URL=postgresql+psycopg://...@localhost:5432/blocky`. Adminer connects to server `db` (the compose service name), not `localhost`. If you get `role "blocky" does not exist`, another Postgres is occupying port 5432.
