"""The all_true study (blind review 1, R1-7): `audit/design/v03_all_true_study.py` and `prereg/v03/ALL_TRUE_STUDY.json`. The tests
read design quantities only (G7a-type scoring of single-point baselines, source reliabilities); no new_true, new_false, T-1 or G8
value of a v0.3 world is shown (PREREG_v0.3 section 2)."""

import io
import json
import re
import unittest
from contextlib import redirect_stdout
from fractions import Fraction as F
from pathlib import Path

from audit.design import v03_all_true_study as S
from audit.exact import ExactTaus, feasible
from audit.system import FIXED
from audit.v03 import checks as V
from audit.v03 import prefreeze_check as PC
from audit.v03.worldset import build_cached

ROOT = Path(__file__).resolve().parent.parent
STUDY_JSON = ROOT / "prereg" / "v03" / "ALL_TRUE_STUDY.json"
PREREG = " ".join((ROOT / "prereg" / "PREREG_v0.3.md").read_text(encoding="utf-8").split())


class ModuleTests(unittest.TestCase):
    def test_docstring_has_objective_method_and_design_quantities_only(self):
        doc = " ".join(S.__doc__.split())
        for item in ("Objective.", "Method.", "Design quantities only", "TAU_RULE_STUDY.json", "first 30 valid", "930000"):
            self.assertIn(item, doc)

    def test_it_is_a_pre_freeze_study_with_an_out_attribute(self):
        self.assertEqual(PC.STUDIES["all_true study"], ("audit.design.v03_all_true_study", "prereg/v03/ALL_TRUE_STUDY.json"))
        self.assertEqual(S.OUT, ROOT / "prereg" / "v03" / "ALL_TRUE_STUDY.json")
        self.assertEqual(S.BASELINES, ("all_true", "echo", "all_false", "all_unknown", "all_both"))

    def test_the_taus_are_the_forty_q40_taus_of_s2(self):
        taus = S.load_taus()
        self.assertEqual(len(taus), 40)
        doc = json.loads((ROOT / "prereg" / "v03" / "TAU_RULE_STUDY.json").read_text(encoding="utf-8"))
        self.assertEqual(taus[0].tau_s, F(doc["draws"]["Q-40"][0]["tau"]["tau_s"]))
        self.assertEqual(doc["n_draws"], 40)

    def test_at_least_compares_the_printed_decimals_exactly(self):
        self.assertTrue(S.at_least([0.55, 0.95], "0.95"))
        self.assertFalse(S.at_least([0.55, 0.949], "0.95"))
        self.assertTrue(S.at_least([0.9], "0.90"))
        self.assertFalse(S.at_least([], "0.90"))


class DrawRecordTests(unittest.TestCase):
    TAUS = ExactTaus(F(1, 2), F(1, 10), F(1, 2), F(1, 2))

    @staticmethod
    def point(feas=True, pos=True):
        m = {"fidelity": F(1) if feas else F(0), "deviation": F(0), "consistency": F(1), "uncertainty": F(0),
             "new_true": F(1)}
        return (m, pos)

    def world(self, seed, scoring_alphas, names=("all_true",)):
        pts = {n: [self.point(False, False)] * 10 for n in S.BASELINES}
        for name in names:
            pts[name] = [self.point(True, a in scoring_alphas) if a in scoring_alphas or a == 0.5 else self.point(False, True)
                         for a in S.ALPHAS]
        return {"seed": seed, "points": pts, "reliabilities": [0.6]}

    def test_a_baseline_scores_only_where_it_is_feasible_and_positive(self):
        w = self.world(7, (0.95, 0.9))
        rec = S.draw_record(self.TAUS, [w])["all_true"]
        self.assertEqual(rec["scoring_worlds"], {"7": ["0.95", "0.90"]})
        self.assertEqual((rec["n_worlds_scoring"], rec["n_worlds_feasible"]), (1, 1))
        self.assertEqual(rec["scoring_by_alpha"], {"0.95": 1, "0.90": 1})  # levels with no scoring world are left out
        # feasible but never positive: feasible counts it, scoring does not
        pts = [self.point(True, False)] * 10
        w2 = {"seed": 8, "points": {n: pts for n in S.BASELINES}, "reliabilities": [0.6]}
        rec2 = S.draw_record(self.TAUS, [w2])["echo"]
        self.assertEqual((rec2["n_worlds_feasible"], rec2["n_worlds_scoring"], rec2["scoring_worlds"]), (1, 0, {}))
        # positive but infeasible under tau: not scoring
        pts3 = [self.point(False, True)] * 10
        w3 = {"seed": 9, "points": {n: pts3 for n in S.BASELINES}, "reliabilities": [0.6]}
        self.assertEqual(S.draw_record(self.TAUS, [w3])["echo"]["n_worlds_scoring"], 0)

    def test_summarize_reports_min_median_max_and_the_same_set_flag(self):
        rec = lambda counts: {"baselines": {n: {"n_worlds_scoring": c, "scoring_by_alpha": {"0.95": 1} if c else {},
                                                "scoring_worlds": {"1": ["0.95"]} if c else {}}
                                            for n, c in ((b, counts if b == "all_true" else 0) for b in S.BASELINES)}}
        out = S.summarize([rec(2), rec(2), rec(2)])
        self.assertEqual(out["all_true"]["n_worlds_scoring"], {"min": 2, "median": 2, "max": 2})
        self.assertTrue(out["all_true"]["same_worlds_and_levels_in_every_draw"])
        self.assertEqual(out["echo"]["scoring_alpha_levels"], [])
        different = rec(2)
        different["baselines"]["all_true"]["scoring_worlds"] = {"2": ["0.95"]}
        self.assertFalse(S.summarize([rec(2), different])["all_true"]["same_worlds_and_levels_in_every_draw"])


class ScoringIsG7aTests(unittest.TestCase):
    def test_the_study_scores_a_baseline_exactly_as_g7a_does(self):
        world, ctx, enc = build_cached(930000, 940000)
        reduced = S.reduce_world(world, ctx, enc)
        taus = S.load_taus()[0]
        feas, pos = V.baseline_points(FIXED, world, ctx, enc, taus, S.BASELINES)
        for i, name in enumerate(S.BASELINES):
            for j, (m, positive) in enumerate(reduced["points"][name]):
                # booleans only: no new_false or new_true value is shown
                self.assertTrue(bool(feasible(m, taus)) == bool(feas[i][j]))
                self.assertTrue(bool(positive) == bool(pos[i][j]))
        arm = V.all_true_arm(FIXED, world, ctx, enc, taus)
        scored = [f"{a:.2f}" for a, (m, p) in zip(S.ALPHAS, reduced["points"]["all_true"]) if p and feasible(m, taus)]
        self.assertEqual(scored, [f"{a:.2f}" for a in arm["scoring_alphas"]])
        self.assertEqual(reduced["reliabilities"], [p.value for p in world.params.source_reliabilities])
        self.assertTrue(all(set(m) == {"fidelity", "deviation", "consistency", "uncertainty", "new_true"}
                            for pts in reduced["points"].values() for m, _ in pts))
        self.assertTrue(all(m["new_true"] == 1 for pts in reduced["points"].values() for m, _ in pts))  # a placeholder


class CommittedJsonTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc = json.loads(STUDY_JSON.read_text(encoding="utf-8"))

    def test_lf_line_endings_and_no_forbidden_quantity(self):
        raw = STUDY_JSON.read_bytes()
        self.assertNotIn(b"\r", raw)

        def keys(o):
            if isinstance(o, dict):
                for k, v in o.items():
                    yield k
                    yield from keys(v)
            elif isinstance(o, list):
                for v in o:
                    yield from keys(v)

        self.assertFalse([k for k in keys(self.doc) if re.search(r"new_false|new_true|t1|g8|largest", str(k), re.I)])
        self.assertEqual(len(self.doc["draws"]), 40)
        self.assertEqual(len(self.doc["test_world_seeds"]), 30)

    def test_the_numbers_are_those_the_prereg_prints(self):
        s = self.doc["summary"]
        self.assertEqual(s["all_true"]["n_worlds_scoring"], {"min": 22, "median": 22.0, "max": 22})  # 22 of 30 in every draw
        self.assertTrue(s["all_true"]["same_worlds_and_levels_in_every_draw"])
        self.assertEqual(s["all_true"]["scoring_alpha_levels"], ["0.95", "0.90", "0.85"])
        for name in ("echo", "all_false", "all_unknown", "all_both"):
            self.assertEqual(s[name]["n_worlds_scoring"], {"min": 0, "median": 0.0, "max": 0}, name)
            self.assertEqual(s[name]["scoring_alpha_levels"], [], name)
        self.assertEqual(self.doc["worlds_with_a_source_at_or_above"], {"0.95": 6, "0.90": 20})
        for text in ("22 of the 30 development test worlds", "only 6 of the 30 worlds have a source at or above 0.95",
                     "and 20 at or above 0.90"):
            self.assertIn(text, PREREG)
        self.assertIn("echo, all_false, all_unknown and all_both never scored", PREREG)

    def test_every_draw_has_the_same_all_true_worlds_and_the_five_baselines(self):
        first = self.doc["draws"][0]["baselines"]["all_true"]["scoring_worlds"]
        self.assertEqual(len(first), 22)
        for d in self.doc["draws"]:
            self.assertEqual(set(d["baselines"]), set(S.BASELINES))
            self.assertEqual(d["baselines"]["all_true"]["scoring_worlds"], first)
            self.assertTrue(set(next(iter(first.values()))) <= {"0.95", "0.90", "0.85"})
        # a world with a source at or above 0.95 is among the scoring worlds only at the levels the study lists
        hi = {s for s, r in self.doc["highest_reliability_per_world"].items() if r >= 0.95}
        self.assertEqual(len(hi), 6)

    def test_quick_mode_prints_and_writes_nothing(self):
        before = STUDY_JSON.read_bytes()
        buf = io.StringIO()
        with redirect_stdout(buf):
            self.assertEqual(S.main(["--quick"]), 0)
        self.assertEqual(STUDY_JSON.read_bytes(), before)
        self.assertIn("all_true:", buf.getvalue())
        self.assertNotIn("new_false", buf.getvalue())


if __name__ == "__main__":
    unittest.main()
