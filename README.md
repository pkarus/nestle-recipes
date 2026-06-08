# RelationalAI demo template

Clone this repo, point Claude Code at it, and Claude will run an interactive
intake (5 questions), then build a full end-to-end RelationalAI demo
against the sales-engineering Snowflake account - synthetic data, ontology,
queries, local notebook, Snowsight notebook, Cortex Agent, runbook, and a
demo-day pre-flight gate - without further interruption.

## Use

```bash
git clone <this-template> my-new-demo
cd my-new-demo
# open in Claude Code (VSCode extension or terminal)
# tell Claude:  "Start a new RelationalAI demo."
```

That's it. Claude reads [CLAUDE.md](CLAUDE.md), runs [INTAKE.md](INTAKE.md),
writes a `BRIEF.md`, and then proceeds through the locked
[PIPELINE.md](PIPELINE.md) phase by phase. The two existing reference demos
([supply_chain_demo](../supply_chain_demo) and
[airplanes_demo](../airplanes_demo)) are wired up by absolute path in
[REFERENCES.md](REFERENCES.md) - Claude copies the patterns, not the content.

## What you get

By the end of a full run, your repo will contain:

- `rai_code/manual/<domain>.py` - the PyRel ontology (full concepts, properties, derived relationships)
- `rai_code/manual/demo_queries.py` - the demo questions answered as PyRel queries (rules / graph / heuristic / prescriptive / persistent rule)
- `rai_code/manual/<domain>_demo.ipynb` - local Jupyter notebook with Plotly visualisations
- A Snowsight notebook of the same shape, uploaded to the SE account
- `agent/deploy.py` + `agent/queries.py` - Snowflake Intelligence (Cortex) agent deployment with chart-hint wrappers
- `data/` - synthetic data generator + Snowflake loader (idempotent)
- `prep_demo.py` - the 10-minute pre-flight gate that verifies the whole stack before a live demo
- `RUNNING.html` - speaker runbook with embedded result figures
- `<DOMAIN>_TALK_TRACK.md` + `SNOWSIGHT_DEMO.md` - local notebook and SI talk tracks
- `HANDOFF_BRIEFING.md` - context dump for the next human or agent
- `DEMO_QUESTIONS.md` + `DATA_DICTIONARY.md`

## Why a template

The two existing demos converged on the same shape after weeks of trial and
error. This template captures the convergence so the next demo lands in a
day, not a week.

## What's pre-tuned

- The RelationalAI skills plugin (`rai@RelationalAI`) is pre-registered in
  [.claude/settings.json](.claude/settings.json), so on first session start
  Claude has all 15 `/rai-*` skills available.
- Bash command allowlists for `snow`, `uv`, `.venv/bin/python`, `.venv/bin/rai`,
  and read-only git are pre-approved so Claude won't interrupt mid-run.
- File edits in the project are auto-accepted (`defaultMode: acceptEdits`).
- Destructive operations (database drop, agent teardown, `git push`,
  `git reset --hard`, `rm -rf`) are denied - Claude has to ask.

## Reference demos

- [supply_chain_demo](../supply_chain_demo) - 10-question supply chain demo
  with min-cost LP and 0/1 knapsack
- [airplanes_demo](../airplanes_demo) - 5-act EHAM A-CDM demo with rules,
  graph, heuristic, MIP, and persistent rule

Both live as sibling directories. The template's [REFERENCES.md](REFERENCES.md)
points at specific files in each.

## Requirements

- A connection profile `rai` in `~/.snowflake/connections.toml` pointing at
  the sales-engineering account (account `ajb85638`, role `RAI_DEVELOPER` or
  `ACCOUNTADMIN`, warehouse `RAI_XS`)
- Python 3.13 (`.python-version` pinned)
- `uv` (`pipx install uv` if missing)
- `snow` CLI (`uv tool install snowflake-cli` if missing)
- The RelationalAI Native App installed on the SE Snowflake account (it is)

## Notes

The template is reference-only - there are no Python stubs to delete. Claude
re-derives every file from the references each demo, parameterised on
`BRIEF.md`.
