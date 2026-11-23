"""The n_q study (blind review 2, R2-3): `audit/design/v03_nq_study.py` and `prereg/v03/NQ_STUDY.json`. The tests read design
quantities only (the denominators n_q of new_false, feasibility under the Q-40 tau, uncertainty); no new_true, new_false, T-1 or
G8 value of a v0.3 world is shown (PREREG_v0.3 section 2)."""

import io
import json
import re
import unittest
from contextlib import redirect_stdout
from fractions import Fraction as F
from pathlib import Path

from audit.design import v03_nq_study as S
from audit.exact import ExactTaus
from audit.v03 import prefreeze_check as PC

ROOT = Path(__file__).resolve().parent.parent
STUDY_JSON = ROOT / "prereg" / "v03" / "NQ_STUDY.json"
POWER_JSON = ROOT / "prereg" / "v03" / "POWER_STUDY.json"
PREREG = " ".join((ROOT / "prereg" / "PREREG_v0.3.md").read_text(encoding="utf-8").split())


def world(seed, n_q, uncertainty, feasible=True):
    """A synthetic world record: n_q and uncertainty per alpha (lists in ALPHAS order); every other metric passes tau."""
    four = {a: {"fidelity": F(1) if feasible else F(0), "deviation": F(0), "consistency": F(1), "uncertainty": F(u)}
            for a, u in zip(S.ALPHAS, uncertainty)}
    return {"seed": seed, "four": four, "n_q": dict(zip(S.ALPHAS, n_q))}


class ModuleTests(unittest.TestCase):
    def test_docstring_has_objective_method_and_design_quantities_only(self):
        doc = " ".join(S.__doc__.split())
        for item in ("Objective", "Method", "Design quantities only", "POWER_STUDY.json", "decided_outside_count"):
            self.assertIn(item, doc)

    def test_it_is_a_pre_freeze_study_with_an_out_attribute(self):
        self.assertEqual(PC.STUDIES["n_q study"], ("audit.design.v03_nq_study", "prereg/v03/NQ_STUDY.json"))
        self.assertEqual(S.OUT, STUDY_JSON)
        self.assertEqual(S.POWER, POWER_JSON)

    def test_n_q_is_counted_by_the_function_the_t1_judge_uses(self):
        from audit.v03 import checks as V

        self.assertIs(S.decided_outside_count, V.decided_outside_count)

    def test_exact_median(self):
        self.assertEqual(S.exact_median([3, 1, 2]), 2)
        self.assertEqual(S.exact_median([1, 2]), 1.5)
        self.assertEqual(S.exact_median([1, 3]), 2)
        self.assertIsInstance(S.exact_median([1, 3]), int)

    def test_the_taus_are_read_exactly_from_the_power_study(self):
        draw = {"tau": {"tau_s": "5/7", "tau_d": "0/1", "tau_t": "3/4", "tau_b": "2/3"}}
        self.assertEqual(S.taus_of(draw), ExactTaus(F(5, 7), F(0), F(3, 4), F(2, 3)))


class SummaryTests(unittest.TestCase):
    def test_per_alpha_median_min_max_and_the_count_below_20(self):
        ws = [world(1, [0, 1, 2, 3, 4, 5, 6, 7, 8, 9], [0] * 10), world(2, [0, 2, 4, 6, 8, 10, 12, 14, 16, 18], [0] * 10),
              world(3, [5, 5, 5, 5, 5, 5, 5, 5, 20, 40], [0] * 10)]
        s = S.nq_summary(ws)
        self.assertEqual(list(s), [f"{a:.2f}" for a in S.ALPHAS])
        self.assertEqual(s["0.95"], {"median": 0, "min": 0, "max": 5, "n_below_20": 3, "n_worlds": 3})
        self.assertEqual(s["0.55"], {"median": 16, "min": 8, "max": 20, "n_below_20": 2, "n_worlds": 3})
        self.assertEqual(s["0.50"], {"median": 18, "min": 9, "max": 40, "n_below_20": 2, "n_worlds": 3})  # 20 is not below 20

    def test_pairs_need_feasible_points_and_a_strictly_smaller_uncertainty(self):
        taus = ExactTaus(F(1, 2), F(0), F(1, 2), F(1))
        u = [F(i, 10) for i in range(10)]  # uncertainty rises with the index (0.95 is index 0): all distinct
        ws = [world(1, list(range(10)), u)]  # n_q rises with the uncertainty: q (smaller uncertainty) has the smaller n_q
        self.assertEqual(S.pair_counts(ws, taus), {"n_pairs": 45, "n_falling": 45})  # 10 points, 45 ordered pairs
        # n_q does not fall from p to q when q, with the smaller uncertainty, has the larger or an equal n_q
        ws = [world(1, list(reversed(range(10))), u)]
        self.assertEqual(S.pair_counts(ws, taus), {"n_pairs": 45, "n_falling": 0})
        self.assertEqual(S.pair_counts([world(1, [3] * 10, u)], taus), {"n_pairs": 45, "n_falling": 0})
        self.assertEqual(S.pair_counts([world(1, [0] * 10, u, feasible=False)], taus), {"n_pairs": 0, "n_falling": 0})
        self.assertEqual(S.pair_counts([world(1, [3] * 10, [F(1, 2)] * 10)], taus), {"n_pairs": 0, "n_falling": 0})  # ties
        self.assertEqual(S.pair_counts(ws * 2, taus), {"n_pairs": 90, "n_falling": 0})


class CommittedStudyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc = json.loads(STUDY_JSON.read_text(encoding="utf-8"))

    def test_lf_line_endings_and_no_forbidden_key(self):
        self.assertNotIn(b"\r", STUDY_JSON.read_bytes())

        def keys(o):
            if isinstance(o, dict):
                for k, v in o.items():
                    yield k
                    yield from keys(v)
            elif isinstance(o, list):
                for v in o:
                    yield from keys(v)

        self.assertFalse([k for k in keys(self.doc) if re.search(r"new_false|new_true|t1_outcome|g8|largest|holds", str(k), re.I)])

    def test_the_worlds_and_the_taus_are_the_power_studys(self):
        power = json.loads(POWER_JSON.read_text(encoding="utf-8"))
        self.assertEqual(self.doc["test_world_seeds"], power["test_world_seeds"])
        self.assertEqual(self.doc["n_test_worlds"], 50)
        self.assertEqual([d["tau"] for d in self.doc["t1_pairs"]["draws"]], [d["tau"] for d in power["draws"]])
        self.assertEqual(self.doc["t1_pairs"]["n_draws"], 40)
        self.assertEqual(sorted(self.doc["n_q_per_world"]), sorted(str(s) for s in power["test_world_seeds"]))

    def test_the_numbers_are_those_the_prereg_prints(self):
        by = self.doc["n_q_by_alpha"]
        self.assertEqual([by[a]["median"] for a in ("0.80", "0.70", "0.60")], [12, 19, 28])
        self.assertIn("its median is 12 at α 0.80, 19 at 0.70 and 28 at 0.60 (`prereg/v03/NQ_STUDY.json`)", PREREG)
        self.assertEqual(self.doc["t1_pairs"]["n_pairs"], 18796)
        self.assertEqual(self.doc["t1_pairs"]["n_falling"], 0)
        self.assertIn("18 796 T-1 pairs of the power study's development worlds", PREREG)
        self.assertIn("It fell on none", PREREG)

    def test_the_summary_follows_from_the_per_world_table(self):
        for alpha, s in self.doc["n_q_by_alpha"].items():
            vals = [w[alpha] for w in self.doc["n_q_per_world"].values()]
            self.assertEqual(S.exact_median(vals), s["median"], alpha)
            self.assertEqual((min(vals), max(vals), sum(v < 20 for v in vals), len(vals)),
                             (s["min"], s["max"], s["n_below_20"], s["n_worlds"]), alpha)

    def test_the_pair_totals_are_the_sums_over_the_draws(self):
        p = self.doc["t1_pairs"]
        self.assertEqual(sum(d["n_pairs"] for d in p["draws"]), p["n_pairs"])
        self.assertEqual(sum(d["n_falling"] for d in p["draws"]), p["n_falling"])

    def test_quick_mode_prints_and_writes_nothing(self):
        before = STUDY_JSON.read_bytes()
        buf = io.StringIO()
        with redirect_stdout(buf):
            self.assertEqual(S.main(["--quick"]), 0)
        self.assertEqual(STUDY_JSON.read_bytes(), before)
        self.assertIn("n_q median", buf.getvalue())
        self.assertNotIn("new_false", buf.getvalue())


if __name__ == "__main__":
    unittest.main()
