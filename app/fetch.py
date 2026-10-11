from blocket_api import BlocketAPI, CarAd, CarModel
from blocket_api.constants import Location
import time
import json
from pathlib import Path


api = BlocketAPI()
locs = [Location.SKANE]
EXCLUDE = ["privatleasing"]
car_ads = []
mc_ads = []

def get_cars(min_price = 0, max_price = 10000):
    '''Fill up car_ads with ads based on filter criteria'''

    cars = api.search_car(
        locations=locs,
        price_from = min_price,
        price_to = max_price
        )
     
    total = cars["metadata"]["result_size"]["match_count"]
    if total < 1:
            print("No ads found, cancelling fetch.")
            return

    print(f"Found {total} ads. Will crawl {(total // 2500) + 1} times.")
    if total > 2500 and max_price - min_price > 1:
        mid = (max_price + min_price) // 2
        get_cars(min_price, mid)
        get_cars(mid+1, max_price)
        return
    
    fetch_range_cars(min_price, max_price, cars)

def fetch_range_cars(min_price, max_price, ads):
    '''Page through one price range that has 2500 reslts or fewer'''
    print(f"Fetching cars in range: {min_price} - {max_price}")
    
    last = ads["metadata"]["paging"]["last"]
    print(f"Fetchin page: 1/{last}")
    car_ads.extend(ads["docs"])
    
    for page in range(2, last + 1):
        print(f"Fetching page: {page}/{last}")
        time.sleep(2.35)
        res = api.search_car(
            locations=locs,
            price_from = min_price,
            price_to=max_price,
            page=page
        )
        car_ads.extend(res["docs"])
    save_cars()

def is_excluded(ad):
    text = f"{ad.get('heading')} {ad.get('model_specification', '')}".lower()
    return any(word in text for word in EXCLUDE)

def save_cars():
    print(f'Before filter: {len(car_ads)}')
    car_ads[:]=[ad for ad in car_ads if not is_excluded(ad)]
    print(f'After filter: {len(car_ads)}')

    Path("data").mkdir(exist_ok = True)
    Path("data/cars.json").write_text(
        json.dumps(car_ads, indent=2, ensure_ascii = False), encoding="utf-8"
    )

def get_mcs(min_price = 0, max_price = 45000):
    '''Fill up car_ads with ads based on filter criteria'''

    mcs = api.search_mc(
        locations=locs,
        price_from = min_price,
        price_to = max_price
        )
    
    total = mcs["metadata"]["result_size"]["match_count"]
    if total < 1:
        print("No ads found, cancelling fetch.")
        return
            
    print(f"Found {total} ads. Will crawl {(total // 2500) + 1} times.")
    if total > 2500 and max_price - min_price > 1:
        mid = (max_price + min_price) // 2
        get_mcs(min_price, mid)
        get_mcs(mid+1, max_price)
        return
    
    fetch_range_mcs(min_price, max_price, mcs)

    
def fetch_range_mcs(min_price, max_price, ads):
    '''Page through one price range that has 2500 reslts or fewer'''
    print(f"Fetching MCs in range: {min_price} - {max_price}")

    last = ads["metadata"]["paging"]["last"]
    print(f"Fetching page: 1/{last}")
    mc_ads.extend(ads["docs"])

    for page in range(2, last + 1):
        print(f"Fetching page: {page}/{last}")
        time.sleep(2.35)
        res = api.search_mc(
            locations=locs,
            price_from = min_price,
            price_to=max_price,
            page=page
        )
        mc_ads.extend(res["docs"])
    save_mcs()


def save_mcs():
    print(f'Before filter: {len(mc_ads)}')
    mc_ads[:]=[ad for ad in mc_ads if not is_excluded(ad)]
    print(f'After filter: {len(mc_ads)}')
   
    Path("data").mkdir(exist_ok = True)
    Path("data/mcs.json").write_text(
    json.dumps(mc_ads, indent=2, ensure_ascii = False), encoding="utf-8"
    )


