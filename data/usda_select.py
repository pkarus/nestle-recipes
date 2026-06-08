"""
usda_select.py - load USDA SR Legacy into a clean food x nutrient matrix and
resolve a curated list of whole-food ingredients to specific USDA foods.

The curated list is the recipe-building vocabulary for a vegan endurance-athlete
diet: grains, legumes, plant proteins, nuts/seeds, vegetables, fruits, fortified
plant foods, oils, and flavor items. Each entry maps a display name + food group
+ commodity to a precise USDA description regex; the matcher prefers the
shortest "clean" (unsalted / generic) description so we get canonical nutrition.

Run directly to print the resolved selection for review:
  .venv/bin/python data/usda_select.py
"""
import os
import re

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
USDA_DIR = os.path.join(HERE, "seed", "FoodData_Central_sr_legacy_food_csv_2018-04")

# nutrient_id -> column name (per 100 g)
NUTRIENTS = {
    1008: "kcal", 1003: "protein_g", 1005: "carb_g", 1004: "fat_g",
    1079: "fiber_g", 1258: "satfat_g", 2000: "sugars_g", 1093: "sodium_mg",
    1087: "calcium_mg", 1089: "iron_mg", 1092: "potassium_mg", 1095: "zinc_mg",
    1090: "magnesium_mg", 1114: "vitd_ug", 1162: "vitc_mg", 1178: "b12_ug",
}

# display_name, food_group, commodity, regex (matched against USDA description)
# Regexes are written to land on the canonical generic item.
CURATED = [
    # grains and starches
    ("Rolled oats (dry)", "grain", "oats", r"^Cereals, oats, regular and quick, not fortified, dry"),
    ("Brown rice (cooked)", "grain", "rice", r"^Rice, brown, long-grain, cooked"),
    ("White rice (cooked)", "grain", "rice", r"^Rice, white, long-grain, regular, enriched, cooked"),
    ("Quinoa (cooked)", "grain", "quinoa", r"^Quinoa, cooked"),
    ("Whole wheat bread", "grain", "wheat", r"^Bread, whole-wheat, commercially prepared$"),
    ("Whole wheat pasta (cooked)", "grain", "wheat", r"^Pasta, whole-wheat, cooked"),
    ("Couscous (cooked)", "grain", "wheat", r"^Couscous, cooked"),
    ("Buckwheat groats (cooked)", "grain", "buckwheat", r"^Buckwheat groats, roasted, cooked"),
    ("Millet (cooked)", "grain", "millet", r"^Millet, cooked"),
    ("Corn tortilla", "grain", "maize", r"^Tortillas, ready-to-bake or -fry, corn"),
    ("Potato (baked)", "starch", "potato", r"^Potatoes, baked, flesh and skin, without salt"),
    ("Sweet potato (baked)", "starch", "potato", r"^Sweet potato, cooked, baked in skin, flesh, without salt"),
    ("Rye bread", "grain", "rye", r"^Bread, rye$"),
    # legumes and plant proteins
    ("Lentils (cooked)", "legume", "lentils", r"^Lentils, mature seeds, cooked, boiled, without salt"),
    ("Chickpeas (cooked)", "legume", "chickpeas", r"^Chickpeas \(garbanzo beans, bengal gram\), mature seeds, cooked, boiled, without salt"),
    ("Black beans (cooked)", "legume", "beans", r"^Beans, black, mature seeds, cooked, boiled, without salt"),
    ("Kidney beans (cooked)", "legume", "beans", r"^Beans, kidney, red, mature seeds, cooked, boiled, without salt"),
    ("Firm tofu", "plant_protein", "soy", r"^Tofu, raw, firm, prepared with calcium sulfate"),
    ("Tempeh", "plant_protein", "soy", r"^Tempeh$"),
    ("Edamame (cooked)", "legume", "soy", r"^Edamame, frozen, prepared"),
    ("Green peas (cooked)", "legume", "peas", r"^Peas, green, frozen, cooked, boiled, drained, without salt"),
    # nuts and seeds
    ("Almonds", "nuts_seeds", "nuts", r"^Nuts, almonds$"),
    ("Walnuts", "nuts_seeds", "nuts", r"^Nuts, walnuts, english$"),
    ("Cashews", "nuts_seeds", "nuts", r"^Nuts, cashew nuts, raw"),
    ("Peanut butter", "nuts_seeds", "peanuts", r"^Peanut butter, smooth style, without salt"),
    ("Chia seeds", "nuts_seeds", "seeds", r"^Seeds, chia seeds, dried"),
    ("Flaxseed (ground)", "nuts_seeds", "seeds", r"^Seeds, flaxseed$"),
    ("Sunflower seeds", "nuts_seeds", "seeds", r"^Seeds, sunflower seed kernels, dried"),
    ("Pumpkin seeds", "nuts_seeds", "seeds", r"^Seeds, pumpkin and squash seed kernels, dried"),
    ("Tahini", "nuts_seeds", "seeds", r"^Seeds, sesame butter, tahini"),
    # vegetables
    ("Spinach (raw)", "vegetable", "vegetables", r"^Spinach, raw$"),
    ("Kale (raw)", "vegetable", "vegetables", r"^Kale, raw$"),
    ("Broccoli (cooked)", "vegetable", "vegetables", r"^Broccoli, cooked, boiled, drained, without salt"),
    ("Carrot (raw)", "vegetable", "vegetables", r"^Carrots, raw$"),
    ("Red bell pepper (raw)", "vegetable", "vegetables", r"^Peppers, sweet, red, raw$"),
    ("Tomato (raw)", "vegetable", "vegetables", r"^Tomatoes, red, ripe, raw, year round average"),
    ("Onion (raw)", "vegetable", "vegetables", r"^Onions, raw$"),
    ("Mushroom (raw)", "vegetable", "vegetables", r"^Mushrooms, white, raw$"),
    ("Zucchini (cooked)", "vegetable", "vegetables", r"^Squash, summer, zucchini, includes skin, cooked, boiled, drained, without salt"),
    ("Cauliflower (cooked)", "vegetable", "vegetables", r"^Cauliflower, cooked, boiled, drained, without salt"),
    ("Sweet corn (cooked)", "vegetable", "maize", r"^Corn, sweet, yellow, cooked, boiled, drained, without salt"),
    ("Avocado", "vegetable", "vegetables", r"^Avocados, raw, all commercial varieties"),
    # fruits
    ("Banana", "fruit", "fruit", r"^Bananas, raw$"),
    ("Apple", "fruit", "fruit", r"^Apples, raw, with skin"),
    ("Orange", "fruit", "fruit", r"^Oranges, raw, all commercial varieties"),
    ("Blueberries", "fruit", "fruit", r"^Blueberries, raw$"),
    ("Strawberries", "fruit", "fruit", r"^Strawberries, raw$"),
    ("Dates", "fruit", "fruit", r"^Dates, medjool$"),
    ("Raisins", "fruit", "fruit", r"^Raisins, dark, seedless"),
    ("Mango", "fruit", "fruit", r"^Mangos, raw$"),
    # fortified plant foods and dairy alternatives
    ("Soy milk (fortified)", "plant_dairy", "soy", r"^Soymilk, original and vanilla, with added calcium, vitamins A and D"),
    ("Almond milk (fortified)", "plant_dairy", "nuts", r"^Beverages, almond milk, unsweetened, shelf stable"),
    ("Fortified breakfast cereal", "fortified", "wheat", r"^Cereals ready-to-eat, wheat, puffed, fortified"),
    ("Fortified gluten-free cereal", "fortified", "rice", r"^Cereals ready-to-eat, rice, puffed, fortified"),
    # fats and oils
    ("Olive oil", "fat", "olive_oil", r"^Oil, olive, salad or cooking"),
    ("Rapeseed (canola) oil", "fat", "veg_oil", r"^Oil, canola$"),
    # flavor and sweeteners
    ("Maple syrup", "sweetener", "sugar", r"^Syrups, maple$"),
    ("Cocoa powder (unsweetened)", "flavor", "cocoa", r"^Cocoa, dry powder, unsweetened$"),
    ("Dark chocolate", "flavor", "cocoa", r"^Chocolate, dark, 70-85% cacao solids"),
    ("Coffee (brewed)", "beverage", "coffee", r"^Beverages, coffee, brewed, prepared with tap water$"),
    ("Soy sauce", "flavor", "soy", r"^Soy sauce made from soy and wheat \(shoyu\)$"),
]


def load_matrix():
    food = pd.read_csv(os.path.join(USDA_DIR, "food.csv"))
    fn = pd.read_csv(os.path.join(USDA_DIR, "food_nutrient.csv"),
                     usecols=["fdc_id", "nutrient_id", "amount"])
    fn = fn[fn.nutrient_id.isin(NUTRIENTS)]
    mat = (fn.pivot_table(index="fdc_id", columns="nutrient_id", values="amount", aggfunc="first")
             .rename(columns=NUTRIENTS))
    m = food.merge(mat, on="fdc_id")
    m = m.dropna(subset=["kcal", "protein_g", "carb_g", "fat_g"]).copy()
    return m


def resolve(matrix):
    """Return a dataframe of curated ingredients resolved to USDA foods."""
    rows = []
    for name, group, commodity, rx in CURATED:
        cand = matrix[matrix.description.str.contains(rx, case=False, na=False, regex=True)]
        if len(cand) == 0:
            rows.append({"name": name, "group": group, "commodity": commodity,
                         "fdc_id": None, "description": "NO MATCH"})
            continue
        # prefer the shortest description (most generic canonical item)
        best = cand.loc[cand.description.str.len().idxmin()]
        rec = {"name": name, "group": group, "commodity": commodity,
               "fdc_id": int(best.fdc_id), "description": best.description}
        for col in NUTRIENTS.values():
            rec[col] = None if pd.isna(best[col]) else round(float(best[col]), 3)
        rows.append(rec)
    return pd.DataFrame(rows)


if __name__ == "__main__":
    m = load_matrix()
    sel = resolve(m)
    nomatch = sel[sel.fdc_id.isna()]
    print(f"resolved {sel.fdc_id.notna().sum()}/{len(sel)} curated ingredients")
    if len(nomatch):
        print("\nNO MATCH:")
        for n in nomatch.name:
            print("  -", n)
    print("\nresolved table:")
    with pd.option_context("display.max_rows", None, "display.width", 200):
        print(sel[["name", "fdc_id", "kcal", "protein_g", "carb_g", "fat_g", "description"]].to_string(index=False))
