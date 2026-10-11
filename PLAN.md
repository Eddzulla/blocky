# Blocky — Implementation Plan

Goal: fetch car/motorcycle listings from blocket.se, store them in PostgreSQL with price history, serve them via FastAPI, and display them in a React frontend.

This plan follows the roadmap in the README. Each phase lists what to build, the key decisions you'll need to make, and a "done when" check so you know when to move on.

---

## Phase 0 — Project structure

Before writing more code, split the single `blocky.py` script into a proper package so later phases have somewhere to live.

```
blocky/
  app/
    __init__.py
    fetch.py          # blocket_api calls (what blocky.py does today)
    models.py         # Pydantic schemas (normalized listing shape)
    db/
      __init__.py
      base.py         # SQLAlchemy engine/session setup
      models.py        # SQLAlchemy ORM tables
      crud.py          # upsert / query helpers
    api/
      __init__.py
      main.py          # FastAPI app + routers
    scheduler.py       # periodic fetch job
  alembic/              # migration scripts (generated)
  alembic.ini
  frontend/             # React + Vite + TS app
  .env                  # DB connection string, not committed
  requirements.txt
```

**Done when:** `blocky.py`'s logic lives in `app/fetch.py` as importable functions (not a top-level script), and the repo has this folder layout.

---

## Phase 1 — Fetch listings and save to JSON *(mostly done)*

You already have working calls to `search_car` / `search_mc`. Finish this phase properly:

- Turn the fetch logic into a function, e.g. `fetch_all_cars(location, price_from, price_to) -> list[dict]`, that pages through results (the commented-out `while` loop in `blocky.py` is your starting point).
- Handle both verticals (car, mc) with one shared paging helper — don't duplicate the loop.
- Respect the API's limits: 50 results/page, 50 pages max per query. If a query's `match_count` exceeds 2500, split by price range and fetch each range separately.
- Save raw (but scrubbed) results to `data/*.json` for now, so you can inspect the shape without a DB.

**Done when:** running one command fetches all current car + mc listings for your search params and writes clean JSON to `data/`.

---

## Phase 2 — Normalize with Pydantic

Design a `Listing` Pydantic model representing one ad in the shape you actually want to store — not blocket's raw shape.

Fields to decide on (look at `metadata.json` and a real ad for the raw shape):
- `id`, `title`, `vertical` (car/mc), `price_amount` (int, from `price["amount"]`), `mileage_km` (convert from Swedish mil: `×10`), `created_at` / listing date, `url`, `location`.
- A validator or field for `sales_form` so you can filter out `new`/`leasing` listings if you only want used.

Write a function `normalize(raw_ad: dict) -> Listing` and a small script/test that runs it over your saved JSON to confirm every field maps correctly and nothing throws.

**Done when:** you can load `data/*.json`, normalize every ad into `Listing` objects, with zero validation errors.

---

## Phase 3 — Store in Postgres (upserts + price history)

1. **Install & run Postgres locally** (Docker is easiest: `docker run -e POSTGRES_PASSWORD=... -p 5432:5432 postgres`).
2. **Add SQLAlchemy models** in `app/db/models.py`:
   - `Listing` table: one row per ad, keyed by blocket's ad `id`. Holds the latest known state.
   - `PriceHistory` table: `listing_id` (FK), `price`, `observed_at`. One row per price change, not per fetch.
3. **Set up Alembic**: `alembic init alembic`, point it at your models' metadata, generate the first migration, run it.
4. **Write upsert logic** in `app/db/crud.py`:
   - For each normalized `Listing`: if the ad `id` doesn't exist, insert it + one `PriceHistory` row.
   - If it exists and the price changed, update the `Listing` row and append a new `PriceHistory` row.
   - If it exists and nothing changed, skip it (don't write unnecessary rows).
5. Wire Phase 1's fetch output through Phase 2's normalizer into this upsert function.

**Done when:** running the fetch twice in a row (with no real price changes) doesn't create duplicate `PriceHistory` rows, and changing a price between runs does.

---

## Phase 4 — Schedule updates

Decide how listings stay fresh. Two reasonable options for a project this size:

- **Simple:** a cron job (or macOS `launchd`) that runs `python -m app.scheduler` every N minutes/hours.
- **In-process:** `APScheduler` running inside the same process as the FastAPI app.

Either way, the scheduled job is just: fetch → normalize → upsert (Phases 1–3 chained). Log how many listings were new/updated/unchanged each run so you can sanity-check it over time.

**Done when:** listings in the DB update on their own on a schedule, without you running the script by hand.

---

## Phase 5 — FastAPI endpoints

Build a minimal read API over the DB:

- `GET /listings` — paginated, with query params for filtering (`vertical`, `price_min`, `price_max`, `location`, sort).
- `GET /listings/{id}` — single listing detail.
- `GET /listings/{id}/price-history` — the price-history rows for one listing.

Use SQLAlchemy sessions via FastAPI's dependency injection (`Depends`), and reuse your Pydantic `Listing` model (or a response-specific variant) for serialization so the API's output shape matches what you normalized in Phase 2.

**Done when:** `uvicorn app.api.main:app --reload` serves all three endpoints and you can hit them with `curl`/the auto-generated `/docs` page.

---

## Phase 6 — React UI

Scaffold with Vite (`npm create vite@latest frontend -- --template react-ts`).

Minimum viable UI:
- A listings table/grid fetching `GET /listings`, with filter controls (price range, vertical).
- A detail view per listing, including a simple price-history chart (even a basic line chart is enough).
- Basic pagination.

Point the frontend at the FastAPI base URL via an env var (`VITE_API_URL`) so dev vs. prod config isn't hardcoded. You'll likely need CORS enabled on the FastAPI side (`fastapi.middleware.cors`) for local dev.

**Done when:** you can browse listings and see a price history for at least one ad, end-to-end, through the UI.

---

## Cross-cutting notes

- **Secrets:** DB credentials go in `.env`, loaded via `python-dotenv` or `pydantic-settings` — never hardcoded, never committed. Add `.env` to `.gitignore` if it isn't already.
- **Testing as you go:** you don't need a full test suite, but a quick script or two per phase (fetch → file, file → normalized, normalized → DB) will save you from debugging three layers at once later.

Work through the phases roughly in order — each one assumes the previous is working. Ask when you get stuck on a specific step rather than a whole phase; it'll be easier to point you at the right concept.
