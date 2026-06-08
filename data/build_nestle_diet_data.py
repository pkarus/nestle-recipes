"""
build_nestle_diet_data.py - deterministic generator for the Nestle diet/menu
optimization demo (RelationalAI prescriptive demo).

Theme: "from price volatility to profit protection, preserving nutrition and
sustainability." Hero persona: a vegan endurance athlete. The data backs three
demo questions: a rules audit (Q1), a cost-minimizing menu MIP (Q2), and a
persistent-rule re-solve under a CO2 cap or price shock (Q3).

Data provenance (hybrid, reproducible):
  - Nutrition spine: USDA FoodData Central SR Legacy (CC0, public domain),
    resolved to specific foods in usda_select.py.
  - Branded products: Open Food Facts (ODbL), pulled by fetch_seeds.py.
  - Sustainability coefficients: representative figures from Poore & Nemecek
    (2018, Science), processed by Our World in Data (CC BY 4.0).
  - Recipes, prices, persona targets: synthesized here from published standards.

Run: .venv/bin/python data/build_nestle_diet_data.py
Outputs: data/out/*.csv (one file per table) + data/out/DATA_DICTIONARY.md
"""
import os
import random
import sys

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
os.makedirs(OUT, exist_ok=True)
sys.path.insert(0, HERE)
import usda_select as U  # noqa: E402

SEED = 42
RNG = random.Random(SEED)

# Per-100g nutrient columns carried on every ingredient and summed onto recipes.
NUTRI_COLS = [
    "kcal", "protein_g", "carb_g", "fat_g", "fiber_g", "sugars_g", "satfat_g",
    "sodium_mg", "calcium_mg", "iron_mg", "potassium_mg", "zinc_mg",
    "magnesium_mg", "vitd_ug", "vitc_mg", "b12_ug",
]

# Allergen / diet flag columns.
ALLERGEN_COLS = ["has_gluten", "has_dairy", "has_egg", "has_soy", "has_nuts",
                 "has_peanuts", "has_sesame", "has_fish"]

# ---------------------------------------------------------------------------
# 1. Sustainability coefficients (Poore & Nemecek 2018 / OWID, CC BY 4.0).
#    kg CO2e per kg of food, and liters of freshwater per kg. Keyed by commodity
#    first, then food_group. Representative values; documented, not exact.
# ---------------------------------------------------------------------------
CO2_BY_COMMODITY = {
    "rice": 4.0, "oats": 1.6, "wheat": 1.4, "rye": 1.4, "maize": 1.0,
    "buckwheat": 1.3, "millet": 1.3, "quinoa": 1.5, "potato": 0.5,
    "lentils": 0.9, "beans": 2.0, "chickpeas": 0.9, "peas": 0.9, "soy": 2.0,
    "nuts": 0.43, "peanuts": 1.2, "seeds": 0.6, "vegetables": 0.5, "fruit": 0.5,
    "olive_oil": 5.4, "veg_oil": 3.5, "sugar": 1.8, "cocoa": 19.0,
    "coffee": 0.8, "yeast": 1.5,
}
WATER_BY_COMMODITY = {
    "rice": 2248, "oats": 600, "wheat": 648, "rye": 648, "maize": 900,
    "buckwheat": 600, "millet": 600, "quinoa": 1200, "potato": 60,
    "lentils": 1200, "beans": 1500, "chickpeas": 1200, "peas": 397, "soy": 800,
    "nuts": 4134, "peanuts": 1852, "seeds": 1500, "vegetables": 320, "fruit": 700,
    "olive_oil": 3000, "veg_oil": 1500, "sugar": 800, "cocoa": 3000,
    "coffee": 1200, "yeast": 500,
}
CO2_BY_GROUP_DEFAULT = 1.0
WATER_BY_GROUP_DEFAULT = 800


def co2_kg(commodity):
    return CO2_BY_COMMODITY.get(commodity, CO2_BY_GROUP_DEFAULT)


def water_l(commodity):
    return WATER_BY_COMMODITY.get(commodity, WATER_BY_GROUP_DEFAULT)


# ---------------------------------------------------------------------------
# 2. Commodities + monthly price index (Jan 2025 .. Jun 2026). Anchored to real
#    recent moves so a "re-optimize after the spike" event is datable. Index is
#    a normalized price (1.00 = Jan 2025). The demo "today" is 2026-06.
# ---------------------------------------------------------------------------
MONTHS = pd.period_range("2025-01", "2026-06", freq="M").astype(str).tolist()


def _series(points):
    """Linear-interpolate a few (month_index, value) anchors across 18 months."""
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    out = []
    for i in range(len(MONTHS)):
        # find bracketing anchors
        if i <= xs[0]:
            out.append(ys[0])
            continue
        if i >= xs[-1]:
            out.append(ys[-1])
            continue
        for a in range(len(xs) - 1):
            if xs[a] <= i <= xs[a + 1]:
                t = (i - xs[a]) / (xs[a + 1] - xs[a])
                out.append(round(ys[a] + t * (ys[a + 1] - ys[a]), 3))
                break
    return out


# (month_index, index_value). Shapes mirror Trading Economics moves.
COMMODITY_SPEC = {
    # commodity_id: (display_name, unit, base_usd_per_kg, price_index_anchors)
    "cocoa":     ("Cocoa", "USD/kg", 8.50, [(0, 1.00), (3, 1.95), (6, 1.55), (12, 0.75), (17, 0.62)]),
    "coffee":    ("Coffee (arabica)", "USD/kg", 6.20, [(0, 1.00), (4, 1.85), (8, 1.30), (13, 1.05), (17, 0.92)]),
    "wheat":     ("Wheat", "USD/kg", 0.32, [(0, 1.00), (6, 1.08), (12, 0.96), (17, 0.93)]),
    "soy":       ("Soybean", "USD/kg", 0.45, [(0, 1.00), (6, 1.06), (12, 1.02), (17, 1.00)]),
    "oats":      ("Oats", "USD/kg", 0.40, [(0, 1.00), (6, 1.10), (12, 1.05), (17, 1.03)]),
    "rice":      ("Rice", "USD/kg", 0.55, [(0, 1.00), (6, 0.95), (12, 0.90), (17, 0.88)]),
    "nuts":      ("Tree nuts", "USD/kg", 9.00, [(0, 1.00), (6, 1.12), (12, 1.18), (17, 1.22)]),
    "peanuts":   ("Peanuts", "USD/kg", 3.20, [(0, 1.00), (6, 1.05), (12, 1.08), (17, 1.06)]),
    "sugar":     ("Sugar", "USD/kg", 0.45, [(0, 1.00), (6, 0.95), (12, 0.90), (17, 0.88)]),
    "veg_oil":   ("Vegetable oil", "USD/kg", 1.20, [(0, 1.00), (6, 1.10), (12, 1.05), (17, 1.02)]),
    "olive_oil": ("Olive oil", "USD/kg", 8.00, [(0, 1.00), (4, 1.30), (10, 1.10), (17, 0.95)]),
    "lentils":   ("Lentils", "USD/kg", 1.40, [(0, 1.00), (8, 1.05), (17, 1.02)]),
    "beans":     ("Dry beans", "USD/kg", 1.60, [(0, 1.00), (8, 1.04), (17, 1.01)]),
    "chickpeas": ("Chickpeas", "USD/kg", 1.50, [(0, 1.00), (8, 1.06), (17, 1.03)]),
    "peas":      ("Peas", "USD/kg", 1.30, [(0, 1.00), (8, 1.03), (17, 1.01)]),
    "potato":    ("Potato", "USD/kg", 0.60, [(0, 1.00), (8, 1.02), (17, 1.00)]),
    "vegetables": ("Vegetables (mixed)", "USD/kg", 1.80, [(0, 1.00), (8, 1.05), (17, 1.03)]),
    "fruit":     ("Fruit (mixed)", "USD/kg", 2.20, [(0, 1.00), (8, 1.04), (17, 1.02)]),
    "seeds":     ("Seeds", "USD/kg", 6.50, [(0, 1.00), (8, 1.08), (17, 1.10)]),
    "quinoa":    ("Quinoa", "USD/kg", 3.80, [(0, 1.00), (8, 1.05), (17, 1.04)]),
    "maize":     ("Maize", "USD/kg", 0.30, [(0, 1.00), (8, 0.98), (17, 0.96)]),
    "buckwheat": ("Buckwheat", "USD/kg", 1.90, [(0, 1.00), (8, 1.03), (17, 1.02)]),
    "millet":    ("Millet", "USD/kg", 1.70, [(0, 1.00), (8, 1.03), (17, 1.02)]),
    "rye":       ("Rye", "USD/kg", 0.45, [(0, 1.00), (8, 1.02), (17, 1.00)]),
    "yeast":     ("Yeast / fortificants", "USD/kg", 12.00, [(0, 1.00), (8, 1.02), (17, 1.01)]),
}


def build_commodity_tables():
    com_rows, hist_rows = [], []
    for cid, (name, unit, base, anchors) in COMMODITY_SPEC.items():
        idx = _series(anchors)
        cur = idx[-1]
        com_rows.append({
            "commodity_id": cid, "commodity_name": name, "unit": unit,
            "base_price_usd_per_kg": base,
            "current_price_index": cur,
            "current_price_usd_per_kg": round(base * cur, 4),
            "peak_price_index": max(idx),
            "is_volatile": cid in ("cocoa", "coffee", "olive_oil"),
        })
        for m, v in zip(MONTHS, idx):
            hist_rows.append({
                "commodity_id": cid, "price_month": m + "-01",
                "price_index": v, "price_usd_per_kg": round(base * v, 4),
            })
    return pd.DataFrame(com_rows), pd.DataFrame(hist_rows)


# cost shock scenario: volatile commodities spike (Q3 price-shock re-solve).
SHOCK_MULTIPLIER = {"cocoa": 2.5, "coffee": 1.9, "olive_oil": 1.4, "nuts": 1.3}

# realistic retail base cost (USD per 100 g / 100 ml) by food group. The commodity
# price index then modulates it so volatile commodities (cocoa, coffee, nuts,
# olive oil) move over time and under the shock scenario.
REALISTIC_BASE_COST = {
    "grain": 0.12, "starch": 0.08, "legume": 0.18, "plant_protein": 0.50,
    "nuts_seeds": 1.30, "vegetable": 0.35, "fruit": 0.40, "plant_dairy": 0.22,
    "fortified": 1.20, "fat": 0.30, "sweetener": 0.45, "flavor": 1.40,
    "beverage": 0.15, "snack": 0.90, "ready_meal": 1.40,
}
# explicit costs for the hand-authored specialty items (processed, branded).
HAND_COST = {
    "Pea protein powder": 2.20, "Soy protein powder": 1.90,
    "Nutritional yeast (fortified)": 2.50,
    "Vegan protein shake (fortified)": 0.60, "Fortified oat drink": 0.25,
}


def ingredient_cost_per_100g(commodity, group, price_index, shock=False, branded=False):
    base = REALISTIC_BASE_COST.get(group, 0.40)
    mult = price_index
    if shock:
        mult *= SHOCK_MULTIPLIER.get(commodity, 1.0)
    if branded:
        base *= 1.3
    return round(base * mult, 4)  # per 100 g


# ---------------------------------------------------------------------------
# 3. Hand-authored specialty / fortified ingredients (vegan), incl. the Nestle
#    Health Science angle (Boost-style shake, plant protein). Nutrition values
#    are representative label values; clearly marked source='curated'.
# ---------------------------------------------------------------------------
def _nut(kcal, p, c, f, fib, sug, sat, na, ca, fe, k, zn, mg, vd, vc, b12):
    return dict(zip(NUTRI_COLS, [kcal, p, c, f, fib, sug, sat, na, ca, fe, k, zn, mg, vd, vc, b12]))


HAND_AUTHORED = [
    # name, group, commodity, brand, gluten_free, allergens, nutrition
    ("Pea protein powder", "plant_protein", "peas", "Nestle PerformaPlant", True,
     {"has_soy": False}, _nut(380, 80, 5, 5, 5, 1, 1, 600, 120, 6, 150, 3.5, 60, 0, 0, 0)),
    ("Soy protein powder", "plant_protein", "soy", "Nestle PerformaPlant", True,
     {"has_soy": True}, _nut(375, 82, 3, 4, 4, 1, 0.8, 700, 200, 8, 200, 4, 70, 0, 0, 0)),
    ("Nutritional yeast (fortified)", "fortified", "yeast", "Nestle VitaBoost", True,
     {}, _nut(345, 50, 36, 5, 22, 0, 1, 30, 30, 5, 2000, 8, 100, 0, 0, 115)),
    ("Vegan protein shake (fortified)", "plant_dairy", "soy", "Nestle Boost Plant", True,
     {"has_soy": True}, _nut(85, 7, 8, 2.8, 1.2, 4, 0.5, 70, 150, 2.4, 200, 3, 50, 3.0, 9, 0.6)),
    ("Fortified oat drink", "plant_dairy", "oats", "Nestle Garden Blend", True,
     {}, _nut(47, 1.0, 7.0, 1.5, 0.8, 3.3, 0.2, 40, 120, 0.4, 130, 0.4, 12, 2.4, 0, 0.38)),
]

# Fortification overlay (per 100 g) for USDA items that are fortified in real
# products but where the SR Legacy record is incomplete. Representative UK/US
# fortified-label values.
FORTIFY_OVERLAY = {
    "Fortified breakfast cereal": {"vitd_ug": 4.2, "b12_ug": 6.7, "calcium_mg": 330.0},
    "Fortified gluten-free cereal": {"vitd_ug": 4.2, "b12_ug": 6.7, "calcium_mg": 330.0, "iron_mg": 28.0},
    "Soy milk (fortified)": {"vitd_ug": 1.5, "b12_ug": 1.0},
    "Almond milk (fortified)": {"vitd_ug": 1.3, "b12_ug": 0.5},
}


# ---------------------------------------------------------------------------
# 4. Build the INGREDIENT master from USDA + hand-authored + Open Food Facts.
# ---------------------------------------------------------------------------
def _empty_allergens():
    return {c: False for c in ALLERGEN_COLS}


def _allergens_for(name, group, commodity):
    a = _empty_allergens()
    n = name.lower()
    if commodity in ("wheat", "rye", "buckwheat") or "bread" in n or "pasta" in n or "couscous" in n or "cereal" in n or "tortilla" in n:
        if commodity in ("wheat", "rye"):
            a["has_gluten"] = True
        if "couscous" in n or "pasta" in n or ("bread" in n and "rye" in n) or ("bread" in n and "wheat" in n):
            a["has_gluten"] = True
    if commodity == "soy" or "soy" in n or "tofu" in n or "tempeh" in n or "edamame" in n:
        a["has_soy"] = True
    if group == "nuts_seeds" and ("almond" in n or "walnut" in n or "cashew" in n):
        a["has_nuts"] = True
    if "almond milk" in n:
        a["has_nuts"] = True
    if "peanut" in n:
        a["has_peanuts"] = True
    if "tahini" in n or "sesame" in n:
        a["has_sesame"] = True
    if "soy sauce" in n:
        a["has_gluten"] = True  # shoyu contains wheat
        a["has_soy"] = True
    return a


def _diet_flags(allergens):
    # everything in our catalog is plant-based -> vegan + vegetarian true.
    is_vegan = True
    is_vegetarian = True
    is_gluten_free = not allergens["has_gluten"]
    return is_vegan, is_vegetarian, is_gluten_free


def build_ingredients():
    rows = []
    iid = 0

    # 4a. USDA curated whole foods (full micronutrient profiles)
    matrix = U.load_matrix()
    usda = U.resolve(matrix)
    com_df, hist_df = build_commodity_tables()
    price_idx = dict(zip(com_df.commodity_id, com_df.current_price_index))

    for _, r in usda.iterrows():
        iid += 1
        commodity, group = r["commodity"], r["group"]
        allergens = _allergens_for(r["name"], group, commodity)
        is_v, is_veg, is_gf = _diet_flags(allergens)
        rec = {
            "ingredient_id": iid, "ingredient_name": r["name"], "brand": None,
            "is_branded": False, "source": "usda", "source_id": str(int(r["fdc_id"])),
            "food_group": group, "commodity_id": commodity,
            "is_fortified": False, "is_estimated_micros": False,
        }
        for col in NUTRI_COLS:
            rec[col] = None if pd.isna(r[col]) else round(float(r[col]), 3)
        rec.update(allergens)
        rec["is_vegan"], rec["is_vegetarian"], rec["is_gluten_free"] = is_v, is_veg, is_gf
        pidx = price_idx.get(commodity, 1.0)
        rec["cost_per_100g"] = ingredient_cost_per_100g(commodity, group, pidx)
        rec["cost_per_100g_shock"] = ingredient_cost_per_100g(commodity, group, pidx, shock=True)
        rec["co2e_per_kg"] = co2_kg(commodity)
        rec["water_l_per_kg"] = water_l(commodity)
        rec["nutriscore_grade"] = None
        rec["nova_group"] = 1
        rows.append(rec)

    # 4b. hand-authored specialty / fortified
    for name, group, commodity, brand, gf, allergen_over, nut in HAND_AUTHORED:
        iid += 1
        allergens = _empty_allergens()
        allergens.update(allergen_over)
        rec = {
            "ingredient_id": iid, "ingredient_name": name, "brand": brand,
            "is_branded": True, "source": "curated", "source_id": None,
            "food_group": group, "commodity_id": commodity,
            "is_fortified": True, "is_estimated_micros": False,
        }
        rec.update(nut)
        rec.update(allergens)
        rec["is_vegan"], rec["is_vegetarian"] = True, True
        rec["is_gluten_free"] = gf and not allergens["has_gluten"]
        pidx = price_idx.get(commodity, 1.0)
        base_cost = HAND_COST.get(name, REALISTIC_BASE_COST.get(group, 0.40))
        rec["cost_per_100g"] = round(base_cost * pidx, 4)
        rec["cost_per_100g_shock"] = round(base_cost * pidx * SHOCK_MULTIPLIER.get(commodity, 1.0), 4)
        rec["co2e_per_kg"] = co2_kg(commodity)
        rec["water_l_per_kg"] = water_l(commodity)
        rec["nutriscore_grade"] = "b"
        rec["nova_group"] = 4
        rows.append(rec)

    usda_df = pd.DataFrame(rows)

    # group medians (per 100g) for imputing OFF micronutrients
    micro_cols = ["calcium_mg", "iron_mg", "potassium_mg", "zinc_mg",
                  "magnesium_mg", "vitd_ug", "vitc_mg", "b12_ug"]
    grp_med = usda_df.groupby("food_group")[micro_cols].median()
    overall_med = usda_df[micro_cols].median()

    # 4c. Open Food Facts branded products
    off = pd.read_csv(os.path.join(HERE, "seed", "off_products.csv"))
    off_sel = _select_off(off)
    for _, p in off_sel.iterrows():
        iid += 1
        group, commodity = p["_group"], p["_commodity"]
        allergens = _empty_allergens()
        atags = str(p.get("allergens_tags") or "")
        if "en:gluten" in atags:
            allergens["has_gluten"] = True
        if "en:milk" in atags:
            allergens["has_dairy"] = True
        if "en:eggs" in atags:
            allergens["has_egg"] = True
        if "en:soybeans" in atags:
            allergens["has_soy"] = True
        if "en:nuts" in atags:
            allergens["has_nuts"] = True
        if "en:peanuts" in atags:
            allergens["has_peanuts"] = True
        if "en:sesame-seeds" in atags:
            allergens["has_sesame"] = True
        if "en:fish" in atags:
            allergens["has_fish"] = True
        labels = str(p.get("labels_tags") or "")
        is_vegan = "en:vegan" in labels
        is_gf = ("en:gluten-free" in labels) or (not allergens["has_gluten"])
        # nutrition: macros from OFF; sodium from sodium_100g(g)->mg or salt/2.5
        kcal = _f(p.get("energy_kcal_100g"))
        prot = _f(p.get("proteins_100g"))
        carb = _f(p.get("carbohydrates_100g"))
        fat = _f(p.get("fat_100g"))
        fib = _f(p.get("fiber_100g"), 0.0)
        sug = _f(p.get("sugars_100g"), 0.0)
        sat = _f(p.get("saturated_fat_100g"), 0.0)
        if pd.notna(p.get("sodium_100g")):
            na = round(_f(p.get("sodium_100g")) * 1000, 1)
        elif pd.notna(p.get("salt_100g")):
            na = round(_f(p.get("salt_100g")) / 2.5 * 1000, 1)
        else:
            na = 0.0
        rec = {
            "ingredient_id": iid, "ingredient_name": str(p["product_name"])[:80].strip(),
            "brand": (str(p["brands"])[:60] if pd.notna(p["brands"]) and str(p["brands"]).strip() else "Generic"),
            "is_branded": True, "source": "off", "source_id": str(p["code"]),
            "food_group": group, "commodity_id": commodity,
            "is_fortified": False, "is_estimated_micros": True,
            "kcal": kcal, "protein_g": prot, "carb_g": carb, "fat_g": fat,
            "fiber_g": fib, "sugars_g": sug, "satfat_g": sat, "sodium_mg": na,
        }
        med = grp_med.loc[group] if group in grp_med.index else overall_med
        for mc in micro_cols:
            v = med[mc] if pd.notna(med[mc]) else overall_med[mc]
            rec[mc] = round(float(v), 3) if pd.notna(v) else 0.0
        rec.update(allergens)
        rec["is_vegan"], rec["is_vegetarian"], rec["is_gluten_free"] = is_vegan, True, is_gf
        pidx = price_idx.get(commodity, 1.0)
        rec["cost_per_100g"] = ingredient_cost_per_100g(commodity, group, pidx, branded=True)
        rec["cost_per_100g_shock"] = ingredient_cost_per_100g(commodity, group, pidx, shock=True, branded=True)
        rec["co2e_per_kg"] = co2_kg(commodity)
        rec["water_l_per_kg"] = water_l(commodity)
        ns = str(p.get("nutriscore_grade") or "").strip().lower()
        rec["nutriscore_grade"] = ns if ns in list("abcde") else None
        rec["nova_group"] = int(p["nova_group"]) if pd.notna(p.get("nova_group")) else 4
        rows.append(rec)

    df = pd.DataFrame(rows)
    # apply fortification overlay to incomplete USDA fortified records
    for name, over in FORTIFY_OVERLAY.items():
        mask = df.ingredient_name == name
        for col, val in over.items():
            df.loc[mask, col] = val
        df.loc[mask, "is_fortified"] = True
    # whole-plant foods legitimately have 0 for some nutrients (vit D, B12,
    # sugars); USDA simply omits those rows. Treat missing as 0 so columns are
    # complete and NOT NULL for the modeler.
    for col in NUTRI_COLS:
        df[col] = df[col].fillna(0.0).round(3)
    # order columns
    front = ["ingredient_id", "ingredient_name", "brand", "is_branded", "source",
             "source_id", "food_group", "commodity_id", "is_fortified",
             "is_estimated_micros", "is_vegan", "is_vegetarian", "is_gluten_free",
             "nutriscore_grade", "nova_group", "cost_per_100g", "cost_per_100g_shock",
             "co2e_per_kg", "water_l_per_kg"]
    cols = front + NUTRI_COLS + ALLERGEN_COLS
    df = df[cols]
    return df, com_df, hist_df


def _f(v, default=None):
    try:
        if v is None or (isinstance(v, float) and pd.isna(v)):
            return default
        return float(v)
    except (TypeError, ValueError):
        return default


OFF_GROUP_RULES = [
    ("plant-based-milk", "plant_dairy", "soy"),
    ("plant-milk", "plant_dairy", "soy"),
    ("soy-milk", "plant_dairy", "soy"),
    ("oat-milk", "plant_dairy", "oats"),
    ("almond-milk", "plant_dairy", "nuts"),
    ("yogurt", "plant_dairy", "soy"),
    ("tofu", "plant_protein", "soy"),
    ("tempeh", "plant_protein", "soy"),
    ("meat-substitute", "plant_protein", "soy"),
    ("meat-alternative", "plant_protein", "soy"),
    ("veggie-burger", "plant_protein", "soy"),
    ("legume", "legume", "lentils"),
    ("bean", "legume", "beans"),
    ("hummus", "legume", "chickpeas"),
    ("breakfast-cereal", "grain", "wheat"),
    ("muesli", "grain", "oats"),
    ("granola", "grain", "oats"),
    ("bread", "grain", "wheat"),
    ("pasta", "grain", "wheat"),
    ("bar", "snack", "oats"),
    ("snack", "snack", "oats"),
    ("nut", "nuts_seeds", "nuts"),
    ("chocolate", "flavor", "cocoa"),
    ("juice", "beverage", "fruit"),
    ("smoothie", "beverage", "fruit"),
]


def _classify_off(categories):
    c = str(categories or "").lower()
    for key, group, commodity in OFF_GROUP_RULES:
        if key in c:
            return group, commodity
    return "snack", "oats"


# common non-English tokens that slip past the pure-ASCII filter; drop them so
# the branded layer reads as clean English products.
_NON_EN = (" au ", " aux ", " con ", " sans ", " con ", " bio", "soja", "frutos",
           "hamburguesa", "kichererbsen", "barquillos", "neulas", "tartiner",
           "garde du corps", "puerro", "vasca", "escalivada", "taza", "ecol",
           "crema", "avellanas", "naranja", "wurfel", "wurzel", " mit ", " und ",
           "citron", "pistache", "carotte", "chanvre", "cepes", "fromage",
           "queso", "leche", "avena", "galleta", "tomate et", "noisettes")


def _looks_english(name):
    n = str(name)
    if any(ord(ch) > 127 for ch in n):
        return False
    low = " " + n.lower() + " "
    return not any(tok in low for tok in _NON_EN)


def _select_off(off, target=45):
    """Pick a focused, relevant, English (UK/US) set of OFF products."""
    df = off.copy()
    df = df[df.product_name.notna() & (df.product_name.str.len() >= 3)]
    df = df[df.product_name.map(_looks_english)]
    df["_has_brand"] = df.brands.fillna("").str.len() > 0
    df = df[df["_has_brand"]]
    df["_grp"] = df.categories_tags.map(_classify_off)
    df["_group"] = df["_grp"].map(lambda t: t[0])
    df["_commodity"] = df["_grp"].map(lambda t: t[1])
    df["_vegan"] = df.labels_tags.fillna("").str.contains("en:vegan")
    df["_hasns"] = df.nutriscore_grade.fillna("").str.lower().isin(list("abcde"))
    df = df[(df.energy_kcal_100g.between(10, 900)) & (df.proteins_100g.between(0, 90))]
    # spread across groups: prefer vegan + has-nutriscore, deterministic
    picks = []
    per_group = max(4, target // 7)
    df["_lname"] = df.product_name.str.lower()
    order = df.sort_values(["_group", "_vegan", "_hasns", "code"],
                           ascending=[True, False, False, True])
    for g, sub in order.groupby("_group"):
        sub = sub.drop_duplicates(subset="_lname")
        picks.append(sub.head(per_group))
    sel = pd.concat(picks).drop_duplicates(subset="code")
    sel = sel.drop_duplicates(subset="_lname").head(target)
    return sel.sort_values("code").reset_index(drop=True)


# ---------------------------------------------------------------------------
# 5. Recipes: synthesize single-serving recipes from the ingredient catalog.
#    meal_type in {breakfast, main, snack}; lunch and dinner slots both draw
#    from 'main'. Recipe nutrition/cost/CO2 are derived by summing the BOM.
# ---------------------------------------------------------------------------
POOLS = {
    "oats": ["Rolled oats (dry)", "Scottish porridge oats"],
    "milk": ["Soy milk (fortified)", "Almond milk (fortified)", "Fortified oat drink",
             "Sweetened soya drink", "Almond milk"],
    "fruit": ["Banana", "Apple", "Blueberries", "Strawberries", "Mango", "Orange", "Dates", "Raisins"],
    "nut_seed": ["Almonds", "Walnuts", "Cashews", "Peanut butter", "Chia seeds",
                 "Flaxseed (ground)", "Sunflower seeds", "Pumpkin seeds", "Tahini"],
    "protein": ["Firm tofu", "Tempeh", "Lentils (cooked)", "Chickpeas (cooked)",
                "Black beans (cooked)", "Kidney beans (cooked)", "Edamame (cooked)",
                "Pea protein powder", "Soy protein powder"],
    "tofu_tempeh": ["Firm tofu", "Tempeh"],
    "legume": ["Lentils (cooked)", "Chickpeas (cooked)", "Black beans (cooked)", "Kidney beans (cooked)"],
    "grain_main": ["Brown rice (cooked)", "White rice (cooked)", "Quinoa (cooked)",
                   "Whole wheat pasta (cooked)", "Couscous (cooked)",
                   "Buckwheat groats (cooked)", "Millet (cooked)"],
    "starch": ["Potato (baked)", "Sweet potato (baked)", "Brown rice (cooked)", "Quinoa (cooked)"],
    "veg": ["Spinach (raw)", "Kale (raw)", "Broccoli (cooked)", "Carrot (raw)",
            "Red bell pepper (raw)", "Tomato (raw)", "Onion (raw)", "Mushroom (raw)",
            "Zucchini (cooked)", "Cauliflower (cooked)", "Sweet corn (cooked)"],
    "leafy": ["Spinach (raw)", "Kale (raw)"],
    "oil": ["Olive oil", "Rapeseed (canola) oil"],
}
CUISINES = ["Mediterranean", "Asian", "Mexican", "Indian", "Middle Eastern", "American", "British"]


def _short(name):
    return name.split(" (")[0].strip()


def build_recipes(ing_df):
    by_name = {r.ingredient_name: r for r in ing_df.itertuples(index=False)}

    def have(names):
        return [n for n in names if n in by_name]

    for k in POOLS:
        POOLS[k] = have(POOLS[k])

    recipes = []          # recipe rows
    bom = []              # recipe_ingredient rows
    rid = [0]

    def pick(pool, n=1):
        opts = POOLS[pool]
        return RNG.sample(opts, min(n, len(opts)))

    def add(meal_type, name_fmt, items, cuisine):
        """items: list of (ingredient_name, grams). Computes derived totals."""
        # merge duplicate ingredients within a recipe (sum grams) so the
        # (recipe, ingredient) bill-of-materials key stays unique
        merged = {}
        for n, g in items:
            if n in by_name:
                merged[n] = merged.get(n, 0) + g
        items = list(merged.items())
        if not items:
            return
        rid[0] += 1
        r_id = rid[0]
        tot = {c: 0.0 for c in NUTRI_COLS}
        cost = cost_shock = co2 = water = 0.0
        gf = True
        names_for_title = []
        for nm, g in items:
            row = by_name[nm]
            f = g / 100.0
            for c in NUTRI_COLS:
                tot[c] += getattr(row, c) * f
            cost += row.cost_per_100g * f
            cost_shock += row.cost_per_100g_shock * f
            co2 += row.co2e_per_kg * (g / 1000.0)
            water += row.water_l_per_kg * (g / 1000.0)
            gf = gf and bool(row.is_gluten_free)
            bom.append({"recipe_id": r_id, "ingredient_id": int(row.ingredient_id),
                        "ingredient_name": nm, "quantity_g": round(g, 1)})
            names_for_title.append(_short(nm))
        rec = {
            "recipe_id": r_id,
            "recipe_name": name_fmt,
            "meal_type": meal_type,
            "cuisine": cuisine,
            "servings": 1,
            "prep_time_min": RNG.choice([5, 10, 10, 15, 15, 20, 25, 30]),
            "n_ingredients": len(items),
            "total_grams": round(sum(g for _, g in items), 1),
            "is_vegan": True, "is_vegetarian": True, "is_gluten_free": gf,
            "cost_usd": round(cost, 4),
            "cost_usd_shock": round(cost_shock, 4),
            "co2e_kg": round(co2, 4),
            "water_l": round(water, 1),
        }
        for c in NUTRI_COLS:
            rec[c] = round(tot[c], 2)
        recipes.append(rec)

    # ---- BREAKFAST templates ----
    for fruit in POOLS["fruit"]:
        for ns in ["Almonds", "Walnuts", "Peanut butter", "Chia seeds", "Sunflower seeds"]:
            if ns not in by_name or fruit not in by_name:
                continue
            milk = pick("milk")[0]
            items = [("Rolled oats (dry)", 90), (milk, 250), (fruit, 120), (ns, 25), ("Maple syrup", 15)]
            add("breakfast", f"{_short(fruit)} oat bowl with {_short(ns).lower()}", items, "British")
    # fortified cereal bowls (drive vitamin D / B12 / iron; Nestle CPW angle).
    # Both a wheat-based and a gluten-free fortified cereal so a gluten-free
    # re-solve stays feasible.
    milk0 = "Soy milk (fortified)" if "Soy milk (fortified)" in by_name else (pick("milk")[0])
    for cereal in ["Fortified breakfast cereal", "Fortified gluten-free cereal"]:
        if cereal not in by_name:
            continue
        for fruit in ["Banana", "Blueberries", "Strawberries", "Raisins", "Mango"]:
            if fruit not in by_name:
                continue
            label = "cereal" if cereal == "Fortified breakfast cereal" else "gluten-free cereal"
            items = [(cereal, 60), (milk0, 250), (fruit, 100), ("Almonds", 20)]
            add("breakfast", f"Fortified {label} with {_short(fruit).lower()}", items, "British")
    # smoothies
    for fruit in ["Banana", "Blueberries", "Strawberries", "Mango"]:
        for prot, pg in [("Pea protein powder", 30), ("Soy protein powder", 30), ("Peanut butter", 25), ("Firm tofu", 80)]:
            if fruit not in by_name or prot not in by_name:
                continue
            milk = pick("milk")[0]
            items = [(milk, 250), (fruit, 150), (prot, pg), ("Flaxseed (ground)", 12)]
            add("breakfast", f"{_short(fruit)} {_short(prot).lower()} smoothie", items, "American")
    # tofu scramble
    for v1, v2 in [("Spinach (raw)", "Mushroom (raw)"), ("Kale (raw)", "Tomato (raw)"), ("Red bell pepper (raw)", "Onion (raw)")]:
        items = [("Firm tofu", 150), (v1, 70), (v2, 70), ("Rapeseed (canola) oil", 8),
                 ("Nutritional yeast (fortified)", 8), ("Whole wheat bread", 60)]
        add("breakfast", f"Tofu scramble with {_short(v1).lower()} on toast", items, "British")
    # chia pudding
    for fruit in ["Banana", "Blueberries", "Mango", "Strawberries"]:
        milk = pick("milk")[0]
        items = [("Chia seeds", 30), (milk, 200), (fruit, 90), ("Maple syrup", 12)]
        add("breakfast", f"{_short(fruit)} chia pudding", items, "American")

    # ---- MAIN templates (lunch/dinner) ----
    for grain in POOLS["grain_main"]:
        for prot in ["Firm tofu", "Tempeh", "Chickpeas (cooked)", "Lentils (cooked)", "Black beans (cooked)"]:
            if grain not in by_name or prot not in by_name:
                continue
            v1, v2 = pick("veg", 2) if len(POOLS["veg"]) >= 2 else (POOLS["veg"] * 2)[:2]
            flav = RNG.choice(["Tahini", "Soy sauce"])
            items = [(grain, 220), (prot, 165), (v1, 90), (v2, 90),
                     ("Olive oil", 12), (flav, 15)]
            add("main", f"{_short(prot)} & {_short(grain).lower()} bowl", items, RNG.choice(CUISINES))
    # curries / stews (legume + veg + rice side)
    for leg in POOLS["legume"]:
        for side in ["Brown rice (cooked)", "White rice (cooked)", "Quinoa (cooked)"]:
            if leg not in by_name:
                continue
            v1, v2 = pick("veg", 2)
            items = [(leg, 210), (v1, 100), (v2, 100), (side, 190), ("Rapeseed (canola) oil", 12)]
            add("main", f"{_short(leg)} curry with {_short(side).lower()}", items, "Indian")
    # stir fries
    for tt in POOLS["tofu_tempeh"]:
        for grain in ["Brown rice (cooked)", "White rice (cooked)", "Buckwheat groats (cooked)"]:
            v1, v2 = pick("veg", 2)
            items = [(tt, 180), (v1, 100), (v2, 100), (grain, 190), ("Soy sauce", 14), ("Rapeseed (canola) oil", 10)]
            add("main", f"{_short(tt)} stir-fry with {_short(grain).lower()}", items, "Asian")
    # pasta
    for prot in ["Lentils (cooked)", "Firm tofu", "Chickpeas (cooked)"]:
        for veg in ["Spinach (raw)", "Mushroom (raw)", "Broccoli (cooked)"]:
            items = [("Whole wheat pasta (cooked)", 220), ("Tomato (raw)", 130), (prot, 150),
                     (veg, 90), ("Olive oil", 12)]
            add("main", f"{_short(prot)} pasta with {_short(veg).lower()}", items, "Mediterranean")
    # salads
    for leafy in POOLS["leafy"]:
        for prot in ["Chickpeas (cooked)", "Firm tofu", "Kidney beans (cooked)"]:
            v1, v2 = pick("veg", 2)
            ns = RNG.choice(["Sunflower seeds", "Pumpkin seeds", "Walnuts"])
            items = [(leafy, 90), (prot, 180), (v1, 80), (v2, 80), (ns, 25), ("Olive oil", 14)]
            add("main", f"{_short(prot)} {_short(leafy).lower()} salad", items, "Mediterranean")

    # ---- SNACK templates ----
    for nut in ["Almonds", "Walnuts", "Cashews", "Pumpkin seeds"]:
        for fruit in ["Apple", "Banana", "Raisins"]:
            items = [(nut, 30), (fruit, 80)]
            add("snack", f"{_short(nut)} and {_short(fruit).lower()}", items, "American")
    for fruit in ["Banana", "Apple", "Strawberries"]:
        items = [("Whole wheat bread", 50), ("Peanut butter", 20), (fruit, 60)]
        add("snack", f"Peanut butter toast with {_short(fruit).lower()}", items, "American")
    # hummus & veg
    for veg in ["Carrot (raw)", "Red bell pepper (raw)", "Cauliflower (cooked)"]:
        items = [("Chickpeas (cooked)", 90), ("Tahini", 15), ("Olive oil", 8), (veg, 100)]
        add("snack", f"Hummus with {_short(veg).lower()}", items, "Middle Eastern")
    # energy balls
    for nut in ["Almonds", "Cashews", "Peanut butter"]:
        items = [("Dates", 40), ("Rolled oats (dry)", 30), (nut, 20), ("Cocoa powder (unsweetened)", 6)]
        add("snack", f"Cocoa {_short(nut).lower()} energy balls", items, "American")
    # shakes
    for fruit in ["Banana", "Blueberries", "Mango"]:
        items = [("Vegan protein shake (fortified)", 250), (fruit, 80)]
        add("snack", f"{_short(fruit)} protein shake", items, "American")
    # yogurt-style with OFF drink + oats + fruit
    for fruit in ["Blueberries", "Strawberries", "Banana"]:
        milk = pick("milk")[0]
        items = [(milk, 180), ("Rolled oats (dry)", 30), (fruit, 80), ("Chia seeds", 10)]
        add("snack", f"Overnight oats with {_short(fruit).lower()}", items, "British")

    rec_df = pd.DataFrame(recipes)
    bom_df = pd.DataFrame(bom)
    return rec_df, bom_df


# ---------------------------------------------------------------------------
# 6. Persona, nutrient targets, dietary restrictions, meal slots.
#    Targets for a ~70 kg vegan endurance athlete (~3,000 kcal/day), per
#    NIH/FDA Daily Values and ACSM/ISSN athlete position stands; iron at the
#    1.8x vegan adjustment, B12/vitamin D requiring fortified foods.
# ---------------------------------------------------------------------------
PERSONA = {
    "persona_id": "marco",
    "persona_name": "Marco",
    "description": "Marco, a busy startup executive training for marathons. Time-poor, "
                   "follows a plant-only (vegan) diet, and needs nutritionally complete "
                   "meal prep without the planning overhead.",
    "sex": "M", "age_years": 36, "weight_kg": 70, "activity_level": "high",
    "sport": "marathon running", "diet_pattern": "vegan",
    "target_energy_kcal": 3000,
}
# nutrient_code, display, unit, min, max, direction, priority
NUTRIENT_TARGETS = [
    ("kcal", "Energy", "kcal", 2800, 3300, "range", 1),
    ("protein_g", "Protein", "g", 98, 200, "floor", 1),
    ("carb_g", "Carbohydrate", "g", 420, 600, "floor", 1),
    ("fat_g", "Total fat", "g", 67, 117, "range", 2),
    ("fiber_g", "Fiber", "g", 35, 80, "floor", 2),
    ("satfat_g", "Saturated fat", "g", 0, 33, "ceiling", 2),
    ("sugars_g", "Total sugars", "g", 0, 130, "ceiling", 3),
    ("sodium_mg", "Sodium", "mg", 0, 2300, "ceiling", 2),
    ("calcium_mg", "Calcium", "mg", 1000, 2500, "floor", 1),
    ("iron_mg", "Iron", "mg", 14, 45, "floor", 1),
    ("potassium_mg", "Potassium", "mg", 3400, 12000, "floor", 3),
    ("zinc_mg", "Zinc", "mg", 11, 40, "floor", 2),
    ("magnesium_mg", "Magnesium", "mg", 400, 900, "floor", 3),
    ("vitc_mg", "Vitamin C", "mg", 90, 2000, "floor", 3),
    ("vitd_ug", "Vitamin D", "ug", 15, 100, "floor", 1),
    ("b12_ug", "Vitamin B12", "ug", 2.4, 100, "floor", 1),
]
DIETARY_RESTRICTIONS = [
    ("vegan", "Vegan", "Excludes all animal products", "has_dairy|has_egg|has_fish"),
    ("vegetarian", "Vegetarian", "Excludes meat and fish", "has_fish"),
    ("gluten_free", "Gluten free", "Excludes gluten-containing grains", "has_gluten"),
    ("dairy_free", "Dairy free", "Excludes milk products", "has_dairy"),
    ("nut_free", "Nut free", "Excludes tree nuts", "has_nuts"),
    ("peanut_free", "Peanut free", "Excludes peanuts", "has_peanuts"),
]
MEAL_SLOTS = [
    ("breakfast", "Breakfast", "breakfast", 1, 1, 1),
    ("lunch", "Lunch", "main", 1, 1, 2),
    ("dinner", "Dinner", "main", 1, 1, 3),
    ("snack", "Snack", "snack", 1, 2, 4),
]


def build_status_quo(rec):
    """The athlete's current favourite day: the recipes most exposed to volatile
    commodities (cocoa, coffee, nuts, olive oil), i.e. the highest cost jump
    under a price shock. Backs the Q3 'price volatility to profit protection'
    re-solve: this fixed menu's cost spikes; re-optimizing protects it.
    """
    r = rec.copy()
    r["shock_delta"] = r.cost_usd_shock - r.cost_usd
    rows = []
    plan = [("breakfast", "breakfast", 1), ("main", "lunch", 1),
            ("main", "dinner", 1), ("snack", "snack", 2)]
    used = set()
    for meal_type, slot, n in plan:
        cand = r[(r.meal_type == meal_type) & (~r.recipe_id.isin(used))]
        cand = cand.sort_values("shock_delta", ascending=False).head(n)
        for rr in cand.itertuples():
            used.add(rr.recipe_id)
            rows.append({"slot_id": slot, "recipe_id": int(rr.recipe_id),
                         "recipe_name": rr.recipe_name,
                         "cost_usd": rr.cost_usd, "cost_usd_shock": rr.cost_usd_shock})
    return pd.DataFrame(rows)


def build_dims():
    persona = pd.DataFrame([PERSONA])
    tgt = pd.DataFrame([
        {"persona_id": PERSONA["persona_id"], "nutrient_code": c, "nutrient_name": n,
         "unit": u, "min_amount": lo, "max_amount": hi, "direction": d, "priority": pr}
        for c, n, u, lo, hi, d, pr in NUTRIENT_TARGETS
    ])
    restr = pd.DataFrame([
        {"restriction_id": rid, "restriction_name": nm, "description": desc,
         "excluded_flags": flags}
        for rid, nm, desc, flags in DIETARY_RESTRICTIONS
    ])
    prest = pd.DataFrame([{"persona_id": PERSONA["persona_id"], "restriction_id": "vegan"}])
    slots = pd.DataFrame([
        {"slot_id": sid, "slot_name": nm, "eligible_meal_type": mt,
         "min_recipes": lo, "max_recipes": hi, "slot_order": order}
        for sid, nm, mt, lo, hi, order in MEAL_SLOTS
    ])
    return persona, tgt, restr, prest, slots


def main():
    ing, com, hist = build_ingredients()
    rec, bom = build_recipes(ing)
    persona, tgt, restr, prest, slots = build_dims()
    sq = build_status_quo(rec)

    ing.to_csv(os.path.join(OUT, "ingredient.csv"), index=False)
    com.to_csv(os.path.join(OUT, "commodity.csv"), index=False)
    hist.to_csv(os.path.join(OUT, "commodity_price_history.csv"), index=False)
    rec.to_csv(os.path.join(OUT, "recipe.csv"), index=False)
    bom.to_csv(os.path.join(OUT, "recipe_ingredient.csv"), index=False)
    persona.to_csv(os.path.join(OUT, "persona.csv"), index=False)
    tgt.to_csv(os.path.join(OUT, "persona_nutrient_target.csv"), index=False)
    restr.to_csv(os.path.join(OUT, "dietary_restriction.csv"), index=False)
    prest.to_csv(os.path.join(OUT, "persona_restriction.csv"), index=False)
    slots.to_csv(os.path.join(OUT, "meal_slot.csv"), index=False)
    sq.to_csv(os.path.join(OUT, "status_quo_menu.csv"), index=False)

    print(f"ingredient.csv: {len(ing)} rows "
          f"({(ing.source=='usda').sum()} usda, {(ing.source=='curated').sum()} curated, {(ing.source=='off').sum()} off)")
    print(f"commodity.csv: {len(com)} rows; commodity_price_history.csv: {len(hist)} rows")
    print(f"recipe.csv: {len(rec)} rows; recipe_ingredient.csv: {len(bom)} rows")
    print(f"persona/targets/restrictions/slots: {len(persona)}/{len(tgt)}/{len(restr)}/{len(slots)}")
    print("\nrecipe meal_type:\n", rec.meal_type.value_counts())
    print("\nrecipe per-serving stats (kcal / protein_g / cost_usd):")
    print(rec.groupby("meal_type")[["kcal", "protein_g", "cost_usd"]].mean().round(1))
    print("\nrecipes gluten-free:", int(rec.is_gluten_free.sum()), "/", len(rec))


if __name__ == "__main__":
    main()
