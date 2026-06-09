# Running the Nestle / Marco diet-optimization demo

A RelationalAI Decision Intelligence demo: optimizing the diet of **Marco**, a
busy startup executive training for marathons (vegan). Theme: from ingredient
price volatility to profit protection, preserving nutrition and sustainability.

## The three stages

| Stage | Technique | What happens | Result |
|---|---|---|---|
| Problem | Rules | Cheapest vegan recipe per slot - does it feed Marco? | $5.01/day but fails calories, protein, B12, vitamin D |
| Solution | Optimization model | Cheapest one-day menu meeting all 16 nutrient targets | OPTIMAL $7.06/day |
| Adaptation | Re-solve under a new rule | Add a 3 kg/day carbon cap (or a price shock) and re-solve | $7.17/day, -33% carbon (+$0.11); tighter -> INFEASIBLE |

Opener: "BI told Marco his diet was a disaster in seven colors; DI just hands him
dinner." Running gag: "you can't out-train a bad spreadsheet."

## Prerequisites (one-time)

```bash
# A valid rai connection (refresh the PAT in ~/.snowflake/pat_token if expired):
snow connection test -c rai
# Bootstrap the demo role + database (review first; run once as ACCOUNTADMIN):
snow sql -c rai -f data/00_bootstrap.sql
# Generate + load the data, and validate anchored numbers:
bash data/load_to_snowflake.sh
```

Engines `nestle_diet_logic_xs` and `nestle_diet_prescriptive_xs` (both
HIGHMEM_X64_S) provision on first query and auto-suspend after 10 min.

## Readiness check (run ~10 min before showtime)

```bash
.venv/bin/python prep_demo.py                 # full gate (connection, data, engines, all stages, agent)
.venv/bin/python prep_demo.py --skip-queries  # fast checks only
```

## Run the demo

```bash
# CLI: the three stages, end to end against live Snowflake
.venv/bin/python rai_code/manual/demo_queries.py

# Local notebook (Marco narrative + Plotly figures)
.venv/bin/jupyter lab rai_code/manual/nestle_diet_demo.ipynb
#   regenerate:  .venv/bin/python rai_code/manual/build_notebook.py
#   re-execute:  .venv/bin/jupyter nbconvert --execute --to notebook --inplace \
#                  --ExecutePreprocessor.timeout=1200 rai_code/manual/nestle_diet_demo.ipynb

# Cortex agent (Snowflake Intelligence picker: "nestle_diet")
.venv/bin/python -m agent.deploy status
.venv/bin/python -m agent.deploy chat "Build Marco the cheapest one-day menu that meets all his nutrition targets."
.venv/bin/python -m agent.deploy chat "Re-plan Marco's menu under a 3 kg per day carbon cap."
.venv/bin/python -m agent.deploy chat "What commodities does Marco's optimized diet depend on?"

# Snowflake notebook (runs IN Snowsight; first cell pip installs relationalai)
#   Object: PK_NESTLE_DIET.NOTEBOOKS.NESTLE_DIET_DEMO  -> open in Snowsight, Run All
#   (re)deploy:  bash data/upload_snowsight_notebook.sh
```

## Visualizations

- `RUNNING.html` - self-contained HTML brief with every result figure embedded (open in any browser).
- `build/figures/` - the figures as PNGs + `figures.html` (interactive Plotly). Regenerate:
  `.venv/bin/python build/generate_demo_figures.py && .venv/bin/python build/build_runbook.py`
- The **diet graph** (`q2_diet_graph.png` / `q3_diet_graph.png`) is a recipe -> ingredient ->
  commodity Sankey showing exactly what each optimized menu uses and which commodities it is
  exposed to. `commodity_exposure.png` compares that exposure for the optimal vs carbon-capped diet.
- Same breakdown as a query: `demo_queries.optimal_diet_commodities_df()` (and the agent tool
  `marco_diet_commodities`).

## Layout

- `data/` - reproducible generator (USDA FoodData Central CC0 + Open Food Facts ODbL
  + synthesized recipes/prices), DDL/load/validation SQL, `00_bootstrap.sql`.
- `rai_code/manual/nestle_diet.py` - the PyRel ontology (11 concepts).
- `rai_code/manual/demo_queries.py` - the three stages (problem rules, optimization model, adaptation rule).
- `rai_code/manual/nestle_diet_demo.ipynb` - the local viz notebook.
- `agent/deploy.py`, `agent/queries.py` - the Cortex agent.
- `prep_demo.py` - the pre-demo readiness check. `BRIEF.md` - the full design of record.

## Data provenance and licensing

USDA FoodData Central (public domain, CC0); Open Food Facts (ODbL, attribution +
share-alike on any redistributed derived database); sustainability coefficients
from Poore & Nemecek (2018, Science) processed by Our World in Data (CC BY 4.0);
recipes, prices, and persona targets synthesized from published standards.
