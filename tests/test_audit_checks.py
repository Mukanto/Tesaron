"""Judges on hand-made and collected arrays: holds, fails, undefined, and the anchors (zero and noise data never
HOLD, as in the gate's probes K5)."""

import unittest

import numpy as np

from audit import checks as C
from audit.cache import get_encoding
from audit.system import FIXED
from fractions import Fraction

from audit.exact import ExactTaus, encode_pairs
from tesaron.criterion.wisdom import Point, t1_world

WORLD, CTX, ENC = None, None, None
TAUS = ExactTaus(Fraction(4, 5), Fraction(1, 20), Fraction(9, 10), Fraction(1, 2))


def setUpModule():
    global WORLD, CTX, ENC
    WORLD, CTX, ENC = get_encoding(900001, 900101)


def zeros_probe(data):
    out = {}
    for k, v in data.items():
        v = np.asarray(v)
        out[k] = np.zeros(v.shape, dtype=bool) if v.dtype == np.bool_ else np.zeros(v.shape, dtype=np.float64)
    return out


def noise_probe(data, rng):
    out = {}
    for k, v in data.items():
        v = np.asarray(v)
        out[k] = (rng.random(v.shape) < 0.5) if v.dtype == np.bool_ else rng.standard_normal(v.shape)
    return out


def copy(d):
    return {k: np.array(v, copy=True) for k, v in d.items()}


class AnchorMixin:
    """Zero data and noise never HOLD (a FAILS or an UNDEFINED is acceptable)."""

    def assert_anchored(self, judge, data, n_noise=40):
        self.assertIsNot(judge(zeros_probe(data)), True, "zero data holds")
        rng = np.random.Generator(np.random.PCG64(900901))
        for _ in range(n_noise):
            self.assertIsNot(judge(noise_probe(data, rng)), True, "noise holds")


class G1Tests(unittest.TestCase, AnchorMixin):
    def test_collected_holds_and_variants_fail(self):
        d = C.collect_g1(FIXED, WORLD, CTX, ENC)
        self.assertIs(C.judge_g1(d), True)
        self.assertEqual(d["outlier_pos"].shape[1], 3)
        bad = copy(d)  # (i) an outlier whose typicalities sum to >= 0.5
        bad["outlier_pos"][0] = [0.3, 0.3, 0.3]
        self.assertIs(C.judge_g1(bad), False)
        bad = copy(d)  # (ii) a class unit of ANY entity with mu_neg derived from mu_pos
        bad["class_pos"][5] = 0.01
        bad["class_neg"][5] = 0.99
        self.assertIs(C.judge_g1(bad), False)
        self.assertEqual(len(d["class_pos"]), len([a for a in ENC.units if a.pred.startswith("c")]))
        bad = copy(d)  # (iii) anchor: median own-class typicality of normal entities below 0.5
        bad["own_typicality"] = bad["own_typicality"] * 0.0 + 0.2
        self.assertIs(C.judge_g1(bad), False)
        self.assert_anchored(C.judge_g1, d)

    def test_any_nonzero_class_mu_neg_fails_part_ii_even_when_not_encoded_f(self):
        # R2-13: (ii) is "every class unit of every entity has mu_neg = 0.0 exactly", not "none is encoded F"
        d = C.collect_g1(FIXED, WORLD, CTX, ENC)
        self.assertEqual(C.g1_failed_parts(d), [])
        small = copy(d)
        small["class_neg"][3] = 1e-9  # far below alpha0: no atom is encoded F, but mu_neg is not 0
        small["class_pos"][3] = 0.9
        self.assertIs(C.judge_g1(small), False)
        self.assertEqual(C.g1_failed_parts(small), ["(ii)"])
        ok = copy(d)  # a high mu_neg next to a high mu_pos (B) fails as well
        ok["class_neg"][4] = 0.9
        ok["class_pos"][4] = 0.9
        self.assertEqual(C.g1_failed_parts(ok), ["(ii)"])

    def test_failed_parts_name_every_failing_part(self):
        d = C.collect_g1(FIXED, WORLD, CTX, ENC)
        bad = copy(d)
        bad["outlier_pos"][0] = [0.3, 0.3, 0.3]
        bad["class_neg"][0] = 0.5
        bad["own_typicality"] = bad["own_typicality"] * 0.0 + 0.2
        self.assertEqual(C.g1_failed_parts(bad), ["(i)", "(ii)", "(iii)"])
        self.assertEqual(C.g1_parts(bad), (False, False, False))
        only_i = copy(d)
        only_i["outlier_pos"][0] = [0.3, 0.3, 0.3]
        self.assertEqual(C.g1_failed_parts(only_i), ["(i)"])

    def test_twin_n1b_still_fails_part_ii(self):
        from audit.twins import N1b

        d = C.collect_g1(N1b(), WORLD, CTX, N1b().encode(WORLD, CTX))
        self.assertIs(C.judge_g1(d), False)
        self.assertIn("(ii)", C.g1_failed_parts(d))
        from audit.twins import N1a

        self.assertIs(C.judge_g1(C.collect_g1(N1a(), WORLD, CTX, N1a().encode(WORLD, CTX))), False)


class G2G4Tests(unittest.TestCase, AnchorMixin):
    def test_g2(self):
        d = C.collect_g2(FIXED, WORLD, CTX)
        self.assertIs(C.judge_g2(d), True)
        for k in ("h1", "h2", "h_alt"):
            self.assertEqual(d[k].dtype, np.uint64)
        bad = copy(d)
        bad["h2"] = bad["h2"] + np.uint64(1)
        self.assertIs(C.judge_g2(bad), False)
        bad = copy(d)  # anchor: another encoder seed must give another hash
        bad["h_alt"] = bad["h1"].copy()
        self.assertIs(C.judge_g2(bad), False)
        with_sub = copy(d)
        with_sub["h_sub"] = d["h1"].copy()
        self.assertIs(C.judge_g2(with_sub), True)
        with_sub["h_sub"] = d["h1"] + np.uint64(1)
        self.assertIs(C.judge_g2(with_sub), False)
        self.assert_anchored(C.judge_g2, d)

    def test_g4(self):
        rngs = [np.random.Generator(np.random.PCG64(900700 + i)) for i in range(3)]
        d = C.collect_g4(FIXED, WORLD, CTX, ENC, rngs)
        self.assertIs(C.judge_g4(d), True)
        self.assertEqual(d["h_perm"].shape, (3, 2))
        bad = copy(d)
        bad["h_perm"][1] = bad["h_perm"][1] + np.uint64(1)
        self.assertIs(C.judge_g4(bad), False)
        bad = copy(d)
        bad["fixpoints_equal"] = np.array([False])
        self.assertIs(C.judge_g4(bad), False)
        bad = copy(d)  # anchor: the output has at least one fact
        bad["n_facts"] = np.array([0])
        self.assertIs(C.judge_g4(bad), False)
        sub = copy(d)
        sub["h_sub"] = np.stack([d["h0"]] * 3)
        self.assertIs(C.judge_g4(sub), True)
        sub["h_sub"][2] = sub["h_sub"][2] + np.uint64(1)
        self.assertIs(C.judge_g4(sub), False)
        self.assert_anchored(C.judge_g4, d)


class G3G5G6Tests(unittest.TestCase, AnchorMixin):
    def test_g3(self):
        d = C.collect_g3(FIXED, WORLD, CTX, ENC)
        self.assertIs(C.judge_g3(d), True)
        self.assertTrue(d["decided_before"].any() and not d["decided_after"].any())
        bad = copy(d)
        bad["decided_after"][int(np.argmax(d["decided_before"]))] = True
        self.assertIs(C.judge_g3(bad), False)
        bad = copy(d)  # anchor: at least one ablated unit decided before
        bad["decided_before"][:] = False
        self.assertIs(C.judge_g3(bad), False)
        self.assert_anchored(C.judge_g3, d)

    def test_g5(self):
        d = C.collect_g5(FIXED, WORLD, CTX, ENC)
        self.assertIs(C.judge_g5(d), True)
        bad = copy(d)
        bad["centers_val_corrupt"] = bad["centers"] + 1e-15 + 1e-9
        self.assertIs(C.judge_g5(bad), False)
        bad = copy(d)
        bad["unit_map_val_corrupt"] = bad["unit_map"] + np.uint64(1)
        self.assertIs(C.judge_g5(bad), False)
        bad = copy(d)  # anchor: corrupting D_derive changes the centers
        bad["centers_der_corrupt"] = bad["centers"].copy()
        self.assertIs(C.judge_g5(bad), False)
        self.assert_anchored(C.judge_g5, d)

    def test_g5_selection_is_unchanged_by_corruption(self):
        from audit.checks import corrupt_world
        from tesaron.encoder import encode

        enc_v = encode(corrupt_world(WORLD, ENC.validate_ids), CTX)
        enc_d = encode(corrupt_world(WORLD, ENC.derive_ids), CTX)
        for e in (enc_v, enc_d):
            self.assertEqual((e.selected_ids, e.derive_ids, e.validate_ids),
                             (ENC.selected_ids, ENC.derive_ids, ENC.validate_ids))
        # only values and polarities of the chosen rows changed, ids are the same
        self.assertEqual([f.row_id for f in corrupt_world(WORLD, ENC.derive_ids).feature_rows],
                         [f.row_id for f in WORLD.feature_rows])
        changed = [f for f, g in zip(WORLD.feature_rows, corrupt_world(WORLD, ENC.validate_ids).feature_rows) if f != g]
        self.assertTrue(changed and all(f.row_id in set(ENC.validate_ids) for f in changed))

    def test_g6(self):
        d = C.collect_g6(FIXED, WORLD, CTX, ENC)
        self.assertIs(C.judge_g6(d), True)
        bad = copy(d)  # a hypothesis labelled OBSERVED while outside the pass-1 fixpoint
        i = int(np.argmax(~d["in_pass1"]))
        self.assertFalse(d["in_pass1"][i])
        bad["status"][i] = 3
        self.assertIs(C.judge_g6(bad), False)
        bad = copy(d)  # a solid fact claimed that the pass-1 fixpoint does not contain
        j = int(np.argmax(d["status"] == 3))
        bad["in_pass1"][j] = False
        self.assertIs(C.judge_g6(bad), False)
        und = copy(d)
        und["no_candidate"] = np.array([10.0])
        self.assertIsNone(C.judge_g6(und))
        self.assert_anchored(C.judge_g6, d)


class G7aTests(unittest.TestCase, AnchorMixin):
    def test_collected_holds_with_a_feasible_oracle(self):
        from audit.gate.common import gate_taus

        d = C.collect_g7a(FIXED, WORLD, CTX, ENC, gate_taus())  # tau by the D1 rule on development worlds
        self.assertEqual(d["base_feasible"].shape, (5, 10))
        self.assertEqual(d["oracle_feasible"].shape, (10,))
        self.assertIs(C.judge_g7a(d), True)
        strict = ExactTaus(Fraction(2), Fraction(0), Fraction(2), Fraction(0))  # nothing is feasible
        d2 = C.collect_g7a(FIXED, WORLD, CTX, ENC, strict)
        self.assertIsNone(C.judge_g7a(d2))  # the oracle has no feasible point under strict tau: UNDEFINED

    def test_judge_rules(self):
        base = {"base_feasible": np.zeros((5, 10), dtype=bool), "base_positive": np.ones((5, 10), dtype=bool),
                "oracle_feasible": np.ones(10, dtype=bool), "oracle_positive": np.ones(10, dtype=bool),
                "no_oracle": np.array([0.0])}
        self.assertIs(C.judge_g7a(base), True)  # every baseline infeasible
        d = copy(base)
        d["base_feasible"][2, 3] = True  # a feasible baseline with a positive score
        self.assertIs(C.judge_g7a(d), False)
        d["base_positive"][2, 3] = False  # feasible but scores 0
        self.assertIs(C.judge_g7a(d), True)
        d = copy(base)
        d["oracle_positive"][:] = False  # anchor: the oracle must score > 0 at some alpha
        self.assertIs(C.judge_g7a(d), False)
        d = copy(base)
        d["oracle_feasible"][:] = False
        d["oracle_positive"][:] = True  # an infeasible oracle scores 0
        self.assertIs(C.judge_g7a(d), False)
        d["no_oracle"] = np.array([10.0])
        self.assertIsNone(C.judge_g7a(d))
        self.assert_anchored(C.judge_g7a, base)

    def test_unconstrained_criterion_fails_and_baselines_cannot_score(self):
        from audit.twins import N7

        taus = ExactTaus(Fraction(1, 2), Fraction(1), Fraction(0), Fraction(1))
        plus = C.collect_g7a(FIXED, WORLD, CTX, ENC, taus)
        minus = C.collect_g7a(N7(), WORLD, CTX, ENC, taus)
        self.assertTrue(np.asarray(minus["base_feasible"]).all())  # feasibility ignored
        self.assertIs(C.judge_g7a(minus), False)  # all_true then scores > 0
        self.assertIsNot(C.judge_g7a(plus), None)

    def test_score_is_exactly_positive_or_zero(self):
        self.assertTrue(C._score_positive({"new_true": Fraction(1, 3), "new_false": Fraction(1, 2)}))
        self.assertFalse(C._score_positive({"new_true": Fraction(0), "new_false": Fraction(1, 2)}))
        self.assertFalse(C._score_positive({"new_true": Fraction(1, 2), "new_false": Fraction(1)}))
        self.assertFalse(C._score_positive({"new_true": None, "new_false": Fraction(0)}))


def fid_array(rows):
    """rows: per alpha a list of three Fractions or None (k = 0, 5, 10) -> (alphas, 3, 2) pair array."""
    return encode_pairs([f for r in rows for f in r]).reshape(len(rows), 3, 2)


class G8Tests(unittest.TestCase, AnchorMixin):
    @staticmethod
    def data(fid, dev, n_hyp=3, undefined=0.0):
        return {"fidelity": fid_array(fid), "deviation": fid_array(dev), "n_hypotheses": np.array([n_hyp]),
                "undefined": np.array([undefined])}

    def flat(self, v):
        return [[Fraction(v)] * 3 for _ in range(10)]

    def test_collected_shapes_and_exactness(self):
        res = C.evaluate_grid(FIXED, WORLD, CTX, ENC)
        d = C.collect_g8(FIXED, WORLD, CTX, ENC, res)
        self.assertEqual(d["fidelity"].shape, (10, 3, 2))
        for i, a in enumerate(C.ALPHAS):
            for j, k in enumerate(C.KS):
                ex = res[(a, k)][2]
                self.assertEqual(Fraction(int(d["deviation"][i, j, 0]), int(d["deviation"][i, j, 1])), ex["deviation"])
        self.assertIn(C.judge_g8(d), (True, False, None))

    def test_exact_boundaries(self):
        ok = self.data(self.flat(Fraction(4, 5)), self.flat(0))
        self.assertIs(C.judge_g8(ok), True)
        edge = [[Fraction(1, 20), Fraction(0), Fraction(0)] for _ in range(10)]  # a drop of exactly 0.05
        self.assertIs(C.judge_g8(self.data(edge, self.flat(0))), True)
        over = [[Fraction(21, 400), Fraction(0), Fraction(0)] for _ in range(10)]  # 0.0525 > 0.05
        self.assertIs(C.judge_g8(self.data(over, self.flat(0))), False)
        dev_edge = [[Fraction(0), Fraction(1, 50), Fraction(1, 50)] for _ in range(10)]  # a rise of exactly 0.02
        self.assertIs(C.judge_g8(self.data(self.flat(Fraction(4, 5)), dev_edge)), True)
        dev_over = [[Fraction(0), Fraction(1, 49), Fraction(0)] for _ in range(10)]  # 1/49 > 0.02 (one atom of 49)
        self.assertIs(C.judge_g8(self.data(self.flat(Fraction(4, 5)), dev_over)), False)

    def test_undefined_fidelity_is_skipped_and_all_skipped_is_undefined(self):
        fid = self.flat(Fraction(4, 5))
        fid[3] = [None, None, None]
        fid[4] = [Fraction(4, 5), None, Fraction(1, 5)]  # k = 10 drops by 0.6 but k = 5 is skipped
        self.assertIs(C.judge_g8(self.data(fid, self.flat(0))), False)
        fid[4] = [Fraction(4, 5), None, Fraction(4, 5)]
        self.assertIs(C.judge_g8(self.data(fid, self.flat(0))), True)
        # every comparison skipped: collect() flags it undefined
        self.assertIsNone(C.judge_g8(self.data([[None] * 3] * 10, self.flat(0), undefined=10.0)))
        self.assertIsNone(C.judge_g8(self.data(self.flat(1), self.flat(0), undefined=10.0)))  # no hypothesis

    def test_anchors(self):
        ok = self.data(self.flat(Fraction(4, 5)), self.flat(0))
        self.assertIs(C.judge_g8(self.data(self.flat(Fraction(4, 5)), self.flat(0), n_hyp=0)), False)
        self.assertIs(C.judge_g8(self.data([[None] * 3] * 10, self.flat(0))), False)  # nothing compared
        self.assert_anchored(C.judge_g8, ok)

    def with_atoms(self, d, n_I=40, n_decided=40):
        d["n_I"] = np.array([n_I] * 10, dtype=np.int64)
        d["n_decided"] = np.array([n_decided] * 10, dtype=np.int64)
        return d

    def test_collected_raw_denominators(self):
        res = C.evaluate_grid(FIXED, WORLD, CTX, ENC)
        d = C.collect_g8(FIXED, WORLD, CTX, ENC, res)
        self.assertEqual(d["n_I"].shape, (10,))
        for i, a in enumerate(C.ALPHAS):
            self.assertEqual(int(d["n_I"][i]), res[(a, 0)][1].size_I)
            self.assertEqual(int(d["n_I"][i]), res[(a, 10)][1].size_I)  # |I| does not depend on k
            for j in range(3):  # the stored fractions are in lowest terms: the raw denominator divides evenly
                if int(d["fidelity"][i, j, 1]):
                    self.assertEqual(int(d["n_I"][i]) % int(d["fidelity"][i, j, 1]), 0)
                if int(d["deviation"][i, j, 1]) > 1:
                    self.assertEqual(int(d["n_decided"][i]) % int(d["deviation"][i, j, 1]), 0)
        self.assertEqual(set(C.DECLARED_KEYS["G8"]) - set(d), set())

    def test_single_atom_descriptive_reading(self):
        from audit.descriptive import g8_single_atom_only

        # one atom of 40 decided encoded atoms is 1/40 > 0.02: a FAIL through a single-atom change
        fid = self.flat(Fraction(4, 5))
        dev = [[Fraction(0), Fraction(1, 40), Fraction(0)] for _ in range(10)]
        d = self.with_atoms(self.data(fid, dev))
        d["deviation"][:, 1, :] = np.array([1, 40])
        self.assertIs(C.judge_g8(d), False)
        self.assertIs(g8_single_atom_only(d), True)
        d["deviation"][2, 1, :] = np.array([3, 40])  # three atoms at one alpha
        self.assertIs(g8_single_atom_only(d), False)
        ok = self.with_atoms(self.data(fid, self.flat(0)))
        self.assertIsNone(g8_single_atom_only(ok))  # not a FAILS world

    def test_single_atom_reading_uses_the_raw_denominator_deviation_2_of_40(self):
        # R2-5: a rise of 2 atoms out of 40 is stored as 1/20 in lowest terms; it is two atoms, not one
        from audit.descriptive import g8_single_atom_only

        dev = [[Fraction(0), Fraction(2, 40), Fraction(0)] for _ in range(10)]
        d = self.with_atoms(self.data(self.flat(Fraction(4, 5)), dev), n_I=40, n_decided=40)
        self.assertEqual(tuple(d["deviation"][0, 1]), (1, 20))  # stored reduced
        self.assertIs(C.judge_g8(d), False)
        self.assertIs(g8_single_atom_only(d), False)
        one = [[Fraction(0), Fraction(1, 40), Fraction(0)] for _ in range(10)]  # a single atom
        self.assertIs(g8_single_atom_only(self.with_atoms(self.data(self.flat(Fraction(4, 5)), one))), True)

    def test_single_atom_reading_uses_the_raw_denominator_fidelity_9_of_18(self):
        # R2-5: fidelity 11/18 -> 9/18 is a drop of 2 atoms; the stored 1/2 would make it look like one
        from audit.descriptive import g8_single_atom_only

        fid = [[Fraction(11, 18), Fraction(9, 18), Fraction(11, 18)] for _ in range(10)]
        d = self.with_atoms(self.data(fid, self.flat(0)), n_I=18, n_decided=18)
        self.assertEqual(tuple(d["fidelity"][0, 1]), (1, 2))  # stored reduced
        self.assertIs(C.judge_g8(d), False)
        self.assertIs(g8_single_atom_only(d), False)
        one = [[Fraction(1), Fraction(17, 18), Fraction(1)] for _ in range(10)]  # one atom of 18: 1/18 > 0.05
        d = self.with_atoms(self.data(one, self.flat(0)), n_I=18, n_decided=18)
        self.assertIs(C.judge_g8(d), False)
        self.assertIs(g8_single_atom_only(d), True)
        self.assertIn("lowest terms", g8_single_atom_only.__doc__)
        self.assertNotIn("share a denominator", g8_single_atom_only.__doc__)


class T1Tests(unittest.TestCase, AnchorMixin):
    @staticmethod
    def data(unc, nf, feasible=None, undefined=0.0):
        n = len(unc)
        return {"feasible": np.array(feasible if feasible is not None else [True] * n),
                "uncertainty": encode_pairs([Fraction(x) for x in unc]),
                "new_false": encode_pairs([Fraction(x) for x in nf]), "undefined": np.array([undefined])}

    def test_exact_delta(self):
        F = Fraction
        self.assertIs(C.judge_t1(self.data([F(2, 5), F(1, 5), F(1, 10)], [F(3, 10), F(17, 50), F(1, 4)])), True)
        self.assertIs(C.judge_t1(self.data([F(2, 5), F(1, 5)], [F(1, 4), F(3, 10)])), True)  # exactly delta = 1/20
        self.assertIs(C.judge_t1(self.data([F(2, 5), F(1, 5)], [F(1, 4), F(31, 100)])), False)  # 0.06 > 0.05
        self.assertIs(C.judge_t1(self.data([F(2, 5), F(1, 5), F(1, 10)], [F(3, 10), F(17, 50), F(2, 5)])), False)

    def test_float_tie_is_decided_exactly(self):
        # 0.35 - 0.30 is 0.04999999999999999 in floats; as 7/20 - 3/10 it is exactly 1/20, which holds
        F = Fraction
        self.assertIs(C.judge_t1(self.data([F(1, 2), F(1, 4)], [F(3, 10), F(7, 20)])), True)
        self.assertIs(C.judge_t1(self.data([F(1, 2), F(1, 4)], [F(3, 10), F(7, 20) + F(1, 10**9)])), False)

    def test_definedness_and_anchor(self):
        F = Fraction
        self.assertIsNone(C.judge_t1(self.data([F(1, 2), F(1, 4)], [F(1, 10)] * 2, undefined=10.0)))
        one = self.data([F(1, 2), F(1, 4)], [F(1, 10), F(1, 2)], feasible=[True, False])
        self.assertIs(C.judge_t1(one), False)  # one feasible point: nothing to compare (anchor)
        same = self.data([F(1, 4), F(1, 4)], [F(1, 10), F(1, 2)])
        self.assertIs(C.judge_t1(same), False)  # equal uncertainty: no pair
        unc = [Fraction(i, 40) for i in range(1, 31)]
        base = self.data(unc, [Fraction(3, 10) + Fraction(i, 1000) for i in range(30)])
        self.assertIs(C.judge_t1(base), True)
        self.assert_anchored(C.judge_t1, base)

    def test_collect_t1_feasibility_and_definedness(self):
        F = Fraction
        ex = lambda f, u: {"fidelity": f, "deviation": F(0), "consistency": F(1), "uncertainty": u, "new_true": F(1, 2),
                           "new_false": F(1, 10)}
        points = [ex(F(9, 10), F(3, 10)), ex(F(9, 10), F(3, 10)), ex(F(1, 2), F(1, 5))]
        d = C.collect_t1(points, TAUS)
        self.assertEqual(d["feasible"].tolist(), [True, True, False])
        self.assertEqual(float(d["undefined"][0]), 10.0)  # two feasible points, equal uncertainty
        points[1] = ex(F(9, 10), F(1, 4))
        self.assertEqual(float(C.collect_t1(points, TAUS)["undefined"][0]), 0.0)
        points[0]["new_true"] = None  # an undefined new_true is infeasible
        self.assertEqual(C.collect_t1(points, TAUS)["feasible"].tolist(), [False, True, False])
        tight = ExactTaus(F(9, 10), F(0), F(1), F(3, 10))  # tau compared exactly: uncertainty 3/10 <= 3/10 holds
        self.assertTrue(C.collect_t1([ex(F(9, 10), F(3, 10))], tight)["feasible"][0])

    def test_judge_matches_tesaron_t1_world_on_real_grid_points(self):
        res = C.evaluate_grid(FIXED, WORLD, CTX, ENC)
        exacts = C.exact_list(res)
        taus = ExactTaus(Fraction(1, 2), Fraction(1, 5), Fraction(1, 2), Fraction(9, 10))
        d = C.collect_t1(exacts, taus)
        feas = d["feasible"]
        pts = [Point(1 - e["new_false"].__float__(), 0.5, bool(f), None, float(e["uncertainty"]), float(e["new_false"]))
               for e, f in zip(exacts, feas)]
        expected = t1_world(pts, 0.05).value
        got = {True: "pass", False: "fail", None: "undefined"}[C.judge_t1(d)]
        self.assertIn(got, ("pass", "fail", "undefined"))
        if expected != "undefined":
            self.assertEqual(got, expected)  # floats and exact agree unless a tie sits on delta

    def test_structure_arm(self):
        from audit.descriptive import t1_structure

        F = Fraction
        grid_points = []
        for a, k in C.GRID:
            u = F(1, 10) + F(int(round((0.95 - a) * 20)), 20)  # uncertainty falls as alpha falls
            nf = F(1, 10) if a >= 0.65 else F(1, 2)  # a jump below the 0.65/0.60 boundary
            grid_points.append({"fidelity": F(9, 10), "deviation": F(0), "consistency": F(1), "uncertainty": F(1, 2) - u / 2,
                                "new_true": F(1, 2), "new_false": nf})
        taus = ExactTaus(F(1, 2), F(1, 2), F(1, 2), F(1))
        st = t1_structure(grid_points, taus)
        self.assertEqual(st["feasible_alphas"], sorted(C.ALPHAS, reverse=True))
        self.assertTrue(st["some_alpha_le_060_feasible"])
        self.assertIs(st["t1_crossing_pairs"], False)  # new_false jumps across the 0.60/0.65 boundary
        self.assertIs(st["t1_window_pairs"], True)  # flat inside alpha 0.65-0.80

    def test_grid_constants(self):
        self.assertEqual(len(C.GRID), 30)
        self.assertEqual(C.ALPHAS[0], 0.95)
        self.assertEqual(C.ALPHAS[-1], 0.5)
        self.assertIn(0.7, C.ALPHAS)
        from audit.exact import DELTA, EPS_D, EPS_F

        self.assertEqual((EPS_F, EPS_D, DELTA), (Fraction(1, 20), Fraction(1, 50), Fraction(1, 20)))

    def test_declared_keys_are_returned(self):
        res = C.evaluate_grid(FIXED, WORLD, CTX, ENC)
        self.assertTrue(set(C.DECLARED_KEYS["G8"]) <= set(C.collect_g8(FIXED, WORLD, CTX, ENC, res)))
        self.assertTrue(set(C.DECLARED_KEYS["G7"]) <= set(C.collect_g7a(FIXED, WORLD, CTX, ENC, TAUS)))
        self.assertTrue(set(C.DECLARED_KEYS["T-1"]) <= set(C.collect_t1(C.exact_list(res), TAUS)))
        for t, collect in (("G1", C.collect_g1), ("G3", C.collect_g3), ("G5", C.collect_g5), ("G6", C.collect_g6)):
            self.assertTrue(set(C.DECLARED_KEYS[t]) <= set(collect(FIXED, WORLD, CTX, ENC)), t)
        self.assertTrue(set(C.DECLARED_KEYS["G2"]) <= set(C.collect_g2(FIXED, WORLD, CTX)))
        self.assertEqual(sorted(C.DECLARED_KEYS), sorted(C.TEST_IDS))


class G6BruteForceTests(unittest.TestCase):
    def test_g6_does_not_use_tesaron_decoder_closure(self):
        import inspect

        src = inspect.getsource(C.collect_g6)
        self.assertIn("closure_fact_keys", src)
        self.assertNotIn("naive_eval", src)

    def test_g2_judge_with_two_subprocess_hashes(self):
        d = C.collect_g2(FIXED, WORLD, CTX)
        ok = copy(d)
        ok["h_sub"] = np.stack([d["h1"], d["h1"]])
        self.assertIs(C.judge_g2(ok), True)
        ok["h_sub"][1] = ok["h_sub"][1] + np.uint64(1)
        self.assertIs(C.judge_g2(ok), False)


if __name__ == "__main__":
    unittest.main()
