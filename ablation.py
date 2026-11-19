"""Switch off one check at a time in the reference agent and see which cases catch it.

An eval set that still passes with a check switched off is not testing that check.
"""
from pathlib import Path
from harness.agents import SpecAgent, CHECKS
from run_eval import evaluate

ROOT = Path(__file__).resolve().parent


def ablate():
    out = []
    for chk in CHECKS:
        rows, s = evaluate(SpecAgent(off={chk}))
        out.append(dict(check=chk, passed=s["passed"], critical=s["critical"], gate=s["gate"],
                        caught=[r["id"] for r in rows if not r["passed"]]))
    return out


if __name__ == "__main__":
    res = ablate()
    lines = ["# Ablation: reference agent with one check switched off", "",
             "| Check switched off | Cases passed | Cases with a critical error | Gate | Cases that caught it |",
             "|---|---|---|---|---|"]
    lines += [f"| {r['check']} | {r['passed']} of 25 | {r['critical']} | {'pass' if r['gate'] else 'FAIL'} | "
              f"{', '.join(map(str, r['caught'])) or 'none'} |" for r in res]
    txt = "\n".join(lines) + "\n"
    (ROOT / "reports").mkdir(exist_ok=True)
    (ROOT / "reports" / "ablation.md").write_text(txt)
    print(txt)
