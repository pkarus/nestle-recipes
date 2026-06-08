#!/usr/bin/env bash
# Upload the Snowsight notebook + its .py dependencies to a Snowsight Notebook
# at PK_NESTLE_DIET.NOTEBOOKS.NESTLE_DIET_DEMO, runnable in Snowsight (container
# runtime + PyPI external access so the notebook's `pip install relationalai`
# cell works). Reuses the shared NOTEBOOK_CPU_XS compute pool (no new pool).
#
# Prereq (one-time, ACCOUNTADMIN): the demo role needs USAGE on the pool:
#   snow sql -c rai --query \
#     "GRANT USAGE ON COMPUTE POOL NOTEBOOK_CPU_XS TO ROLE RAI_DEMO_NESTLE_DIET;"
#
# Run:  bash data/upload_snowsight_notebook.sh
set -euo pipefail

CONN="${CONN:-rai}"
ROLE="${ROLE:-RAI_DEMO_NESTLE_DIET}"
DB="PK_NESTLE_DIET"
NB_SCHEMA="NOTEBOOKS"
NB_STAGE="NESTLE_DIET_NOTEBOOK_STAGE"
NB_NAME="NESTLE_DIET_DEMO"
NB_FOLDER="nestle_diet"
NB_MAIN="nestle_diet_demo_snowsight.ipynb"
POOL="${POOL:-NOTEBOOK_CPU_XS}"

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC=(
  "$ROOT/rai_code/manual/nestle_diet_demo_snowsight.ipynb"
  "$ROOT/rai_code/manual/nestle_diet.py"
  "$ROOT/rai_code/manual/demo_queries.py"
  "$ROOT/rai_code/manual/requirements.txt"
)

echo "==> [1/4] regenerate the Snowsight notebook from the local one"
"$ROOT/.venv/bin/python" "$ROOT/rai_code/manual/build_snowsight_notebook.py"

echo "==> [2/4] schema + stage"
snow sql -c "$CONN" --role "$ROLE" -q "
USE DATABASE $DB;
CREATE SCHEMA IF NOT EXISTS $NB_SCHEMA;
CREATE STAGE IF NOT EXISTS $DB.$NB_SCHEMA.$NB_STAGE
  FILE_FORMAT = (TYPE = CSV SKIP_HEADER = 1 FIELD_OPTIONALLY_ENCLOSED_BY = '\"'
                 NULL_IF = ('','NULL') EMPTY_FIELD_AS_NULL = TRUE);" >/dev/null

echo "==> [3/4] PUT files (auto_compress=FALSE so Snowsight reads them directly)"
for f in "${SRC[@]}"; do
  echo "  - $(basename "$f")"
  snow sql -c "$CONN" --role "$ROLE" -q \
    "PUT file://$f @$DB.$NB_SCHEMA.$NB_STAGE/$NB_FOLDER/ AUTO_COMPRESS=FALSE OVERWRITE=TRUE;" >/dev/null
done

echo "==> [4/4] CREATE OR REPLACE NOTEBOOK + ADD LIVE VERSION"
# Container runtime (SYSTEM\$BASIC_RUNTIME) is required: the warehouse runtime's
# Anaconda channel does not include relationalai. PyPI external access lets the
# in-notebook `pip install relationalai` cell run.
snow sql -c "$CONN" --role "$ROLE" -q "
CREATE OR REPLACE NOTEBOOK $DB.$NB_SCHEMA.$NB_NAME
  FROM '@$DB.$NB_SCHEMA.$NB_STAGE/$NB_FOLDER'
  MAIN_FILE = '$NB_MAIN'
  QUERY_WAREHOUSE = RAI_XS
  COMPUTE_POOL = $POOL
  RUNTIME_NAME = 'SYSTEM\$BASIC_RUNTIME'
  IDLE_AUTO_SHUTDOWN_TIME_SECONDS = 1800
  EXTERNAL_ACCESS_INTEGRATIONS = (PYPI_ACCESS_INTEGRATION, S3_RAI_INTERNAL_BUCKET_EGRESS_INTEGRATION)
  COMMENT = 'Nestle / Marco vegan diet optimization - 3-question PyRel demo. Stage folder: $NB_FOLDER/';
ALTER NOTEBOOK $DB.$NB_SCHEMA.$NB_NAME ADD LIVE VERSION FROM LAST;" >/dev/null

echo "Done. Open PK_NESTLE_DIET.NOTEBOOKS.NESTLE_DIET_DEMO in Snowsight and Run All."
