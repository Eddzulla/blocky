from app import fetch 
from app.models import to_listings
from app.db.base import SessionLocal
from app.db.crud import upsert_listings

def main():
    fetch.get_cars()
    fetch.get_mcs()

    car_ads = fetch.filter_ads(fetch.car_ads)
    mc_ads = fetch.filter_ads(fetch.mc_ads)

    car_listings = to_listings(car_ads, "car")
    mc_listings = to_listings(mc_ads, "mc")

    with SessionLocal() as session:
        upsert_listings(session, car_listings + mc_listings)
        session.commit()

    print(f'Upserted {len(car_listings)} cars and {len(mc_listings)} motorcycles')

if __name__ == "__main__":
    main()