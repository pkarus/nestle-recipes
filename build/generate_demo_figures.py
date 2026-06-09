"""Generate the Nestle / Marco demo result visualizations.

Runs the three questions against live Snowflake and writes, to build/figures/:
  q1_nutrient_gap.png        - the naive day's % of each target (red = miss)
  q2_naive_vs_optimal.png    - nutrient achievement: naive vs optimal
  q3_cost_vs_co2.png         - cost and CO2: baseline vs carbon-capped
  commodity_volatility.png   - cocoa/coffee/wheat price index (the volatility hook)
  q2_diet_graph.png          - optimal menu: recipe -> ingredient -> commodity Sankey
  q3_diet_graph.png          - carbon-capped menu: same Sankey
  commodity_exposure.png     - $ exposure by commodity: optimal vs capped
  figures.html               - all of the above as one interactive Plotly page

This is a plain script (no Jupyter event loop), so RAI calls run directly.

    .venv/bin/python build/generate_demo_figures.py
"""
import os
import sys

import plotly.graph_objects as go
import plotly.io as pio

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
FIG = os.path.join(HERE, "figures")
os.makedirs(FIG, exist_ok=True)
sys.path.insert(0, os.path.join(REPO, "rai_code", "manual"))

import demo_queries as dq  # noqa: E402
from demo_queries import model, Recipe, _build_menu_problem, _menu_df  # noqa: E402
from nestle_diet import (  # noqa: E402
    RecipeIngredient, Ingredient, Commodity, CommodityPrice,
)
from relationalai.semantics.std import aggregates as aggs  # noqa: E402

GREEN, RED, BLUE = "#2ca02c", "#d62728", "#1f77b4"
NUTR = ["kcal", "protein_g", "carb_g", "fiber_g", "calcium_mg", "iron_mg", "b12_ug", "vitd_ug"]


def composition_df():
    """For the currently-selected menu (Recipe.selected populated by the last
    solve), the recipe -> ingredient -> commodity breakdown with cost share."""
    df = model.where(
        Recipe.selected > 0.5,
        RecipeIngredient.recipe(Recipe),
        RecipeIngredient.ingredient(Ingredient),
        Ingredient.commodity(Commodity),
    ).select(
        Recipe.recipe_name.alias("recipe"),
        Ingredient.ingredient_name.alias("ingredient"),
        Commodity.commodity_name.alias("commodity"),
        RecipeIngredient.quantity_g.alias("grams"),
        Ingredient.cost_per_100g.alias("cost_per_100g"),
    ).to_df()
    df["cost"] = df.grams / 100.0 * df.cost_per_100g
    return df


def sankey(df, title):
    """recipe -> ingredient -> commodity, flows weighted by cost contribution."""
    recipes = sorted(df.recipe.unique())
    ings = sorted(df.ingredient.unique())
    coms = sorted(df.commodity.unique())
    com_label = {c: f"{c} (commodity)" for c in coms}  # avoid name collisions
    nodes = recipes + ings + [com_label[c] for c in coms]
    idx = {n: i for i, n in enumerate(nodes)}
    s, t, v = [], [], []
    ri = df.groupby(["recipe", "ingredient"])["cost"].sum().reset_index()
    for r in ri.itertuples():
        s.append(idx[r.recipe]); t.append(idx[r.ingredient]); v.append(round(r.cost, 4))
    ic = df.groupby(["ingredient", "commodity"])["cost"].sum().reset_index()
    for r in ic.itertuples():
        s.append(idx[r.ingredient]); t.append(idx[com_label[r.commodity]]); v.append(round(r.cost, 4))
    n = len(recipes)
    colors = (["#13294b"] * len(recipes) + ["#1f77b4"] * len(ings) + ["#2ca02c"] * len(coms))
    fig = go.Figure(go.Sankey(
        node=dict(label=nodes, color=colors, pad=12, thickness=14),
        link=dict(source=s, target=t, value=v),
    ))
    fig.update_layout(title=title + "  (navy = recipe, blue = ingredient, green = commodity; flow = $ cost)",
                      template="plotly_white", width=1000, height=620, font_size=11)
    return fig


def pct(tot):
    return {c: 100.0 * tot[c] / tgt.loc[c, "min_amount"]
            for c in NUTR if c in tgt.index and tgt.loc[c, "min_amount"] > 0}


print("Q1: naive day ...")
day, totals, cost = dq.q1_rules()
tgt = dq.marco_targets().set_index("code")

print("Q2 + Q3: optimal menu, capture composition, carbon-capped re-solve ...")
p = _build_menu_problem("cost_usd")
p.solve("highs")
base = _menu_df()
opt_totals = {c: float(base[c].sum()) for c in NUTR}
base_cost, base_co2 = float(base.cost_usd.sum()), float(base.co2e_kg.sum())
opt_comp = composition_df()
p.satisfy(model.require(aggs.sum(Recipe.co2e_kg * Recipe.selected) <= 3.0), name=["co2_cap"])
p.solve("highs")
capped = _menu_df()
cap_cost, cap_co2 = float(capped.cost_usd.sum()), float(capped.co2e_kg.sum())
cap_comp = composition_df()

print("commodity price history ...")
prices = model.where(
    CommodityPrice.commodity(Commodity),
    Commodity.commodity_id.in_(["cocoa", "coffee", "wheat"]),
).select(
    Commodity.commodity_id.alias("commodity"),
    CommodityPrice.price_month.alias("month"),
    CommodityPrice.price_index.alias("idx"),
).to_df().sort_values(["commodity", "month"])

figs = []

np_, op = pct(totals), pct(opt_totals)
f1 = go.Figure(go.Bar(x=list(np_), y=[round(v) for v in np_.values()],
                      marker_color=[GREEN if v >= 100 else RED for v in np_.values()],
                      text=[f"{v:.0f}%" for v in np_.values()], textposition="outside"))
f1.add_hline(y=100, line_dash="dash", annotation_text="target floor")
f1.update_layout(title=f"The problem: Marco's ${cost:.2f} naive day - % of each nutrient target met (red = miss)",
                 yaxis_title="% of floor", template="plotly_white", width=860, height=440)
figs.append(("q1_nutrient_gap", f1))

keys = list(op)
f2 = go.Figure()
f2.add_bar(name=f"naive (${cost:.2f})", x=keys, y=[round(np_[k]) for k in keys], marker_color=RED)
f2.add_bar(name=f"optimal (${base_cost:.2f})", x=keys, y=[round(op[k]) for k in keys], marker_color=GREEN)
f2.add_hline(y=100, line_dash="dash", annotation_text="target floor")
f2.update_layout(barmode="group", title="The solution: nutrient targets met - naive vs optimized menu",
                 yaxis_title="% of floor", template="plotly_white", width=900, height=440)
figs.append(("q2_naive_vs_optimal", f2))

f3 = go.Figure()
f3.add_bar(name="cost $/day", x=["baseline", "CO2-capped"], y=[round(base_cost, 2), round(cap_cost, 2)], marker_color=BLUE)
f3.add_bar(name="CO2 kg/day", x=["baseline", "CO2-capped"], y=[round(base_co2, 2), round(cap_co2, 2)], marker_color=GREEN)
f3.update_layout(barmode="group",
                 title=f"Adaptation: +${cap_cost-base_cost:.2f}/day buys {100*(1-cap_co2/base_co2):.0f}% less carbon (tighter caps go infeasible)",
                 template="plotly_white", width=720, height=440)
figs.append(("q3_cost_vs_co2", f3))

f4 = go.Figure()
for cid, sub in prices.groupby("commodity"):
    f4.add_scatter(x=sub.month, y=sub.idx, mode="lines+markers", name=cid)
f4.update_layout(title="Why re-optimize: commodity price index (1.00 = Jan 2025) - cocoa and coffee swing hard",
                 yaxis_title="price index", template="plotly_white", width=860, height=420)
figs.append(("commodity_volatility", f4))

figs.append(("q2_diet_graph", sankey(opt_comp, f"The solution - what Marco eats (${base_cost:.2f}/day)")))
figs.append(("q3_diet_graph", sankey(cap_comp, f"Adaptation - carbon-capped menu - what Marco eats (${cap_cost:.2f}/day, {cap_co2:.2f} kg CO2)")))

# Commodity exposure: $ per commodity, optimal vs capped
ex_opt = opt_comp.groupby("commodity")["cost"].sum()
ex_cap = cap_comp.groupby("commodity")["cost"].sum()
allc = sorted(set(ex_opt.index) | set(ex_cap.index), key=lambda c: -(ex_opt.get(c, 0) + ex_cap.get(c, 0)))
f7 = go.Figure()
f7.add_bar(name="optimal", x=allc, y=[round(ex_opt.get(c, 0), 2) for c in allc], marker_color=BLUE)
f7.add_bar(name="carbon-capped", x=allc, y=[round(ex_cap.get(c, 0), 2) for c in allc], marker_color=GREEN)
f7.update_layout(barmode="group", title="Commodity cost exposure of Marco's diet ($/day) - optimal vs carbon-capped",
                 yaxis_title="$/day", template="plotly_white", width=960, height=460)
figs.append(("commodity_exposure", f7))

for name, fig in figs:
    fig.write_image(os.path.join(FIG, f"{name}.png"), scale=2)
    print("  wrote", f"{name}.png")

html = "<html><head><meta charset='utf-8'><title>Marco demo figures</title></head><body>"
html += "<h1>Nestle / Marco diet-optimization - result figures</h1>"
for _, fig in figs:
    html += pio.to_html(fig, include_plotlyjs="cdn", full_html=False)
html += "</body></html>"
with open(os.path.join(FIG, "figures.html"), "w") as f:
    f.write(html)
print("wrote figures.html")
print(f"\nNumbers: naive ${cost:.2f}, optimal ${base_cost:.2f}/{base_co2:.2f}kg, capped ${cap_cost:.2f}/{cap_co2:.2f}kg")
print(f"optimal diet touches {opt_comp.commodity.nunique()} commodities; "
      f"top exposure: {ex_opt.sort_values(ascending=False).head(3).round(2).to_dict()}")
