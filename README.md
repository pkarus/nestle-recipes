# Nestle Decision Intelligence: optimizing Marco's diet

A RelationalAI demo of **Decision Intelligence** for Nestle, built around the
slide line *"from price volatility to profit protection: algorithmic recipe
optimization that preserves nutrition and sustainability."* Concretely: optimize
a daily diet for **Marco**, a busy startup executive who trains for marathons
and eats vegan.

> Marco runs a startup and runs marathons, so he optimizes everything: burn
> rate, runway, his 5K splits. His diet, though, he runs on vibes. Being an
> exec, he built a spreadsheet, and forty tabs later he had a beautiful
> dashboard that told him, in seven colors, exactly how under-fed he was. That
> is Business Intelligence: it told Marco his diet was a disaster. **Decision
> Intelligence just hands him dinner.**

One RelationalAI model over real nutrition data and a synthesized recipe catalog
backs three questions. Running gag: *you can't out-train a bad spreadsheet.*

## The three questions

| # | Reasoner | Question | Result (verified live) |
|---|---|---|---|
| Q1 | Rules | Just pick the cheapest vegan recipe per meal slot. Does it feed Marco? | **$5.01/day** but FAILS: short on calories, protein, carbs, B12, and vitamin D |
| Q2 | Prescriptive (MIP) | Cheapest one-day menu that meets all 16 of his nutrition targets | **OPTIMAL, $7.06/day** - about $2 more buys full compliance (the optimizer pulls in a fortified shake and cereal to clear the B12 / vitamin-D floors) |
| Q3 | Persistent rule | An operator adds a sustainability rule: cap the diet's carbon | **$7.17/day at 2.92 kg CO2** (+$0.11 for ~33% less carbon); tighten to 2.5 kg and the solver returns **INFEASIBLE** - it proves no compliant menu exists rather than faking one |

The same model also answers *"what recipes and commodities does the diet
actually use?"* - a recipe to ingredient to commodity breakdown that surfaces
the diet's price-volatility exposure (the optimal menu leans on soybean, fruit,
and oats).

## Run it

```bash
# Pre-flight gate (~10 min before showtime): connection, data, engines, Q1-Q3, agent
.venv/bin/python prep_demo.py

# The three questions, end to end against live Snowflake
.venv/bin/python rai_code/manual/demo_queries.py

# Local notebook (Marco narrative + Plotly figures, including the diet graphs)
.venv/bin/jupyter lab rai_code/manual/nestle_diet_demo.ipynb

# Cortex agent in Snowflake Intelligence (picker name: nestle_diet)
.venv/bin/python -m agent.deploy chat "Build Marco the cheapest one-day menu that meets all his nutrition targets."
.venv/bin/python -m agent.deploy chat "What commodities does Marco's optimized diet depend on?"
```

In **Snowsight**, open the notebook `PK_NESTLE_DIET.NOTEBOOKS.NESTLE_DIET_DEMO`
and Run All (its first cell `pip install relationalai`). For a no-setup
overview, open [`RUNNING.html`](RUNNING.html) in any browser - a self-contained
brief with every result figure embedded.

## What's in here

```
rai_code/manual/
  nestle_diet.py              the PyRel ontology (11 concepts over PK_NESTLE_DIET)
  demo_queries.py             Q1 rules, Q2 prescriptive MIP, Q3 persistent rule + diet composition
  nestle_diet_demo.ipynb      local notebook (narrative + Plotly)
  nestle_diet_demo_snowsight.ipynb   the Snowsight version (pip install relationalai)
agent/
  deploy.py, queries.py       Cortex agent: deploy + the QueryCatalog tools
data/
  fetch_seeds.py              download USDA + Open Food Facts seeds
  build_nestle_diet_data.py   deterministic generator (seed=42)
  generate_sql.py             DDL (full metadata) + load + validation SQL
  00_bootstrap.sql            one-time demo role + database (review before running)
  load_to_snowflake.sh        idempotent loader; upload_snowsight_notebook.sh
  out/                        generated tables (CSV) + SQL + DATA_DICTIONARY.md
build/
  generate_demo_figures.py    result figures incl. recipe->ingredient->commodity diet graphs
  build_runbook.py            renders RUNNING.html
prep_demo.py                  the pre-flight gate (5/5)
BRIEF.md                      full design of record; RUNNING.md the run order
```

## The data (real, openly licensed; recipes synthesized)

- **Nutrition spine:** USDA FoodData Central SR Legacy (public domain, CC0).
- **Branded products:** Open Food Facts (ODbL) - real vegan/plant-based products
  with Nutri-Score, allergens, and labels.
- **Sustainability:** CO2e and water per food from Poore & Nemecek (2018,
  *Science*), processed by Our World in Data (CC BY 4.0).
- **Recipes, prices, persona targets:** synthesized from published standards
  (NIH/FDA Daily Values, ACSM/ISSN athlete intakes). All numbers reproduce from
  `bash data/load_to_snowflake.sh` (seed=42).

Recreate the dataset: `data/fetch_seeds.py` then `data/build_nestle_diet_data.py`
then `data/generate_sql.py`. The 44 MB of downloaded seed data is gitignored and
re-fetched on demand.

## Requirements

- A `rai` connection profile in `~/.snowflake/connections.toml` (account
  `ajb85638`, warehouse `RAI_XS`); the RelationalAI Native App installed on the
  account.
- Python 3.13 + `uv`; `snow` CLI. Create the venv with `uv venv` and
  `uv pip install relationalai pandas pyarrow requests pulp plotly`.
- One-time: review and run `data/00_bootstrap.sql` (creates the scoped role
  `RAI_DEMO_NESTLE_DIET` and database `PK_NESTLE_DIET`), then
  `bash data/load_to_snowflake.sh`.

## Note

This is a sales-engineering demo. The nutrition and sustainability figures are
real and citable; the recipes, prices, and the Marco persona are synthetic. It
is not dietary advice.
