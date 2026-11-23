"""G7a over four baselines and the all_true descriptive arm (PREREG_v0.3 sections 1, 2 and 3.2; author decision 2026-11-23).

The synthetic tests use made-up arrays. The one development-world test reads G7a outcomes and the all_true arm, which the
no-pilot rule allows (PREREG section 2); it never reads a T-1 or G8 quantity."""

import re
import unittest
from pathlib import Path

import numpy as np

from audit import checks as C
from audit.system import FIXED
from audit.twins import N7
from audit.v03 import aggregate as AG
from audit.v03 import checks as V
from audit.v03.run_v03 import build_calibration
from audit.v03.seeds import DEV_CORE, seeder
from audit.v03.worldset import generate_valid_v03

PREREG = Path(__file__).resolve().parent.parent / "prereg" / "PREREG_v0.3.md"
NA = len(V.ALPHAS)


def data(base_f=None, base_p=None, oracle_f=None, oracle_p=None, no_oracle=False, rows=4):
    z = np.zeros((rows, NA), dtype=bool)
    o = np.zeros(NA, dtype=bool)
    return {"base_feasible": z if base_f is None else base_f, "base_positive": z if base_p is None else base_p,
            "oracle_feasible": o if oracle_f is None else oracle_f, "oracle_positive": o if oracle_p is None else oracle_p,
            "no_oracle": C._flag(no_oracle)}


def anchor():
    o = np.zeros(NA, dtype=bool)
    o[0] = True
    return {"oracle_f": o, "oracle_p": o}


class G7aJudgeTests(unittest.TestCase):
    def test_four_baselines_are_named(self):
        self.assertEqual(V.G7A_BASELINES, ("echo", "all_false", "all_unknown", "all_both"))
        self.assertNotIn("all_true", V.G7A_BASELINES)
        self.assertEqual(V.ALL_TRUE, "all_true")

    def test_holds_fails_undefined(self):
        self.assertIs(V.judge_g7a(data(**anchor())), True)
        # a baseline that is feasible and positive at one alpha fails the test
        f = np.zeros((4, NA), dtype=bool)
        f[2, 5] = True
        self.assertIs(V.judge_g7a(data(base_f=f, base_p=f, **anchor())), False)
        # feasible but scoring 0, or positive but infeasible: no violation
        self.assertIs(V.judge_g7a(data(base_f=f, **anchor())), True)
        self.assertIs(V.judge_g7a(data(base_p=f, **anchor())), True)
        # no anchor (the oracle scores nowhere): FAILS; no feasible oracle point at all: UNDEFINED
        self.assertIs(V.judge_g7a(data()), False)
        self.assertIsNone(V.judge_g7a(data(no_oracle=True)))

    def test_data_that_is_not_four_baselines_wide_is_not_judged(self):
        self.assertIs(V.judge_g7a(data(rows=5, **anchor())), False)  # a v0.2 array with all_true in it
        self.assertIs(V.judge_g7a(data(rows=3, **anchor())), False)
        self.assertIs(C.judge_g7a(data(rows=5, **anchor())), True)  # audit.checks is unchanged and judges any width

    def test_the_judge_table_replaces_only_g7_and_t1(self):
        self.assertIs(V.JUDGES["G7"], V.judge_g7a)
        self.assertIs(V.JUDGES["T-1"], V.judge_t1)  # T-1 of v0.3 has the one-atom floor (R1-1)
        for t in ("G1", "G2", "G3", "G4", "G5", "G6", "G8"):
            self.assertIs(V.JUDGES[t], C.JUDGES[t])

    def test_the_gate_probes_do_not_pass(self):
        rng = np.random.default_rng(0)
        zeros = {k: np.zeros_like(np.asarray(v)) for k, v in data(**anchor()).items()}
        self.assertIsNot(V.judge_g7a(zeros), True)
        noise = {k: rng.normal(size=np.asarray(v).shape) for k, v in data(**anchor()).items()}
        self.assertIsNot(V.judge_g7a(noise), True)


class G7aClaimTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        lines = [re.sub(r"^\s*>\s?", "", ln) for ln in PREREG.read_text(encoding="utf-8").splitlines()]
        cls.text = " ".join(" ".join(lines).split())

    def test_the_claim_is_the_prereg_wording(self):
        self.assertIn("| G7a | " + AG.CLAIMS["G7"] + " |", self.text)
        self.assertIn("none of four degenerate baselines", AG.CLAIMS["G7"].lower())
        self.assertNotIn("all_true", AG.CLAIMS["G7"])
        for t in ("G1", "G2", "G3", "G4", "G5", "G6", "G8"):  # T-1's claim states the one-atom floor (R2-1), see test_v03_run
            self.assertEqual(AG.CLAIMS[t], AG.V02_CLAIMS[t])

    def test_the_sentence_uses_the_narrowed_claim(self):
        out = [(1000 + i, "HOLDS") for i in range(50)]
        none = {"n_worlds": 50, "n_worlds_scoring": 0, "n_worlds_feasible": 0, "scoring_by_alpha": {}}
        text = AG.aggregate_test("G7", out, all_true=none)["text"]
        # the fixed G7a sentence (PREREG 4, R1-3) follows the verdict sentence; with no scoring world it has no parenthesis
        self.assertEqual(text, f"G7a holds: {AG.CLAIMS['G7']}, in all 50 defined test worlds (0 undefined). "
                               "(A check of the implementation or of the criterion, not a discovery.) "
                               + AG.g7a_sentence(none))
        self.assertIn("scored > 0 on 0 of 50 test worlds; echo, all_unknown and all_both score 0", text)


class AllTrueSummaryTests(unittest.TestCase):
    def test_counts(self):
        arms = [{"feasible_alphas": [0.95, 0.9], "scoring_alphas": [0.95, 0.9], "scores": True},
                {"feasible_alphas": [0.95], "scoring_alphas": [0.95], "scores": True},
                {"feasible_alphas": [], "scoring_alphas": [], "scores": False},
                {"feasible_alphas": [0.85], "scoring_alphas": [], "scores": False}]
        s = AG.all_true_summary(arms)
        self.assertEqual((s["n_worlds"], s["n_worlds_scoring"], s["n_worlds_feasible"]), (4, 2, 3))
        self.assertEqual(s["scoring_by_alpha"], {"0.95": 2, "0.9": 1})
        self.assertEqual(AG.all_true_summary([]), {"n_worlds": 0, "n_worlds_scoring": 0, "n_worlds_feasible": 0,
                                                    "scoring_by_alpha": {}})


class DevelopmentWorldTests(unittest.TestCase):
    """G7a and the all_true arm on three development worlds; N7 (the unconstrained criterion) must still FAIL."""

    @classmethod
    def setUpClass(cls):
        sd = seeder(DEV_CORE)
        cls.taus = build_calibration(DEV_CORE, None, 8, 0).taus.main
        cls.recs = generate_valid_v03(3, sd, "world-test", "enc-test", "aux")[0]

    def test_g7a_data_keys_and_shapes(self):
        for r in self.recs:
            d = V.collect_g7a(FIXED, r.world, r.context, r.encoding, self.taus)
            self.assertTrue(set(C.DECLARED_KEYS["G7"]) <= set(d))
            self.assertEqual(d["base_feasible"].shape, (4, NA))
            self.assertEqual(d["base_positive"].shape, (4, NA))
            self.assertIn(V.judge_g7a(d), (True, False, None))

    def test_n7_still_fails(self):
        for r in self.recs:
            d = V.collect_g7a(N7(), r.world, r.context, r.encoding, self.taus)
            self.assertTrue(d["base_feasible"].all())  # feasibility is ignored
            self.assertIs(V.judge_g7a(d), False)

    def test_the_all_true_arm_is_not_in_the_g7a_data_and_is_well_formed(self):
        for r in self.recs:
            arm = V.all_true_arm(FIXED, r.world, r.context, r.encoding, self.taus)
            self.assertEqual(set(arm), {"feasible_alphas", "scoring_alphas", "scores"})
            self.assertTrue(set(arm["scoring_alphas"]) <= set(arm["feasible_alphas"]) <= set(V.ALPHAS))
            self.assertEqual(arm["scores"], bool(arm["scoring_alphas"]))
            # the same scoring code as a G7a baseline: scoring all_true as a fifth row gives the same answer
            f, p = V.baseline_points(FIXED, r.world, r.context, r.encoding, self.taus, ("echo", "all_true"))
            self.assertEqual(bool((f[1] & p[1]).any()), arm["scores"])


if __name__ == "__main__":
    unittest.main()
