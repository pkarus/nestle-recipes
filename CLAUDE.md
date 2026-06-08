# CLAUDE.md - agent orientation for this RelationalAI demo

You are about to build (or work on) a RelationalAI demo against the sales-
engineering Snowflake account. This file is the entry point. Read it fully
before doing anything else.

## What this repo is

A blank slate cloned from `demo-agent-template`. The end state is a full
end-to-end RelationalAI demo following the shape of the two reference demos:

- `/Users/piotrkraus/rai-repos/supply_chain_demo` - 10 questions, LP + knapsack
- `/Users/piotrkraus/rai-repos/airplanes_demo` - 5 acts, MIP + persistent rule

The shape is described in [PIPELINE.md](PIPELINE.md). Both reference demos
live as sibling directories and are mapped file-by-file in [REFERENCES.md](REFERENCES.md).

## First action (always)

Check whether `BRIEF.md` exists at the repo root.

- **If `BRIEF.md` is missing or is still the unfilled template**, you must run
  the intake protocol in [INTAKE.md](INTAKE.md) before anything else. The
  intake is five questions delivered via the `AskUserQuestion` tool, then
  you write `BRIEF.md` from the answers. Do not skip this - every downstream
  phase depends on the brief.
- **If `BRIEF.md` is filled in**, read it, then read [PIPELINE.md](PIPELINE.md)
  and resume from the first phase whose exit criteria are not met. Do not
  ask the user where to resume - the file system tells you.

After the intake, proceed through [PIPELINE.md](PIPELINE.md) one phase at a
time. Each phase has explicit exit criteria. You do not move to the next
phase until the current phase is green. Use the `TaskCreate` / `TaskUpdate`
tools to track phase progress so the user can watch.

## RelationalAI skills (how they load, how to use them)

Two skill sources, in order of priority.

### 1. The `rai@RelationalAI` marketplace plugin (15 skills, auto-loaded)

The plugin is registered in [.claude/settings.json](.claude/settings.json) via:

```json
"extraKnownMarketplaces": {
  "RelationalAI": {"source": {"source": "github", "repo": "RelationalAI/rai-agent-skills"}}
},
"enabledPlugins": {"rai@RelationalAI": true}
```

Claude Code fetches the plugin from GitHub on session start and exposes 15
slash-skills automatically. Confirm they loaded by checking
`/Users/piotrkraus/.claude/plugins/` (cache) or by typing `/rai-` in chat
and seeing what completes. If nothing completes, the plugin failed to load -
run the user-facing command `/plugin install rai@RelationalAI` once, or
verify network access to github.com.

The full set: `rai-setup`, `rai-discovery`, `rai-build-starter-ontology`,
`rai-ontology-design`, `rai-pyrel-coding`, `rai-querying`, `rai-rules-authoring`,
`rai-graph-analysis`, `rai-prescriptive-problem-formulation`,
`rai-prescriptive-solver-management`, `rai-prescriptive-results-interpretation`,
`rai-cortex-integration`, `rai-health`, `rai-predictive-modeling` (early
access, GNN), `rai-predictive-training` (early access, GNN).

#### Discovery is the router. Always discover before implementing.

`rai-discovery` is the **translation layer** between user-facing questions
and reasoner implementations. It does two distinct jobs:

1. **Ideation pass.** Given an ontology + a domain, what questions can the
   data actually answer? Surfaces candidate questions across reasoner
   families that you may not have thought of.
2. **Classification + hints pass.** Given one candidate question, which
   reasoner family fits (rules / graph / heuristic / prescriptive /
   persistent rule / hybrid) and which sub-pattern within that family?
   Emits the implementation hints the next skill consumes.

Run discovery **twice** in the lifecycle:

- **Phase 1 (Position)** for the ideation pass - brainstorm candidates
  across families, then pick the 3 / 5 / 10 questions the demo will tell.
- **Phase 4 (Author queries)** for the classification + hints pass, once
  per question, immediately before invoking the implementation skill.
  Phase 1's classification was provisional; per-question discovery
  sharpens it and produces the hints the implementation skill needs.

Skipping discovery and jumping straight to a reasoner skill is the
fastest way to write the wrong query: a path question framed as a filter,
a heuristic written as if it were optimal, an assignment LP that should
have been a flow MIP. Discovery is cheap; the wrong skill costs an hour
of rework.

#### Implementation pipelines per reasoner family

Once discovery has classified a question, the implementation pipeline is
fixed per family. Invoke the skills in the order shown:

| Family | Pipeline (in order) | Notes |
|---|---|---|
| **Rules** (validation, classification, derivation, alerting, reconciliation) | `rai-rules-authoring` → `rai-querying` | rules-authoring creates new derived properties on the ontology; querying then reads and aggregates them. **Querying cannot create derived properties** - if you need a new tier / flag / segment, rules-authoring must run first |
| **Graph** (centrality, community, reachability, distance, similarity, components) | `rai-graph-analysis` → `rai-querying` | graph-analysis covers algorithm-family selection inside the skill (sub-discovery), graph construction from the ontology, parameter tuning, and result extraction; querying then reads results |
| **Graph** (path enumeration via `relationalai.semantics.std.paths`) | `rai-pathfinder` (project-local) → `rai-querying` | marketplace `rai-graph-analysis` does **not** cover path enumeration. Use the project-local skill copied from `supply_chain_demo/.claude/skills/rai-pathfinder/SKILL.md` - see "Project-local skills" below |
| **Heuristic** (deterministic scoring over the ontology) | `rai-querying` only | no separate authoring skill - heuristic scores ARE derived properties expressed through the query DSL |
| **Prescriptive** (LP / MIP) | `rai-prescriptive-problem-formulation` → `rai-prescriptive-solver-management` → `rai-prescriptive-results-interpretation` | strict linear pipeline. Formulation defines decision variables / constraints / objective; solver-management classifies the problem, selects the solver (HiGHS / Gurobi), validates, runs; results-interpretation extracts the solution, classifies status codes, explains why this is optimal |
| **Persistent rule** (operator adds a rule, ontology re-solves) | `rai-rules-authoring` → re-invoke the prescriptive pipeline above | the rule lives on the model; the "query" is a re-solve of the prescriptive problem under the new rule |
| **Predictive** (GNN, pre-GA - only if intake Q4 asked for it) | `rai-predictive-modeling` → `rai-predictive-training` | modeling covers entities / edges / features / Snowflake data loading; training covers fit / predict / evaluate |

Two rules that apply to **all** families:

1. **`rai-querying` is mandatory before any query.** Its SKILL.md says:
   *"Load this BEFORE writing any PyRel query, even your first one - your
   prior knowledge of the syntax is likely stale."* Treat that as binding.
2. **`rai-pyrel-coding` is the syntax fallback.** When a family skill
   leaves a syntax detail ambiguous (imports, type system, property
   declarations, references), invoke `rai-pyrel-coding` rather than
   guessing from training data.

#### Skill use by phase (the index)

| Phase | Skills (in order of invocation) |
|---|---|
| 1 - Position | `rai-discovery` (ideation pass) → `rai-ontology-design` |
| 2 - Data | *(no RAI skill - `snow` CLI; `rai-setup` to validate connection)* |
| 3 - Ontology | `rai-build-starter-ontology` → `rai-ontology-design` → `rai-pyrel-coding` for syntax |
| 4 - Queries | **per question:** `rai-discovery` (classify + hints) → matching family pipeline (see table above). `rai-querying` must be loaded before the first query is written |
| 5 - Local notebook | `rai-querying`, `rai-pyrel-coding` |
| 6 - Snowsight notebook | `rai-querying`, `rai-pyrel-coding`; `rai-setup` for stage upload |
| 7 - Cortex agent | `rai-cortex-integration`; `rai-querying` for the catalog |
| 8 - Gate + runbook | `rai-health`, `rai-setup` |
| 9 - Talk track + handoff | `rai-prescriptive-results-interpretation` (to explain solver output to the audience) |

Skills auto-load, but invoke them **explicitly** via the `Skill` tool when
you enter a phase or move on to a new question - that signals progress to
the user and ensures the skill's authoritative SKILL.md is in your context,
not a memory of it.

### 2. Project-local skills (the pre-GA-feature pattern)

For pre-GA features that aren't in the marketplace plugin yet, the reference
demos add a project-local skill at `.claude/skills/<skill-name>/SKILL.md`.
Claude Code picks these up automatically from the active project.

The canonical example is
`supply_chain_demo/.claude/skills/rai-pathfinder/SKILL.md` - a 417-line
authoritative reference for path queries via
`relationalai.semantics.std.paths` (codename "Pathfinder"). The marketplace
`/rai-graph-analysis` skill does NOT cover path enumeration; rai-pathfinder
does.

**Rule for your demo:** if Phase 4 has a question that uses
`relationalai.semantics.std.paths` (path enumeration, BOM walks,
multi-leg routing), copy that SKILL.md into your repo at
`.claude/skills/rai-pathfinder/SKILL.md` and load it before writing the
query. Same pattern for any future pre-GA feature - the agent invents a
local skill so the rules are written down once and the next session
inherits them.

## PyRel source-of-truth checkout

The PyRel repo is checked out locally at `/Users/piotrkraus/rai-repos/PyRel`.
Treat it as ground truth when the marketplace skills or public docs are
thin. The installed `relationalai` package in `.venv/` may lag the checkout -
run `uv pip show relationalai` and compare against `PyRel/pyproject.toml`.

| Path | What's in it |
|---|---|
| `PyRel/src/relationalai/semantics/` | Authoritative API surface. `std/paths` is the pathfinder source. `reasoners/prescriptive/` is the LP/MIP layer. |
| `PyRel/example/paths/` | Runnable path-query examples. **Read before authing a Phase 4 graph-path question.** |
| `PyRel/example/prescriptive/` | Runnable LP/MIP examples. Read before Phase 4 prescriptive. |
| `PyRel/example/cortex/` | Runnable Cortex agent examples. Read at Phase 7. |
| `PyRel/tests/end2end/` | Tests as documentation - each test is a small runnable PyRel program. Grep here for unfamiliar idioms. |
| `PyRel/tests/reasoners/` | Reasoner-specific tests. Same as above, narrower scope. |
| `PyRel/docs/` | Markdown documentation. Less polished than the public site but more current. |
| `PyRel/notes/` | Design notes and unreleased-feature discussion. |

Read access to `/Users/piotrkraus/rai-repos/PyRel/**` is pre-allowed in
[.claude/settings.json](.claude/settings.json). When you cite an API
signature in a comment or docstring, prefer pasting it from PyRel source
over your training data.

## Environment is pre-configured for autonomous runs

[.claude/settings.json](.claude/settings.json) pre-allows the commands you
need (`snow sql` scoped to `--role RAI_DEMO_*` for writes, `snow connection`,
`snow notebook`, `snow stage`, `uv`, `.venv/bin/python`, `.venv/bin/rai`,
`.venv/bin/jupyter`, git read + commit + plain push, shell scripts under
`data/`, `rai_code/`, `agent/`, and common file utilities) and pre-accepts
file edits inside this repo. You should be able to run for an hour without
an interrupt during normal phase execution.

**Things that will still ask** (intentionally):
- `git push --force` (any flavour), `git push --delete`, `git reset --hard`,
  `git checkout --force`. A plain `git push` to the existing upstream is allowed.
- `rm -rf` of anything
- `agent/deploy.py teardown`
- Any SQL that contains `DROP DATABASE`, `DROP SCHEMA`, `TRUNCATE`,
  `DELETE FROM`, or role-elevation patterns (`USE ROLE ACCOUNTADMIN`,
  `--role ACCOUNTADMIN`, etc.) - see the deny list in
  [.claude/settings.json](.claude/settings.json) for the exhaustive set

If something interrupts you that shouldn't, log it in `BRIEF.md` under
`### Autonomy issues` and continue - don't relitigate it with the user.

**Note on chained commands.** Claude Code's permission patterns match the
**full command string**, so `cd ~/rai-repos/bmw_demo && git status` does
**not** match `Bash(git status*)` and will prompt even though `git status`
on its own would not. Chaining with `&&` or `|` therefore *tightens*
allow-list matching, never loosens it (and the deny list uses substring
matching, so chained dangerous ops are still caught). When inspecting a
sibling repo, prefer `git -C ~/rai-repos/<repo> <subcommand>` over
`cd ~/rai-repos/<repo> && git <subcommand>` - the `-C` form keeps the
allow pattern simple. A handful of common chained read-only forms are
pre-allowed for convenience (see [.claude/settings.json](.claude/settings.json)),
but the `-C` form is the more general fix.

## Snowflake conventions (sales-engineering account)

- Connection profile: `rai` in `~/.snowflake/connections.toml`
- Account: `ajb85638`
- Warehouse: `RAI_XS` (auto-resume; cheap)
- **Role: `RAI_DEMO_<DOMAIN>` (created at intake)** - scoped to the demo DB only.
  Every `snow sql` call passes `--role RAI_DEMO_<DOMAIN>` explicitly. See
  the "Snowflake security harness" section below for the full model.
- Native App: RelationalAI is installed on this account
- PyRel auto-discovers credentials from `~/.snowflake/connections.toml` - no `raiconfig.yaml` needed
- Engine sizing:
  - **Start small during build.** Both engines default to `HIGHMEM_X64_XS`
    while the agent is iterating - dev work is mostly the agent thinking,
    not the engine computing, and idle time on a large engine burns
    credits for nothing. Most Phase 4 queries run fine on XS.
  - Logic engine name: `<domain>_logic_xs` (rules + graph + heuristic)
  - Prescriptive engine name: `<domain>_prescriptive_xs` (LP / MIP)
  - **Size up only when measured.** If a query times out or `/rai-health`
    reports memory pressure, bump to `S`. The reference demos ended up at
    `L` (logic) and `M` (prescriptive) for warm showtime performance with
    a 47-flight MIP - that's a final tune, not a starting point. Resize
    via `.venv/bin/rai reasoners alter <name> --size HIGHMEM_X64_S`.
  - The Phase 8 `prep_demo.py` gate records the resize decision in
    `BRIEF.md` so the next session knows why the engine is bigger.
  - Both are **named** engines so they persist across runs. Set
    auto-suspend short (5 min) so idle time doesn't accumulate cost:
    `.venv/bin/rai reasoners alter <name> --auto-suspend-mins 5`.

The exact `_build_config()` pattern that works in both local Python AND inside
a Snowsight notebook is in `supply_chain_demo/rai_code/manual/supply_chain.py`
- copy it.

## Snowflake modeling principles

The Snowflake schema is not just data storage - it is the **input to the
RelationalAI agentic modeler**, which reads database metadata to produce a
v0 ontology in the UI. Two principles follow.

### Denormalised, not 3NF

A real customer's Snowflake schema is wide and flat. Joins cost more than
scans on Snowflake; denormalisation is the native idiom. Going to 3NF makes
the demo look academic rather than realistic, and it gives the agentic
modeler fewer columns to attach concepts to.

- Aim for ~15-20 tables: a mix of dimensions / masters / junctions /
  events / time series. Use the supply_chain shape as the reference.
- Where 3NF would split, leave the redundancy. Repeat the customer name on
  every order line. Repeat the product category on every transaction.
- Junction tables stay - the agentic modeler turns them into concepts
  with relationships (the `SupplierProduct` / `BomEntry` / `Lane` pattern).
- Avoid pure `(id, name)` lookup tables - inline the name on the parent.

### Metadata is the contract with the agentic modeler

The v0 ontology the modeler produces is only as good as the metadata it
reads. Thin metadata = thin v0 = more enrichment work in Phase 3 that
better DDL at Phase 2 would have avoided. Every table that ships into the
demo DB MUST have:

| Metadata | What it teaches the modeler |
|---|---|
| Database `COMMENT` | One sentence: what the demo represents |
| Schema `COMMENT` | One sentence per schema: what lives in it |
| Table `COMMENT` | One sentence per table - the grain ("one row per X") and the real-world entity it represents |
| Column `COMMENT` | Every column: meaning, units, value range if bounded. Yes, every one |
| Primary keys | `CONSTRAINT pk_<table> PRIMARY KEY (...)`. Snowflake does not enforce but the modeler reads them as concept keys |
| Foreign keys | `CONSTRAINT fk_<table>_<ref> FOREIGN KEY (col) REFERENCES <ref>(col)`. Same: not enforced, but the modeler uses them to infer relationships between concepts |
| `NOT NULL` | On every column that's never null in the data. Tells the modeler "this is a required property" |
| `UNIQUE` | On natural keys that aren't the PK. Tells the modeler "this column identifies the entity" |
| Tags in `<DB>.META` | `DATA_DOMAIN`, `TABLE_ROLE` (dim / fact / junction / event), `GRAIN`, `DEMO_AREA` |

The agentic modeler is the first reader of your schema. Imagine a senior
data engineer who has never seen the domain reviewing your DDL: they
should be able to draft a correct v0 ontology from the DDL alone, with
no chat context. If they can't, your metadata is thin.

Pattern reference: `supply_chain_demo/annotate_and_doc.py` applies COMMENTs
and tags after the loader runs. Copy and extend it - if the original
pattern doesn't include PK/FK declarations, add them. This metadata is
required, not optional, and Phase 2 does not exit until it's complete.

## Snowflake security harness

The sales-engineering account is shared. The `rai` connection profile's
default role on this machine has broad privileges (likely `ACCOUNTADMIN`).
Running the agent unsupervised against that profile is unsafe. The harness
has two layers.

### Layer 1: a demo-specific role (the real defense)

At intake, the agent generates `data/00_bootstrap.sql` from
[BOOTSTRAP.template.sql](BOOTSTRAP.template.sql) and asks the user to
review and confirm. The bootstrap, run **once** as the rai profile's
default role:

1. Creates `RAI_DEMO_<DOMAIN>`, owned by SYSADMIN, granted to the current user.
2. Creates the demo database `<DEMO_DB>` and grants the demo role ALL on it
   (current + future schemas, tables, views, stages, procs, notebooks).
3. Grants the demo role `USAGE` + `OPERATE` on warehouse `RAI_XS`. No
   `MODIFY`, so the role cannot alter or drop the warehouse.
4. Grants the RAI Native App's `RAI_DEVELOPER` / `RAI_USER` application
   roles to the demo role (so PyRel works).
5. Grants minimal Snowflake Intelligence access for Cortex agent deploy.

After bootstrap, the demo role can do **anything inside the demo DB** and
nothing outside it. Snowflake itself enforces this. The agent cannot:

- DROP / ALTER any database, schema, table, or warehouse outside `<DEMO_DB>` (no grants).
- CREATE / DROP / ALTER any user (not an account-level role).
- Create programmatic access tokens (PATs) - requires `CREATE USER` or `ALTER USER`.
- GRANT or REVOKE any privilege (no `MANAGE GRANTS` on the role).
- Touch the share, network policies, integrations, or replication (no grants).

### Layer 2: Claude Code Bash deny list (belt and braces)

[.claude/settings.json](.claude/settings.json) blocks risky one-liners at
the shell layer, before Snowflake even sees them:

- `USE ROLE ACCOUNTADMIN` / `SECURITYADMIN` / `SYSADMIN` in `snow sql -q`
- `--role ACCOUNTADMIN` / `SECURITYADMIN` / `SYSADMIN` on the CLI
- `CREATE USER`, `ALTER USER`, `DROP USER`
- `PROGRAMMATIC ACCESS TOKEN` (PAT creation)
- `GRANT ... ON ACCOUNT`, `MANAGE GRANTS`, `IMPORTED PRIVILEGES`
- `CREATE WAREHOUSE`, `DROP WAREHOUSE`, `ALTER WAREHOUSE`
- `CREATE ROLE` / `DROP ROLE` outside the demo-role pattern (`RAI_DEMO_*`)

These would be denied by Snowflake anyway under the demo role, but the
shell-layer deny stops the agent from accidentally hand-typing them when
the user has temporarily switched into ACCOUNTADMIN for a one-off.

### Rules of the road for the agent

1. **Every `snow sql` call** explicitly passes `--role RAI_DEMO_<DOMAIN>`
   and `-c rai`. Never rely on the profile default. Example:
   ```
   snow sql --role RAI_DEMO_SUPPLY_CHAIN -c rai -q "SELECT 1"
   snow sql --role RAI_DEMO_SUPPLY_CHAIN -c rai -f data/02_schema.sql
   ```
2. **DDL files live under `data/` and are reviewable.** When you write
   bootstrap, schema, or grant SQL, save it to a file and run via
   `snow sql -f`, not via `-q`. The user reviews; that is the gate.
3. **If you think you need ACCOUNTADMIN**, you don't. Either the demo
   role is missing a grant (fix the bootstrap, ask the user to re-run it),
   or you're operating outside the demo's scope (you shouldn't be).
4. **Engines are named and managed by the demo role.** The reasoner
   resume/suspend calls go through `.venv/bin/rai reasoners ...` which
   uses the demo role via the profile + `--role` flag.
5. **At teardown**, the agent's `agent/deploy.py teardown` only un-registers
   the Cortex agent. To drop the demo DB itself, the user runs a
   one-line ACCOUNTADMIN `DROP DATABASE <DEMO_DB>; DROP ROLE
   RAI_DEMO_<DOMAIN>;` manually - the agent does not.

## Python environment

- Python 3.13, pinned in [.python-version](.python-version)
- Project venv at `.venv/` (create with `uv venv` if missing)
- Install packages with `uv add <pkg>` or `uv pip install <pkg>`
- Global CLIs (`snow`, `uv` itself) are not in the venv - they're system-wide
  via `uv tool install <pkg>` or pipx
- `relationalai` package (PyRel) - install with `uv add relationalai`
- `PyRel` source is checked out at `/Users/piotrkraus/rai-repos/PyRel` - use
  it as ground truth when public docs are thin

You will create `.venv/` early in Phase 2. Don't put it off.

## Repo layout (target - phase 1 starts empty)

```
.
├── CLAUDE.md                       # this file
├── INTAKE.md                       # the 5-question intake protocol
├── PIPELINE.md                     # the locked 9-phase pipeline
├── BRIEF.md                        # written after intake (does not exist yet)
├── BRIEF.template.md               # the brief format
├── BOOTSTRAP.template.sql          # the demo-role + DB bootstrap SQL (intake step 3)
├── REFERENCES.md                   # file-by-file pointers into the two demos
├── DEMO_QUESTION_CATALOG.md        # question archetypes per reasoner
├── RUNBOOK.template.html           # phase 8 deliverable
├── HANDOFF.template.md             # phase 9 deliverable
├── README.md                       # human-facing intro
├── .python-version
├── .gitignore
├── .claude/
│   └── settings.json               # marketplace + plugin + allowlists
├── rai_code/manual/                # ontology + queries + notebook live here
├── agent/                          # Cortex Agent deployment + queries catalog
├── data/                           # synthetic data generator + loader
└── build/                          # PyRel runtime cache (gitignored)
```

You will populate the empty directories as you move through phases. Do not
create files outside this shape without a reason - the reference demos
followed it strictly and it pays off in Phase 8 when you wire `prep_demo.py`.

## Definition of done (the non-negotiable rule)

A phase is not done until the artifact it produces **executes end-to-end
without errors against the live Snowflake demo DB**.

Execution is mostly local Python (your `.venv`, your machine) talking to
the live Snowflake account where the data lives - PyRel reads from
`PK_<DOMAIN>` over the network via the `rai` connection profile + demo
role. So "end-to-end" means the queries actually fire against Snowflake,
the engines actually execute, the agent actually answers - not mocked,
not dry-run, not unit-tested-in-isolation. Real data, real engines, real
answers. The exception is Phase 6, where the notebook itself executes
inside Snowsight (Snowflake-side).

| Phase | Where does the test run | What runs against Snowflake |
|---|---|---|
| **Phase 4** | Local Python | `demo_queries.py main()` fires every query against the live demo DB; engines compute server-side; DataFrames return to local |
| **Phase 5** | Local Jupyter | Same as Phase 4, wrapped in nbconvert. Cells green, figures render |
| **Phase 6** | Snowsight (in Snowflake) | The notebook executes server-side via `snow notebook execute`. Then manual re-run in the Snowsight UI to catch silent chart-render failures |
| **Phase 7** | Local CLI (chat round-trip) | `agent.deploy chat "..."` hits the deployed Cortex agent in Snowsight; the agent executes the PyRel query server-side and returns text + table |
| **Phase 8** | Local Python (the gate) | `prep_demo.py` is local but every check it runs hits Snowflake - SQL validation, engine resume, demo_queries.py, agent chat, notebook re-execute |

**Per-phase exit:**

- **Phase 4** smoke test (`.venv/bin/python rai_code/manual/demo_queries.py`)
  runs all queries top-to-bottom green. No tracebacks. No silent empty
  DataFrames where the anchored numbers say there should be rows.
- **Phase 5** local Jupyter notebook executes top-to-bottom via
  `.venv/bin/jupyter nbconvert --execute --to notebook --inplace`. Every
  cell green. Every figure renders.
- **Phase 6** Snowsight notebook executes top-to-bottom via
  `snow notebook execute <DB>.NOTEBOOKS.<DOMAIN>_DEMO`. Then **open it in
  the Snowsight UI and re-run all cells** (the CLI sometimes reports
  success while a chart silently fails to render).
- **Phase 7** Cortex agent answers each demo question via
  `.venv/bin/python -m agent.deploy chat "..."` correctly. Every question.
- **Phase 8** `prep_demo.py` finishes with all checks GREEN, cold start
  inside the budget.

If any of the above is yellow or red, **iterate until it's green**. Don't
move to the next phase. Don't paper over a failure with a comment. Don't
"come back to it later". The reference demos went through several
iterations to land green; yours will too.

When a notebook cell fails in Snowsight but works locally, the culprit is
usually one of: the first `pip install relationalai` cell failing because
the notebook has no PyPI external access integration attached (set
`EXTERNAL_ACCESS_INTEGRATIONS = (PYPI_ACCESS_INTEGRATION)` in the
`CREATE OR REPLACE NOTEBOOK` - see Phase 6); missing change tracking on a
table; a stale stage upload (re-run the `snow stage copy` step); the
`_build_config()` not detecting the Snowsight session (Snowsight needs
`ConfigFromActiveSession`, local needs `create_config()` - your Phase 3
`_build_config()` must handle both); or a Plotly figure width/height that
Jupyter accepts but Snowsight rejects. For headless `snow notebook execute`
specifically, the notebook also needs a `COMPUTE_POOL` set (interactive
open provisions one automatically; headless does not).

When a Cortex agent deploys and answers from the CLI but is missing from
the Snowflake Intelligence picker, it was deployed to `<DB>.RAI_AGENT`
instead of `SNOWFLAKE_INTELLIGENCE.AGENTS`. The picker only lists agents in
the SI schema. Set `agent_schema="SNOWFLAKE_INTELLIGENCE.AGENTS"` and
redeploy (see Phase 7).

Document any failure you fix in `BRIEF.md` under "Design decisions" so
the next session inherits the gotcha.

## Style and tone

- No em-dashes in generated documents - the user dislikes them.
- No emojis in code or docs.
- Plain prose in markdown - minimal headers, no bullet-spam.
- When you have a choice between asking the user and inferring from
  `BRIEF.md` + the references, infer. The intake was
  there so you would not have to interrupt later.
- Truth over approval. If a demo idea is weak (no graph traversal, no
  optimisation, no rule-cascade), say so in `BRIEF.md`
  and propose a stronger one.

## When you finish a phase

1. Update the `TaskCreate` task for that phase to `completed`.
2. Append a one-paragraph "Phase N done - X" note in `BRIEF.md` under
   `## Phase log`.
3. Immediately start the next phase. Do not ask "ready to proceed?".

## When you get stuck

1. Check `/rai-health` (engine state) and `/rai-setup` (connection state) first.
2. Grep the two reference demos for the symptom. Almost everything you'll
   hit they've already hit.
3. Grep the PyRel checkout. In order:
   - `PyRel/example/<reasoner>/` for a runnable answer
   - `PyRel/tests/end2end/<area>/` for a test that exercises the same path
   - `PyRel/src/relationalai/semantics/` for the actual API signature
4. If the issue is path-query specific, read
   `supply_chain_demo/.claude/skills/rai-pathfinder/SKILL.md` end-to-end -
   it captures every footgun the marketplace skills don't cover.
5. If still stuck after 15 minutes, write the question in `BRIEF.md` under
   `### Open questions` and proceed with the next independent task. Surface
   the open questions in your end-of-session summary.

## End of file. Start with INTAKE.md.
