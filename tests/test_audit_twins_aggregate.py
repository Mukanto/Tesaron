import unittest

import numpy as np

from audit import checks as C
from audit.aggregate import (
    CLAIMS,
    EXPECTED_PARAGRAPH,
    G8_FAILS_SENTENCE,
    LIMITATION,
    T1_HOLDS_SENTENCE,
    hypothesis_summary,
    structure_counts,
    structure_text,
    t1_sentence,
    undefined_as_fails,
    MIN_DEFINED,
    Z_95_ONE_SIDED,
    aggregate_test,
    verdict_table,
    wilson_lower,
)
from audit.cache import get_encoding
from audit.exact import encode_pairs
from audit.hashing import encoding_hash
from audit.system import FIXED
from audit.twins import N1a, N1b, N2, N3, N4, N5, N6, N7, N8, TWINS_BY_TEST, with_trade_off
from audit.twins._source import PairSource, RngSource, SetOrderSource
from fractions import Fraction

from audit.exact import ExactTaus
from tesaron.enums import EpistemicStatus

TAUS = ExactTaus(Fraction(4, 5), Fraction(1, 20), Fraction(9, 10), Fraction(1, 2))


class TwinTests(unittest.TestCase):
    """Each twin has its intended effect on development world 900001 (the fixed system HOLDS there)."""

    @classmethod
    def setUpClass(cls):
        cls.world, cls.ctx, cls.enc = get_encoding(900001, 900101)
        cls.perm = lambda self: [np.random.Generator(np.random.PCG64(900700 + i)) for i in range(3)]

    def judge(self, test, system):
        w, c = self.world, self.ctx
        enc = system.encode(w, c)
        if test == "G1":
            return C.judge_g1(C.collect_g1(system, w, c, enc))
        if test == "G2":
            return C.judge_g2(C.collect_g2(system, w, c))
        if test == "G3":
            return C.judge_g3(C.collect_g3(system, w, c, enc))
        if test == "G4":
            return C.judge_g4(C.collect_g4(system, w, c, enc, self.perm()))
        if test == "G5":
            return C.judge_g5(C.collect_g5(system, w, c, enc))
        if test == "G6":
            return C.judge_g6(C.collect_g6(system, w, c, enc))
        res = C.evaluate_grid(system, w, c, enc)
        if test == "G7":
            return C.judge_g7a(C.collect_g7a(system, w, c, enc, TAUS))
        return C.judge_g8(C.collect_g8(system, w, c, enc, res))

    def test_fixed_system_holds_the_implementation_tests(self):
        for test in ("G1", "G2", "G3", "G4", "G5", "G6"):
            with self.subTest(test=test):
                self.assertIs(self.judge(test, FIXED), True)

    def test_n1a_normalizes_typicalities(self):
        enc = N1a().encode(self.world, self.ctx)
        sums = {}
        for a, u in enc.units.items():
            if a.pred.startswith("c"):
                sums[a.args[0]] = sums.get(a.args[0], 0.0) + u.mu_pos.value
        self.assertTrue(all(abs(s - 1.0) < 1e-9 for s in sums.values()))
        self.assertIs(self.judge("G1", N1a()), False)

    def test_n1b_sets_mu_neg_from_mu_pos(self):
        enc = N1b().encode(self.world, self.ctx)
        for a, u in enc.units.items():
            if a.pred.startswith("c"):
                self.assertAlmostEqual(u.mu_neg.value, 1.0 - u.mu_pos.value, places=12)
        self.assertIs(self.judge("G1", N1b()), False)

    def test_n2_changes_the_encoding_between_runs(self):
        twin = N2(RngSource(np.random.Generator(np.random.PCG64(900801))))
        self.assertNotEqual(encoding_hash(twin.encode(self.world, self.ctx)), encoding_hash(twin.encode(self.world, self.ctx)))
        self.assertIs(self.judge("G2", N2(RngSource(np.random.Generator(np.random.PCG64(900801))))), False)
        # the same rng state gives the same twin behaviour (gate K6)
        a = N2(RngSource(np.random.Generator(np.random.PCG64(900802)))).encode(self.world, self.ctx)
        b = N2(RngSource(np.random.Generator(np.random.PCG64(900802)))).encode(self.world, self.ctx)
        self.assertEqual(encoding_hash(a), encoding_hash(b))

    def test_n3_adds_prior_units_without_provenance(self):
        enc = N3().encode(self.world, self.ctx)
        priors = [u for u in enc.units.values() if not u.provenance]
        self.assertGreater(len(priors), 100)
        self.assertTrue(all(u.mu_pos.value == 0.8 and u.mu_neg.value == 0.0 for u in priors))
        self.assertIs(self.judge("G3", N3()), False)

    def test_n4_orders_ties_differently(self):
        rng = np.random.Generator(np.random.PCG64(900803))
        twin = N4(RngSource(rng))
        facts = FIXED.interface_facts(self.enc.units, 0.7)
        outs = [twin.decode(facts, self.ctx.rules, self.ctx.vocabulary, 5) for _ in range(4)]
        from audit.hashing import output_hash

        self.assertGreater(len({output_hash(o) for o in outs}), 1)
        self.assertIs(self.judge("G4", N4(RngSource(np.random.Generator(np.random.PCG64(900803))))), False)

    def test_n4_set_order_source(self):
        keys = [f"k{i}" for i in range(20)]
        order = SetOrderSource().order(keys)
        self.assertEqual(sorted(order), list(range(20)))

    def test_n2_real_run_uses_two_derived_seeds(self):
        src = PairSource(900011, 900022)
        self.assertEqual([src.draw_seed() for _ in range(4)], [900011, 900022, 900011, 900022])
        twin = N2(PairSource(900011, 900022))
        a, b = twin.encode(self.world, self.ctx), twin.encode(self.world, self.ctx)
        self.assertNotEqual(encoding_hash(a), encoding_hash(b))
        # reproducible: a fresh twin with the same pair gives the same first encoding
        twin2 = N2(PairSource(900011, 900022))
        self.assertEqual(encoding_hash(twin2.encode(self.world, self.ctx)), encoding_hash(a))
        self.assertIs(C.judge_g2(C.collect_g2(N2(PairSource(900011, 900022)), self.world, self.ctx)), False)

    def test_no_system_entropy_in_the_audit_code(self):
        import pathlib

        for p in pathlib.Path(__file__).resolve().parent.parent.joinpath("audit").rglob("*.py"):
            text = p.read_text(encoding="utf-8")
            self.assertNotIn("default_rng()", text, p.name)
            self.assertNotIn("os.urandom", text, p.name)

    def test_n5_fits_on_the_union(self):
        twin_enc = N5().encode(self.world, self.ctx)
        self.assertNotEqual(twin_enc.fit.centers, self.enc.fit.centers)
        self.assertEqual(twin_enc.derive_ids, self.enc.derive_ids)
        self.assertIs(self.judge("G5", N5()), False)

    def test_n6_inserts_hypotheses_as_observed(self):
        facts = FIXED.interface_facts(self.enc.units, 0.7)
        out = N6().decode(facts, self.ctx.rules, self.ctx.vocabulary, 10)
        self.assertTrue(out.hypotheses)
        for c in out.hypotheses:
            self.assertIs(out.facts[c.fact].status, EpistemicStatus.OBSERVED)
        self.assertIs(self.judge("G6", N6()), False)

    def test_n7_is_the_unconstrained_criterion(self):
        self.assertTrue(N7.ignore_feasibility)
        self.assertFalse(getattr(FIXED, "ignore_feasibility", False))
        d = C.collect_g7a(N7(), self.world, self.ctx, self.enc, TAUS)
        self.assertTrue(d["base_feasible"].all())  # feasibility is ignored: every baseline point is scored
        self.assertIs(C.judge_g7a(d), False)  # all_true then scores > 0

    def test_n8_overwrites_the_first_min_k_n_observations(self):
        from tesaron.enums import Channel

        for alpha in (0.9, 0.7, 0.5):
            facts = FIXED.interface_facts(self.enc.units, alpha)
            chans = {}
            for ch, a in facts:
                chans.setdefault(a, set()).add(ch)
            decided = sorted(f for f in facts if len(chans[f[1]]) == 1)
            for k in (5, 10):
                out = N8().decode(facts, self.ctx.rules, self.ctx.vocabulary, k)
                chosen = decided[: min(k, len(decided))]
                self.assertEqual(len(out.hypotheses), len(chosen))
                for (ch, atom), c in zip(chosen, out.hypotheses):
                    opposite = (Channel.NEG if ch is Channel.POS else Channel.POS, atom)
                    self.assertEqual(c.fact, opposite)
                    self.assertIs(out.facts[opposite].status, EpistemicStatus.HYPOTHESIS)
                    # the observation is gone (it can only come back as a derived fact)
                    self.assertIsNot(out.status_of(ch, atom), EpistemicStatus.OBSERVED)
            out0 = N8().decode(facts, self.ctx.rules, self.ctx.vocabulary, 0)  # k = 0: nothing is overwritten
            self.assertEqual(out0.hypotheses, ())
            self.assertTrue(set(facts) <= set(out0.facts))

    def test_n8_fails_g8_on_the_development_world(self):
        w, c = self.world, self.ctx
        for propagate in (True, False):
            twin = N8(propagate)
            enc = twin.encode(w, c)
            res = C.evaluate_grid(twin, w, c, enc)
            self.assertIs(C.judge_g8(C.collect_g8(twin, w, c, enc, res)), False)

    def test_gate_plus_systems(self):
        from audit.gate.plus_systems import NoPropagation, Oracle

        w, c, enc = self.world, self.ctx, self.enc
        # G8 plus: no encoded atom changes, hypotheses are added
        res = C.evaluate_grid(NoPropagation(), w, c, enc)
        self.assertIs(C.judge_g8(C.collect_g8(NoPropagation(), w, c, enc, res)), True)
        out = res[(0.7, 10)][0]
        hyp = {h.fact for h in out.hypotheses}
        self.assertTrue(hyp)
        self.assertEqual({out.facts[f].status for f in hyp}, {EpistemicStatus.HYPOTHESIS})
        # G7a plus: the oracle keeps I at its encoded value and gives the rest of K its world value
        _, m, ex = Oracle().evaluate_exact(w, c, enc, 0.7, 5)
        self.assertEqual((ex["new_true"], ex["new_false"], ex["uncertainty"]), (1, 0, 0))

    def test_nt_trade_off(self):
        u = [Fraction(i, 20) + Fraction(1, 10) for i in range(20)]
        nf = [Fraction(1, 10)] * 20
        out = with_trade_off(u, nf)
        self.assertEqual(out[0] - out[-1], Fraction(1, 5))  # lowest uncertainty has the highest new_false, +1/5 exactly
        self.assertEqual(out[-1], Fraction(1, 10))
        mask = [5 <= i < 15 for i in range(20)]  # the span is taken over the masked points; others unchanged
        out = with_trade_off(u, nf, mask)
        self.assertEqual(out[5] - out[14], Fraction(1, 5))
        self.assertEqual((out[0], out[19]), (nf[0], nf[19]))
        data = {"feasible": np.ones(20, dtype=bool), "uncertainty": encode_pairs(u), "new_false": encode_pairs(nf),
                "undefined": np.array([0.0])}
        self.assertIs(C.judge_t1(data), True)
        data["new_false"] = encode_pairs(with_trade_off(u, nf))
        self.assertIs(C.judge_t1(data), False)  # a trade-off of 0.2 over the span exceeds delta = 0.05

    def test_twin_table(self):
        self.assertEqual(sorted(TWINS_BY_TEST), ["G1", "G2", "G3", "G4", "G5", "G6", "G7", "G8"])
        self.assertEqual({t.__name__ for ts in TWINS_BY_TEST.values() for t in ts},
                         {"N1a", "N1b", "N2", "N3", "N4", "N5", "N6", "N7", "N8"})


class AggregateTests(unittest.TestCase):
    STRUCT = {"some_alpha_le_060_feasible": False, "alpha_ge_085_feasible": True, "t1_window_pairs": True,
              "t1_crossing_pairs": None, "t1_cross_080_085": False}

    def agg(self, test, outcomes, **kw):
        if test == "T-1":
            kw.setdefault("structure", [dict(self.STRUCT) for _ in outcomes])
        if test == "G8":
            kw.setdefault("n_hypotheses", [5] * len(outcomes))
        return aggregate_test(test, outcomes, **kw)

    @staticmethod
    def outcomes(holds, fails=0, undefined=0):
        out = ["HOLDS"] * holds + ["FAILS"] * fails + ["UNDEFINED"] * undefined
        return [(1000 + i, o) for i, o in enumerate(out)]

    def test_wilson_constant_and_edge_cases(self):
        self.assertEqual(Z_95_ONE_SIDED, 1.6448536269514722)
        self.assertGreaterEqual(wilson_lower(30, 30), 0.80)
        self.assertGreaterEqual(wilson_lower(28, 30), 0.80)
        self.assertLess(wilson_lower(27, 30), 0.80)
        self.assertEqual(wilson_lower(0, 0), 0.0)

    def test_quantitative_rule_applies_to_g8_and_t1_only(self):
        for test in ("G8", "T-1"):
            for holds, fails, verdict in ((30, 0, "HOLDS"), (28, 2, "HOLDS"), (27, 3, "FAILS"), (0, 30, "FAILS")):
                self.assertEqual(self.agg(test, self.outcomes(holds, fails))["verdict"], verdict, (test, holds))
            self.assertEqual(self.agg(test, self.outcomes(15, 0))["verdict"], "INSUFFICIENT")
            self.assertEqual(self.agg(test, self.outcomes(16, 0))["verdict"], "HOLDS")
            self.assertEqual(self.agg(test, self.outcomes(15, 1))["verdict"], "FAILS")  # 16 defined, bound 0.76
            self.assertEqual(self.agg(test, self.outcomes(14, 1, 14))["verdict"], "INSUFFICIENT")
        # G7a is deterministic: one FAILS world fails it, 29 holding worlds hold it
        self.assertEqual(self.agg("G7", self.outcomes(29, 1))["verdict"], "FAILS")
        self.assertEqual(self.agg("G7", self.outcomes(30))["verdict"], "HOLDS")

    def test_undefined_is_excluded_not_counted_as_holds(self):
        r = self.agg("G8", self.outcomes(28, 2, 5))
        self.assertEqual((r["n_defined"], r["n_undefined"], r["n_holds"]), (30, 5, 28))
        self.assertEqual(r["verdict"], "HOLDS")
        self.assertEqual(self.agg("G8", self.outcomes(10, 0, 20))["verdict"], "INSUFFICIENT")
        d = undefined_as_fails(self.outcomes(28, 2, 5))  # descriptive: UNDEFINED counted as FAILS
        self.assertEqual((d["n_holds"], d["n"]), (28, 35))
        self.assertLess(d["wilson_lower"], wilson_lower(28, 30))

    def test_deterministic_rule(self):
        self.assertEqual(self.agg("G1", self.outcomes(30))["verdict"], "HOLDS")
        r = self.agg("G1", self.outcomes(29, 1))
        self.assertEqual((r["verdict"], r["first_failing_world"]), ("FAILS", 1029))
        self.assertEqual(self.agg("G6", self.outcomes(16, 0, 14))["verdict"], "HOLDS")
        self.assertEqual(self.agg("G6", self.outcomes(15, 0, 15))["verdict"], "INSUFFICIENT")
        # one FAILS world fails the test even with fewer than 16 defined worlds
        self.assertEqual(self.agg("G6", self.outcomes(5, 1, 24))["verdict"], "FAILS")

    def test_fixed_wording(self):
        r = self.agg("G1", self.outcomes(30))
        self.assertEqual(
            r["text"],
            "G1 holds: Membership degrees are not turned into probabilities, in all 30 defined test worlds "
            "(0 undefined). (A check of the implementation or of the criterion, not a discovery.)",
        )
        self.assertEqual(
            self.agg("G3", self.outcomes(27, 3))["text"],
            "G3 does not hold: 3 of 30 defined test worlds fail; the first failing world is 1027.",
        )
        self.assertTrue(self.agg("G7", self.outcomes(30))["text"].startswith("G7a holds: "))
        r = self.agg("G8", self.outcomes(28, 2, 3))
        self.assertEqual(
            r["text"],
            "G8 holds: Creativity (abduction) preserves meaning. 28 of 30 defined worlds hold (Wilson lower bound "
            "0.817, threshold 0.80); 3 undefined. Hypotheses at (\u03b1\u2080, k = 10) over the defined worlds: minimum 5, "
            "median 5 (the mean of the two middle values), maximum 5.",
        )
        r = self.agg("G8", self.outcomes(20, 10, 2))
        self.assertIn("G8 does not hold: 20 of 30 defined worlds hold (Wilson lower bound ", r["text"])
        self.assertIn("2 undefined; the first failing world is 1020.", r["text"])
        self.assertIn(G8_FAILS_SENTENCE, r["text"])
        self.assertTrue(r["text"].endswith(r["hypotheses"]["text"]))  # the hypothesis counts close the G8 text
        self.assertIn("single decided encoded atom", G8_FAILS_SENTENCE)
        self.assertNotIn(G8_FAILS_SENTENCE, self.agg("G8", self.outcomes(30))["text"])  # only with FAILS
        t = self.agg("T-1", self.outcomes(30))
        self.assertIn("It is not a graded test of the thesis.", t["text"])  # the T-1 sentence accompanies every verdict
        self.assertTrue(t["text"].endswith(T1_HOLDS_SENTENCE))  # regime sentence, structure counts, then the caveat
        self.assertEqual(self.agg("T-1", self.outcomes(15))["text"][:5], "T-1: ")
        self.assertEqual(
            self.agg("G2", self.outcomes(15))["text"], "G2: insufficient worlds (15 defined, 16 required); no verdict."
        )
        for test in ("G8", "T-1"):
            self.assertEqual(self.agg(test, self.outcomes(30))["expected_paragraph"], EXPECTED_PARAGRAPH)
        for test in ("G1", "G7"):
            self.assertIsNone(self.agg(test, self.outcomes(30))["expected_paragraph"])
        self.assertIn("about 0.003 at a per-world rate of 0.71 (T-1)", EXPECTED_PARAGRAPH)
        self.assertIn("They say nothing about natural-language input.", LIMITATION)
        self.assertEqual(self.agg("G6", self.outcomes(20, 0, 2))["limitation"], LIMITATION)
        self.assertEqual(MIN_DEFINED, 16)

    def test_detector_qualifier(self):
        r = self.agg("G1", self.outcomes(30), detector_both=4)
        self.assertEqual(r["detector_qualifier"], "the detector did not separate on 4 worlds")
        self.assertTrue(r["text"].endswith("(the detector did not separate on 4 worlds)"))
        self.assertIsNone(self.agg("G1", self.outcomes(30), detector_both=0)["detector_qualifier"])
        self.assertIsNone(self.agg("G1", self.outcomes(29, 1), detector_both=3)["detector_qualifier"])  # FAILS

    def test_table_has_one_row_per_test_and_no_combined_verdict(self):
        per = {t: self.outcomes(30) for t in CLAIMS}
        table = verdict_table(per, structure=[self.STRUCT] * 30, n_hypotheses=[5] * 30)
        self.assertEqual([r["test"] for r in table["rows"]], ["G1", "G2", "G3", "G4", "G5", "G6", "G7", "G8", "T-1"])
        self.assertNotIn("combined", " ".join(table))
        self.assertEqual(table["limitation"], LIMITATION)
        with self.assertRaises(ValueError):
            self.agg("G9", self.outcomes(30))
        with self.assertRaises(ValueError):
            self.agg("G1", [(1, "PASS")])


if __name__ == "__main__":
    unittest.main()


class StructureAndHypothesisTests(unittest.TestCase):
    """R2-3: the T-1 structure next to the verdict (synthetic per-world structure dicts) and the G8 hypothesis counts."""

    @staticmethod
    def world(le060, ge085, window, cross060, cross080):
        return {"some_alpha_le_060_feasible": le060, "alpha_ge_085_feasible": ge085, "t1_window_pairs": window,
                "t1_crossing_pairs": cross060, "t1_cross_080_085": cross080}

    def setUp(self):
        self.worlds = (
            [self.world(True, True, True, True, True)] * 4
            + [self.world(False, True, False, None, True)] * 3
            + [self.world(False, False, None, None, None)] * 2
            + [self.world(True, False, True, False, None)] * 1
            + [self.world(True, True, True, True, True)] * 5  # undefined worlds: not counted
        )
        self.outcomes = [(i, "HOLDS" if i < 7 else "FAILS" if i < 10 else "UNDEFINED") for i in range(15)]

    def test_counts_over_the_defined_worlds_only(self):
        c = structure_counts(self.outcomes, self.worlds)
        self.assertEqual(c["n"], 10)
        self.assertEqual((c["alpha_le_060"], c["alpha_ge_085"]), (5, 7))
        self.assertEqual(c["t1_window_pairs"], {"hold": 5, "fail": 3, "none": 2})
        self.assertEqual(c["t1_crossing_pairs"], {"hold": 4, "fail": 1, "none": 5})
        self.assertEqual(c["t1_cross_080_085"], {"hold": 7, "fail": 0, "none": 3})
        with self.assertRaises(ValueError):
            structure_counts(self.outcomes, self.worlds[:3])

    def test_the_printed_sentences(self):
        c = structure_counts(self.outcomes, self.worlds)
        self.assertEqual(
            structure_text(c),
            "Structure (I-5): of 10 defined worlds, 5 had some feasible \u03b1 \u2264 0.60 and 7 some feasible "
            "\u03b1 \u2265 0.85. Pairs inside \u03b1 0.65\u20130.80: 5 hold, 3 fail, 2 none. "
            "Pairs crossing 0.60/0.65: 4/1/5. Pairs crossing 0.80/0.85: 7/0/3.",
        )
        self.assertEqual(
            t1_sentence(c),
            "In these worlds T-1 compares regimes of the three source reliabilities: on 5 of 10 defined worlds the "
            "feasible set reached \u03b1 \u2264 0.60, where the 0.60 source is admitted, and on 7 it reached "
            "\u03b1 \u2265 0.85, where the 0.80 source is excluded. T-1's outcome depends strongly on the calibrated "
            "bounds, which vary between calibration draws. It is not a graded test of the thesis.",
        )

    def test_the_t1_text_carries_the_structure_and_the_holds_sentence(self):
        outcomes = [(i, "HOLDS") for i in range(30)]
        worlds = [self.world(False, True, True, None, True)] * 30
        r = aggregate_test("T-1", outcomes, structure=worlds)
        self.assertEqual(r["verdict"], "HOLDS")
        self.assertIn(t1_sentence(r["structure"]), r["text"])
        self.assertIn(T1_HOLDS_SENTENCE, r["text"])
        # the order of the T-1 text (R3-9): the regime sentence, then the structure counts, then (HOLDS only) the caveat
        text = r["text"]
        self.assertLess(text.index(t1_sentence(r["structure"])), text.index(structure_text(r["structure"])))
        self.assertLess(text.index(structure_text(r["structure"])), text.index(T1_HOLDS_SENTENCE))
        self.assertTrue(text.endswith(T1_HOLDS_SENTENCE))
        self.assertEqual(r["structure"]["alpha_le_060"], 0)
        fails = aggregate_test("T-1", [(i, "FAILS") for i in range(30)], structure=worlds)
        self.assertNotIn(T1_HOLDS_SENTENCE, fails["text"])  # only with a HOLDS verdict
        self.assertTrue(fails["text"].endswith(structure_text(fails["structure"])))
        self.assertIn(t1_sentence(fails["structure"]), fails["text"])
        few = aggregate_test("T-1", [(i, "HOLDS") for i in range(10)] + [(99, "UNDEFINED")] * 20, structure=worlds)
        self.assertEqual(few["verdict"], "INSUFFICIENT")
        self.assertIn(t1_sentence(few["structure"]), few["text"])  # the regime sentence is printed for every verdict
        self.assertTrue(few["text"].endswith(structure_text(few["structure"])))
        self.assertIn("Structure (I-5): of 10 defined worlds", few["text"])
        self.assertLess(few["text"].index("compares regimes"), few["text"].index("Structure (I-5)"))
        self.assertNotIn(T1_HOLDS_SENTENCE, few["text"])
        with self.assertRaises(ValueError):
            aggregate_test("T-1", outcomes)  # the structure is required
        self.assertIsNone(aggregate_test("G1", outcomes)["structure"])

    def test_expected_paragraph_ends_with_the_calibrated_bounds_sentence(self):
        self.assertTrue(EXPECTED_PARAGRAPH.endswith(
            "A different outcome would mean that the test worlds, or for T-1 the calibrated bounds, differ from the "
            "development ones (see the structure counts)."))

    def test_expected_paragraph_mentions_insufficient_worlds(self):
        self.assertIn("T-1 and G8 are expected to FAIL. T-1 may also end in \"insufficient worlds\": on development "
                      "worlds its number of defined worlds varied strongly between calibration draws.",
                      EXPECTED_PARAGRAPH)

    def test_failed_g1_parts_are_named(self):
        outcomes = [(1000 + i, "FAILS" if i == 3 else "HOLDS") for i in range(30)]
        r = aggregate_test("G1", outcomes, failed_parts={1003: ["(i)", "(ii)"]})
        self.assertTrue(r["text"].endswith("the first failing world is 1003. Failed parts in the first failing world: (i), (ii)."))
        plain = aggregate_test("G1", outcomes)
        self.assertNotIn("Failed parts", plain["text"])
        other = aggregate_test("G2", outcomes, failed_parts={1003: ["(ii)"]})
        self.assertNotIn("Failed parts", other["text"])  # G1 only

    def test_hypothesis_summary_odd_and_even(self):
        odd = [(i, "HOLDS") for i in range(5)] + [(9, "UNDEFINED")]
        s = hypothesis_summary(odd, [3, 1, 7, 5, 9, 100])
        self.assertEqual((s["n"], s["min"], s["median"], s["max"]), (5, 1, "5", 9))
        self.assertEqual(s["text"], "Hypotheses at (\u03b1\u2080, k = 10) over the defined worlds: minimum 1, median 5, maximum 9.")
        even = [(i, "FAILS") for i in range(4)]
        s = hypothesis_summary(even, [2, 8, 4, 5])
        self.assertEqual((s["min"], s["median"], s["max"]), (2, "4.5", 8))  # the mean of the middle values 4 and 5
        self.assertIn("median 4.5 (the mean of the two middle values)", s["text"])
        self.assertEqual(hypothesis_summary(even, [1, 1, 1, 7])["median"], "1")
        self.assertEqual(hypothesis_summary([(0, "UNDEFINED")], [0])["n"], 0)
        with self.assertRaises(ValueError):
            hypothesis_summary(even, [1, 2])

    def test_g8_text_carries_the_hypothesis_counts(self):
        outcomes = [(i, "HOLDS") for i in range(30)]
        r = aggregate_test("G8", outcomes, n_hypotheses=list(range(30)))
        self.assertIn("minimum 0, median 14.5 (the mean of the two middle values), maximum 29.", r["text"])
        self.assertEqual(r["hypotheses"]["median"], "14.5")
        with self.assertRaises(ValueError):
            aggregate_test("G8", outcomes)  # the counts are required
        self.assertIsNone(aggregate_test("G1", outcomes)["hypotheses"])
