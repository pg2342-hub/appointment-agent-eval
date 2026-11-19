"""Run an agent over the 25 cases, three runs each, and apply the go-live gate from the spec.

  python3 run_eval.py --agent spec            # reference agent
  python3 run_eval.py --agent naive           # every check switched off
  python3 run_eval.py --agent my_module:MyAgent   # your own agent (needs propose(case, tms))
"""
import argparse, importlib, json
from pathlib import Path
from harness.tms import TMS
from harness.agents import SpecAgent, NaiveAgent
from harness.grader import grade, CRITICAL

ROOT = Path(__file__).resolve().parent
GATE = "24 of 25 cases on all three runs, zero critical errors, T1-T2 at 14 of 15 or better, T3-T4 at 10 of 10"


def load_agent(name):
    if name == "spec":
        return SpecAgent()
    if name == "naive":
        return NaiveAgent()
    mod, cls = name.split(":")
    return getattr(importlib.import_module(mod), cls)()


def evaluate(agent, runs=3, cases=None, tms=None):
    tms = tms or TMS()
    cases = cases or json.loads((ROOT / "data" / "cases.json").read_text())
    rows = []
    for c in cases:
        run_errs = [grade(c["expected"], agent.propose(c, tms)) for _ in range(runs)]
        errs = sorted({e for r in run_errs for e in r})
        rows.append(dict(id=c["id"], tier=c["tier"], title=c["title"], passed=not errs, errors=errs,
                         critical=bool(set(errs) & CRITICAL)))
    s = summarize(rows)
    return rows, s


def summarize(rows):
    p = lambda tiers: sum(r["passed"] for r in rows if r["tier"] in tiers)
    n = lambda tiers: sum(r["tier"] in tiers for r in rows)
    s = dict(passed=p("T1T2T3T4"), total=len(rows), t12=p("T1T2"), t12_n=n("T1T2"), t34=p("T3T4"), t34_n=n("T3T4"),
             critical=sum(r["critical"] for r in rows))
    s["gate"] = s["passed"] >= 24 and s["critical"] == 0 and s["t12"] >= 14 and s["t34"] == s["t34_n"]
    return s


def report(name, rows, s, runs):
    out = [f"# Eval report: `{name}` agent", "",
           f"{s['passed']} of {s['total']} cases passed on all {runs} runs. T1-T2 {s['t12']} of {s['t12_n']}, "
           f"T3-T4 {s['t34']} of {s['t34_n']}, cases with a critical error {s['critical']}. "
           f"Gate ({GATE}): **{'PASS' if s['gate'] else 'FAIL'}**.", "",
           "| # | Tier | Case | Result | Errors |", "|---|---|---|---|---|"]
    out += [f"| {r['id']} | {r['tier']} | {r['title']} | {'pass' if r['passed'] else 'FAIL'} | {' '.join(r['errors'])} |"
            for r in rows]
    return "\n".join(out) + "\n"


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--agent", default="spec")
    ap.add_argument("--runs", type=int, default=3)
    a = ap.parse_args()
    agent = load_agent(a.agent)
    rows, s = evaluate(agent, a.runs)
    tag = a.agent.replace(":", "_")
    (ROOT / "reports").mkdir(exist_ok=True)
    (ROOT / "reports" / f"{tag}_report.md").write_text(report(a.agent, rows, s, a.runs))
    (ROOT / "reports" / f"{tag}_results.json").write_text(json.dumps(dict(summary=s, cases=rows), indent=1))
    print(report(a.agent, rows, s, a.runs))
