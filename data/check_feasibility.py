"""
check_feasibility.py - local PuLP model of the demo's Q2 menu MIP, used to (a)
confirm the generated data admits a feasible compliant menu and (b) compute the
anchored numbers the talk track quotes. This mirrors what PyRel will solve in
Phase 4; it is NOT shipped to Snowflake.

Menu: exactly 1 breakfast + 2 mains (lunch+dinner) + 1-2 snacks, all vegan,
minimize total cost s.t. every nutrient target (floor/ceiling/range) is met.

Run: .venv/bin/python data/check_feasibility.py [--co2cap KG] [--shock]
"""
import argparse
import os

import pandas as pd
import pulp

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")


def load():
    rec = pd.read_csv(os.path.join(OUT, "recipe.csv"))
    tgt = pd.read_csv(os.path.join(OUT, "persona_nutrient_target.csv"))
    slots = pd.read_csv(os.path.join(OUT, "meal_slot.csv"))
    return rec, tgt, slots


def solve(rec, tgt, slots, cost_col="cost_usd", co2_cap=None, max_diet_min=None,
          require_gf=False, verbose=True):
    pool = rec[rec.is_vegan]
    if require_gf:
        pool = pool[pool.is_gluten_free]
    pool = pool.reset_index(drop=True)
    prob = pulp.LpProblem("menu", pulp.LpMinimize)
    y = {int(r.recipe_id): pulp.LpVariable(f"y_{int(r.recipe_id)}", cat="Binary")
         for r in pool.itertuples()}
    rid_to = {int(r.recipe_id): r for r in pool.itertuples()}

    # objective: total cost
    prob += pulp.lpSum(y[i] * rid_to[i].__getattribute__(cost_col) for i in y)

    # slot counts by meal_type
    for s in slots.itertuples():
        ids = [i for i in y if rid_to[i].meal_type == s.eligible_meal_type]
        cnt = pulp.lpSum(y[i] for i in ids)
        if s.slot_name in ("Lunch", "Dinner"):
            continue  # handled jointly below
        prob += cnt >= s.min_recipes
        prob += cnt <= s.max_recipes
    # mains: lunch + dinner => exactly 2 distinct mains
    main_ids = [i for i in y if rid_to[i].meal_type == "main"]
    prob += pulp.lpSum(y[i] for i in main_ids) == 2

    # nutrient constraints
    for t in tgt.itertuples():
        col = t.nutrient_code
        expr = pulp.lpSum(y[i] * getattr(rid_to[i], col) for i in y)
        if t.direction in ("floor", "range") and pd.notna(t.min_amount):
            prob += expr >= t.min_amount
        if t.direction in ("ceiling", "range") and pd.notna(t.max_amount):
            prob += expr <= t.max_amount

    if co2_cap is not None:
        prob += pulp.lpSum(y[i] * rid_to[i].co2e_kg for i in y) <= co2_cap
    if max_diet_min is not None:
        prob += pulp.lpSum(y[i] * rid_to[i].prep_time_min for i in y) <= max_diet_min

    status = prob.solve(pulp.PULP_CBC_CMD(msg=0))
    st = pulp.LpStatus[status]
    chosen = [rid_to[i] for i in y if y[i].value() and y[i].value() > 0.5]
    if verbose:
        print(f"status={st}  cost_col={cost_col}  co2_cap={co2_cap}  gf={require_gf}")
        if chosen:
            tot = {c: sum(getattr(r, c) for r in chosen) for c in
                   ["kcal", "protein_g", "carb_g", "fat_g", "fiber_g", "calcium_mg",
                    "iron_mg", "b12_ug", "vitd_ug", "sodium_mg", "satfat_g"]}
            cost = sum(getattr(r, cost_col) for r in chosen)
            co2 = sum(r.co2e_kg for r in chosen)
            print(f"  cost=${cost:.2f}  co2={co2:.2f}kg  kcal={tot['kcal']:.0f}  "
                  f"protein={tot['protein_g']:.0f}g  carb={tot['carb_g']:.0f}g  "
                  f"fiber={tot['fiber_g']:.0f}g  calcium={tot['calcium_mg']:.0f}mg  "
                  f"iron={tot['iron_mg']:.1f}mg  B12={tot['b12_ug']:.1f}ug  vitD={tot['vitd_ug']:.1f}ug")
            for r in sorted(chosen, key=lambda r: r.meal_type):
                print(f"    [{r.meal_type:9}] {r.recipe_name:48} ${getattr(r, cost_col):.2f}  {r.kcal:.0f}kcal  {r.protein_g:.0f}gP")
    return st, chosen


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--co2cap", type=float, default=None)
    ap.add_argument("--shock", action="store_true")
    ap.add_argument("--gf", action="store_true")
    args = ap.parse_args()
    rec, tgt, slots = load()
    print(f"pool: {len(rec)} recipes")
    solve(rec, tgt, slots,
          cost_col="cost_usd_shock" if args.shock else "cost_usd",
          co2_cap=args.co2cap, require_gf=args.gf)


if __name__ == "__main__":
    main()
