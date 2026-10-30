from blocket_api import BlocketAPI, CarSortOrder, McSortOrder
from blocket_api.constants import Location
import time
import json
from datetime import date
from pathlib import Path
import random


api = BlocketAPI()
locs = [Location.SKANE, Location.HALLAND, Location.BLEKINGE]
EXCLUDE = ["privatleasing", "privatleasa", "p-leasa", "p-leasing","lease","leasing","fullserviceleasing!", "fullserviceleasing", "leasingkampanj","företagsleasing"]
LEASING_SALES_FORM = 5
PRIVATE_LEASE_MAX_AGE_YEARS = 3
PRIVATE_LEASE_PRICE_CEILING = 15000
MAX_QUICK_FETCH_PAGES = 50
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

    print(f"Found {total} ads in range {min_price}-{max_price}.")
    _fetch_range(search_fn, ads, label, min_price, max_price, result)


def _fetch_range(search_fn, ads: list, label: str, min_price, max_price, first_page):
    '''Page through one price range that has 2500 results or fewer'''
    print(f"Fetching {label} in range: {min_price} - {max_price}")

    last = first_page["metadata"]["paging"]["last"]
    print(f"Fetching page: 1/{last}")
    ads.extend(first_page["docs"])

    for page in range(2, last + 1):
        print(f"Fetching page: {page}/{last}")
        time.sleep(random.uniform(4, 7))
        res = search_fn(
            locations=locs,
            price_from=min_price,
            price_to=max_price,
            page=page
        )
        ads.extend(res["docs"])


def get_new_cars(existing_ids: set[int], min_price = 0, max_price = 50000):
    '''Fill up car_ads with only ads not already in existing_ids, newest-published first'''
    _get_new_listings(api.search_car, CarSortOrder.PUBLISHED_DESC, car_ads, "cars", existing_ids, min_price, max_price)


def get_new_mcs(existing_ids: set[int], min_price = 0, max_price = 50000):
    '''Fill up mc_ads with only ads not already in existing_ids, newest-published first'''
    _get_new_listings(api.search_mc, McSortOrder.PUBLISHED_DESC, mc_ads, "MCs", existing_ids, min_price, max_price)


def _get_new_listings(search_fn, sort_order, ads: list, label: str, existing_ids: set[int], min_price, max_price):
    '''Page newest-first until hitting an ad already in existing_ids, or a safety cap.
    Doesn't need price-range splitting like the full fetch: we're not after every match,
    just the leading edge of ones we haven't seen yet.'''
    page = 1
    while page <= MAX_QUICK_FETCH_PAGES:
        res = search_fn(
            locations=locs,
            price_from=min_price,
            price_to=max_price,
            sort_order=sort_order,
            page=page,
        )
        docs = res["docs"]
        if not docs:
            break

        for ad in docs:
            if int(ad["id"]) in existing_ids:
                print(f"{label}: reached an already-known listing on page {page}, stopping. Found {len(ads)} new ad(s).")
                return
            ads.append(ad)

        print(f"{label}: page {page} done, {len(ads)} new ad(s) so far")

        last = res["metadata"]["paging"]["last"]
        if page >= last:
            break
        page += 1
        time.sleep(random.uniform(4, 7))
    else:
        print(f"{label}: hit the {MAX_QUICK_FETCH_PAGES}-page safety cap. Found {len(ads)} new ad(s); there may be more.")


def _is_excluded(ad):
    if ad.get("sales_form") == LEASING_SALES_FORM:
        return True
    if "amount_ex_vat" in (ad.get("price") or {}):
        return True
    if ad.get("organisation_name"):
        return True
    if _is_private_lease_sublet(ad):
        return True
    
    text = f"{ad.get('heading', '')} {ad.get('model_specification') or ''}".lower()
    return any(word in text for word in EXCLUDE)


def _is_private_lease_sublet(ad):
    '''Near-new car at a suspiciously low price: no real used car that age sells this
    cheap, so it's almost certainly a leasing offer (private sublet or dealer deal)
    that sales_form/amount_ex_vat didn't flag.'''
    year = ad.get("year")
    if year is None or date.today().year - year > PRIVATE_LEASE_MAX_AGE_YEARS:
        return False
    price = (ad.get("price") or {}).get("amount")
    return price is not None and price < PRIVATE_LEASE_PRICE_CEILING


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


def append_data(ads: list, vertical: str):
    '''Merge new ads into the existing data/<vertical>.json, deduped by id.'''
    path = Path("data") / f"{vertical}.json"
    path.parent.mkdir(exist_ok=True)

    existing = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
    by_id = {ad["id"]: ad for ad in existing}
    by_id.update({ad["id"]: ad for ad in ads})
    merged = list(by_id.values())

    path.write_text(
        json.dumps(merged, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f'Merged {len(ads)} new ads into {path} ({len(merged)} total)')
