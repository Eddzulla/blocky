# blocky

Collects car and motorcycle listings from blocket.se, stores them in PostgreSQL, and shows them in a React frontend.

## Stack

- **Fetching:** [`blocket-api`](https://github.com/dunderrrrrr/blocket_api), httpx
- **Validation:** Pydantic
- **Database:** PostgreSQL 17 (Docker), SQLAlchemy, Alembic
- **API:** FastAPI
- **Frontend:** React + Vite + TypeScript, react-router-dom, ESLint

## Practical commands

Quick reference for day-to-day work. Run everything from the project root unless noted.

**Database**
```bash
docker compose up -d          # start Postgres + Adminer
alembic upgrade head          # create/update tables (first run, or after a new migration)
docker compose down           # stop (data is kept in the pgdata volume)
```

**Backend (FastAPI)**
```bash
source .venv/bin/activate     # Windows: .venv\Scripts\Activate.ps1
uvicorn app.api.main:app --reload
```
Serves at http://127.0.0.1:8000, interactive docs at http://127.0.0.1:8000/docs.

**Data pipeline** (fetches from Blocket and updates the database)
```bash
python -m app.pipeline
```

**Frontend (React)**
```bash
cd frontend
npm run dev
```
Serves at http://localhost:5173.

See [Commands](#commands) below for the full reference (Docker, Alembic, database queries, etc).

## How it works

```
Blocket search API ──▶ fetch ──▶ filter ──▶ normalize ──▶ upsert ──▶ Postgres (listings table)
                     app/fetch.py         app/models.py  app/db/crud.py
```

1. **Fetch:** searches Skåne for used cars (up to 40,000 kr) and motorcycles (up to 50,000 kr). A query is capped at 2,500 results, so larger price ranges are split in half until each part fits. Pages are fetched with a delay between requests.
2. **Filter:** drops leasing ads whose heading or model specification matches a word in `EXCLUDE`.
3. **Normalize:** turns each raw ad into a Pydantic `Listing` (price in SEK, mileage in km) and removes duplicate IDs.
4. **Upsert:** writes all listings to the `listings` table in one `INSERT ... ON CONFLICT (id) DO UPDATE`. `first_seen` is set when a listing is first inserted; `last_seen` is updated on every run.

The data lives in Postgres, in the Docker volume `pgdata`. Raw JSON in `data/` is only an optional local debug copy and is gitignored.

## Project layout

```
app/
  pipeline.py     # main entry point: fetch → filter → normalize → upsert
  fetch.py        # search Blocket, split price ranges, filter leasing ads
  models.py       # Pydantic Listing, normalize(), to_listings()
  db/
    base.py       # engine, SessionLocal, Base (reads DATABASE_URL)
    models.py     # SQLAlchemy tables
    crud.py       # get_listings(), get_makes(), upsert_listings()
  api/
    main.py       # FastAPI app, CORS
    listings.py   # router: GET /listings, /listings/{id}, /listings/makes
    schemas.py    # ListingOut, ListingPage response models
    deps.py       # DB session dependency
alembic/          # database migrations
tests/            # test_normalize.py (runs offline against data/cars.json)
blocky.py         # fetch only, no database (for debugging)
frontend/         # Vite + React + TS app (see frontend/src)
docker-compose.yml
```

## Setup

The project is developed and run on **macOS** with [Docker Desktop](https://www.docker.com/products/docker-desktop/). Where it will run in production is still open (see [PLAN.md](PLAN.md)).

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install blocket-api httpx beautifulsoup4 pydantic sqlalchemy "psycopg[binary]" python-dotenv alembic fastapi uvicorn
```

On Windows, use `python -m venv .venv` and `.venv\Scripts\Activate.ps1` instead (`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once if PowerShell refuses to run it).

Create `.env` in the project root (not committed):

```
POSTGRES_USER=blocky
POSTGRES_PASSWORD=<password>
POSTGRES_DB=blocky
DATABASE_URL=postgresql+psycopg://blocky:<password>@localhost:5432/blocky
```

For the frontend, `cd frontend && npm install`, then create `frontend/.env` (not committed):

```
VITE_API_URL=http://127.0.0.1:8000
```

## Running the database locally

1. **Start Docker Desktop** and wait until it shows "Engine running".
2. **Start the containers** from the project root:
   ```bash
   docker compose up -d
   ```
3. **Check that they're running:**
   ```bash
   docker compose ps
   ```
   `blocky-db-1` and `blocky-adminer-1` should both show `Up`.
4. **First time only, create the tables:**
   ```bash
   alembic upgrade head
   ```
5. **Connect** with any of these:

   | Client | How |
   |---|---|
   | psql (terminal) | `docker compose exec db psql -U blocky -d blocky` |
   | Adminer (browser) | http://localhost:8080. System `PostgreSQL`, Server **`db`**, user/password/database from `.env` |
   | VS Code / DBeaver / pgAdmin | Host **`localhost`**, port `5432`, user/password/database from `.env` |
   | Python | `DATABASE_URL` in `.env` (already used by the app and Alembic) |

6. **Stop when done:**
   ```bash
   docker compose down
   ```
   The data is kept in the `pgdata` volume and is still there on the next `up`.

Adminer uses Server `db` because it runs in its own container and reaches Postgres by its service name. Everything outside Docker uses `localhost`. If the connection fails with *role "blocky" does not exist*, another Postgres is probably running on port 5432.

## Running the program

From the project root, with the virtual environment active:

```bash
docker compose up -d          # 1. start Postgres (and Adminer)
alembic upgrade head          # 2. create/update tables (first time, or after a new migration)
python -m app.pipeline        # 3. fetch from Blocket and update the database
```

When it finishes, it prints how many cars and motorcycles were upserted. A full run takes a few minutes because of the delay between requests. Running it again updates prices and `last_seen` without creating duplicate rows.

Check the result:

```bash
docker compose exec db psql -U blocky -d blocky -c "SELECT vertical, count(*) FROM listings GROUP BY vertical;"
```

or browse the table in Adminer at http://localhost:8080.

## Commands

Run everything from the project root. Run modules with `python -m app.<module>`, not `python app/<module>.py`, or you get `ModuleNotFoundError: app`.

### Pipeline

| Command | What it does |
|---|---|
| `python -m app.pipeline` | Fetch, filter, normalize and upsert into Postgres |
| `python blocky.py` | Fetch only, without touching the database |
| `python -m tests.test_normalize` | Check that all listings in `data/cars.json` normalize without errors (expects `N ok, 0 errors`) |

### Docker

| Command | What it does |
|---|---|
| `docker compose up -d` | Start Postgres and Adminer in the background |
| `docker compose ps` | Show running containers |
| `docker compose logs db` | Show database logs |
| `docker compose down` | Stop containers (data is kept) |
| `docker compose down -v` | Stop containers **and delete all data** |

### Database

| Command | What it does |
|---|---|
| `docker compose exec db psql -U blocky -d blocky` | Open an interactive SQL prompt (exit with `\q`) |
| `docker compose exec db psql -U blocky -d blocky -c "<sql>"` | Run a single SQL command |
| `\dt` | List tables (inside psql) |
| `\d listings` | Show the columns of `listings` (inside psql) |

### Alembic (migrations)

| Command | What it does |
|---|---|
| `alembic revision --autogenerate -m "<message>"` | Write a migration from changes in `app/db/models.py` |
| `alembic upgrade head` | Apply all pending migrations |
| `alembic downgrade -1` | Undo the latest migration |
| `alembic current` | Show which migration the database is on |
| `alembic history` | List all migrations |

To change a table: edit `app/db/models.py` → `revision --autogenerate` → review the file in `alembic/versions/` → `upgrade head`.

## Frontend

```bash
cd frontend
npm install        # first time only
npm run dev        # http://localhost:5173
```

Pages (`frontend/src/`):
- `/` (`ListingsPage.tsx`) — listings table with a car/mc toggle, a make dropdown (backed by `GET /listings/makes`), price and year range sliders (`RangeSlider.tsx`), sortable Year/Price/Mileage column headers, pagination, and a Reset filters button. Filter/sort/pagination state is held in `App.tsx` (the router root) so it survives navigating to a listing and back.
- `/listings/:id` (`ListingDetail.tsx`) — single listing detail, with a link to the live Blocket ad.

Requires the FastAPI server running at `VITE_API_URL` (CORS is already enabled for `http://localhost:5173`).

## Notes on Blocket data

- `search_car()` / `search_mc()` take enum lists: `models=[CarModel.HONDA]`, `locations=[Location.SKANE]`.
- Listings are in `results["docs"]`, 50 per page, max 50 pages per query (2,500 results). Larger queries are split by price range.
- `price` is a dict (`price["amount"]`). `mileage` is in Swedish mil (×10 for km).
- The car endpoint includes used, new and leasing listings (`sales_form`).
- Detail fields such as horsepower and number of owners are only on the listing page, not in search results.


## Roadmap

- [x] Fetch listings and save them to JSON
- [x] Normalize the data with Pydantic
- [x] Store in Postgres with upserts (`listings` table)
- [x] Connect fetch → normalize → upsert in one command (`app/pipeline.py`)
- [x] FastAPI endpoints
- [x] React UI (table, filters, sorting, pagination, detail view)
- [ ] Price history table
- [ ] Schedule updates
