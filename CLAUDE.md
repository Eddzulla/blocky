# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Working with this user

The user is learning and writes most backend/data-pipeline code themselves — explain approaches and post snippets in chat there rather than editing. For frontend work, the user has granted direct edit access: implement the change yourself, verify it (`tsc -b --noEmit`, `npm run lint`, and a functional check against the real DB/API where relevant), and explain what changed and why afterward. Running read-only checks (inspecting `data/*.json`, querying the DB, running tests) to verify work is always welcome regardless of area.

When a feature request has a genuine design decision with no inferable right answer (e.g. data source for a dropdown, numeric bounds for a slider, a breaking API rename), ask via a short set of options rather than guessing — but check "Established conventions" below first, since many of these have already been decided and shouldn't need re-asking.

`PLAN.md` holds the current phase status, design decisions and known issues. Read it before suggesting next steps, and keep it updated when decisions change.

## Commands

Run everything from the project root: `alembic.ini`, `.env` and `docker-compose.yml` live there, and `app` is only importable from there. Running from `app/` gives Alembic's "No 'script_location' key found".

```bash
docker compose up -d                    # Postgres 17 (localhost:5432) + Adminer (localhost:8080)
alembic upgrade head                    # apply migrations
python -m app.pipeline                  # fetch → filter → normalize → upsert into Postgres
python blocky.py                        # fetch from Blocket → data/cars.json, data/mcs.json (debug, no DB)
python -m tests.test_normalize          # normalize every saved listing; expects "N ok, 0 errors"
uvicorn app.api.main:app --reload       # FastAPI at :8000, docs at /docs
docker compose exec db psql -U blocky -d blocky -c "<sql>"
```

Frontend, from `frontend/`:
```bash
npm run dev                             # Vite dev server at :5173
npx tsc -b --noEmit                     # type-check only, no emit — run before considering frontend work done
npm run lint                            # ESLint
```

Run Python modules with `python -m app.x` / `python -m tests.x`, not `python tests/x.py` (which gives `ModuleNotFoundError: app`). There's no pytest suite; `tests/test_normalize.py` is a plain script that runs offline against `data/cars.json`.

Schema changes: edit `app/db/models.py` → `alembic revision --autogenerate -m "..."` → review the file in `alembic/versions/` → `alembic upgrade head`. `alembic/env.py` loads `DATABASE_URL` from `.env` and imports `app.db.models` to register the tables on `Base.metadata`.

## Architecture

Pipeline: **fetch → filter → normalize → upsert**, currently split into two commands with JSON files in between.

- `app/fetch.py`: uses the `blocket-api` library, which calls Blocket's internal JSON search endpoints directly (`/mobility/search/api/search/SEARCH_ID_CAR_USED` and `SEARCH_ID_MC_USED`). Results accumulate in module-level lists `car_ads` / `mc_ads`. Queries are capped at 50 pages × 50 results, so `get_cars`/`get_mcs` recursively split the price range when `match_count > 2500`. `fetch_range_*` pages through a range that fits. `save_*` applies `is_excluded` (text match against `EXCLUDE`) in place and writes JSON.
- `app/models.py`: **Pydantic** `Listing` plus `normalize(raw, vertical)`. This is the validation layer.
- `app/db/models.py`: **SQLAlchemy** `Listing` (table `listings`). This is the storage layer. Its column names deliberately match the Pydantic fields.
- `app/db/crud.py`: `upsert_listings` builds a single Postgres `INSERT ... ON CONFLICT (id) DO UPDATE` from `model_dump()` rows. The update set is derived from the dict keys, so a new field needs only the Pydantic field, the SQLAlchemy column and a migration. `first_seen` is set only on insert; `last_seen` is bumped on every upsert.
- `app/db/base.py`: engine, `SessionLocal`, `Base`. Reads `DATABASE_URL` at import time, so importing anything under `app.db` requires `.env`.
- `app/db/crud.py`: `upsert_listings` as above, plus `get_listings()` (filtered/sorted/paginated query behind the API) and `get_makes()` (distinct makes for a vertical). String filters use `func.lower(...)` on both sides — don't assume stored data is already lowercase (older rows may predate a normalization change). Sortable nullable columns (`price_sek`, `mileage_km`) use `.nulls_last()` on both `asc()` and `desc()` — Postgres defaults to `NULLS FIRST` on `DESC`, which puts missing data at the top otherwise.
- `app/api/main.py`: FastAPI app. CORS allows `http://localhost:5173` (Vite dev), **GET only** — adding a mutating endpoint later means updating `allow_methods`.
- `app/api/listings.py`: router (`prefix="/listings"`). Static routes (`/makes`) must be declared **before** the dynamic `/{listing_id}` route — FastAPI/Starlette matches routes in registration order with no type-aware precedence, so `/listings/makes` would otherwise be swallowed by `/{listing_id}` and fail int validation.
- `app/api/schemas.py`: `ListingOut` (Pydantic `Listing` + `first_seen`/`last_seen`), `ListingPage` (`items`/`total`/`limit`/`offset`).

There are two classes named `Listing`. Import the table as `from app.db import models as db` (`db.Listing`).

## Frontend architecture (`frontend/`)

Vite + React + TypeScript, ESLint (chosen over oxlint for ecosystem maturity), `react-router-dom`. No Context/Redux — state is lifted by hand to whichever component needs to outlive its children.

- `src/main.tsx`: just mounts `<App />`. Routing lives in `App.tsx`, not here.
- `src/App.tsx`: the **persistent root**. Owns `BrowserRouter`/`Routes` and any state that must survive navigating between routes (currently: `vertical`, `filters`, `offset`, `sort`, `order`). Passed down as props to `ListingsPage`. Add new cross-route state here, not in a page component — a page component unmounts when the route changes, a root component wrapping `<Routes>` does not.
- `src/ListingsPage.tsx`: the `/` route. Receives lifted state as props. Owns its own *draft* input state (slider/dropdown positions before "Apply" is clicked) locally, initialized **from the lifted `filters` prop** (not hardcoded defaults) so re-mounting after navigation shows the last-applied values, not resets. Also exports `PRICE_BOUNDS`, `YEAR_MIN`/`YEAR_MAX`, the `Filters` type, and `defaultFilters(vertical)` — reused by both the vertical-switch handler and the "Reset filters" button so the reset logic isn't duplicated.
- `src/ListingDetail.tsx`: the `/listings/:id` route. Standalone fetch via `useParams`.
- `src/RangeSlider.tsx`: dual-handle numeric range control — two overlapping native `<input type="range">`s with `pointer-events: none` on the track and `pointer-events: auto` only on `::-webkit-slider-thumb`/`::-moz-range-thumb`, so either handle can be dragged independently without a library. Reused for both price and year; onChange handlers clamp so the handles can't cross.
- `src/api.ts`: typed client. TypeScript interfaces mirror the backend Pydantic/FastAPI schemas field-for-field, including nullability (`price_sek: number | null`, matching `int | None`). `ListingsQuery` carries `[key: string]: unknown` — required because an interface without an index signature can't be passed where `Record<string, unknown>` is expected, a `tsc -b` error that only surfaces on a full build, not `vite dev`.
- `tsconfig.app.json` has `verbatimModuleSyntax: true` — type-only imports must use `import type { X }`, not a plain `import { X }`.

## Established conventions for new features

Check here before asking the user to re-decide something already settled:

- **Query param naming**: snake_case, matching the FastAPI/Pydantic field name exactly (`price_min`, `price_max`, `year_min`, `year_max`). Frontend and backend field names should always match 1:1.
- **Route paths**: double-check singular vs. plural between frontend calls and backend routes — this exact mismatch has caused silent 404s twice (`/listing/:id` vs `/listings/:id`, and a `getListings`/`getListing` path mix-up in `api.ts`).
- **Enumerable filters → dropdown backed by a distinct-values endpoint** (see `GET /listings/makes`), not a hardcoded list — stays correct as data changes.
- **Numeric range filters → `RangeSlider`** (dual-handle), bounds from `PRICE_BOUNDS` (fetch caps: cars 0–30,000 kr, mc 0–40,000 kr) or `YEAR_MIN`/`YEAR_MAX` (1990–current year) in `ListingsPage.tsx`. Don't reintroduce plain min/max text inputs or two separate sliders.
- **Filter UI pattern**: local "draft" state bound to the controls, committed to lifted "applied" state only on "Apply" (or immediately for `vertical`/sort/pagination, which have no draft concept). Keeps requests from firing on every keystroke/drag.
- **Before calling frontend work done**: run `npx tsc -b --noEmit` and `npm run lint` from `frontend/`, and a functional check against real data (direct `crud` function calls or `curl` against a temporary `uvicorn` instance) — several bugs in this project only surfaced that way, not from reading the code.
- **Known, accepted lint noise**: `react-hooks/set-state-in-effect` fires on the two standard data-fetching effects (`setLoading(true)` / `setError(null)` at the top of a `useEffect`). This is the normal loading-state pattern; it's deliberately left as-is, not a bug to fix.

## Blocket data gotchas

- `blocket-api` filters take **lists of enums**: `models=[CarModel.HONDA]`, `locations=[Location.SKANE]`. A bare enum or string raises `'str' object has no attribute 'value'`.
- Results: `res["docs"]` (listings), `res["metadata"]["result_size"]["match_count"]`, `res["metadata"]["paging"]["last"]`.
- `price` is a dict (`price["amount"]`). `mileage` is in Swedish mil (×10 for km) and is missing for many listings.
- `SEARCH_ID_CAR_USED` returns used, new **and** leasing listings; `sales_form` tells them apart.
- Fields such as horsepower and number of owners exist only on the listing page (`/mobility/item/<id>`, as `<dt>`/`<dd>` pairs). `blocket-api`'s `get_ad()` currently returns no specifications because its parser no longer matches the HTML.
- Raw listings include `regno`, `chassis_number` and `coordinates`. These stay in local `data/` (gitignored) and aren't normalized into the DB.
- Blocket's `robots.txt` prohibits automated crawling without permission. Keep request volume small, with delays between requests.

## Environment

The project runs on **macOS** (zsh/bash, Docker Desktop for Mac, `.venv/bin/python`). Development moved here from Windows 11; the production host is still undecided, so keep commands and scheduling advice OS-appropriate (don't assume this is still Windows, and don't assume a specific Linux host either) and keep the Python/frontend code portable.

`.env` (gitignored) defines `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` (used by docker-compose) and `DATABASE_URL=postgresql+psycopg://...@localhost:5432/blocky`. Adminer connects to server `db` (the compose service name), not `localhost`. If you get `role "blocky" does not exist`, something else already owns port 5432 — on macOS this is usually a Homebrew `postgresql@<version>` service (`brew services stop postgresql@17`), not a Docker config issue.

`frontend/.env` (gitignored) defines `VITE_API_URL=http://127.0.0.1:8000`.
