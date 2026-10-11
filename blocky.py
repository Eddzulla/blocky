from blocket_api import BlocketAPI, CarAd, CarModel
from blocket_api.constants import Location
import time
import json
from pathlib import Path

api = BlocketAPI()
page = 1
all_ads = []


cars = api.search_car(
    locations=[Location.SKANE],
    price_from= 0,
    price_to = 50000
    )
print(cars["metadata"])
print(cars["metadata"]["result_size"]["match_count"])

mcs = api.search_mc(
    locations = [Location.SKANE],
    price_from = 0,
    price_to = 50000
)

print(mcs["metadata"]["result_size"]["match_count"])
'''
while True and page < 3:
    results = api.search_car(models=[CarModel.HONDA], page = page)
    all_ads.extend(results["docs"])

    last = results["metadata"]["paging"]["last"]
    if page >= last:
        break;
    print(f"Page {page} done.")
    page += 1
    time.sleep(2)

print(all_ads[0])
print(len(all_ads))

Path("data").mkdir(exist_ok=True)
Path("data/honda.json").write_text(
    json.dumps(all_ads, indent=2, ensure_ascii=False), encoding="utf-8"
)
    '''