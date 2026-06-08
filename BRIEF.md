# BRIEF.md - demo specification

> Single source of truth for the demo's identity. Written from the research
> synthesis on 2026-06-08 and the user's four scoping decisions. Downstream
> phases read this and resume from the first unmet exit criterion.

## Domain

**Pitch (one phrase):** "Algorithmic diet and menu optimization for Nestle:
from ingredient price volatility to profit protection, while preserving
nutrition and sustainability."

**Why RelationalAI here, in one paragraph:** The diet problem is the founding
problem of linear programming (Stigler 1945, solved by Dantzig's simplex in
1947), so it maps one-to-one onto RAI's prescriptive LP/MIP reasoner. A single
ontology over foods, recipes, nutrition, prices, and CO2 backs all three demo
beats: a rules pass classifies which recipes are eligible and nutrition-safe
for a persona, a prescriptive solve builds the cheapest compliant daily menu
under nutrition floors/ceilings and a carbon cap, and a persistent rule lets an
operator add a constraint (a price shock or a tighter CO2 cap) that the model
stores and re-solves against. That rule-accumulation-plus-re-solve loop, with
explainable cost deltas (shadow prices), is awkward in a notebook of one-off
LPs and is exactly what RAI makes operationally alive.

## Inputs

- [ ] Schema (CSV / DDL / PDF): none
- [ ] Problem statement document: none (one deck screenshot only)
- [ ] Existing Snowflake database to demo against: none
- [x] Otherwise: invent the data, seeded from real public datasets

Provided input: one slide, "Applications of Decision Intelligence in Nestle",
whose portfolio-optimization bullet reads "From price volatility to profit
protection: algorithmic recipe optimization that preserves nutrition and
sustainability." The user's framing: demonstrate diet-plan optimization, e.g.
an optimal diet for a vegan athlete or someone with gluten intolerance.

## Scope

- **Length / depth:** 10 min / 3 questions (Snowsight short)
- **Number of demo questions:** 3
- **Reasoners showcased:** rules, prescriptive (MIP), persistent rule
- **Cortex agent (Phase 7):** yes
- **Runbook + prep_demo gate (Phase 8):** yes

## Audience

Nestle business and data stakeholders evaluating Decision Intelligence. They
will recognize the commodity-volatility pain (coffee and cocoa are Nestle's own
named inflationary inputs in FY2024 results) and care that the optimized diet
is realistic, nutritionally sound, and sustainable, not a mathematical curiosity.

**Implication for data rigor:** nutrition numbers must be real (USDA FoodData
Central, CC0) and sustainability coefficients must be citable (Poore & Nemecek
2018, processed by Our World in Data, CC BY 4.0). Branded products are seeded
from Open Food Facts (ODbL). Persona nutrient targets follow published
standards (NIH/FDA Daily Values; ACSM/ISSN athlete position stands). The naive
cost-only diet is shown as a deliberate failure, not hidden.

## The three questions (the narrative arc)

The audience-tested arc from the literature: show the naive answer, let it be
absurd, then add business rules and re-solve, quantifying the cost of each rule.

| # | Reasoner | Question | What it shows |
|---|---|---|---|
| Q1 | Rules | "Which recipes are eligible for our vegan endurance athlete, and what happens if we just pick the cheapest compliant ones?" | Classifies recipes by vegan-eligibility and flags nutrition-guardrail breaches; the naive cheapest selection misses protein/micros. Exposes the problem. |
| Q2 | Prescriptive (MIP) | "Build the cheapest one-day menu (breakfast, lunch, dinner, snack) that meets every nutrition target and stays under the carbon cap." | Binary recipe-to-meal-slot selection; nutrient floors and ceilings; per-recipe and variety caps; CO2 constraint; minimize cost. Returns an optimal, realistic menu with total cost, total CO2, and the binding nutrient. The fix. |
| Q3 | Persistent rule | "A buyer flags a commodity price spike (or ops tightens the carbon cap). Add the rule and re-solve." | The model stores the new rule and re-optimizes; show the menu diff, the cost delta, and the shadow price ("this rule costs $X/day because it forces out cheap recipe Y"). Operator authority and the price-volatility payoff. |

The pitfall designed against: a pure cost-min LP collapses to 4-6 foods in huge
quantities (the Stigler/Dantzig "200 bouillon cubes" trap). Fixes baked into
the data and formulation: every nutrient minimum has a maximum; per-recipe
serving caps (~95th percentile of intake); diversity/variety constraints;
meal-slot structure via binary variables; optional "stay close to a normal
diet" acceptability term.

## Hero persona

**Marco** (`persona_id = marco`), a busy startup executive who trains for
marathons and eats vegan. The character carries the demo's framing: he
optimizes everything about his company and his splits but runs his diet on
vibes, so he is the perfect case for Decision Intelligence. The talk track
speaks about Marco by name (persona table, queries, and the Cortex agent).
Insight-joke opener: "BI told Marco his diet was a disaster in seven colors;
DI just hands him dinner." Running gag: "you can't out-train a bad spreadsheet."

Profile: a ~70 kg marathoner, ~3,000 kcal/day,
carbohydrate ~7 g/kg/day (~490 g), protein ~1.4 g/kg/day (~98 g), fat 25-30% of
energy, fiber >= 30 g, plus micronutrient floors (iron, calcium, B12, zinc) and
ceilings (sodium <= 2,300 mg, saturated fat). Plant-only: excludes meat, dairy,
eggs, fish. Honest beat available: strict-vegan full micronutrient adequacy can
be infeasible, which the solver will surface rather than fake.

## Data strategy

Hybrid, fully reproducible via a seeded generator (mirrors the airplanes/
supply_chain pattern: a Python generator emits denormalized tables + DDL +
validation.sql).

- **Nutrition spine:** USDA FoodData Central Foundation Foods / SR Legacy (CC0,
  public domain). Food x nutrient matrix via food_nutrient join.
- **Branded products:** Open Food Facts filtered Parquet (ODbL): real products
  with per-100g nutrition, allergens_tags, labels_tags (en:vegan,
  en:gluten-free), nutriscore_grade, nova_group. Attribution + share-alike
  honored on any redistributed derived data.
- **Recipes:** synthesized, ~80-200, ingredients mapping by name onto the
  nutrition spine. Gives clean numeric quantities and traceable per-recipe
  nutrition that real recipe corpora lack.
- **Sustainability:** per-ingredient CO2e/kg and freshwater/kg from OWID/Poore
  & Nemecek. (Carbon-vs-water rankings diverge, which makes any later
  multi-objective angle non-trivial.)
- **Prices:** synthetic ingredient/commodity price time series anchored to real
  moves (cocoa, coffee, dairy, wheat, palm oil) so a "re-optimize after the
  cocoa spike" event is datable.

Proposed denormalized schema (~12-15 tables): INGREDIENT (USDA/OFF nutrition +
cost + CO2e + water + allergen/diet flags + brand), RECIPE (derived nutrition,
cost, CO2e, Nutri-Score, meal_type), RECIPE_INGREDIENT (bill-of-materials
junction), PERSONA, PERSONA_NUTRIENT_TARGET (min/max per nutrient),
DIETARY_RESTRICTION, MEAL_SLOT, COMMODITY, INGREDIENT_PRICE_HISTORY,
NESTLE_BRAND/category dim.

## Names (derived, lock these now)

| Thing | Value |
|---|---|
| Model name (PyRel) | `nestle_diet` |
| Database name (Snowflake) | `PK_NESTLE_DIET` |
| **Demo role (security harness)** | `RAI_DEMO_NESTLE_DIET` |
| Schema for sources | `PK_NESTLE_DIET.DIET` |
| Schema for agent | `PK_NESTLE_DIET.RAI_AGENT` |
| Logic engine | `nestle_diet_logic_xs` (HIGHMEM_X64_XS, auto-suspend 5 min) |
| Prescriptive engine | `nestle_diet_prescriptive_xs` (HIGHMEM_X64_XS, auto-suspend 5 min) |
| Notebook stage | `PK_NESTLE_DIET.NOTEBOOKS.NESTLE_DIET_NOTEBOOK_STAGE` |
| Snowsight notebook | `PK_NESTLE_DIET.NOTEBOOKS.NESTLE_DIET_DEMO` |
| Cortex agent | `nestle_diet` |

## Snowflake security harness

> Filled during intake step 3 (bootstrap). Pending: generate
> `data/00_bootstrap.sql` from BOOTSTRAP.template.sql for `RAI_DEMO_NESTLE_DIET`
> + `PK_NESTLE_DIET`, then user reviews and runs it once.

- **Bootstrap SQL run:** `data/00_bootstrap.sql` (pending generation + review).
- **Demo role:** `RAI_DEMO_NESTLE_DIET`.
- **Demo database:** `PK_NESTLE_DIET`.

## Anchored numbers

> Locked from the generated data (seed=42) via the local PuLP model of the menu
> MIP (`data/check_feasibility.py`), which mirrors what PyRel solves in Phase 4.
> All reproduce from `data/out/04_validation.sql`. Menu structure: 1 breakfast +
> 2 mains (lunch+dinner) + 1-2 snacks, all vegan, minimize cost s.t. 16 nutrient
> targets. Catalog: 84 ingredients (61 USDA + 5 fortified specialty + 18 Open
> Food Facts), 168 recipes (73 breakfast, 68 main, 27 snack), 122 gluten-free.

| Question | Expected answer | Source |
|---|---|---|
| Q1 (Rules) | 168 recipes, all 168 vegan-eligible, 122 gluten-free. The naive "cheapest recipe per slot" day costs only **$5.01** but FAILS the targets: protein 90g (<98), B12 2.0ug (<2.4), vitamin D 3.0ug (<15), only 2544 kcal (<2800). Cheap looks fine until you check nutrition. | `04_validation.sql` C |
| Q2 (Prescriptive) | MIP OPTIMAL; cheapest compliant one-day vegan menu = **$7.06/day**, all 16 targets met, 2806 kcal, 107g protein, vitamin D 16.2ug (binding), CO2 4.38 kg. Spending ~$2 over the naive diet buys full nutritional compliance. The fortified shake/cereal are pulled in to hit B12 and vitamin D. | `04_validation.sql` |
| Q3 (Persistent rule, CO2 cap) - IMPLEMENTED | Reuse Q2's Problem, add a 3.0 kg CO2/day cap, re-solve: OPTIMAL **$7.17/day at 2.92 kg** (baseline was $7.06 / 4.38 kg), i.e. **+$0.11 for a ~33% carbon cut** and the menu shifts to chickpea/lentil pasta bowls. Tighten to 2.5 kg -> **INFEASIBLE** (the feasibility wall: the model proves no compliant menu exists). Live in `demo_queries.py` q3. | `demo_queries.py` q3 |
| Q3 (Persistent rule, price shock) - DATA-LEVEL ALTERNATIVE | The status-quo favourite menu = $7.32/day, rising to $8.26/day (+13%) under the cocoa/coffee/nut/oil shock; re-optimizing protects it back to ~$7.15. Backed by `status_quo_menu` + `cost_usd_shock`; usable as an alternate Q3 beat without a second MIP. | `04_validation.sql` D |

## Phase log

### Phase 1 - Positioning
In progress. Concept, scope (3 questions, Snowsight-short), hero persona (vegan
endurance athlete), cost-primary objective with nutrition + CO2 constraints,
data strategy (USDA + OFF + synthetic recipes), schema sketch, and names locked
from the research synthesis and the user's four scoping decisions on 2026-06-08.

### Phase 2 - Data
Generated and verified locally on 2026-06-08. A deterministic generator
(`data/build_nestle_diet_data.py`, seed=42) builds 11 denormalized tables from
real seed data: USDA FoodData Central SR Legacy (CC0) for the 61-food nutrition
spine, Open Food Facts (ODbL) for 18 UK branded vegan products, plus 5
hand-authored fortified specialty items (Nestle Health Science style). 168
single-serving recipes with a 800-row bill-of-materials, derived nutrition/cost/
CO2; a vegan endurance athlete persona with 16 nutrient targets; commodity price
history (25 commodities x 18 months) anchored to real cocoa/coffee/wheat moves;
and a status-quo menu for the price-shock story. `data/generate_sql.py` emits
DDL with full metadata (column + table comments, PK/FK, NOT NULL, change
tracking), `03_load.sql`, `04_validation.sql`, and `DATA_DICTIONARY.md`.
`data/check_feasibility.py` (PuLP) confirms the menu MIP is OPTIMAL and locks the
anchored numbers. NOT yet loaded to Snowflake: the `rai` connection's
programmatic access token is expired (see Autonomy issues); load is one command
(`bash data/load_to_snowflake.sh`) once the token is refreshed and the user has
run `data/00_bootstrap.sql`.

### Phase 3 - Ontology
Done 2026-06-08. `rai_code/manual/nestle_diet.py` is the PyRel ontology over
PK_NESTLE_DIET.DIET: 11 concepts (Commodity, CommodityPrice, DietaryRestriction,
MealSlot, Ingredient, Recipe, RecipeIngredient, Persona, NutrientTarget,
PersonaRestriction, StatusQuoMenuItem), Boolean flag properties, FK
relationships, and `model.define` data binding from the Snowflake tables. Two
named engines provisioned READY: nestle_diet_logic_xs and
nestle_diet_prescriptive_xs, both at HIGHMEM_X64_S (HIGHMEM_X64_XS is NOT
provisionable on this account, contrary to the template default; config updated
and noted). Validation (`python rai_code/manual/nestle_diet.py`) passes: every
concept count matches the source except RecipeIngredient 799 vs 800 (one recipe
lists an ingredient twice; the (recipe,ingredient) junction identity merges
them, recipe nutrition unaffected; generator dedupe is a pending polish). Marco
resolves correctly (marathon running, vegan, 3000 kcal). Gotchas fixed: `!= None`
null-guards produce an untypable None literal (load nullable columns directly
instead, PyRel skips null facts); engine size must be S not XS.

### Phase 4 - Queries
Done 2026-06-08. `rai_code/manual/demo_queries.py` runs all three questions
green end-to-end against the live engines (`python rai_code/manual/demo_queries.py`,
exit 0). Q1 (rules): vegan catalog + the naive cheapest-per-slot day = $5.01 that
fails kcal/protein/carb/B12/vitamin-D. Q2 (prescriptive MIP via
relationalai.semantics.reasoners.prescriptive.Problem, HiGHS): binary
Recipe.selected scoped to vegan, slot constraints (1 breakfast, 2 mains, 1-2
snacks), 16 nutrient floor/ceiling constraints from Marco's targets, minimize
cost -> OPTIMAL $7.06/day, 2806 kcal, 107g protein, vitD 16.2ug, B12 4.2ug.
Q3 (persistent rule): reuse Q2's Problem, add a 3.0 kg CO2 cap, re-solve ->
OPTIMAL $7.17/day at 2.92 kg (+$0.11 for ~33% less carbon, menu shifts to
chickpea/lentil pasta); tighten to 2.5 kg -> INFEASIBLE (feasibility wall).
Gotchas fixed: decision-variable property must be a declared numeric Float
(`Recipe.selected = model.Property(f"{Recipe} has {Float:selected}")`), not
inferred Any; re-solving a SECOND Problem on the same property raises FDError,
so Q3 reuses Q2's Problem (constraints accumulate, re-solve updates values).

### Phase 5 - Local notebook
Done 2026-06-08. `rai_code/manual/nestle_diet_demo.ipynb` (built by
`build_notebook.py`) tells the Marco story in 5 code cells + markdown and renders
3 Plotly figures (Q1 nutrient-gap bars, Q2 menu table, Q3 cost-vs-CO2). Executes
top-to-bottom green via `jupyter nbconvert --execute` with the exact numbers
($5.01 fail, $7.06 optimal, +$0.11 for 33% less carbon). Gotcha: relationalai
1.9.0 guards its blocking sync API against a running event loop, so the notebook
runs every query/solve in a worker thread (a `run()` helper); model import on the
main thread is fine. Q2+Q3 share one Problem to avoid the re-solve FDError.

### Phase 6 - Snowsight notebook
Done 2026-06-08. `rai_code/manual/nestle_diet_demo_snowsight.ipynb` (generated by
`build_snowsight_notebook.py` from the local notebook: adds a `pip install
relationalai` cell and cwd-relative imports). Deployed to
PK_NESTLE_DIET.NOTEBOOKS.NESTLE_DIET_DEMO via `data/upload_snowsight_notebook.sh`
(stage + PUT of notebook + nestle_diet.py + demo_queries.py + requirements.txt;
CREATE NOTEBOOK with container runtime SYSTEM$BASIC_RUNTIME, QUERY_WAREHOUSE
RAI_XS, COMPUTE_POOL NOTEBOOK_CPU_XS (shared; granted USAGE to the demo role),
EXTERNAL_ACCESS_INTEGRATIONS PYPI + S3_RAI). Confirmed present via SHOW NOTEBOOKS.
Run path: open in Snowsight and Run All (the pip cell installs PyRel; container
runtime required because the warehouse Anaconda channel lacks relationalai).
Headless `snow notebook execute` not run here (compute-pool spin-up + package
install); the interactive Run-All path is the intended demo flow.

### Phase 5b - Visualizations + HTML brief
Done 2026-06-08. `build/generate_demo_figures.py` writes 7 figures to
`build/figures/` (+ interactive figures.html): Q1 nutrient gap, naive-vs-optimal
achievement, Q3 cost-vs-CO2, commodity price volatility, and the DIET GRAPHS -
recipe -> ingredient -> commodity Sankeys per menu - plus a commodity cost-exposure
comparison (optimal vs capped). `build/build_runbook.py` embeds them into a
self-contained `RUNNING.html` brief. The diet composition is also a query
(`demo_queries.optimal_diet_commodities_df`) and an agent tool
(`marco_diet_commodities`): the optimal diet touches 11 commodities, top exposure
Soybean $1.90/day, Fruit $1.14, Oats $0.79.

### Phase 7 - Cortex agent
Done 2026-06-08. `agent/deploy.py` + `agent/queries.py` deploy the `nestle_diet`
agent to SNOWFLAKE_INTELLIGENCE.AGENTS (appears in the SI picker) with sprocs in
PK_NESTLE_DIET.RAI_AGENT (all 4 RAI sprocs live). Three QueryCatalog tools wrap
the questions (naive day, optimal menu, carbon-capped menu). Verified via
`agent.deploy chat`: all three Marco questions answered correctly with exact
numbers and narrative ($5.01 fail, $7.06 optimal, $7.17/-33% carbon). Gotcha:
demo_queries imports nestle_diet package-aware (try `from . import` else top-level)
so the agent's sproc and the CLI share one Model instance.

### Phase 8 - Gate + runbook
Done 2026-06-08. `prep_demo.py` is the pre-flight gate: checks connection, data +
anchored counts, both engines, the three demo queries (Q1 $5.01 fail / Q2 OPTIMAL
$7.06 / Q3 INFEASIBLE wall), and the deployed agent, with a PASS/FAIL summary.
Gate result 2026-06-08: **5/5 PASS**. Runbook: `RUNNING.md` documents the run
order. (Engine check matches the truncated `rai reasoners list` display.)

## Status: COMPLETE
The demo is built and verified end-to-end against live Snowflake (account
ajb85638, PK_NESTLE_DIET). `prep_demo.py` is 5/5. Phases 1-5, 7, 8 done; Phase 6
(Snowsight server-side notebook) deferred as optional.

### Phase 9 - Talk track + handoff
_pending_

## Design decisions

- **Diet/menu optimization over recipes (not raw foods, not whole meals).**
  Choosing raw foods yields an unappetizing "eat 1.2 kg of lentils" diet;
  choosing whole pre-built menus is too coarse to show interesting
  optimization. Recipes are the sweet spot and are rich enough to constrain on
  macros, variety, budget, and carbon.
- **Cost-primary objective.** Matches the slide headline "price volatility to
  profit protection." Nutrition floors/ceilings and a CO2 cap are constraints,
  not objectives, keeping the model a clean MIP and the story aligned to the
  business case.
- **Real nutrition + real sustainability data, synthetic recipes/prices.** The
  audience will challenge nutrition realism, so the spine is USDA (CC0) plus
  Open Food Facts branded products (ODbL); recipes and price series are
  synthesized for control over feasibility and the anchored numbers.
- **Single hero persona (vegan endurance athlete)** for a tight 10-minute arc.
  The strict-vegan-adequacy infeasibility risk is kept as an honest beat.
- **Naive diet shown as Act 1.** The famous degenerate LP failure is the
  problem-exposure beat, not a hidden bug.

### Engine sizing

- **Logic engine size:** `XS` (default).
- **Prescriptive engine size:** `XS` (default). A 3-question demo with a
  small recipe set and binary slot assignment should solve well within XS on
  HiGHS; size up only if measured.
- **Auto-suspend:** 5 minutes for both.

## Open questions

- Exact recipe count and the precise anchored numbers are set when the
  generator runs and the data is tuned backwards to the talk track.
- Open Food Facts ODbL share-alike applies to any redistributed derived
  database; confirm the demo DB is internal-only or carries ODbL attribution.
- Whether Q3's persistent rule should be the carbon-cap tightening or the
  commodity price shock (both are supported by the data; pick the stronger
  live beat during Phase 4).

## Autonomy issues

- Two early prompts were on `cd`-prefixed multi-statement shell scripts and a
  bare `cd /tmp`, which do not match the allow patterns. Read-only local
  inspection (jq over transcripts, reading workflow journals) is now run as
  single allowlisted commands with absolute paths. User confirmed standing
  approval for such read-only calls.
- **Snowflake load blocked (2026-06-08):** the `rai` connection's programmatic
  access token is expired ("Programmatic access token is expired", account
  ajb85638). All data + SQL artifacts are generated and verified locally, but
  bootstrap and load cannot run until the user refreshes the PAT (PAT creation
  requires ALTER USER, which the security harness denies the agent, so this is a
  manual user step). After refresh: run `snow sql -c rai -f data/00_bootstrap.sql`
  once, then `bash data/load_to_snowflake.sh`.
