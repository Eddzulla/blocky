# Blocky: Implementation Plan

Goal: fetch car and motorcycle listings from blocket.se, store them in PostgreSQL, serve them via FastAPI, and display them in a React frontend.

For setup and day-to-day commands, see [README.md](README.md).

---

## Status (2026-10-22)

| Phase | Status |
|---|---|
| 0. Project structure | ✅ Done (except `scheduler.py`, `requirements.txt`) |
| 1. Fetch and save to JSON | ✅ Done |
| 2. Normalize with Pydantic | ✅ Done |
| 3. Store in Postgres | ✅ Done. `python -m app.pipeline` runs fetch → filter → normalize → upsert; verified stable row counts and `first_seen`/`last_seen` across repeated runs |
| 4. Schedule updates | ⏸️ Postponed. The pipeline is run manually for now |
| 5. FastAPI endpoints | ✅ Done. `GET /listings` (filters: `vertical`, `price_min`/`price_max`, `make`, `location`, `year` as a minimum, `sort`/`order`, pagination) and `GET /listings/{id}` |
| 6. React UI | 🟡 In progress. `frontend/src/api.ts` typed client done; `App.tsx` renders a basic listings table with a car/mc toggle. **Next:** filter inputs, pagination controls, detail view + routing |

**Current data:** 1,547 cars and 285 motorcycles (Skåne) in `listings`.

---

## How it works today

```
python -m app.pipeline → fetch.get_cars/get_mcs → filter_ads → to_listings (dedupe + normalize) → upsert_listings → commit
python blocky.py       → fetch only (debugging); JSON output to data/ is being reworked
```

- **Fetch (`app/fetch.py`):** `blocket-api` library, `locations=[Location.SKANE]`. Recursive price-range splitting when `match_count > 2500`; paging with a 2.35 s delay. Page 1 comes from the first request; the loop starts at page 2.
- **Filtering (`is_excluded`):** drops ads whose `heading` and `model_specification` contain any word in `EXCLUDE` (leasing variants). Applied in `save_cars()` / `save_mcs()` by modifying the list in place (`car_ads[:] = ...`).
- **Normalize (`app/models.py`):** Pydantic `Listing` plus `normalize(raw, vertical)`. `price["amount"]` → `price_sek`, `mileage × 10` → `mileage_km` (Blocket uses Swedish mil). `make`, `model`, `model_specification` and `location` are lowercased here so API filtering can do plain equality matches.
- **Database (`app/db/`):** SQLAlchemy 2.0 `Listing` table. `id` is Blocket's ad ID (primary key, no autoincrement). `vertical` is `"car"` or `"mc"` (indexed). `first_seen` is set on insert only; `last_seen` is updated on every upsert.
- **Upsert (`app/db/crud.py`):** a single `INSERT ... ON CONFLICT (id) DO UPDATE` for all rows. The update columns are built from the Pydantic fields, so new fields are included automatically. `get_listings()` builds the filtered/sorted/paginated query behind the API.
- **Migrations (Alembic):** `create_listings`, then `add_vertical_to_listings`. `alembic/env.py` reads `DATABASE_URL` from `.env` and uses `Base.metadata`.
- **Infrastructure:** `docker-compose.yml` runs `postgres:17` (port 5432, `pgdata` volume) and `adminer` (http://localhost:8080, bound to 127.0.0.1).
- **API (`app/api/`):** FastAPI app in `main.py` with CORS enabled for `http://localhost:5173` (Vite dev server). `listings.py` holds the router, `schemas.py` the response models (`ListingOut`, `ListingPage`), `deps.py` the DB session dependency.
- **Frontend (`frontend/`):** Vite + React + TS, ESLint (not oxlint). `src/api.ts` is a typed client (`getListings`, `getListing`) reading `VITE_API_URL` from `.env`. `App.tsx` currently renders a listings table with a vertical toggle.

---

## Decisions

- **Use the `blocket-api` Python library, not the hosted REST API at blocket-api.se.** The library calls blocket.se directly; the hosted API adds a third-party dependency.
- **Two `Listing` classes, kept on purpose:** Pydantic in `app/models.py` (validation, and later API output) and SQLAlchemy in `app/db/models.py` (storage). In `crud.py`, import the table as `from app.db import models as db`.
- **One `listings` table for cars and motorcycles**, told apart by `vertical`. Blocket IDs don't overlap between categories.
- **Price history is postponed.** Only `listings` exists for now. When it's added: a `price_history` table (`listing_id` FK, `price_sek`, `observed_at`) with one row per *change*, not per fetch, created through a new Alembic migration.
- **Search-result fields only, for now.** Horsepower, number of owners, colour and similar fields are only on the listing page. `blocket-api`'s `get_ad()` currently doesn't return them (its spec parser no longer matches Blocket's HTML). If needed later, parse the `<dt>`/`<dd>` pairs with BeautifulSoup, and only for listings not seen before.
- **Development moved from Windows 11 to macOS.** The project is portable by design (`.env` config, Postgres in Docker, no hard-coded OS-specific paths), so this was a clean switch. The production host is still undecided.
- **Docker for Postgres**, via Docker Desktop (for Mac now). On macOS, a Homebrew `postgresql@17` service can grab port 5432 before Docker does, causing `role "blocky" does not exist`; fix is `brew services stop postgresql@17`, not a Docker config change.
- **Scope kept small:** Skåne, with capped price ranges (cars up to 30,000 kr, motorcycles up to 40,000 kr). Blocket's `robots.txt` prohibits automated crawling without written permission, so keep it small, personal and infrequent.
- **String fields are normalized to lowercase** (`make`, `model`, `model_specification`, `location`) so API filters can use exact-match equality instead of case-insensitive comparisons. Applies going forward from `normalize()`; existing rows update to lowercase on their next `python -m app.pipeline` run (same `id`, upserted in place).

---

## Next steps

### Phase 6: React UI (current)
Done so far: `src/api.ts` (typed client for `getListings`/`getListing`), CORS enabled in `app/api/main.py` for `http://localhost:5173`, and `App.tsx` rendering a listings table with a car/mc toggle.

Left to do:
- Filter inputs (price range, make, minimum year) wired to `ListingsQuery` and re-fetched on change.
- Pagination controls using `total`/`limit`/`offset` from `ListingPage`.
- A detail view per listing (`GET /listings/{id}`), with routing (e.g. `react-router`) to get there from the table.

**Done when:** you can filter, page through, and open a single listing's detail from the browser.

### Phase 4: schedule updates (postponed)
Still manual (`python -m app.pipeline`) for now. Revisit once the production host is decided — the approach depends on the OS it runs on (e.g. `launchd`/cron on macOS or Linux, Task Scheduler on Windows).

Also worth doing whenever this is picked back up: have `upsert_listings` return how many rows were new vs. updated and print that per run, and consider marking listings not seen recently as inactive (`last_seen` older than the start of the current run).

### Later: production (host undecided)
For now everything runs locally: Postgres in Docker, the pipeline run manually, FastAPI with `uvicorn --reload`, and React with `npm run dev`.

The host is still to be decided. Options:
- **Keep it on a personal machine.** Simplest, but only works while that machine is on.
- **An always-on home machine** (mini PC, NAS or similar).
- **A small cloud VPS.** Always on, but it costs money and the API is reachable from the internet, so it needs authentication.

Whichever is chosen, the target shape is the same: Docker Compose with `db`, `api` and `web` (nginx serving the built React app and proxying `/api` to FastAPI). Things to do regardless of host:
- **Backups:** a scheduled `docker compose exec -T db pg_dump -U blocky blocky > backups/blocky-<date>.sql`.
- **Remote access:** Tailscale rather than opening ports to the internet.

---

## Known issues and cleanup

- `fetch.py` duplicates the car and mc logic (`get_cars`/`get_mcs`, `fetch_range_*`, `save_*`). Merge into one helper that takes the search function as a parameter.
- `EXCLUDE` contains `"lease"`, which matches any word containing it. Consider filtering on the `sales_form` field (value `"Leasing"`) instead of, or as well as, the text match.
- `is_excluded` uses `ad.get('heading')` without a default, which gives the text `"None"` when the heading is missing. This is harmless but should be tidied up.
- The "Will crawl N times" print is only an estimate.
- No `requirements.txt` yet: run `pip freeze > requirements.txt`.
- `app/__init__.py` and `tests/__init__.py` are missing. Running with `-m` works without them.
- `upsert_listings` sends everything in one statement. Postgres allows at most 65,535 parameters, so chunk the list (about 1,000 rows per chunk) once there are more than about 6,000 listings.
- Raw JSON in `data/` contains every field from Blocket. It stays local (`data/` is gitignored); only the normalized fields reach the database.

---

## Conventions

- Run every command from the project root (`alembic.ini`, `.env` and `docker-compose.yml` live there). Run modules with `python -m app.<module>`.
- Schema changes: edit `app/db/models.py` → `alembic revision --autogenerate -m "..."` → review the file → `alembic upgrade head`.
- Secrets only in `.env`, never committed.
- Working style: the user writes the code. Explain approaches and post snippets in chat rather than editing project files, unless asked.
