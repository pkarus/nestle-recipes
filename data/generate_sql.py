"""
generate_sql.py - emit Snowflake DDL (with full metadata), a loader, and
validation queries for the Nestle diet-optimization demo, from data/out/*.csv.

The DDL is written for the RelationalAI agentic modeler: every table and column
carries a COMMENT, primary keys and foreign keys are declared (Snowflake does
not enforce them but the modeler reads them as concept keys / relationships),
NOT NULL marks required properties, and change tracking is enabled for RAI CDC.

Outputs (data/out/):
  02_schema.sql       CREATE SCHEMA + CREATE TABLE (+ comments, PK/FK, change tracking)
  03_load.sql         CREATE STAGE + COPY INTO per table
  04_validation.sql   anchored-number checks
  DATA_DICTIONARY.md  human-readable column reference

Run: .venv/bin/python data/generate_sql.py
"""
import os

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")

DB = "PK_NESTLE_DIET"
SCHEMA = "DIET"

# nutrient column -> (snowflake_type, unit, label)
NUTRI_META = {
    "kcal": ("FLOAT", "kcal", "Energy"),
    "protein_g": ("FLOAT", "g", "Protein"),
    "carb_g": ("FLOAT", "g", "Carbohydrate"),
    "fat_g": ("FLOAT", "g", "Total fat"),
    "fiber_g": ("FLOAT", "g", "Dietary fiber"),
    "sugars_g": ("FLOAT", "g", "Total sugars"),
    "satfat_g": ("FLOAT", "g", "Saturated fat"),
    "sodium_mg": ("FLOAT", "mg", "Sodium"),
    "calcium_mg": ("FLOAT", "mg", "Calcium"),
    "iron_mg": ("FLOAT", "mg", "Iron"),
    "potassium_mg": ("FLOAT", "mg", "Potassium"),
    "zinc_mg": ("FLOAT", "mg", "Zinc"),
    "magnesium_mg": ("FLOAT", "mg", "Magnesium"),
    "vitd_ug": ("FLOAT", "ug", "Vitamin D"),
    "vitc_mg": ("FLOAT", "mg", "Vitamin C"),
    "b12_ug": ("FLOAT", "ug", "Vitamin B12"),
}
ALLERGEN_META = {
    "has_gluten": "TRUE if the item contains gluten (wheat, barley, rye)",
    "has_dairy": "TRUE if the item contains dairy",
    "has_egg": "TRUE if the item contains egg",
    "has_soy": "TRUE if the item contains soy",
    "has_nuts": "TRUE if the item contains tree nuts",
    "has_peanuts": "TRUE if the item contains peanuts",
    "has_sesame": "TRUE if the item contains sesame",
    "has_fish": "TRUE if the item contains fish or shellfish",
}


def nutri_cols(per):
    """Column metadata for the 16 nutrient columns; `per` is '100 g' or 'serving'."""
    out = []
    for c, (t, unit, label) in NUTRI_META.items():
        out.append((c, t, True, f"{label} per {per} ({unit})"))
    return out


def allergen_cols():
    return [(c, "BOOLEAN", True, desc) for c, desc in ALLERGEN_META.items()]


# Per table: grain (table comment), role tag, primary key, foreign keys,
# and explicit column metadata (name, sf_type, not_null, comment).
TABLES = {
    "commodity": {
        "grain": "One row per traded commodity input. Master/dimension; the cost and "
                 "price-volatility backbone for ingredients.",
        "role": "dim",
        "pk": ["commodity_id"],
        "fk": [],
        "cols": [
            ("commodity_id", "VARCHAR", True, "Commodity code (natural key), e.g. cocoa, coffee, wheat"),
            ("commodity_name", "VARCHAR", True, "Human-readable commodity name"),
            ("unit", "VARCHAR", True, "Quotation unit for the base price"),
            ("base_price_usd_per_kg", "FLOAT", True, "Reference price in USD per kg at index 1.00 (Jan 2025)"),
            ("current_price_index", "FLOAT", True, "Latest normalized price index (1.00 = Jan 2025)"),
            ("current_price_usd_per_kg", "FLOAT", True, "Latest price in USD per kg"),
            ("peak_price_index", "FLOAT", True, "Maximum price index observed over the history window"),
            ("is_volatile", "BOOLEAN", True, "TRUE for commodities with high recent price volatility (cocoa, coffee, olive oil)"),
        ],
    },
    "commodity_price_history": {
        "grain": "One row per commodity per month. Time series of the monthly price "
                 "index, Jan 2025 to Jun 2026, anchored to real commodity moves.",
        "role": "event",
        "pk": ["commodity_id", "price_month"],
        "fk": [("commodity_id", "commodity", "commodity_id")],
        "cols": [
            ("commodity_id", "VARCHAR", True, "Commodity code; FK to commodity"),
            ("price_month", "DATE", True, "First day of the month for this price observation"),
            ("price_index", "FLOAT", True, "Normalized price index (1.00 = Jan 2025)"),
            ("price_usd_per_kg", "FLOAT", True, "Price in USD per kg for the month"),
        ],
    },
    "ingredient": {
        "grain": "One row per ingredient or branded product. Master table carrying "
                 "per-100g nutrition, cost, sustainability, and allergen/diet flags. "
                 "Sourced from USDA FoodData Central (CC0), Open Food Facts (ODbL), "
                 "and hand-authored fortified specialty items.",
        "role": "dim",
        "pk": ["ingredient_id"],
        "fk": [("commodity_id", "commodity", "commodity_id")],
        "cols": [
            ("ingredient_id", "NUMBER", True, "Surrogate key for the ingredient"),
            ("ingredient_name", "VARCHAR", True, "Display name of the ingredient or product"),
            ("brand", "VARCHAR", False, "Brand name for branded products; null for generic foods"),
            ("is_branded", "BOOLEAN", True, "TRUE if this is a branded retail product"),
            ("source", "VARCHAR", True, "Provenance: usda, off (Open Food Facts), or curated"),
            ("source_id", "VARCHAR", False, "Identifier in the source system (USDA fdc_id or OFF barcode)"),
            ("food_group", "VARCHAR", True, "Food group, e.g. grain, legume, plant_protein, nuts_seeds, vegetable, fruit"),
            ("commodity_id", "VARCHAR", True, "Primary commodity input; FK to commodity"),
            ("is_fortified", "BOOLEAN", True, "TRUE if the item is fortified (added vitamins/minerals)"),
            ("is_estimated_micros", "BOOLEAN", True, "TRUE if micronutrients were imputed from food-group medians (OFF products)"),
            ("is_vegan", "BOOLEAN", True, "TRUE if the ingredient is vegan"),
            ("is_vegetarian", "BOOLEAN", True, "TRUE if the ingredient is vegetarian"),
            ("is_gluten_free", "BOOLEAN", True, "TRUE if the ingredient is gluten free"),
            ("nutriscore_grade", "VARCHAR", False, "Nutri-Score grade a-e (Open Food Facts); null if unknown"),
            ("nova_group", "NUMBER", False, "NOVA processing group 1-4 (1 = unprocessed, 4 = ultra-processed)"),
            ("cost_per_100g", "FLOAT", True, "Estimated retail cost in USD per 100 g at current commodity prices"),
            ("cost_per_100g_shock", "FLOAT", True, "Estimated cost per 100 g under the commodity price-shock scenario"),
            ("co2e_per_kg", "FLOAT", True, "Greenhouse-gas footprint in kg CO2e per kg (Poore & Nemecek 2018 / OWID)"),
            ("water_l_per_kg", "FLOAT", True, "Freshwater withdrawal in liters per kg (Poore & Nemecek 2018 / OWID)"),
        ] + nutri_cols("100 g") + allergen_cols(),
    },
    "recipe": {
        "grain": "One row per single-serving recipe. Each recipe is a bundle of "
                 "ingredients (see recipe_ingredient) with nutrition, cost, and CO2e "
                 "derived by summing the bill of materials.",
        "role": "fact",
        "pk": ["recipe_id"],
        "fk": [],
        "cols": [
            ("recipe_id", "NUMBER", True, "Surrogate key for the recipe"),
            ("recipe_name", "VARCHAR", True, "Display name of the recipe"),
            ("meal_type", "VARCHAR", True, "Meal type the recipe serves: breakfast, main, or snack"),
            ("cuisine", "VARCHAR", True, "Cuisine style"),
            ("servings", "NUMBER", True, "Number of servings the recipe yields (1 = single serving)"),
            ("prep_time_min", "NUMBER", True, "Preparation time in minutes"),
            ("n_ingredients", "NUMBER", True, "Number of distinct ingredients in the recipe"),
            ("total_grams", "FLOAT", True, "Total edible mass of one serving in grams"),
            ("is_vegan", "BOOLEAN", True, "TRUE if all ingredients are vegan"),
            ("is_vegetarian", "BOOLEAN", True, "TRUE if all ingredients are vegetarian"),
            ("is_gluten_free", "BOOLEAN", True, "TRUE if all ingredients are gluten free"),
            ("cost_usd", "FLOAT", True, "Cost of one serving in USD at current commodity prices"),
            ("cost_usd_shock", "FLOAT", True, "Cost of one serving in USD under the commodity price-shock scenario"),
            ("co2e_kg", "FLOAT", True, "Greenhouse-gas footprint of one serving in kg CO2e"),
            ("water_l", "FLOAT", True, "Freshwater footprint of one serving in liters"),
        ] + nutri_cols("serving"),
    },
    "recipe_ingredient": {
        "grain": "One row per ingredient used in a recipe (the bill of materials). "
                 "Junction between recipe and ingredient with the quantity used.",
        "role": "junction",
        "pk": ["recipe_id", "ingredient_id"],
        "fk": [("recipe_id", "recipe", "recipe_id"), ("ingredient_id", "ingredient", "ingredient_id")],
        "cols": [
            ("recipe_id", "NUMBER", True, "Recipe; FK to recipe"),
            ("ingredient_id", "NUMBER", True, "Ingredient; FK to ingredient"),
            ("ingredient_name", "VARCHAR", True, "Denormalized ingredient name for readability"),
            ("quantity_g", "FLOAT", True, "Quantity of the ingredient in this recipe, in grams"),
        ],
    },
    "persona": {
        "grain": "One row per demo persona. The optimization target profile.",
        "role": "dim",
        "pk": ["persona_id"],
        "fk": [],
        "cols": [
            ("persona_id", "VARCHAR", True, "Persona code (natural key)"),
            ("persona_name", "VARCHAR", True, "Display name of the persona"),
            ("description", "VARCHAR", True, "Short description of the persona"),
            ("sex", "VARCHAR", True, "Biological sex used for nutrient reference values"),
            ("age_years", "NUMBER", True, "Age in years"),
            ("weight_kg", "NUMBER", True, "Body weight in kg (drives per-kg protein/carb targets)"),
            ("activity_level", "VARCHAR", True, "Activity level"),
            ("sport", "VARCHAR", True, "Primary sport / training modality"),
            ("diet_pattern", "VARCHAR", True, "Dietary pattern, e.g. vegan"),
            ("target_energy_kcal", "NUMBER", True, "Target daily energy intake in kcal"),
        ],
    },
    "persona_nutrient_target": {
        "grain": "One row per persona per nutrient. The optimization constraints "
                 "(floor/ceiling/range) the daily menu must satisfy.",
        "role": "junction",
        "pk": ["persona_id", "nutrient_code"],
        "fk": [("persona_id", "persona", "persona_id")],
        "cols": [
            ("persona_id", "VARCHAR", True, "Persona; FK to persona"),
            ("nutrient_code", "VARCHAR", True, "Nutrient column code matching recipe/ingredient nutrition columns"),
            ("nutrient_name", "VARCHAR", True, "Human-readable nutrient name"),
            ("unit", "VARCHAR", True, "Unit of the min/max amounts"),
            ("min_amount", "FLOAT", True, "Minimum daily amount (floor); 0 if none"),
            ("max_amount", "FLOAT", False, "Maximum daily amount (ceiling); null if none"),
            ("direction", "VARCHAR", True, "Constraint type: floor, ceiling, or range"),
            ("priority", "NUMBER", True, "Constraint priority 1 (highest) to 3 (lowest)"),
        ],
    },
    "dietary_restriction": {
        "grain": "One row per dietary restriction. Reference for restriction rules "
                 "that exclude ingredients carrying given allergen/diet flags.",
        "role": "dim",
        "pk": ["restriction_id"],
        "fk": [],
        "cols": [
            ("restriction_id", "VARCHAR", True, "Restriction code (natural key)"),
            ("restriction_name", "VARCHAR", True, "Display name of the restriction"),
            ("description", "VARCHAR", True, "What the restriction excludes"),
            ("excluded_flags", "VARCHAR", True, "Pipe-delimited ingredient flags excluded by this restriction"),
        ],
    },
    "persona_restriction": {
        "grain": "One row per persona per active dietary restriction. Junction "
                 "linking personas to the restrictions they follow.",
        "role": "junction",
        "pk": ["persona_id", "restriction_id"],
        "fk": [("persona_id", "persona", "persona_id"), ("restriction_id", "dietary_restriction", "restriction_id")],
        "cols": [
            ("persona_id", "VARCHAR", True, "Persona; FK to persona"),
            ("restriction_id", "VARCHAR", True, "Restriction; FK to dietary_restriction"),
        ],
    },
    "meal_slot": {
        "grain": "One row per meal slot in a daily plan. Defines how many recipes of "
                 "which meal type fill each slot in the menu optimization.",
        "role": "dim",
        "pk": ["slot_id"],
        "fk": [],
        "cols": [
            ("slot_id", "VARCHAR", True, "Slot code (natural key): breakfast, lunch, dinner, snack"),
            ("slot_name", "VARCHAR", True, "Display name of the slot"),
            ("eligible_meal_type", "VARCHAR", True, "Recipe meal_type eligible for this slot"),
            ("min_recipes", "NUMBER", True, "Minimum recipes assigned to this slot"),
            ("max_recipes", "NUMBER", True, "Maximum recipes assigned to this slot"),
            ("slot_order", "NUMBER", True, "Display order of the slot within a day"),
        ],
    },
    "status_quo_menu": {
        "grain": "One row per recipe in the persona's current 'favourite' daily menu. "
                 "The fixed baseline whose cost spikes under a price shock; the Q3 "
                 "re-solve protects against that spike.",
        "role": "fact",
        "pk": ["slot_id", "recipe_id"],
        "fk": [("recipe_id", "recipe", "recipe_id")],
        "cols": [
            ("slot_id", "VARCHAR", True, "Meal slot this recipe fills"),
            ("recipe_id", "NUMBER", True, "Recipe; FK to recipe"),
            ("recipe_name", "VARCHAR", True, "Denormalized recipe name for readability"),
            ("cost_usd", "FLOAT", True, "Cost of the recipe at current prices"),
            ("cost_usd_shock", "FLOAT", True, "Cost of the recipe under the price-shock scenario"),
        ],
    },
}

# Load order respects FK dependencies.
LOAD_ORDER = ["commodity", "commodity_price_history", "ingredient", "recipe",
              "recipe_ingredient", "persona", "dietary_restriction",
              "persona_restriction", "persona_nutrient_target", "meal_slot",
              "status_quo_menu"]


def q(s):
    return s.replace("'", "''")


def emit_schema():
    L = []
    L.append("-- 02_schema.sql - Nestle diet-optimization demo schema")
    L.append("-- Generated by data/generate_sql.py. Run as the demo role RAI_DEMO_NESTLE_DIET.")
    L.append(f"USE DATABASE {DB};")
    L.append(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA} "
             f"COMMENT = 'Vegan diet/menu optimization demo: ingredients, recipes, nutrition, prices, persona targets.';")
    L.append(f"USE SCHEMA {SCHEMA};")
    L.append("")
    for t in LOAD_ORDER:
        spec = TABLES[t]
        L.append(f"-- {t}: {spec['grain']}")
        L.append(f"CREATE OR REPLACE TABLE {t} (")
        lines = []
        for name, typ, nn, comment in spec["cols"]:
            nns = " NOT NULL" if nn else ""
            lines.append(f"    {name} {typ}{nns} COMMENT '{q(comment)}'")
        # primary key
        lines.append(f"    CONSTRAINT pk_{t} PRIMARY KEY ({', '.join(spec['pk'])})")
        # foreign keys
        for col, rt, rcol in spec["fk"]:
            lines.append(f"    CONSTRAINT fk_{t}_{col} FOREIGN KEY ({col}) REFERENCES {rt} ({rcol})")
        L.append(",\n".join(lines))
        L.append(f") COMMENT = '{q(spec['grain'])}';")
        L.append(f"ALTER TABLE {t} SET CHANGE_TRACKING = TRUE;")
        L.append("")
    open(os.path.join(OUT, "02_schema.sql"), "w").write("\n".join(L))
    print("wrote 02_schema.sql")


STAGE = "DIET_STAGE"


def emit_load():
    L = []
    L.append("-- 03_load.sql - stage + COPY INTO for the Nestle diet demo")
    L.append("-- PUT the CSVs to the stage first (see load_to_snowflake.sh), then run this.")
    L.append(f"USE DATABASE {DB};")
    L.append(f"USE SCHEMA {SCHEMA};")
    L.append(f"CREATE STAGE IF NOT EXISTS {STAGE} FILE_FORMAT = ("
             "TYPE = CSV SKIP_HEADER = 1 FIELD_OPTIONALLY_ENCLOSED_BY = '\"' "
             "NULL_IF = ('', 'NULL') EMPTY_FIELD_AS_NULL = TRUE TRIM_SPACE = TRUE);")
    L.append("")
    for t in LOAD_ORDER:
        L.append(f"TRUNCATE TABLE IF EXISTS {t};")
        L.append(f"COPY INTO {t} FROM @{STAGE}/{t}.csv "
                 "FILE_FORMAT = (TYPE = CSV SKIP_HEADER = 1 FIELD_OPTIONALLY_ENCLOSED_BY = '\"' "
                 "NULL_IF = ('', 'NULL') EMPTY_FIELD_AS_NULL = TRUE TRIM_SPACE = TRUE) "
                 "ON_ERROR = ABORT_STATEMENT;")
        L.append("")
    open(os.path.join(OUT, "03_load.sql"), "w").write("\n".join(L))
    print("wrote 03_load.sql")


def emit_validation():
    """Anchored-number checks. Values are computed from the generated CSVs so the
    SQL and the data cannot drift."""
    rec = pd.read_csv(os.path.join(OUT, "recipe.csv"))
    ing = pd.read_csv(os.path.join(OUT, "ingredient.csv"))
    sq = pd.read_csv(os.path.join(OUT, "status_quo_menu.csv"))
    n_ing = len(ing)
    n_off = int((ing.source == "off").sum())
    n_rec = len(rec)
    n_vegan_rec = int(rec.is_vegan.sum())
    n_gf_rec = int(rec.is_gluten_free.sum())
    sq_base = round(sq.cost_usd.sum(), 2)
    sq_shock = round(sq.cost_usd_shock.sum(), 2)

    L = []
    L.append("-- 04_validation.sql - anchored-number checks for the Nestle diet demo")
    L.append(f"USE DATABASE {DB};")
    L.append(f"USE SCHEMA {SCHEMA};")
    L.append("")
    L.append(f"-- A. Catalog size. Expect ingredient={n_ing} (off={n_off}), recipe={n_rec}.")
    L.append("SELECT 'ingredients' AS metric, COUNT(*) AS value FROM ingredient")
    L.append("UNION ALL SELECT 'ingredients_off', COUNT(*) FROM ingredient WHERE source = 'off'")
    L.append("UNION ALL SELECT 'recipes', COUNT(*) FROM recipe;")
    L.append("")
    L.append(f"-- B. Diet eligibility. Expect vegan recipes={n_vegan_rec}, gluten-free recipes={n_gf_rec}.")
    L.append("SELECT 'vegan_recipes' AS metric, COUNT(*) AS value FROM recipe WHERE is_vegan")
    L.append("UNION ALL SELECT 'gluten_free_recipes', COUNT(*) FROM recipe WHERE is_gluten_free;")
    L.append("")
    L.append("-- C. Q1 problem exposure: the cheapest recipe per slot (1 breakfast,")
    L.append("--    2 mains, 2 snacks) is cheap but misses nutrition targets.")
    L.append("WITH ranked AS (")
    L.append("  SELECT recipe_id, recipe_name, meal_type, cost_usd, kcal, protein_g, b12_ug, vitd_ug, calcium_mg,")
    L.append("         ROW_NUMBER() OVER (PARTITION BY meal_type ORDER BY cost_usd) AS rn")
    L.append("  FROM recipe WHERE is_vegan")
    L.append("),")
    L.append("naive AS (")
    L.append("  SELECT * FROM ranked WHERE (meal_type = 'breakfast' AND rn = 1)")
    L.append("     OR (meal_type = 'main' AND rn <= 2) OR (meal_type = 'snack' AND rn <= 2)")
    L.append(")")
    L.append("SELECT ROUND(SUM(cost_usd),2) AS naive_cost_usd, ROUND(SUM(kcal),0) AS kcal,")
    L.append("       ROUND(SUM(protein_g),0) AS protein_g, ROUND(SUM(b12_ug),1) AS b12_ug,")
    L.append("       ROUND(SUM(vitd_ug),1) AS vitd_ug, ROUND(SUM(calcium_mg),0) AS calcium_mg")
    L.append("FROM naive;  -- expect ~$5.01, protein<98, b12<2.4, vitd<15, kcal<2800 (fails targets)")
    L.append("")
    L.append(f"-- D. Q3 price-shock story: status-quo menu cost baseline vs shock.")
    L.append(f"--    Expect baseline ~${sq_base}, shock ~${sq_shock}.")
    L.append("SELECT ROUND(SUM(cost_usd),2) AS status_quo_baseline_usd,")
    L.append("       ROUND(SUM(cost_usd_shock),2) AS status_quo_shock_usd,")
    L.append("       ROUND(SUM(cost_usd_shock) - SUM(cost_usd),2) AS shock_increase_usd")
    L.append("FROM status_quo_menu;")
    L.append("")
    L.append("-- E. Marco's nutrient targets present (expect 16 rows).")
    L.append("SELECT COUNT(*) AS nutrient_targets FROM persona_nutrient_target WHERE persona_id = 'marco';")
    L.append("")
    L.append("-- F. Referential integrity spot-checks (expect 0 orphans).")
    L.append("SELECT 'orphan_recipe_ingredients' AS check_name, COUNT(*) AS bad FROM recipe_ingredient ri")
    L.append("  LEFT JOIN recipe r ON ri.recipe_id = r.recipe_id WHERE r.recipe_id IS NULL")
    L.append("UNION ALL SELECT 'orphan_ingredient_commodity', COUNT(*) FROM ingredient i")
    L.append("  LEFT JOIN commodity c ON i.commodity_id = c.commodity_id WHERE c.commodity_id IS NULL;")
    open(os.path.join(OUT, "04_validation.sql"), "w").write("\n".join(L))
    print("wrote 04_validation.sql")


def emit_dict():
    L = ["# Data dictionary - Nestle diet-optimization demo", "",
         "Generated by data/generate_sql.py. All tables live in "
         f"`{DB}.{SCHEMA}`.", "",
         "Provenance: USDA FoodData Central SR Legacy (CC0, public domain) for the "
         "nutrition spine; Open Food Facts (ODbL) for branded products; Poore & "
         "Nemecek (2018, Science) processed by Our World in Data (CC BY 4.0) for "
         "CO2e/water; recipes, prices, and persona targets synthesized.", ""]
    for t in LOAD_ORDER:
        spec = TABLES[t]
        L.append(f"## {t}  ({spec['role']})")
        L.append("")
        L.append(spec["grain"])
        L.append("")
        L.append(f"Primary key: `{', '.join(spec['pk'])}`")
        if spec["fk"]:
            fks = "; ".join(f"`{c}` -> `{rt}.{rc}`" for c, rt, rc in spec["fk"])
            L.append(f"  Foreign keys: {fks}")
        L.append("")
        L.append("| column | type | null | description |")
        L.append("|---|---|---|---|")
        for name, typ, nn, comment in spec["cols"]:
            L.append(f"| {name} | {typ} | {'NOT NULL' if nn else 'null'} | {comment} |")
        L.append("")
    open(os.path.join(OUT, "DATA_DICTIONARY.md"), "w").write("\n".join(L))
    print("wrote DATA_DICTIONARY.md")


def main():
    # sanity: every TABLES column set matches the CSV header
    for t in LOAD_ORDER:
        csv = os.path.join(OUT, f"{t}.csv")
        cols = list(pd.read_csv(csv, nrows=0).columns)
        spec_cols = [c[0] for c in TABLES[t]["cols"]]
        if cols != spec_cols:
            raise SystemExit(f"COLUMN MISMATCH for {t}:\n  csv : {cols}\n  spec: {spec_cols}")
    emit_schema()
    emit_load()
    emit_validation()
    emit_dict()
    print("all SQL artifacts generated")


if __name__ == "__main__":
    main()
