import json, unittest
from pathlib import Path
from harness.tms import TMS
from harness.agents import SpecAgent, NaiveAgent, CHECKS
from harness.grader import grade
from run_eval import evaluate

CASES = json.loads((Path(__file__).resolve().parent.parent / "data" / "cases.json").read_text())


class TestHarness(unittest.TestCase):
    def test_case_mix_matches_spec(self):
        tiers = [c["tier"] for c in CASES]
        self.assertEqual(len(CASES), 25)
        self.assertEqual([tiers.count(t) for t in ("T1", "T2", "T3", "T4")], [7, 8, 6, 4])

    def test_reference_agent_passes_gate(self):
        _, s = evaluate(SpecAgent())
        self.assertEqual(s["passed"], 25)
        self.assertTrue(s["gate"])

    def test_naive_agent_fails_gate(self):
        _, s = evaluate(NaiveAgent())
        self.assertFalse(s["gate"])
        self.assertGreater(s["critical"], 0)

    def test_every_check_is_caught_by_some_case(self):
        for chk in CHECKS:
            rows, _ = evaluate(SpecAgent(off={chk}))
            self.assertTrue(any(not r["passed"] for r in rows), chk)

    def test_duplicate_booking_is_critical(self):
        exp = next(c for c in CASES if c["id"] == 5)["expected"]
        p = dict(action="book", load=exp["load"], appointments=exp["appointments"], channel="email",
                 confirmation="X", notify=[], flags=[])
        self.assertIn("E3", grade(exp, p))

    def test_invented_confirmation_is_caught(self):
        c = next(c for c in CASES if c["id"] == 1)
        p = SpecAgent().propose(c, TMS())
        self.assertEqual(grade(c["expected"], p), [])
        p["confirmation"] = "MADE-UP"
        self.assertIn("E6", grade(c["expected"], p))

    def test_wrong_load_write_is_critical(self):
        c = next(c for c in CASES if c["id"] == 15)
        p = SpecAgent(off={"po_match"}).propose(c, TMS())
        self.assertIn("E3", grade(c["expected"], p))

    def test_time_zone_conversion(self):
        tms = TMS()
        ct = tms.local("MEM-SHIP", "2026-12-08T13:00")
        self.assertEqual(tms.fmt("CIN-RCV", ct), "2026-12-08T14:00")


if __name__ == "__main__":
    unittest.main()
