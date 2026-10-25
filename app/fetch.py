from blocket_api import BlocketAPI
from blocket_api.constants import Location
import time
import json
from pathlib import Path
import random


api = BlocketAPI()
locs = [Location.SKANE]
EXCLUDE = ["privatleasing", "privatleasa", "p-leasa", "p-leasing","lease","leasing","fullserviceleasing!", "fullserviceleasing", "leasingkampanj","företagsleasing"]
LEASING_SALES_FORM = 5
car_ads = []
mc_ads = []

def get_cars(min_price = 0, max_price = 50000):
    '''Fill up car_ads with ads based on filter criteria'''
    _get_listings(api.search_car, car_ads, "cars", min_price, max_price)


def get_mcs(min_price = 0, max_price = 50000):
    '''Fill up mc_ads with ads based on filter criteria'''
    _get_listings(api.search_mc, mc_ads, "MCs", min_price, max_price)


def _get_listings(search_fn, ads: list, label: str, min_price, max_price):
    '''Search one price range and recursively split it if it has more than 2500 results'''
    result = search_fn(
        locations=locs,
        price_from=min_price,
        price_to=max_price
    )

    total = result["metadata"]["result_size"]["match_count"]
    if total < 1:
        print("No ads found, cancelling fetch.")
        return

    if total > 2500 and max_price - min_price > 1:
        mid = (max_price + min_price) // 2
        _get_listings(search_fn, ads, label, min_price, mid)
        _get_listings(search_fn, ads, label, mid + 1, max_price)
        return

    print(f"Found {total} ads. Will crawl {(total // 2500) + 1} times.")
    _fetch_range(search_fn, ads, label, min_price, max_price, result)


def _fetch_range(search_fn, ads: list, label: str, min_price, max_price, first_page):
    '''Page through one price range that has 2500 results or fewer'''
    print(f"Fetching {label} in range: {min_price} - {max_price}")

    last = first_page["metadata"]["paging"]["last"]
    print(f"Fetching page: 1/{last}")
    ads.extend(first_page["docs"])

    for page in range(2, last + 1):
        print(f"Fetching page: {page}/{last}")
        time.sleep(random.random() + 1)
        res = search_fn(
            locations=locs,
            price_from=min_price,
            price_to=max_price,
            page=page
        )
        ads.extend(res["docs"])


def _is_excluded(ad):
    if ad.get("sales_form") == LEASING_SALES_FORM:
        return True
    text = f"{ad.get('heading', '')} {ad.get('model_specification', '')}".lower()
    return any(word in text for word in EXCLUDE)


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
