# Nestle diet-optimization demo - data

Synthetic-on-real dataset for the RelationalAI vegan diet/menu optimization
demo. Hero persona: a vegan endurance athlete. Theme: "from price volatility to
profit protection, preserving nutrition and sustainability."

## Provenance (hybrid, fully reproducible)

- **Nutrition spine:** USDA FoodData Central SR Legacy (CC0, public domain). 61
  whole foods resolved to specific `fdc_id`s in `usda_select.py`, each carrying a
  full 16-nutrient profile per 100 g.
- **Branded products:** Open Food Facts (ODbL, attribution + share-alike). 18 UK
  vegan/plant-based products with real Nutri-Score, NOVA, allergen and label
  tags, pulled by `fetch_seeds.py` via the search-a-licious API.
- **Sustainability:** per-food CO2e/kg and freshwater/kg from Poore & Nemecek
  (2018, Science), processed by Our World in Data (CC BY 4.0). Representative
  figures encoded in `build_nestle_diet_data.py`.
- **Fortified specialty items, recipes, prices, persona targets:** synthesized
  from published standards (NIH/FDA Daily Values, ACSM/ISSN athlete intakes).

## Pipeline

```
fetch_seeds.py            -> data/seed/   (USDA SR Legacy zip + off_products.csv)
usda_select.py            -> resolves 61 curated whole foods to USDA foods
build_nestle_diet_data.py -> data/out/*.csv   (11 tables, deterministic seed=42)
generate_sql.py           -> data/out/02_schema.sql, 03_load.sql, 04_validation.sql, DATA_DICTIONARY.md
check_feasibility.py      -> local PuLP menu MIP; confirms feasibility + anchored numbers
```

Regenerate everything from scratch:

```bash
.venv/bin/python data/fetch_seeds.py             # idempotent; skips existing seeds
.venv/bin/python data/build_nestle_diet_data.py
.venv/bin/python data/generate_sql.py
.venv/bin/python data/check_feasibility.py       # expect status=Optimal, ~$7.06/day
```

## Tables (in PK_NESTLE_DIET.DIET)

| table | grain | rows |
|---|---|---|
| commodity | one per traded commodity input | 25 |
| commodity_price_history | one per commodity per month (Jan 2025 - Jun 2026) | 450 |
| ingredient | one per ingredient / branded product (nutrition + cost + CO2 + flags) | 84 |
| recipe | one per single-serving recipe (derived nutrition/cost/CO2) | 168 |
| recipe_ingredient | bill of materials (recipe x ingredient x grams) | 800 |
| persona | the optimization target profile | 1 |
| persona_nutrient_target | floor/ceiling/range per nutrient | 16 |
| dietary_restriction | restriction reference (vegan, gluten-free, ...) | 6 |
| persona_restriction | persona x active restriction | 1 |
| meal_slot | breakfast / lunch / dinner / snack slot rules | 4 |
| status_quo_menu | the athlete's current favourite day (price-shock baseline) | 5 |

See `data/out/DATA_DICTIONARY.md` for full column-level documentation.

## Loading into Snowflake

One-time, by the user (the security-harness review gate):

```bash
snow sql -c rai -f data/00_bootstrap.sql      # creates RAI_DEMO_NESTLE_DIET + PK_NESTLE_DIET
```

Then, repeatable:

```bash
bash data/load_to_snowflake.sh                # regenerate + schema + stage + COPY + validate
```

Both require a valid `rai` connection. If `snow` reports the programmatic access
token expired, refresh it first.

## Anchored numbers (locked, seed=42)

- Q1: naive cheapest day = $5.01 but fails (protein 90g, B12 2.0ug, vitamin D
  3.0ug, 2544 kcal - all below target).
- Q2: optimal compliant menu = $7.06/day, 2806 kcal, all 16 targets met,
  vitamin D 16.2ug (binding).
- Q3: status-quo favourite $7.32 -> $8.26/day (+13%) under the commodity price
  shock; re-optimizing protects it back to ~$7.15/day.
