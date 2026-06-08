"""Build nestle_diet_demo_snowsight.ipynb from the local notebook.

The Snowsight version differs from the local one in two ways:
  1. A first code cell that `pip install relationalai` (+ plotly) - Snowsight's
     container runtime needs the package installed at run time.
  2. The setup cell adds the notebook's own stage folder to sys.path (the .py
     files are staged alongside the notebook), instead of a local absolute path.

_build_config() already detects the active Snowpark session in Snowsight
(ConfigFromActiveSession), so no connection config is needed there. The worker-
thread run() helper still applies (Snowsight's kernel also runs an event loop).

    .venv/bin/python rai_code/manual/build_snowsight_notebook.py
"""
import os

import nbformat as nbf

HERE = os.path.dirname(os.path.abspath(__file__))
LOCAL = os.path.join(HERE, "nestle_diet_demo.ipynb")
OUT = os.path.join(HERE, "nestle_diet_demo_snowsight.ipynb")

nb = nbf.read(LOCAL, as_version=4)

# 1. Prepend a pip-install cell (after the title markdown cell).
pip_cell = nbf.v4.new_code_cell(
    "# Snowsight: install RelationalAI (PyRel) and Plotly into the notebook's\n"
    "# container runtime. Requires the PyPI external access integration on the\n"
    "# notebook (set in CREATE NOTEBOOK), or add them via the Packages panel.\n"
    "import sys\n"
    "!pip install relationalai==1.9.0 plotly"
)
# insert after the first (title) markdown cell
nb.cells.insert(1, pip_cell)

# 2. Rewrite the setup cell's sys.path line: in Snowsight the staged .py files
# sit next to the notebook (current working directory), not a local abs path.
for c in nb.cells:
    if c.cell_type == "code" and "sys.path.insert(0," in c.source and "ThreadPoolExecutor" in c.source:
        lines = c.source.splitlines()
        new = []
        for ln in lines:
            if ln.strip().startswith("sys.path.insert(0,"):
                new.append("import os")
                new.append("sys.path.insert(0, os.getcwd())  # staged .py files sit beside the notebook")
            else:
                new.append(ln)
        c.source = "\n".join(new)
        break

nbf.write(nb, open(OUT, "w"))
print(f"wrote {OUT} ({len(nb.cells)} cells, pip-install cell + cwd sys.path)")
