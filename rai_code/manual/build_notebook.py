"""Build nestle_diet_demo.ipynb - the local demo notebook (Marco narrative +
the three questions + Plotly figures).

relationalai 1.9.0 guards its blocking sync API against a running event loop, so
inside a Jupyter kernel every query/solve must run in a worker thread (no loop
there). Model import/construction is fine on the main thread; only .to_df() /
.solve() need the thread. The notebook uses a tiny run() helper for that.

    .venv/bin/python rai_code/manual/build_notebook.py
    .venv/bin/jupyter nbconvert --execute --to notebook --inplace \
        --ExecutePreprocessor.timeout=1200 rai_code/manual/nestle_diet_demo.ipynb
"""
import os

import nbformat as nbf

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "nestle_diet_demo.ipynb")

md = nbf.v4.new_markdown_cell
code = nbf.v4.new_code_cell

cells = [
    md(
        "# Decision Intelligence for Nestle: optimizing Marco's diet\n\n"
        "Meet **Marco**. Marco runs a startup and runs marathons, so he optimizes "
        "everything: burn rate, runway, his 5K splits. His diet, though, he runs on "
        "vibes. Being an exec, he built a spreadsheet, and forty tabs later he had a "
        "beautiful dashboard that told him, in seven colors, exactly how under-fed he "
        "was.\n\n"
        "That is Business Intelligence: it told Marco his diet was a disaster. "
        "**Decision Intelligence just hands him dinner.**\n\n"
        "Marco is a vegan endurance athlete (~70 kg, ~3,000 kcal/day). This notebook "
        "runs three questions against a RelationalAI model over real nutrition data "
        "(USDA FoodData Central + Open Food Facts) and a synthesized recipe catalog."
    ),
    code(
        "import sys\n"
        f"sys.path.insert(0, {HERE!r})\n"
        "from concurrent.futures import ThreadPoolExecutor\n"
        "import plotly.graph_objects as go\n"
        "import demo_queries as dq\n"
        "from demo_queries import model, Recipe, _build_menu_problem, _menu_df\n"
        "from relationalai.semantics.std import aggregates as aggs\n"
        "\n"
        "# relationalai 1.9.0 blocks its sync API on a running event loop (Jupyter),\n"
        "# so run every query/solve in a worker thread that has no loop.\n"
        "_ex = ThreadPoolExecutor(max_workers=1)\n"
        "def run(fn, *a, **k):\n"
        "    return _ex.submit(fn, *a, **k).result()\n"
        "print('Loaded. Engines warm on first query.')"
    ),
    md(
        "## Q1 (Rules) - the problem: cheap looks fine until you check nutrition\n\n"
        "If Marco just grabs the cheapest vegan recipe per meal slot, the day is "
        "cheap and quietly malnourished."
    ),
    code(
        "day, totals, cost = run(dq.q1_rules)\n"
        "tgt = run(dq.marco_targets).set_index('code')\n"
        "nutr = ['kcal','protein_g','carb_g','fiber_g','calcium_mg','iron_mg','b12_ug','vitd_ug']\n"
        "labels, pct, colors = [], [], []\n"
        "for c in nutr:\n"
        "    if c in tgt.index and tgt.loc[c,'min_amount'] > 0:\n"
        "        p = 100.0 * totals[c] / tgt.loc[c,'min_amount']\n"
        "        labels.append(c); pct.append(round(p,0))\n"
        "        colors.append('#2ca02c' if p >= 100 else '#d62728')\n"
        "fig = go.Figure(go.Bar(x=labels, y=pct, marker_color=colors,\n"
        "                       text=[f'{p:.0f}%' for p in pct], textposition='outside'))\n"
        "fig.add_hline(y=100, line_dash='dash', annotation_text='target floor')\n"
        "fig.update_layout(title=f\"Q1: Marco's ${cost:.2f} naive day - % of each target met (red = miss)\",\n"
        "                  yaxis_title='% of floor', width=820, height=420)\n"
        "fig.show()"
    ),
    md(
        "Cheap (about $5/day) but it fails on calories, protein, carbs, B12, and "
        "vitamin D. You can't out-train a bad spreadsheet."
    ),
    md(
        "## Q2 + Q3 - the fix, then a persistent rule\n\n"
        "**Q2 (Prescriptive):** a mixed-integer program picks recipes to fill the slots "
        "(1 breakfast, 2 mains, 1-2 snacks), all vegan, meeting all 16 nutrient targets, "
        "at minimum cost. **Q3 (Persistent rule):** the operator adds a 3.0 kg/day "
        "carbon cap and the same model re-solves instantly. We solve both on one Problem "
        "(constraints accumulate) so the decision variable stays consistent."
    ),
    code(
        "def solve_q2_q3():\n"
        "    p = _build_menu_problem('cost_usd')\n"
        "    p.solve('highs')\n"
        "    base = _menu_df()\n"
        "    p.satisfy(model.require(aggs.sum(Recipe.co2e_kg * Recipe.selected) <= 3.0), name=['co2_cap'])\n"
        "    p.solve('highs')\n"
        "    capped = _menu_df()\n"
        "    return base, capped\n"
        "base, capped = run(solve_q2_q3)\n"
        "base_cost, base_co2 = base.cost_usd.sum(), base.co2e_kg.sum()\n"
        "cap_cost, cap_co2 = capped.cost_usd.sum(), capped.co2e_kg.sum()\n"
        "print(f'Q2 optimal: ${base_cost:.2f}/day, {base.kcal.sum():.0f} kcal, '\n"
        "      f'{base.protein_g.sum():.0f} g protein, vitD {base.vitd_ug.sum():.1f} ug, CO2 {base_co2:.2f} kg')\n"
        "print(f'Q3 under 3.0 kg CO2 cap: ${cap_cost:.2f}/day at {cap_co2:.2f} kg '\n"
        "      f'(+${cap_cost-base_cost:.2f} for {100*(1-cap_co2/base_co2):.0f}% less carbon)')"
    ),
    code(
        "m = base.sort_values('meal_type')\n"
        "fig = go.Figure(go.Table(\n"
        "    header=dict(values=['meal','recipe','$','kcal','protein g','B12 ug','vitD ug'],\n"
        "                fill_color='#13294b', font=dict(color='white')),\n"
        "    cells=dict(values=[m.meal_type, m.name, m.cost_usd.round(2), m.kcal.round(0),\n"
        "                       m.protein_g.round(0), m.b12_ug.round(1), m.vitd_ug.round(1)])))\n"
        "fig.update_layout(title=f'Q2: cheapest compliant day for Marco - ${base_cost:.2f}', width=900, height=320)\n"
        "fig.show()"
    ),
    code(
        "fig = go.Figure()\n"
        "fig.add_bar(name='cost $/day', x=['baseline','CO2-capped'], y=[round(base_cost,2), round(cap_cost,2)], marker_color='#1f77b4')\n"
        "fig.add_bar(name='CO2 kg/day', x=['baseline','CO2-capped'], y=[round(base_co2,2), round(cap_co2,2)], marker_color='#2ca02c')\n"
        "fig.update_layout(barmode='group',\n"
        "                  title=f'Q3: +${cap_cost-base_cost:.2f}/day buys {100*(1-cap_co2/base_co2):.0f}% less carbon (tighter caps go infeasible)',\n"
        "                  width=720, height=420)\n"
        "fig.show()"
    ),
    md(
        "## The takeaway\n\n"
        "Same data, same model, three questions: expose the problem, solve it, and let "
        "an operator add a rule the model instantly respects. BI showed Marco the problem "
        "in seven colors; Decision Intelligence handed him dinner, then a greener dinner "
        "when the rule changed. You can't out-train a bad spreadsheet."
    ),
]

nb = nbf.v4.new_notebook()
nb.cells = cells
nb.metadata = {
    "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
    "language_info": {"name": "python"},
}
with open(OUT, "w") as f:
    nbf.write(nb, f)
print(f"wrote {OUT} ({len(cells)} cells)")
