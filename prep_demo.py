#!/usr/bin/env python3
"""prep_demo.py - pre-flight gate for the Nestle / Marco diet-optimization demo.

Run ~10 minutes before showtime. Validates, end to end against live Snowflake:
the connection, the loaded data + anchored numbers, the two reasoner engines,
the three demo queries (Q1 fail / Q2 OPTIMAL / Q3 re-solve + wall), and the
Cortex agent. Prints a PASS/FAIL summary and exits non-zero on any failure.

    .venv/bin/python prep_demo.py
    .venv/bin/python prep_demo.py --skip-queries   # fast: skip the ~4 min solves
    .venv/bin/python prep_demo.py --skip-agent      # skip the agent status check
"""
import argparse
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.abspath(__file__))
PY = os.path.join(REPO, ".venv", "bin", "python")
RAI = os.path.join(REPO, ".venv", "bin", "rai")
ROLE = "RAI_DEMO_NESTLE_DIET"
CONN = "rai"
DB = "PK_NESTLE_DIET"

results = []  # (name, ok, detail)


def run(cmd, timeout=900):
    p = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True, timeout=timeout)
    return p.returncode, p.stdout + p.stderr


def record(name, ok, detail=""):
    results.append((name, ok, detail))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f" - {detail}" if detail else ""))


def check_connection():
    rc, out = run(["snow", "connection", "test", "-c", CONN], timeout=120)
    ok = rc == 0 and "Status" in out and "OK" in out
    record("Snowflake connection", ok, "" if ok else out.strip()[-160:])


def check_data():
    q = (f"SELECT (SELECT COUNT(*) FROM {DB}.DIET.recipe) AS r, "
         f"(SELECT COUNT(*) FROM {DB}.DIET.ingredient) AS i, "
         f"(SELECT COUNT(*) FROM {DB}.DIET.recipe WHERE is_vegan) AS v, "
         f"(SELECT COUNT(*) FROM {DB}.DIET.persona_nutrient_target WHERE persona_id='marco') AS t")
    rc, out = run(["snow", "sql", "--role", ROLE, "-c", CONN, "--query", q], timeout=120)
    nums = re.findall(r"\b(\d+)\b", out)
    # expect recipe=168, ingredient=84, vegan=168, targets=16 somewhere in the row
    ok = rc == 0 and "168" in out and "84" in out and "16" in out
    record("Data + anchored counts (recipe 168 / ingredient 84 / targets 16)", ok,
           "" if ok else out.strip()[-160:])


def check_engines():
    # `rai reasoners list` truncates names in its table (e.g. "nestle_d..."),
    # so match the prefix and require both engine rows.
    rc, out = run([RAI, "reasoners", "list"], timeout=120)
    n = out.lower().count("nestle")
    ok = rc == 0 and n >= 2
    record("Reasoner engines exist (logic + prescriptive)", ok,
           "" if ok else f"found {n} nestle engine rows (need 2)")


def check_queries():
    rc, out = run([PY, "rai_code/manual/demo_queries.py"], timeout=1200)
    q1 = "$5.01" in out or "5.01" in out
    q2 = "OPTIMAL" in out and "7.06" in out
    q3 = "INFEASIBLE" in out and ("2.92" in out or "co2" in out.lower())
    ok = rc == 0 and q1 and q2 and q3
    detail = "" if ok else f"Q1={q1} Q2={q2} Q3={q3} rc={rc}"
    record("Demo queries Q1/Q2/Q3 (naive $5.01 fail, OPTIMAL $7.06, INFEASIBLE wall)", ok, detail)


def check_agent():
    rc, out = run([PY, "-m", "agent.deploy", "status"], timeout=180)
    ok = rc == 0 and "agent_exists=True" in out
    record("Cortex agent deployed (agent_exists=True)", ok, "" if ok else out.strip()[-160:])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-queries", action="store_true")
    ap.add_argument("--skip-agent", action="store_true")
    args = ap.parse_args()

    print("=" * 72)
    print("PREP_DEMO - Nestle / Marco diet-optimization demo pre-flight")
    print("=" * 72)
    check_connection()
    check_data()
    check_engines()
    if not args.skip_queries:
        check_queries()
    if not args.skip_agent:
        check_agent()

    npass = sum(1 for _, ok, _ in results if ok)
    print("=" * 72)
    print(f"SUMMARY: {npass}/{len(results)} checks passed")
    print("=" * 72)
    sys.exit(0 if npass == len(results) else 1)


if __name__ == "__main__":
    main()
