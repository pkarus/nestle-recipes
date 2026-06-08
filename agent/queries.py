"""Pre-canned demo queries exposed to the Cortex agent via QueryCatalog.

Each function is module-level, takes zero arguments, and returns a pandas
DataFrame. Docstrings are what the agent's LLM reads to pick the right tool,
so they describe Marco's question in business language.
"""
from rai_code.manual import demo_queries as dq


def marco_naive_cheapest_day():
    """Marco's naive 'cheapest recipe per slot' day for a vegan endurance
    athlete: 1 breakfast, 2 mains, 2 snacks chosen purely by lowest cost. It is
    cheap (about $5/day) but FAILS his nutrition targets - short on calories,
    protein, carbohydrate, vitamin B12, and vitamin D. Use this to show why
    naive, gut-feel meal planning does not work. Columns: meal_type, recipe,
    cost_usd, kcal, protein_g, b12_ug, vitd_ug."""
    return dq.naive_day_df()


def marco_optimal_menu():
    """Marco's cheapest one-day menu that meets EVERY one of his 16 nutrition
    targets (vegan endurance athlete, ~3000 kcal). This is the optimized answer,
    about $7/day, that fixes the gaps in the naive day - the optimizer pulls in a
    fortified shake and cereal to clear the B12 and vitamin-D floors. Columns:
    meal_type, name, cost_usd, co2e_kg, kcal, protein_g, b12_ug, vitd_ug."""
    return dq.optimal_menu_df()


def marco_menu_under_carbon_cap():
    """Marco's cheapest compliant menu re-solved under a sustainability rule: a
    3.0 kg CO2e per day carbon cap. Still meets every nutrition target, at a
    slightly higher cost for much lower carbon. Use this to show the model
    respecting an operator-added rule. Columns: meal_type, name, cost_usd,
    co2e_kg, kcal, protein_g, b12_ug, vitd_ug."""
    return dq.capped_menu_df(3.0)


def marco_diet_commodities():
    """Which commodities Marco's optimal menu depends on, and how much: cost per
    day and grams per commodity, rolled up from the recipe bill of materials
    (recipe -> ingredient -> commodity). Use this to answer 'what commodities /
    ingredients does the diet use' and to show price-volatility exposure (e.g.
    cocoa, coffee, wheat, soy). Columns: commodity, cost_usd, grams, recipes."""
    return dq.optimal_diet_commodities_df()
