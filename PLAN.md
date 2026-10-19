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
| 3. Store in Postgres | 🟡 `python -m app.pipeline` runs fetch → filter → normalize → upsert. **Next:** finish the JSON debug output in `fetch.py` and verify that a second run keeps the row count and `first_seen` |
| 4. Schedule updates | ⏸️ Postponed. The pipeline is run manually for now |
| 5. FastAPI endpoints | 🟡 **Next** |
| 6. React UI | ⬜ |

**Current data:** 2,212 cars and 419 motorcycles (Skåne) in `listings`.

---

## How it works today

```
python -m app.pipeline → fetch.get_cars/get_mcs → filter_ads → to_listings (dedupe + normalize) → upsert_listings → commit
python blocky.py       → fetch only (debugging); JSON output to data/ is being reworked
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
- **Runs on Windows 11 for now; the production host is undecided.** Development and scheduled runs happen on the Windows PC (PowerShell, Docker Desktop, a `.venv`). Keep everything portable so the choice can wait: configuration in `.env`, Postgres in Docker, and no hard-coded Windows paths in Python code.
- **Docker for Postgres** (Docker Desktop on Windows). The Windows Postgres install was removed because it conflicted on port 5432.
- **Scope kept small:** Skåne, with capped price ranges (cars up to 40,000 kr, motorcycles up to 50,000 kr). Blocket's `robots.txt` prohibits automated crawling without written permission, so keep it small, personal and infrequent.

---

## Next steps

### Phase 3: finish
`python -m app.pipeline` already runs **fetch → filter → normalize → upsert**. What's left: finish `save_data(ads, vertical)` in `fetch.py` as an optional debug output (`data/cars.json`, `data/mcs.json`), restore the price caps (40,000 / 50,000), and verify.

**Done when:** running the pipeline twice gives the same row count, an unchanged `first_seen` and an updated `last_seen`.

### Phase 4: schedule updates (Windows Task Scheduler)
Run the pipeline automatically on the Windows PC. Task Scheduler is the right tool here: it's built in, it runs even when no terminal is open, and the schedule stays separate from the API process.

1. Add a wrapper script `run_pipeline.ps1` in the project root. It changes to the project root, calls the venv's Python directly (no activation needed) and appends output to a log:
   ```powershell
   Set-Location $PSScriptRoot
   New-Item -ItemType Directory -Force logs | Out-Null
   & .\.venv\Scripts\python.exe -m app.pipeline *>> logs\pipeline.log
   ```
2. In Task Scheduler, create a task with a daily trigger (or every few hours). Set the action to `powershell.exe -NoProfile -ExecutionPolicy Bypass -File "<project root>\run_pipeline.ps1"`. Tick "Run task as soon as possible after a scheduled start is missed" in case the PC was asleep.
3. **Prerequisite:** Postgres must be up when the task runs. Turn on "Start Docker Desktop when you sign in". The `db` service should have `restart: unless-stopped` in `docker-compose.yml` so it comes back with Docker.
4. Add `logs/` to `.gitignore`.

Also: have `upsert_listings` return how many rows were new and how many were updated, and print that per run so it lands in the log. Optionally mark listings that haven't been seen recently as inactive (`last_seen` older than the start of the current run).

Limitation: runs only happen while the PC is on and you're signed in. That's fine for now; it's one of the inputs to the production-host decision.

### Phase 5: FastAPI
- `GET /listings`: paginated, with filters `vertical`, `price_min`/`price_max`, `make`, `location`, and sorting.
- `GET /listings/{id}`.
- Sessions via `Depends`; response models based on the Pydantic `Listing`.
- **Done when:** `uvicorn app.api.main:app --reload` serves the endpoints and they work from `/docs`.

### Phase 6: React UI
Vite + React + TS in `frontend/`: a listings table with filters and pagination. Use `VITE_API_URL` for the API address, and enable CORS in FastAPI.

### Later: production (host undecided)
For now everything runs locally on Windows: Postgres in Docker Desktop, the pipeline via Task Scheduler, FastAPI with `uvicorn`, and React with `npm run dev`.

The host is still to be decided. Options:
- **Keep it on the Windows PC.** Simplest. It only works while the PC is on.
- **An always-on home machine** (mini PC, NAS or similar).
- **A small cloud VPS.** Always on, but it costs money and the API is reachable from the internet, so it needs authentication.

Whichever is chosen, the target shape is the same: Docker Compose with `db`, `api` and `web` (nginx serving the built React app and proxying `/api` to FastAPI). That works on Windows and Linux alike. Things to do regardless of host:
- **Backups:** a scheduled `docker compose exec -T db pg_dump -U blocky blocky > backups\blocky-<date>.sql`, run by a second Task Scheduler task on Windows.
- **Remote access:** Tailscale (it has a Windows client) rather than opening ports to the internet.

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
