"""Demo queries for the Nestle diet/menu optimization demo (Marco).

Q1  Rules / problem exposure: the recipe catalog for a vegan athlete, and the
    naive "cheapest recipe per slot" day that looks cheap but misses Marco's
    nutrition targets.
Q2  Prescriptive (MIP): the cheapest one-day menu that meets every target.   [TODO]
Q3  Persistent rule: re-solve under a commodity price shock / added rule.     [TODO]

Run from project root:
    .venv/bin/python rai_code/manual/demo_queries.py
"""
import os
import sys

import pandas as pd

# Import nestle_diet as the SAME module instance whether this file is run as a
# script (python rai_code/manual/demo_queries.py), imported by the notebook
# (from demo_queries import ...), or imported by the agent as a package submodule
# (from rai_code.manual import demo_queries). Two instances would build two
# Model("nestle_diet") objects.
try:
    from . import nestle_diet  # package context (agent: rai_code.manual.demo_queries)
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import nestle_diet  # script / notebook context
model = nestle_diet.model
Recipe = nestle_diet.Recipe
Persona = nestle_diet.Persona
NutrientTarget = nestle_diet.NutrientTarget
RecipeIngredient = nestle_diet.RecipeIngredient
Ingredient = nestle_diet.Ingredient
Commodity = nestle_diet.Commodity
from relationalai.semantics import Float, distinct  # noqa: E402
from relationalai.semantics.std import aggregates as aggs  # noqa: E402
from relationalai.semantics.reasoners.prescriptive import Problem  # noqa: E402

PERSONA_ID = "marco"
# The daily menu shape Marco's planner fills.
SLOT_PLAN = [("breakfast", 1), ("main", 2), ("snack", 2)]

# Decision-variable property for the menu MIP (declared here, never data-bound;
# solve_for() requires a numeric property and populates it with the solution).
Recipe.selected = model.Property(f"{Recipe} has {Float:selected}")


def marco_targets():
    """Marco's nutrient targets as {code: (min, max, direction)}."""
    df = model.where(
        NutrientTarget.persona(Persona),
        Persona.persona_id == PERSONA_ID,
    ).select(
        NutrientTarget.nutrient_code.alias("code"),
        NutrientTarget.nutrient_name.alias("name"),
        NutrientTarget.min_amount.alias("min_amount"),
        NutrientTarget.max_amount.alias("max_amount"),
        NutrientTarget.direction.alias("direction"),
    ).to_df()
    return df


def q1_rules():
    print("=" * 72)
    print("Q1  RULES / PROBLEM EXPOSURE")
    print("=" * 72)

    # 1a. The catalog Marco's planner can draw from (vegan-eligible recipes).
    by_type = model.where(Recipe.is_vegan == True).select(  # noqa: E712
        distinct(
            Recipe.meal_type.alias("meal_type"),
            aggs.count(Recipe).per(Recipe.meal_type).alias("recipes"),
        )
    ).to_df()
    n_vegan = model.select(aggs.count(Recipe).alias("n")).where(Recipe.is_vegan == True).to_df()  # noqa: E712
    n_gf = model.select(aggs.count(Recipe).alias("n")).where(Recipe.is_gluten_free == True).to_df()  # noqa: E712
    print("\nVegan-eligible recipes by meal type:")
    print(by_type.sort_values("meal_type").to_string(index=False))
    print(f"\nVegan recipes: {int(n_vegan['n'].iloc[0])}   "
          f"Gluten-free recipes: {int(n_gf['n'].iloc[0])}")

    # 1b. The naive "cheapest recipe per slot" day. Pull vegan recipes with the
    # nutrients that matter, then assemble the cheapest-per-slot day on the
    # display side (ranking + pick-N-per-group + summing across the picked set).
    cols = ["kcal", "protein_g", "carb_g", "fiber_g", "calcium_mg", "iron_mg",
            "b12_ug", "vitd_ug"]
    sel = [Recipe.recipe_id.alias("recipe_id"), Recipe.recipe_name.alias("name"),
           Recipe.meal_type.alias("meal_type"), Recipe.cost_usd.alias("cost_usd")]
    sel += [getattr(Recipe, c).alias(c) for c in cols]
    recipes = model.where(Recipe.is_vegan == True).select(*sel).to_df()  # noqa: E712

    picked = []
    for meal_type, n in SLOT_PLAN:
        picked.append(recipes[recipes.meal_type == meal_type].nsmallest(n, "cost_usd"))
    day = pd.concat(picked)
    totals = {c: day[c].sum() for c in cols}
    cost = day.cost_usd.sum()

    tgt = marco_targets().set_index("code")
    print("\nNaive cheapest-per-slot day (1 breakfast + 2 mains + 2 snacks):")
    print(day[["meal_type", "name", "cost_usd", "kcal", "protein_g", "b12_ug", "vitd_ug"]]
          .to_string(index=False))
    print(f"\n  Day cost: ${cost:.2f}")
    print("  Nutrition vs Marco's targets:")
    for c in cols:
        if c not in tgt.index:
            continue
        lo = tgt.loc[c, "min_amount"]
        got = totals[c]
        ok = "OK " if got >= lo else "MISS"
        print(f"    {c:12} {got:8.1f}  (floor {lo:7.1f})  {ok}")
    misses = [c for c in cols if c in tgt.index and totals[c] < tgt.loc[c, "min_amount"]]
    print(f"\n  -> Cheap (${cost:.2f}/day) but FAILS on: {', '.join(misses) or 'nothing'}.")
    print("     'You can't out-train a bad spreadsheet.'")
    return day, totals, cost


def _build_menu_problem(cost_attr="cost_usd"):
    """One-day menu MIP for Marco: pick recipes to fill the slots, meet every
    nutrient target, minimize cost. Returns the Problem (un-solved) and the
    decision-variable ref. Vegan-only via the solve_for scope."""
    problem = Problem(model, Float)
    problem.solve_for(
        Recipe.selected,
        where=[Recipe.is_vegan == True],  # noqa: E712  Marco is vegan
        lower=0, upper=1, type="bin",
    )
    # Slot structure: 1 breakfast, 2 mains (lunch+dinner), 1-2 snacks.
    problem.satisfy(model.require(
        aggs.sum(Recipe.selected).where(Recipe.meal_type == "breakfast") == 1), name=["slot_breakfast"])
    problem.satisfy(model.require(
        aggs.sum(Recipe.selected).where(Recipe.meal_type == "main") == 2), name=["slot_main"])
    problem.satisfy(model.require(
        aggs.sum(Recipe.selected).where(Recipe.meal_type == "snack") >= 1), name=["slot_snack_lo"])
    problem.satisfy(model.require(
        aggs.sum(Recipe.selected).where(Recipe.meal_type == "snack") <= 2), name=["slot_snack_hi"])
    # Nutrition: every one of Marco's targets must hold across the chosen day.
    for t in marco_targets().itertuples():
        col = t.code
        if t.direction in ("floor", "range"):
            problem.satisfy(model.require(
                aggs.sum(getattr(Recipe, col) * Recipe.selected) >= float(t.min_amount)),
                name=["floor", col])
        if t.direction in ("ceiling", "range") and pd.notna(t.max_amount):
            problem.satisfy(model.require(
                aggs.sum(getattr(Recipe, col) * Recipe.selected) <= float(t.max_amount)),
                name=["ceil", col])
    problem.minimize(aggs.sum(getattr(Recipe, cost_attr) * Recipe.selected))
    return problem


def _menu_df():
    """Read back the selected recipes after a solve (populate=True)."""
    return model.where(Recipe.selected > 0.5).select(
        Recipe.meal_type.alias("meal_type"),
        Recipe.recipe_name.alias("name"),
        Recipe.cost_usd.alias("cost_usd"),
        Recipe.cost_usd_shock.alias("cost_usd_shock"),
        Recipe.co2e_kg.alias("co2e_kg"),
        Recipe.kcal.alias("kcal"),
        Recipe.protein_g.alias("protein_g"),
        Recipe.carb_g.alias("carb_g"),
        Recipe.fiber_g.alias("fiber_g"),
        Recipe.calcium_mg.alias("calcium_mg"),
        Recipe.iron_mg.alias("iron_mg"),
        Recipe.b12_ug.alias("b12_ug"),
        Recipe.vitd_ug.alias("vitd_ug"),
    ).to_df()


def _show_menu(title, si, df):
    print(f"\n{title}")
    print(f"  status: {si.termination_status}   objective: {si.objective_value}")
    if len(df):
        df = df.sort_values("meal_type")
        print(df[["meal_type", "name", "cost_usd", "kcal", "protein_g", "b12_ug", "vitd_ug"]]
              .to_string(index=False))
        print(f"  day cost ${df.cost_usd.sum():.2f}   CO2 {df.co2e_kg.sum():.2f} kg   "
              f"kcal {df.kcal.sum():.0f}   protein {df.protein_g.sum():.0f} g   "
              f"vitD {df.vitd_ug.sum():.1f} ug   B12 {df.b12_ug.sum():.1f} ug")
    return df


def q2_prescriptive():
    print("\n" + "=" * 72)
    print("Q2  PRESCRIPTIVE: cheapest one-day menu that meets every target")
    print("=" * 72)
    problem = _build_menu_problem("cost_usd")
    problem.solve("highs")
    si = problem.solve_info()
    df = _show_menu("Optimal compliant menu for Marco:", si, _menu_df())
    return problem, si, df


def q3_persistent_rule(problem, base_df, co2_cap=3.0, wall_cap=2.5):
    """Operator adds a sustainability rule. Reuse Q2's SAME Problem (constraints
    accumulate; re-solving updates the decision values in place), so the rule
    persists on the model and propagates to the re-solve. Then tighten further
    to show the feasibility wall."""
    print("\n" + "=" * 72)
    print(f"Q3  PERSISTENT RULE: operator caps the diet at {co2_cap} kg CO2/day, re-solve")
    print("=" * 72)
    base_cost = base_df.cost_usd.sum() if len(base_df) else 0.0
    base_co2 = base_df.co2e_kg.sum() if len(base_df) else 0.0

    problem.satisfy(model.require(
        aggs.sum(Recipe.co2e_kg * Recipe.selected) <= float(co2_cap)), name=["co2_cap"])
    problem.solve("highs")
    si = problem.solve_info()
    df = _show_menu(f"Re-solved menu under the {co2_cap} kg CO2 cap:", si, _menu_df())
    if len(df):
        print(f"\n  baseline ${base_cost:.2f} / {base_co2:.2f} kg  ->  "
              f"capped ${df.cost_usd.sum():.2f} / {df.co2e_kg.sum():.2f} kg  "
              f"(cost delta ${df.cost_usd.sum() - base_cost:+.2f})")

    # Tighten further (same Problem, constraints accumulate) to hit the wall.
    problem.satisfy(model.require(
        aggs.sum(Recipe.co2e_kg * Recipe.selected) <= float(wall_cap)), name=["co2_cap_tight"])
    problem.solve("highs")
    status = problem.solve_info().termination_status
    print(f"\n  Tighten the cap to {wall_cap} kg: solver returns {status} "
          f"-> no compliant menu exists. The model proves it rather than faking one.")
    return problem


# ---------------------------------------------------------------------------
# Agent-facing helpers: zero-arg, no printing, return tidy DataFrames. Each is
# self-contained (own Problem + solve) so it runs cleanly in its own Cortex
# sproc invocation.
# ---------------------------------------------------------------------------
def naive_day_df():
    cols = ["kcal", "protein_g", "carb_g", "fiber_g", "calcium_mg", "iron_mg", "b12_ug", "vitd_ug"]
    sel = [Recipe.recipe_name.alias("recipe"), Recipe.meal_type.alias("meal_type"),
           Recipe.cost_usd.alias("cost_usd")]
    sel += [getattr(Recipe, c).alias(c) for c in cols]
    recipes = model.where(Recipe.is_vegan == True).select(*sel).to_df()  # noqa: E712
    picked = [recipes[recipes.meal_type == mt].nsmallest(n, "cost_usd") for mt, n in SLOT_PLAN]
    return pd.concat(picked)[["meal_type", "recipe", "cost_usd", "kcal", "protein_g", "b12_ug", "vitd_ug"]]


def optimal_menu_df():
    problem = _build_menu_problem("cost_usd")
    problem.solve("highs")
    return _menu_df()


def capped_menu_df(co2_cap=3.0):
    problem = _build_menu_problem("cost_usd")
    problem.solve("highs")
    problem.satisfy(model.require(
        aggs.sum(Recipe.co2e_kg * Recipe.selected) <= float(co2_cap)), name=["co2cap"])
    problem.solve("highs")
    return _menu_df()


def _composition_df():
    """recipe -> ingredient -> commodity for the currently-selected menu
    (Recipe.selected populated by the last solve), with each line's cost."""
    df = model.where(
        Recipe.selected > 0.5,
        RecipeIngredient.recipe(Recipe),
        RecipeIngredient.ingredient(Ingredient),
        Ingredient.commodity(Commodity),
    ).select(
        Recipe.recipe_name.alias("recipe"),
        RecipeIngredient.ingredient_name.alias("ingredient"),
        Commodity.commodity_name.alias("commodity"),
        RecipeIngredient.quantity_g.alias("grams"),
        Ingredient.cost_per_100g.alias("cost_per_100g"),
    ).to_df()
    df["cost_usd"] = (df.grams / 100.0 * df.cost_per_100g).round(4)
    return df


def optimal_diet_commodities_df():
    """The optimal menu's commodity exposure: $/day and grams per commodity,
    i.e. which commodities Marco's optimized diet depends on (the price-volatility
    surface). Builds + solves the optimal menu, then rolls the bill of materials
    up to commodities."""
    problem = _build_menu_problem("cost_usd")
    problem.solve("highs")
    comp = _composition_df()
    out = (comp.groupby("commodity")
           .agg(cost_usd=("cost_usd", "sum"), grams=("grams", "sum"),
                recipes=("recipe", "nunique"))
           .reset_index().sort_values("cost_usd", ascending=False))
    out["cost_usd"] = out.cost_usd.round(2)
    out["grams"] = out.grams.round(0)
    return out


def main():
    q1_rules()
    problem, si, df = q2_prescriptive()
    q3_persistent_rule(problem, df)


if __name__ == "__main__":
    main()
