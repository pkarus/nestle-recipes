"""
fetch_seeds.py - download the real, openly-licensed seed datasets the Nestle
diet-optimization demo is built on. Idempotent: skips files already present.

Sources:
  1. USDA FoodData Central, SR Legacy (CC0, public domain). The food x nutrient
     spine. Downloaded as the official CSV bundle and unzipped under
     data/seed/FoodData_Central_sr_legacy_food_csv_2018-04/.
  2. Open Food Facts (ODbL). Real branded products with per-100g nutrition,
     Nutri-Score, NOVA, and vegan / allergen label tags. Pulled via the
     search-a-licious API (the public legacy + v2 search endpoints were 503ing).

Run: .venv/bin/python data/fetch_seeds.py
"""
import csv
import os
import sys
import time
import zipfile

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
SEED = os.path.join(HERE, "seed")
os.makedirs(SEED, exist_ok=True)

UA = {"User-Agent": "NestleDietDemo/1.0 (piotr.kraus@relational.ai)"}

USDA_URL = (
    "https://fdc.nal.usda.gov/fdc-datasets/"
    "FoodData_Central_sr_legacy_food_csv_2018-04.zip"
)
USDA_ZIP = os.path.join(SEED, "sr_legacy.zip")
USDA_DIR = os.path.join(SEED, "FoodData_Central_sr_legacy_food_csv_2018-04")

OFF_SEARCH = "https://search.openfoodfacts.org/search"
OFF_FIELDS = (
    "code,product_name,brands,categories_tags,labels_tags,allergens_tags,"
    "countries_tags,nutriscore_grade,nova_group,nutriments"
)
OFF_CSV = os.path.join(SEED, "off_products.csv")
# Queries chosen to span the categories a vegan endurance athlete actually eats,
# so the branded layer is relevant, not random. Scoped to UK/US first so product
# names are English (Nestle-realistic, not data noise), then a global vegan
# fallback for variety.
_CATS = [
    'categories_tags:"en:plant-based-milk-alternatives"',
    'categories_tags:"en:tofu"',
    'categories_tags:"en:plant-based-meat-substitutes"',
    'categories_tags:"en:breakfast-cereals"',
    'categories_tags:"en:mueslis"',
    'categories_tags:"en:legumes-and-their-products"',
    'categories_tags:"en:plant-based-yogurts"',
    'categories_tags:"en:cereal-bars"',
    'categories_tags:"en:nuts"',
    'categories_tags:"en:hummus"',
]
_COUNTRIES = ['countries_tags:"en:united-kingdom"', 'countries_tags:"en:united-states"']
OFF_QUERIES = (
    [f'{c} AND {ctry}' for ctry in _COUNTRIES for c in _CATS]
    + ['labels_tags:"en:vegan" AND countries_tags:"en:united-kingdom"',
       'labels_tags:"en:vegan"']
)
OFF_PAGES = 3          # pages per query
OFF_PAGE_SIZE = 100
OFF_TARGET = 700       # stop once we have this many clean products


def download_usda():
    if os.path.isdir(USDA_DIR) and os.path.exists(os.path.join(USDA_DIR, "food.csv")):
        print(f"[usda] already present: {USDA_DIR}")
        return
    print(f"[usda] downloading {USDA_URL}")
    with requests.get(USDA_URL, headers=UA, stream=True, timeout=180) as r:
        r.raise_for_status()
        with open(USDA_ZIP, "wb") as f:
            for chunk in r.iter_content(1 << 16):
                f.write(chunk)
    print(f"[usda] unzipping -> {SEED}")
    with zipfile.ZipFile(USDA_ZIP) as z:
        z.extractall(SEED)
    print(f"[usda] done: {USDA_DIR}")


NUT_KEYS = {
    "energy-kcal_100g": "energy_kcal_100g",
    "proteins_100g": "proteins_100g",
    "carbohydrates_100g": "carbohydrates_100g",
    "fat_100g": "fat_100g",
    "fiber_100g": "fiber_100g",
    "sugars_100g": "sugars_100g",
    "saturated-fat_100g": "saturated_fat_100g",
    "salt_100g": "salt_100g",
    "sodium_100g": "sodium_100g",
}
OUT_COLS = [
    "code", "product_name", "brands", "categories_tags", "labels_tags",
    "allergens_tags", "countries_tags", "nutriscore_grade", "nova_group",
] + list(NUT_KEYS.values())


def _clean_row(p):
    nut = p.get("nutriments") or {}
    name = (p.get("product_name") or "").strip()
    code = str(p.get("code") or "").strip()
    if not name or not code:
        return None
    kcal = nut.get("energy-kcal_100g")
    prot = nut.get("proteins_100g")
    carb = nut.get("carbohydrates_100g")
    fat = nut.get("fat_100g")
    # require the four macros so recipe/diet math is well-defined
    if None in (kcal, prot, carb, fat):
        return None
    brands = p.get("brands") or ""
    if isinstance(brands, list):
        brands = ", ".join(str(b) for b in brands)
    row = {
        "code": code,
        "product_name": name,
        "brands": str(brands).strip(),
        "categories_tags": "|".join(p.get("categories_tags") or []),
        "labels_tags": "|".join(p.get("labels_tags") or []),
        "allergens_tags": "|".join(p.get("allergens_tags") or []),
        "countries_tags": "|".join(p.get("countries_tags") or []),
        "nutriscore_grade": (p.get("nutriscore_grade") or "").strip(),
        "nova_group": p.get("nova_group"),
    }
    for src, dst in NUT_KEYS.items():
        row[dst] = nut.get(src)
    return row


def fetch_off():
    if os.path.exists(OFF_CSV):
        print(f"[off] already present: {OFF_CSV}")
        return
    s = requests.Session()
    s.headers.update(UA)
    seen = {}
    for q in OFF_QUERIES:
        if len(seen) >= OFF_TARGET:
            break
        for page in range(1, OFF_PAGES + 1):
            params = {"q": q, "page": page, "page_size": OFF_PAGE_SIZE, "fields": OFF_FIELDS}
            try:
                r = s.get(OFF_SEARCH, params=params, timeout=60)
                if r.status_code != 200 or "json" not in r.headers.get("content-type", ""):
                    print(f"[off] {q!r} p{page} -> {r.status_code}, skip")
                    break
                hits = r.json().get("hits", [])
            except Exception as e:
                print(f"[off] {q!r} p{page} ERR {type(e).__name__}")
                break
            kept = 0
            for p in hits:
                row = _clean_row(p)
                if row and row["code"] not in seen:
                    seen[row["code"]] = row
                    kept += 1
            print(f"[off] {q!r} p{page}: {len(hits)} hits, +{kept} kept, total {len(seen)}")
            if len(hits) < OFF_PAGE_SIZE:
                break
            time.sleep(1.5)
        time.sleep(1.5)
    rows = list(seen.values())
    with open(OFF_CSV, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=OUT_COLS)
        w.writeheader()
        w.writerows(rows)
    print(f"[off] wrote {len(rows)} products -> {OFF_CSV}")


if __name__ == "__main__":
    download_usda()
    fetch_off()
