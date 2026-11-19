"""Builds docs/results.js for the GitHub Pages demo: every combination of the 12 checks
(4,096 runs of the reference agent, three runs per case) graded by harness/grader.py.

  python3 docs/build_page.py
"""
import itertools, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from harness.tms import TMS
from harness.agents import SpecAgent, CHECKS
from harness.grader import grade

CODES = ["E1", "E2", "E3", "E4", "E5", "E6"]
B64 = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"


def describe(e):
    a = e["action"]
    if a == "handoff":
        return "Hand off to the " + ("account executive" if e["to"] == "ae" else "coordinator") + " (" + e["reason"].replace("_", " ") + ")"
    if a == "record_fcfs":
        return "No appointment needed; record receiving hours"
    if a == "enter_existing":
        return "Enter the customer's appointment " + e["appointments"][0]["local"].replace("T", " ") + "; do not book again"
    s = "Book " + "; ".join(x["facility"] + " " + x["local"].replace("T", " ") for x in e["appointments"]) + " by " + e["channel"]
    if e.get("notify"):
        s += "; notify " + " and ".join("AE" if n == "ae" else n for n in e["notify"])
    return s


def main():
    tms = TMS()
    cases = json.loads((ROOT / "data" / "cases.json").read_text())
    combos = []
    for mask in range(1 << len(CHECKS)):
        off = {c for i, c in enumerate(CHECKS) if mask >> i & 1}
        agent = SpecAgent(off=off)
        row = ""
        for c in cases:
            errs = set()
            for _ in range(3):
                errs |= set(grade(c["expected"], agent.propose(c, tms)))
            row += B64[sum(1 << i for i, k in enumerate(CODES) if k in errs)]
        combos.append(row)
    ref = SpecAgent()
    data = dict(checks=CHECKS, codes=CODES,
                cases=[dict(id=c["id"], tier=c["tier"], title=c["title"], expected=describe(c["expected"]),
                            log=ref.propose(c, tms).get("log", "")) for c in cases],
                combos=combos)
    (ROOT / "docs" / "results.js").write_text("window.RESULTS=" + json.dumps(data, separators=(",", ":")) + ";\n")
    print(len(combos), "combinations written")


if __name__ == "__main__":
    main()
