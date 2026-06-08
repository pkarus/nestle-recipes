# HANDOFF_BRIEFING.md

> Written at Phase 9. Goal: a fresh reader (next human, next agent) can
> understand why this demo is the way it is, what's load-bearing, and
> where to look when things break - without asking the person who built it.
>
> Model after `/Users/piotrkraus/rai-repos/airplanes_demo/HANDOFF_BRIEFING.md`.

## TL;DR

_{{DOMAIN}} demo. {{N}} questions / acts. Runtime ~{{RUNTIME}} on the SE
Snowflake account. Defensible to {{AUDIENCE}}. Built in {{BUILD_TIME}}._

## What's been done

- {{N}}-question talk track written ({{TALK_TRACK_FILE}})
- Synthetic dataset generated with seed=42 ({{ROW_COUNT}} rows across
  {{TABLE_COUNT}} tables)
- Validation SQL reproduces all anchored numbers
  ({{VALIDATION_SQL_FILE}})
- PyRel ontology with {{CONCEPT_COUNT}} concepts and
  {{DERIVED_COUNT}} derived relationships
- All {{N}} queries answer correctly via `demo_queries.py main()` (warm
  runtime: {{WARM_RUNTIME}})
- Cortex agent deployed at `<DB>.RAI_AGENT.{{AGENT_NAME}}`, chat
  smoke-tested
- `prep_demo.py` gate passes cold in {{COLD_GATE_RUNTIME}}, warm in
  {{WARM_GATE_RUNTIME}}
- `RUNNING.html` with embedded figures regenerated

## Why this domain / why these questions

_Three sentences on the domain. What makes it a RelationalAI demo and not
just a SQL demo._

_Three sentences on the question set. Why these {{N}} and not others.
What each one is showcasing about RAI that pure SQL or pure Python can't
do cleanly._

## Key decisions made + justification

_The non-obvious calls. Each as a bullet that explains the choice and why
it beat the alternatives._

- **Schema grain.** _e.g. "fact table is per (location, product, week);
  considered per (lane, week) but that loses the cross-lane comparison Act
  X needs."_
- **Anchored numbers.** _e.g. "KLG = 7 violations because the gate script
  asserts that exact value; if you regenerate the data with a different
  seed it will drift and the talk track will lie. Always use seed=42."_
- **Reasoner choice for Act 3.** _e.g. "Used deterministic fit-score
  instead of GNN because the predictive reasoner is early-access. The
  talk track is explicit about the substitution. When the GNN reasoner
  GA's, swap in `/rai-predictive-modeling`."_
- **Engine sizing.** _e.g. "Logic L because the graph query touches
  ~10K rows; prescriptive M because the MIP has ~5K binaries. Smaller
  sizes were tested and were slow."_
- _add others as relevant_

## User preferences observed during the build

_Truth over approval._ The user wanted to know when an idea was weak.
Surface alternatives, not just compliance.

_No em-dashes in generated documents._

_No emojis in code or docs._

_Plain prose._ Minimal headers, no bullet-spam.

_Don't interrupt mid-phase._ The `.claude/settings.json` is tuned for
autonomous runs. If an unexpected permission prompt fired during the
build, it's logged in `BRIEF.md` under "Autonomy issues".

## Anchored numbers (load-bearing)

Reproduce via `data/{{DOMAIN}}_demo_validation.sql`. If any of these
drift, the talk track lies. The `prep_demo.py` gate asserts them.

| Metric | Value | Where it surfaces |
|---|---|---|
| {{METRIC_1}} | {{VALUE_1}} | {{LOCATION_1}} |
| {{METRIC_2}} | {{VALUE_2}} | {{LOCATION_2}} |
| _add rows_ |  |  |

## Known limitations

_Things that work for the demo but aren't production-shaped._

- {{LIMITATION_1}}
- {{LIMITATION_2}}

## Where to look when something breaks

- **Validation queries.** `data/{{DOMAIN}}_demo_validation.sql`. Run
  against Snowflake to confirm the demo numbers are intact.
- **Smoke test.** `rai_code/manual/demo_queries.py main()` - prints
  shape + first 3 rows of every query.
- **Agent status.** `.venv/bin/python -m agent.deploy status`.
- **Engine state.** `.venv/bin/rai reasoners list`. The gate auto-resumes.
- **Snowflake connection.** `snow connection test -c rai`.
- **PyRel source of truth.** `/Users/piotrkraus/rai-repos/PyRel` for API
  signatures and runnable examples.

## File map

```
{{REPO_FILE_TREE}}
```

## Phase log (from BRIEF.md)

_Copy the per-phase one-paragraph notes from `BRIEF.md` here so this
file stands alone._

## Open questions

_Stuff the build run didn't resolve. Worth a session with the next
person._

- {{OPEN_QUESTION_1}}
- {{OPEN_QUESTION_2}}
