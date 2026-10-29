from app import fetch
from app.models import to_listings
from app.db.base import SessionLocal, check_db
from app.db.crud import upsert_listings, get_existing_ids, record_pipeline_run

def main():
    if not check_db():
        raise SystemExit("Postgres is not reachable. Start it with: docker compose up -d")

    with SessionLocal() as session:
        existing_car_ids = get_existing_ids(session, vertical="car")
        existing_mc_ids = get_existing_ids(session, vertical="mc")

    fetch.get_new_cars(existing_car_ids)
    fetch.get_new_mcs(existing_mc_ids)

    car_ads = fetch.filter_ads(fetch.car_ads) # filter the fetched lists
    mc_ads = fetch.filter_ads(fetch.mc_ads)

    fetch.append_data(car_ads, "cars")
    fetch.append_data(mc_ads, "mcs")

    car_listings = to_listings(car_ads, "car")
    mc_listings = to_listings(mc_ads, "mc")

    with SessionLocal() as session:
        upsert_listings(session, car_listings + mc_listings)
        record_pipeline_run(session, kind="quick")
        session.commit()

    print(f'Quick-fetch: upserted {len(car_listings)} new cars and {len(mc_listings)} new motorcycles')

if __name__ == "__main__":
    main()
