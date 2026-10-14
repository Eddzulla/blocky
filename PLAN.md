# Blocky: Implementation Plan

Goal: fetch car and motorcycle listings from blocket.se, store them in PostgreSQL, serve them via FastAPI, and display them in a React frontend.

For setup and day-to-day commands, see [README.md](README.md).

---

## Status (2026-10-14)

| Phase | Status |
|---|---|
| 0. Project structure | ✅ Done (except `api/`, `scheduler.py`, `frontend/`, `requirements.txt`) |
| 1. Fetch and save to JSON | ✅ Done |
| 2. Normalize with Pydantic | ✅ Done |
| 3. Store in Postgres | 🟡 Upsert works. **Next:** connect fetch → normalize → upsert in one command |
| 4. Schedule updates | ⬜ |
| 5. FastAPI endpoints | ⬜ |
| 6. React UI | ⬜ |

**Current data:** 2,212 cars and 419 motorcycles (Skåne) in `listings`.

---

## How it works today

```
python blocky.py      → app/fetch.py: search Blocket → filter → data/cars.json, data/mcs.json
python -m app.load    → app/load.py: read JSON → dedupe by id → normalize() → upsert_listings() → commit
```

- **Fetch (`app/fetch.py`):** `blocket-api` library, `locations=[Location.SKANE]`. Recursive price-range splitting when `match_count > 2500`; paging with a 2.35 s delay. Page 1 comes from the first request; the loop starts at page 2.
- **Filtering (`is_excluded`):** drops ads whose `heading` and `model_specification` contain any word in `EXCLUDE` (leasing variants). Applied in `save_cars()` / `save_mcs()` by modifying the list in place (`car_ads[:] = ...`).
- **Normalize (`app/models.py`):** Pydantic `Listing` plus `normalize(raw, vertical)`. `price["amount"]` → `price_sek`, `mileage × 10` → `mileage_km` (Blocket uses Swedish mil).
- **Database (`app/db/`):** SQLAlchemy 2.0 `Listing` table. `id` is Blocket's ad ID (primary key, no autoincrement). `vertical` is `"car"` or `"mc"` (indexed). `first_seen` is set on insert only; `last_seen` is updated on every upsert.
- **Upsert (`app/db/crud.py`):** a single `INSERT ... ON CONFLICT (id) DO UPDATE` for all rows. The update columns are built from the Pydantic fields, so new fields are included automatically.
- **Migrations (Alembic):** `create_listings`, then `add_vertical_to_listings`. `alembic/env.py` reads `DATABASE_URL` from `.env` and uses `Base.metadata`.
- **Infrastructure:** `docker-compose.yml` runs `postgres:17` (port 5432, `pgdata` volume) and `adminer` (http://localhost:8080, bound to 127.0.0.1).

---

## Decisions

- **Use the `blocket-api` Python library, not the hosted REST API at blocket-api.se.** The library calls blocket.se directly; the hosted API adds a third-party dependency.
- **Two `Listing` classes, kept on purpose:** Pydantic in `app/models.py` (validation, and later API output) and SQLAlchemy in `app/db/models.py` (storage). In `crud.py`, import the table as `from app.db import models as db`.
- **One `listings` table for cars and motorcycles**, told apart by `vertical`. Blocket IDs don't overlap between categories.
- **Price history is postponed.** Only `listings` exists for now. When it's added: a `price_history` table (`listing_id` FK, `price_sek`, `observed_at`) with one row per *change*, not per fetch, created through a new Alembic migration.
- **Search-result fields only, for now.** Horsepower, number of owners, colour and similar fields are only on the listing page. `blocket-api`'s `get_ad()` currently doesn't return them (its spec parser no longer matches Blocket's HTML). If needed later, parse the `<dt>`/`<dd>` pairs with BeautifulSoup, and only for listings not seen before.
- **Docker for Postgres**, locally and later on a Raspberry Pi 5. The Windows Postgres install was removed because it conflicted on port 5432.
- **Scope kept small:** Skåne, with capped price ranges (cars up to 40,000 kr, motorcycles up to 50,000 kr). Blocket's `robots.txt` prohibits automated crawling without written permission, so keep it small, personal and infrequent.

---

## Next steps

### Phase 3: finish
Create one command that runs **fetch → filter → normalize → upsert** without having to go through JSON (keeping JSON as an optional debug output). For example, `app/pipeline.py` run with `python -m app.pipeline`.

**Done when:** a single command updates the database from Blocket, and running it twice gives the same row count, an unchanged `first_seen` and an updated `last_seen`.

### Phase 4: schedule updates
Run the pipeline automatically: cron on the Pi, Task Scheduler on Windows, or APScheduler inside the FastAPI process. Log how many listings were new or updated per run. Optionally mark listings that haven't been seen recently as inactive (`last_seen` older than the last run).

### Phase 5: FastAPI
- `GET /listings`: paginated, with filters `vertical`, `price_min`/`price_max`, `make`, `location`, and sorting.
- `GET /listings/{id}`.
- Sessions via `Depends`; response models based on the Pydantic `Listing`.
- **Done when:** `uvicorn app.api.main:app --reload` serves the endpoints and they work from `/docs`.

### Phase 6: React UI
Vite + React + TS in `frontend/`: a listings table with filters and pagination. Use `VITE_API_URL` for the API address, and enable CORS in FastAPI.

### Later: deployment
Raspberry Pi 5 with Docker Compose: `db`, `api`, and `web` (nginx). Use an SSD (not an SD card), nightly `pg_dump` backups, and Tailscale for remote access (no public exposure).

---

## Known issues and cleanup

- `fetch.py` duplicates the car and mc logic (`get_cars`/`get_mcs`, `fetch_range_*`, `save_*`). Merge into one helper that takes the search function as a parameter.
- `EXCLUDE` contains `"lease"`, which matches any word containing it. Consider filtering on the `sales_form` field (value `"Leasing"`) instead of, or as well as, the text match.
- `is_excluded` uses `ad.get('heading')` without a default, which gives the text `"None"` when the heading is missing. This is harmless but should be tidied up.
- The "Will crawl N times" print is only an estimate.
- No `requirements.txt` yet: run `pip freeze > requirements.txt`.
- `app/__init__.py` and `tests/__init__.py` are missing. Running with `-m` works without them.
- `.gitignore`: `metadata.json/` only matches a folder (remove the trailing slash), and `data/` is listed twice.
- `upsert_listings` sends everything in one statement. Postgres allows at most 65,535 parameters, so chunk the list (about 1,000 rows per chunk) once there are more than about 6,000 listings.
- Raw JSON in `data/` contains every field from Blocket. It stays local (`data/` is gitignored); only the normalized fields reach the database.

---

## Conventions

- Run every command from the project root (`alembic.ini`, `.env` and `docker-compose.yml` live there). Run modules with `python -m app.<module>`.
- Schema changes: edit `app/db/models.py` → `alembic revision --autogenerate -m "..."` → review the file → `alembic upgrade head`.
- Secrets only in `.env`, never committed.
- Working style: the user writes the code. Explain approaches and post snippets in chat rather than editing project files, unless asked.
