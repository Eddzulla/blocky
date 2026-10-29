# Blocky: Implementation Plan

Goal: fetch car and motorcycle listings from blocket.se, store them in PostgreSQL, serve them via FastAPI, and display them in a React frontend.

For setup and day-to-day commands, see [README.md](README.md).

---

## Status (2026-10-26)

| Phase | Status |
|---|---|
| 0. Project structure | ✅ Done |
| 1. Fetch and save to JSON | ✅ Done. Plus a separate quick-fetch path (below) |
| 2. Normalize with Pydantic | ✅ Done. Now also captures `image_urls` (first 3) and `engine_cc` (mc only) |
| 3. Store in Postgres | ✅ Done. `python -m app.pipeline` (full) and `python -m app.quick_pipeline` (new-only) both fetch → filter → normalize → upsert |
| 4. Schedule updates | ⏸️ Still manual. A concrete plan exists now — see [DEPLOYMENT.md](DEPLOYMENT.md) (systemd timers once hosted on the Ubuntu server) |
| 5. FastAPI endpoints | ✅ Done. `GET /listings` (filters: `vertical`, `price_min`/`price_max`, `mileage_min`/`mileage_max`, `make`, `model`, `search`, `year_min`/`year_max`, `sort`/`order`, pagination — only `is_active` rows), `GET /listings/{id}`, `GET /listings/makes`, `GET /listings/models` |
| 6. React UI | ✅ Done. Table with sortable Make/Model/Year/Price/Mileage/Engine columns, make facet filter, price/mileage/year range sliders, make+model search, pagination, Reset filters, image thumbnail + 3-image gallery on detail, detail view + routing. Filter/sort/pagination state persists across navigation (lifted to `App.tsx`) |

**Current data:** 2,710 active cars (266 inactive) and 349 active motorcycles (66 inactive) in `listings`.

**Open roadmap items:** price history table, real scheduling (deployment plan written, not yet executed) — see "Next steps" below.

---

## How it works today

```
python -m app.pipeline       → fetch.get_cars/get_mcs (full)      → filter_ads → to_listings → upsert_listings → deactivate_missing → commit
python -m app.quick_pipeline → fetch.get_new_cars/get_new_mcs     → filter_ads → to_listings → upsert_listings (no deactivate) → commit
python blocky.py             → fetch only (debugging); no database, no filtering
```

- **Fetch (`app/fetch.py`):** `blocket-api` library, `locations=[Location.SKANE]`. Full fetch (`get_cars`/`get_mcs` → `_get_listings`/`_fetch_range`): recursive price-range splitting when `match_count > 2500`, paging with a random 4–7 s delay. Quick-fetch (`get_new_cars`/`get_new_mcs` → `_get_new_listings`): searches sorted `PUBLISHED_DESC` (newest first, verified empirically that timestamps come back strictly descending), pages forward with the same delay, and stops the instant it hits an `id` already in the DB — capped at `MAX_QUICK_FETCH_PAGES = 50` as a safety net. Raw ad `id`s come back as **strings**; cast to `int` before comparing against DB ids.
- **Filtering (`_is_excluded`):** four layers, checked in order: `sales_form == 5` (dealer/leasing flag), `price.amount_ex_vat` presence (VAT-exclusive pricing only ever appears on business listings), `_is_private_lease_sublet` (≤3-year-old car under 15,000 kr — no genuine used sale is that cheap that new, catches private lease-sublet ads with no other structural marker), and finally the `EXCLUDE` text match as a last resort.
- **Normalize (`app/models.py`):** Pydantic `Listing` plus `normalize(raw, vertical)`. `price["amount"]` → `price_sek`, `mileage × 10` → `mileage_km` (Blocket uses Swedish mil), `image_urls` → first 3 photo URLs, `volume` → `engine_cc` (motorcycles only; always `None` for cars). `make`, `model`, `model_specification` and `location` are lowercased here so API filtering can do plain equality matches.
- **Database (`app/db/`):** SQLAlchemy 2.0 `Listing` table. `id` is Blocket's ad ID (primary key, no autoincrement). `vertical` is `"car"` or `"mc"` (indexed). `first_seen` set on insert only; `last_seen` updated on every upsert. `is_active` (default `true`, indexed) is the soft-delete flag — see Decisions.
- **Upsert (`app/db/crud.py`):** `INSERT ... ON CONFLICT (id) DO UPDATE`, chunked at `UPSERT_CHUNK_SIZE = 1000` rows to stay under Postgres's 65,535-bind-parameter limit. Update columns are derived from the Pydantic fields, so new fields are included automatically; `is_active` is explicitly forced back to `true` on conflict (reactivates a relisted ad). `get_listings()`/`get_makes()`/`get_models()` all filter `is_active = true`. `deactivate_missing()` flips anything not in the current *full* fetch's id set to inactive — never called by quick-fetch (see Decisions).
- **Migrations (Alembic):** `create_listings` → `add_vertical_to_listings` → `add_is_active_to_listings` → `add_image_urls_to_listings` → `add_engine_cc_to_listings`.
- **Infrastructure:** `docker-compose.yml` runs `postgres:17` (port 5432, `pgdata` volume) and `adminer` (http://localhost:8080, bound to 127.0.0.1).
- **API (`app/api/`):** FastAPI app in `main.py` with CORS enabled for `http://localhost:5173` (Vite dev server), GET only. `listings.py` holds the router — static routes (`/makes`, `/models`) registered before the dynamic `/{listing_id}` to avoid being swallowed by it. List-typed query params (`make`, `model`) need `Annotated[list[str] | None, Query()]`, not a bare `list[str]` — FastAPI otherwise silently treats it as a request body field, which a GET never populates (this exact bug shipped once and had to be found via the OpenAPI schema, not by reading the code). `schemas.py` has the response models, `deps.py` the DB session dependency.
- **Frontend (`frontend/`):** Vite + React + TS, ESLint (not oxlint), `react-router-dom`. `src/api.ts` is a typed client reading `VITE_API_URL` from `.env`; interfaces mirror the backend schemas field-for-field, including `ListingsQuery`'s `[key: string]: unknown` index signature (required for passing it where `Record<string, unknown>` is expected — a `tsc -b` error invisible to `vite dev`). `src/App.tsx` is the persistent router root holding cross-route state (`vertical`, `filters`, `offset`, `sort`, `order`); `src/ListingsPage.tsx` is the `/` route (table, facet filter, sliders, search, sorting, pagination); `src/ListingDetail.tsx` is `/listings/:id`; `src/RangeSlider.tsx` is a reusable dual-handle slider (two overlapping native range inputs, the native tracks made transparent so only the custom fill/background divs are visible).

---

## Decisions

- **Use the `blocket-api` Python library, not the hosted REST API at blocket-api.se.** The library calls blocket.se directly; the hosted API adds a third-party dependency.
- **Two `Listing` classes, kept on purpose:** Pydantic in `app/models.py` (validation, and later API output) and SQLAlchemy in `app/db/models.py` (storage). In `crud.py`, import the table as `from app.db import models as db`.
- **One `listings` table for cars and motorcycles**, told apart by `vertical`. Blocket IDs don't overlap between categories.
- **Price history is postponed.** Only `listings` exists for now. When it's added: a `price_history` table (`listing_id` FK, `price_sek`, `observed_at`) with one row per *change*, not per fetch, created through a new Alembic migration.
- **Search-result fields only, for now.** Horsepower, number of owners, colour and similar fields are only on the listing page. `blocket-api`'s `get_ad()` currently doesn't return them (its spec parser no longer matches Blocket's HTML). If needed later, parse the `<dt>`/`<dd>` pairs with BeautifulSoup, and only for listings not seen before.
- **Development moved from Windows 11 to macOS.** The project is portable by design (`.env` config, Postgres in Docker, no hard-coded OS-specific paths), so this was a clean switch. The production host is now decided — an Ubuntu server, see `DEPLOYMENT.md`.
- **Docker for Postgres**, via Docker Desktop (for Mac now). On macOS, a Homebrew `postgresql@17` service can grab port 5432 before Docker does, causing `role "blocky" does not exist`; fix is `brew services stop postgresql@17`, not a Docker config change.
- **Scope kept small:** Skåne, with capped price ranges (cars and motorcycles both up to 50,000 kr). Blocket's `robots.txt` prohibits automated crawling without written permission, so keep it small, personal and infrequent.
- **String fields are normalized to lowercase** (`make`, `model`, `model_specification`, `location`) at ingestion in `normalize()`. However, `get_listings`'s `make` filter and `get_makes` both compare with `func.lower(...)` on the DB side too, rather than trusting all stored rows are already lowercase — rows fetched before this change existed still had mixed case, so relying on ingestion-time lowercasing alone wasn't sufficient.
- **Year filter is `year_min`/`year_max`**, not a single `year` — mirrors the `price_min`/`price_max` naming convention. Changed from an earlier single minimum-only `year` param once a max-year filter was needed.
- **Make filter is a dropdown backed by `GET /listings/makes`** (distinct values per vertical), not a free-text input or a hardcoded list — stays correct as the dataset changes.
- **Price and year filters are dual-handle range sliders** (`RangeSlider.tsx`), not separate min/max inputs. Bounds are fixed, not derived from the data: `PRICE_BOUNDS` (cars and mc both 0–50,000 kr, matching the fetch caps) and `YEAR_MIN`/`YEAR_MAX` (1990–current year), both defined in `ListingsPage.tsx`.
- **Cross-route state (filters/sort/pagination) is lifted to `App.tsx`**, the component that owns `<Routes>`, rather than stored in the URL (`useSearchParams`) or a Context provider. Simplest option that satisfies "don't reset when navigating to a listing and back" without adding a new state-management concept for a two-route app.
- **Nullable sortable columns sort with `NULLS LAST`** in both directions (`app/db/crud.py`) — Postgres's default `NULLS FIRST` on `DESC` was putting listings with no mileage/price data at the top of a descending sort.
- **Mileage is a third range slider**, same pattern and bounds-source as price/year: `MILEAGE_BOUNDS` (cars 0–500,000 km, mc 0–150,000 km), chosen from real percentile data (p95 ≈ 380,000 km for cars) rather than the true max, which includes clear data-entry garbage (one listing claims 4.7M km).
- **Make/model search is word-based, not phrase-based**: each whitespace-separated word in the query must match `make` OR `model` (case-insensitive substring), independently per word. This is what makes "Honda Civic" match only Honda Civics (both words match) while "Auris" alone matches Toyota Auris (the one word matches `model`, regardless of make).
- **Soft-delete via `is_active`, never a real `DELETE`.** Decided against deleting stale rows entirely, now or on a timer — at ~3,400 rows / 3.5MB the table is nowhere near a size where it matters, and deleting forecloses ever building the postponed price-history feature for those listings. `deactivate_missing()` only ever flips `is_active`; nothing in the codebase issues a `DELETE` against `listings`.
- **Quick-fetch stops at the first already-known id, full fetch still does everything.** `get_existing_ids()` returns *all* ids for a vertical regardless of `is_active`, so quick-fetch never second-guesses something it's already seen. Quick-fetch deliberately never calls `deactivate_missing` — that logic assumes the fetch it's given represents the complete current state, which a quick-fetch by design isn't; running it there would have incorrectly deactivated almost everything else.
- **`image_urls` stored as a native Postgres `ARRAY(String)`**, not a join table — it's always ≤3 short strings, doesn't need to be queried/filtered on independently, so a dedicated `images` table would be pure overhead.
- **`engine_cc` added despite not being "always present"** (70.6% coverage on motorcycles) — it's actually *higher* coverage than `mileage` itself on motorcycles (68.3%), so it clears the bar already set by an existing nullable field. Always `None` for cars (the raw `volume` field doesn't exist there at all); the frontend hides the column/row entirely for the car vertical rather than showing an always-empty `—`.
- **Full-fetch request delay raised from `1–2s` to a random `4–7s`** (`random.uniform(4, 7)`), applied to both the full fetch and quick-fetch's paging loops, as a deliberate politeness/rate margin — not because of any observed blocking, but because it was cheap to do and the project's own stance is to stay well under the radar rather than push limits. A full fetch now takes ~6–9 minutes instead of ~2.
- **Recommended run cadence** (not yet automated — see Phase 4 / `DEPLOYMENT.md`): full fetch roughly once a day, quick-fetch every 1–3 hours. Quick-fetch is cheap by construction (it stops almost immediately once caught up), so running it often doesn't meaningfully add load; the full fetch is the expensive one and doesn't need to run more than daily since listings don't change that fast.

---

## Next steps

Everything in the original roadmap (fetch → Postgres → FastAPI → React UI) is done. What's open now:

### Price history table (postponed, still open)
A `price_history` table (`listing_id` FK, `price_sek`, `observed_at`), one row per *price change* detected during upsert, not per fetch. Needs a new Alembic migration and a change to `upsert_listings` to detect and record the change before overwriting `price_sek`.

### Frontend polish (ongoing, no fixed scope)
Small UX items that come up as they're noticed — e.g. the current CSS pass for a livelier look (color, button/dropdown styling). Not a tracked "phase," just addressed as requested.

### Phase 4: schedule updates (plan written, not yet executed)
Both fetch commands exist (`python -m app.pipeline`, `python -m app.quick_pipeline`) and are still triggered manually. The host is now decided — an Ubuntu server — and the full plan is written up in [DEPLOYMENT.md](DEPLOYMENT.md): containerize the API/frontend properly, run both fetches on systemd timers (full fetch ~every 6h, quick-fetch every 1–3h), DuckDNS + Caddy for a free reachable domain with automatic HTTPS, and `ufw`/fail2ban/Tailscale for hardening. Next action is executing that plan once the server itself is reachable.

Also still worth doing whenever scheduling is live: have `upsert_listings`/`deactivate_missing` return and log how many rows were new/updated/deactivated per run, so the systemd timer logs are actually useful for noticing problems.

---

## Known issues and cleanup

All previously-listed fixable issues are resolved:

- ✅ `fetch.py`'s car/mc duplication merged into `_get_listings`/`_fetch_range`, parameterized by search function.
- ✅ Leasing detection no longer relies on the `EXCLUDE` text match alone — `sales_form == 5`, `price.amount_ex_vat` presence, and the near-new-underpriced heuristic (`_is_private_lease_sublet`) all run first; text match is the last-resort fallback.
- ✅ `_is_excluded` uses `ad.get('heading', '')` — no more literal `"None"` in the filter text.
- ✅ The "Will crawl N times" estimate is gone — `_get_listings` now just logs the match count found for a range; `_fetch_range` already logs real per-page progress.
- ✅ `requirements.txt` regenerated. It existed but was corrupted — UTF-16 encoded (a classic PowerShell `>` redirection artifact from the Windows days), unusable as plain text. Regenerated with `pip freeze` from the venv on macOS; now valid UTF-8/ASCII.
- ✅ `app/__init__.py`, `app/api/__init__.py` and `tests/__init__.py` added (were implicit namespace packages before — worked fine with `-m`, but these make them explicit).
- ✅ `upsert_listings` now chunks at `UPSERT_CHUNK_SIZE = 1000` rows per statement, avoiding Postgres's 65,535-bind-parameter limit. Worth revisiting the chunk size if the Pydantic `Listing` model gains many more fields.

Remaining notes (not issues, just context worth keeping):
- Raw JSON in `data/` contains every field from Blocket. It stays local (`data/` is gitignored); only the normalized fields reach the database.
- No `requirements.txt` equivalent is needed for the frontend — `frontend/package.json` already serves that purpose.
- `react-hooks/set-state-in-effect` lint errors on the data-fetching effects in `ListingsPage.tsx` are expected and left as-is (standard loading-state pattern); see CLAUDE.md.
- Pagination controls intentionally appear both above and below the table in `ListingsPage.tsx` (not a duplication bug).

---

## Conventions

- Run every command from the project root (`alembic.ini`, `.env` and `docker-compose.yml` live there). Run modules with `python -m app.<module>`.
- Schema changes: edit `app/db/models.py` → `alembic revision --autogenerate -m "..."` → review the file → `alembic upgrade head`.
- Secrets only in `.env` / `frontend/.env`, never committed.
- Working style: the user writes most backend code themselves (explain + snippets in chat). Frontend edits are made directly, then verified (`tsc -b --noEmit`, `npm run lint`, functional check) and explained afterward. See CLAUDE.md for the full "Established conventions for new features" list (naming, route gotchas, filter UI patterns) so repeat decisions don't need re-asking.
