#!/usr/bin/env bash
#
# load_to_snowflake.sh - idempotent loader for the Nestle diet-optimization demo.
# Regenerates the data + SQL artifacts, then creates the schema, stages the CSVs,
# COPYs them in, and runs the anchored-number validation. Everything runs as the
# scoped demo role RAI_DEMO_NESTLE_DIET (never the profile default).
#
# Prerequisites (one-time):
#   1. A valid `rai` snow connection (refresh the programmatic access token if
#      `snow sql -c rai -q "SELECT 1"` reports it expired).
#   2. The bootstrap has been run once by the user:
#        snow sql -c rai -f data/00_bootstrap.sql
#
# Run:  bash data/load_to_snowflake.sh
set -euo pipefail

ROLE=RAI_DEMO_NESTLE_DIET
CONN=rai
DB=PK_NESTLE_DIET
SCHEMA=DIET
STAGE=DIET_STAGE

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="$REPO/.venv/bin/python"
OUT="$REPO/data/out"

TABLES=(commodity commodity_price_history ingredient recipe recipe_ingredient \
        persona dietary_restriction persona_restriction persona_nutrient_target \
        meal_slot status_quo_menu)

echo "==> 1/5 Regenerating data + SQL artifacts (deterministic, seed=42)"
"$PY" "$REPO/data/build_nestle_diet_data.py"
"$PY" "$REPO/data/generate_sql.py"

echo "==> 2/5 Creating schema + tables (full metadata, change tracking)"
snow sql --role "$ROLE" -c "$CONN" -f "$OUT/02_schema.sql"

echo "==> 3/5 Creating stage + uploading CSVs"
snow sql --role "$ROLE" -c "$CONN" -q \
  "USE DATABASE $DB; USE SCHEMA $SCHEMA; CREATE STAGE IF NOT EXISTS $STAGE \
   FILE_FORMAT = (TYPE = CSV SKIP_HEADER = 1 FIELD_OPTIONALLY_ENCLOSED_BY = '\"' \
   NULL_IF = ('', 'NULL') EMPTY_FIELD_AS_NULL = TRUE TRIM_SPACE = TRUE);"
for t in "${TABLES[@]}"; do
  snow sql --role "$ROLE" -c "$CONN" -q \
    "PUT file://$OUT/$t.csv @$DB.$SCHEMA.$STAGE AUTO_COMPRESS=FALSE OVERWRITE=TRUE;"
done

echo "==> 4/5 COPY INTO tables"
snow sql --role "$ROLE" -c "$CONN" -f "$OUT/03_load.sql"

echo "==> 5/5 Validating anchored numbers"
snow sql --role "$ROLE" -c "$CONN" -f "$OUT/04_validation.sql"

echo "Done. PK_NESTLE_DIET.DIET is loaded and validated."
