"""Build RUNNING.html - a self-contained HTML brief/runbook for the Nestle /
Marco diet-optimization demo, with the result figures base64-embedded so the
file opens anywhere with no dependencies.

Run after build/generate_demo_figures.py:
    .venv/bin/python build/generate_demo_figures.py
    .venv/bin/python build/build_runbook.py
"""
import base64
import os

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
FIG = os.path.join(HERE, "figures")
OUT = os.path.join(REPO, "RUNNING.html")


def img(name, alt):
    path = os.path.join(FIG, f"{name}.png")
    if not os.path.exists(path):
        return f"<p><em>[missing figure: {name}.png - run generate_demo_figures.py]</em></p>"
    b64 = base64.b64encode(open(path, "rb").read()).decode()
    return f'<img alt="{alt}" src="data:image/png;base64,{b64}" style="max-width:100%;border:1px solid #e3e3e3;border-radius:6px;margin:8px 0;">'


CSS = """
body{font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;max-width:1040px;
margin:0 auto;padding:28px;color:#1a1a1a;line-height:1.5}
h1{color:#13294b;border-bottom:3px solid #13294b;padding-bottom:8px}
h2{color:#13294b;margin-top:34px}
.tag{display:inline-block;background:#13294b;color:#fff;border-radius:4px;padding:2px 8px;font-size:12px;margin-right:6px}
.joke{background:#f5f7fb;border-left:4px solid #13294b;padding:12px 16px;border-radius:4px;font-style:italic}
code,pre{background:#f5f5f5;border-radius:4px;font-family:SFMono-Regular,Consolas,monospace}
pre{padding:12px 14px;overflow:auto;font-size:13px}
table{border-collapse:collapse;margin:10px 0;font-size:14px}
th,td{border:1px solid #ddd;padding:6px 10px;text-align:left}
th{background:#13294b;color:#fff}
.kpi{font-size:15px;font-weight:600;color:#13294b}
"""

HTML = f"""<!doctype html><html><head><meta charset="utf-8">
<title>Nestle Decision Intelligence - Marco's diet</title><style>{CSS}</style></head><body>

<h1>Applications of Decision Intelligence in Nestle: optimizing Marco's diet</h1>
<p><span class="tag">RelationalAI</span><span class="tag">prescriptive</span>
<span class="tag">3 stages</span> From ingredient price volatility to profit protection,
preserving nutrition and sustainability.</p>

<div class="joke">Meet <b>Marco</b>. He runs a startup and runs marathons, so he optimizes
everything: burn rate, runway, his 5K splits. His diet, though, he runs on vibes. Being an
exec, he built a spreadsheet, and forty tabs later he had a beautiful dashboard that told
him, in seven colors, exactly how under-fed he was. That is Business Intelligence: it told
Marco his diet was a disaster. <b>Decision Intelligence just hands him dinner.</b></div>

<p>Marco is a vegan endurance athlete (~70 kg, ~3,000 kcal/day). One RelationalAI model over
real nutrition data (USDA FoodData Central, Open Food Facts) and a synthesized recipe catalog
backs three stages. Running gag: <em>you can't out-train a bad spreadsheet.</em></p>

<h2>Stage 1 - The problem: cheap looks fine until you check nutrition</h2>
<p>If Marco grabs the cheapest vegan recipe per slot, the day is cheap and quietly
malnourished. <span class="kpi">$5.01/day, but fails calories, protein, carbs, B12, vitamin D.</span></p>
{img("q1_nutrient_gap", "problem: nutrient gap")}

<h2>Stage 2 - The solution: cheapest menu meeting every target</h2>
<p>An optimization model picks recipes for the slots (1 breakfast, 2 mains, 1-2 snacks),
all vegan, meeting all 16 nutrient targets, at minimum cost. The optimizer pulls in a
fortified shake and cereal precisely to clear the B12 and vitamin-D floors.
<span class="kpi">OPTIMAL: $7.06/day - about $2 more than naive buys full compliance.</span></p>
{img("q2_naive_vs_optimal", "naive vs optimal nutrient achievement")}

<h3>What Marco actually eats, and which commodities it uses</h3>
<p>The optimal menu, traced through its bill of materials: recipe -> ingredient -> commodity.
The green nodes are the commodities the diet is exposed to (the price-volatility surface).</p>
{img("q2_diet_graph", "optimal diet recipe-ingredient-commodity graph")}

<h2>Stage 3 - Adaptation: the model absorbs a new rule</h2>
<p>Add a 3.0 kg/day carbon cap; the same model re-solves instantly.
<span class="kpi">$7.17/day at 2.92 kg - +$0.11 for ~33% less carbon.</span> Tighten the cap
to 2.5 kg and the solver returns INFEASIBLE: it proves no compliant menu exists rather than
faking one.</p>
{img("q3_cost_vs_co2", "adaptation: cost vs CO2")}
<h3>The carbon-capped diet graph</h3>
{img("q3_diet_graph", "capped diet recipe-ingredient-commodity graph")}

<h2>The price-volatility hook and commodity exposure</h2>
<p>Cocoa and coffee swing 40-60% within a year (Nestle's own named inflationary inputs).
Knowing which commodities a diet/recipe depends on is what makes re-optimization valuable.</p>
{img("commodity_volatility", "commodity price index")}
{img("commodity_exposure", "commodity cost exposure optimal vs capped")}

<h2>How to run</h2>
<pre>.venv/bin/python prep_demo.py                          # readiness check
.venv/bin/python rai_code/manual/demo_queries.py      # the three stages
.venv/bin/jupyter lab rai_code/manual/nestle_diet_demo.ipynb   # local notebook
.venv/bin/python -m agent.deploy chat "Build Marco the cheapest compliant menu"
.venv/bin/python -m agent.deploy chat "What commodities does Marco's diet depend on?"</pre>

<p style="color:#777;font-size:12px;margin-top:30px">Data: USDA FoodData Central (CC0),
Open Food Facts (ODbL), sustainability coefficients from Poore &amp; Nemecek (2018, Science)
processed by Our World in Data (CC BY 4.0); recipes, prices, and persona targets synthesized.
Generated from build/figures/ by build_runbook.py.</p>
</body></html>"""

with open(OUT, "w") as f:
    f.write(HTML)
print(f"wrote {OUT} ({len(HTML)//1024} KB)")
