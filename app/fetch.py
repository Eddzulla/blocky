from blocket_api import BlocketAPI
from blocket_api.constants import Location
import time
import json
from pathlib import Path
import random


api = BlocketAPI()
locs = [Location.SKANE]
EXCLUDE = ["privatleasing", "privatleasa", "p-leasa", "p-leasing","lease","leasing","fullserviceleasing!", "fullserviceleasing", "leasingkampanj","företagsleasing"]
car_ads = []
mc_ads = []
first_fetch = False

def get_cars(min_price = 0, max_price = 30000):
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
  
    first_fetch = True
    if first_fetch:
        print(f"Found {total} ads. Will crawl {(total // 2500) + 1} times.")
        first_fetch = False

    if total > 2500 and max_price - min_price > 1:
        mid = (max_price + min_price) // 2
        get_cars(min_price, mid)
        get_cars(mid+1, max_price)
        return
    
    _fetch_range_cars(min_price, max_price, cars)
    

def _fetch_range_cars(min_price, max_price, ads):
    '''Page through one price range that has 2500 reslts or fewer'''
    print(f"Fetching cars in range: {min_price} - {max_price}")
    
    last = ads["metadata"]["paging"]["last"]
    print(f"Fetching page: 1/{last}")
    car_ads.extend(ads["docs"])
    
    for page in range(2, last + 1):
        print(f"Fetching page: {page}/{last}")
        time.sleep(random.random()+1)
        res = api.search_car(
            locations=locs,
            price_from = min_price,
            price_to=max_price,
            page=page
        )
        car_ads.extend(res["docs"])

    

def _is_excluded(ad):
    text = f"{ad.get('heading')} {ad.get('model_specification', '')}".lower()
    return any(word in text for word in EXCLUDE)


def get_mcs(min_price = 0, max_price = 40000):
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
    
    _fetch_range_mcs(min_price, max_price, mcs)
    
def _fetch_range_mcs(min_price, max_price, ads):
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

def filter_ads(ads) -> list:
    filtered = [ad for ad in ads if not _is_excluded(ad)]
    return filtered

def save_data(ads: list, vertical: str):
    path = Path("data") / f"{vertical}.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(
        json.dumps(ads, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f'Saved {len(ads)} ads to {path}')
