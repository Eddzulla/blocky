# blocky

Collects car and motorcycle listings from blocket.se, stores them in PostgreSQL, and shows them in a React frontend.

## Stack

- **Fetching:** [`blocket-api`](https://github.com/dunderrrrrr/blocket_api), httpx
- **Validation:** Pydantic
- **Database:** PostgreSQL 17 (Docker), SQLAlchemy, Alembic
- **API:** FastAPI *(planned)*
- **Frontend:** React + Vite + TypeScript *(planned)*

## Project layout

```
app/
  fetch.py        # fetch listings from Blocket, save to data/*.json
  models.py       # Pydantic Listing + normalize()
  db/
    base.py       # engine, SessionLocal, Base (reads DATABASE_URL)
    models.py     # SQLAlchemy tables
    crud.py       # upsert_listings()
alembic/          # database migrations
tests/            # test_normalize.py
blocky.py         # entry point: fetch and save JSON
docker-compose.yml
```

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install blocket-api httpx beautifulsoup4 pydantic sqlalchemy "psycopg[binary]" python-dotenv alembic
```

Create `.env` in the project root (not committed):

```
POSTGRES_USER=blocky
POSTGRES_PASSWORD=<password>
POSTGRES_DB=blocky
DATABASE_URL=postgresql+psycopg://blocky:<password>@localhost:5432/blocky
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

## Commands

Run everything from the project root.

### Pipeline

| Command | What it does |
|---|---|
| `python blocky.py` | Fetch listings from Blocket and save to `data/*.json` |
| `python -m app.load` | Load `data/*.json`, normalize and upsert into Postgres |
| `python -m tests.test_normalize` | Check that all saved listings normalize without errors |

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
- [ ] Connect fetch → normalize → upsert in one command
- [ ] Price history table
- [ ] Schedule updates
- [ ] FastAPI endpoints
- [ ] React UI
