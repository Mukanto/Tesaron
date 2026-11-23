"""Unit tests of the v0.3 audit layer on synthetic data (seeds, tau, T-1 at k = 0, the structure arm, aggregation, the fixed
wording, the redaction boundary, the twins and the runner's git helpers). Nothing here prints or inspects a T-1 or G8 value of a
real v0.3 world: the T-1, G8 and aggregation logic runs on synthetic metric arrays (PREREG_v0.3 section 2)."""

import hashlib
import os
import re
import subprocess
import sys
import unittest
from fractions import Fraction as F
from pathlib import Path
from unittest import mock

import numpy as np

from audit import checks as C
from audit.exact import ExactTaus, feasible, frac_str
from audit.v03 import aggregate as AG
from audit.v03 import checks as V
from audit.v03 import redact as R
from audit.v03 import seeds as S
from audit.v03.run_v03 import MANIFEST_REL, STUDY_JSON, tracked_manifest_files
from audit.v03.tau import d1_first, metrics_to_json, q40, taus_from_json, taus_to_json

ROOT = Path(__file__).resolve().parent.parent
PREREG = ROOT / "prereg" / "PREREG_v0.3.md"
ALPHAS = V.ALPHAS


def ex(f="1", d="0", c="1", u="0", nt="1/2", nf="0", nq=0):
    """An exact metric dict as T-1 reads it: nq is n_q, the denominator of new_false (0: tolerance delta only)."""
    return {"fidelity": F(f), "deviation": F(d), "consistency": F(c), "uncertainty": F(u), "new_true": F(nt),
            "new_false": F(nf), "n_q": nq}


BAD = dict(f="0", u="1")  # infeasible under TAUS
TAUS = ExactTaus(F(1, 2), F(1, 10), F(1, 2), F(1, 2))


def line(**by_alpha):
    """10 exact metric dicts in ALPHAS order; by_alpha maps "a090" (alpha 0.90) etc. to ex(...) kwargs; the rest is BAD."""
    out = []
    for a in ALPHAS:
        key = f"a{int(round(a * 100)):03d}"
        out.append(ex(**by_alpha[key]) if key in by_alpha else ex(**BAD))
    return out


def norm(text: str) -> str:
    """The PREREG text with line wraps, list indents and blockquote marks collapsed to single spaces."""
    lines = [re.sub(r"^\s*>\s?", "", ln) for ln in text.splitlines()]
    return " ".join(" ".join(lines).split())


# ---------------------------------------------------------------------------------------------------------- seeds
class SeedTests(unittest.TestCase):
    def test_formula_and_roles(self):
        core, salt = "c" * 64, "s" * 64
        for role, i in (("world-test", 0), ("aux", 7), ("perm", 149), ("n2", 99), ("world-calalt-0", 3),
                        ("enc-calalt-19", 199)):
            digest = hashlib.sha256(f"{core}|{salt}|{role}|{i}".encode()).digest()
            self.assertEqual(S.seed(core, salt, role, i), 1_000_000 + int.from_bytes(digest[:8], "big") % 10**9)
        self.assertEqual(len(S.ROLES), 7 + 40)
        for b in range(20):
            self.assertIn(f"world-calalt-{b}", S.ROLES)
            self.assertIn(f"enc-calalt-{b}", S.ROLES)
            self.assertEqual(S.calalt_role("world", b), f"world-calalt-{b}")
        for bad in (("world", 20), ("world", -1), ("enc", True), ("aux", 0)):
            with self.assertRaises(ValueError):
                S.calalt_role(*bad)

    def test_roles_give_distinct_seeds_and_bad_input_is_refused(self):
        core, salt = "c" * 64, "s" * 64
        seen = {S.seed(core, salt, r, 0) for r in S.ROLES}
        self.assertEqual(len(seen), len(S.ROLES))
        self.assertNotEqual(S.seed(core, salt, "world-calalt-0", 0), S.seed(core, salt, "world-calalt-1", 0))
        for args in ((core, salt, "bogus", 0), (core, salt, "aux", -1), (core, salt, "aux", True), (core, "", "aux", 0)):
            with self.assertRaises(ValueError):
                S.seed(*args)
        self.assertTrue(1_000_000 <= S.seed(core, salt, "aux", 0) < 1_000_000 + 10**9)

    def test_development_mapping(self):
        d = S.dev_seed
        self.assertEqual([d("world-test", i) for i in (0, 1, 50)], [930000, 930001, 930050])
        self.assertEqual(d("enc-test", 3), d("world-test", 3) + 10000)
        self.assertEqual(d("world-cal", 0), 930100)
        self.assertEqual(d("enc-cal", 5), 930105 + 10000)
        self.assertEqual(d("aux", 2), 930002 + 20000)
        self.assertEqual(d("world-calalt-0", 0), 931000)
        self.assertEqual(d("world-calalt-1", 0), 931200)
        self.assertEqual(d("enc-calalt-1", 4), 931204 + 10000)
        blocks = [{d(f"world-calalt-{b}", i) for i in range(200)} for b in range(20)]  # disjoint blocks of 200
        self.assertEqual(len(set().union(*blocks)), 20 * 200)
        self.assertEqual(min(min(b) for b in blocks), 931000)
        self.assertTrue(all(isinstance(d(r, 3), int) for r in S.ROLES))
        self.assertIs(S.seeder("dev"), S.dev_seed)
        real = S.seeder("c" * 64, "s" * 64)
        self.assertEqual(real("aux", 1), S.seed("c" * 64, "s" * 64, "aux", 1))


# ------------------------------------------------------------------------------------------------------------ tau
class TauTests(unittest.TestCase):
    def metrics(self, n=40):
        out = []
        for i in range(n):
            out.append({"fidelity": F(100 + i // 2, 200), "deviation": F((i % 7), 70), "consistency": F(90 + i % 5, 100),
                        "uncertainty": F(i % 11, 22)})
        return out

    def test_q40_order_statistics_with_duplicates(self):
        ms = self.metrics()
        t = q40(ms)
        self.assertEqual(t.tau_s, sorted(m["fidelity"] for m in ms)[3])
        self.assertEqual(t.tau_t, sorted(m["consistency"] for m in ms)[3])
        self.assertEqual(t.tau_d, sorted((m["deviation"] for m in ms), reverse=True)[3])
        self.assertEqual(t.tau_b, sorted((m["uncertainty"] for m in ms), reverse=True)[3])
        # duplicates count: fidelity 100/200 occurs twice, so the 4th smallest is the 2nd distinct value
        self.assertEqual(sorted(m["fidelity"] for m in ms)[:5], [F(1, 2), F(1, 2), F(101, 200), F(101, 200), F(102, 200)])
        self.assertEqual(t.tau_s, F(101, 200))
        self.assertEqual(sorted((m["uncertainty"] for m in ms), reverse=True)[:5], [F(10, 22)] * 3 + [F(9, 22)] * 2)
        self.assertEqual(t.tau_b, F(9, 22))  # the 4th largest value, not the 4th distinct one (that would be 7/22)
        with self.assertRaises(ValueError):
            q40(ms[:3])

    def test_d1_on_the_first_ten_worlds(self):
        ms = self.metrics()
        t = d1_first(ms)
        first = ms[:10]
        self.assertEqual((t.tau_s, t.tau_t), (min(m["fidelity"] for m in first), min(m["consistency"] for m in first)))
        self.assertEqual((t.tau_d, t.tau_b), (max(m["deviation"] for m in first), max(m["uncertainty"] for m in first)))
        self.assertEqual(d1_first(ms[:4]).tau_s, min(m["fidelity"] for m in ms[:4]))  # fewer than 10: all of them

    def test_json_roundtrip_is_exact(self):
        t = q40(self.metrics())
        self.assertEqual(taus_from_json(taus_to_json(t)), t)
        self.assertEqual(metrics_to_json(self.metrics(1)[0])["fidelity"], frac_str(F(1, 2)))


# ------------------------------------------------------------------------------------------------------------ T-1
class T1Tests(unittest.TestCase):
    def test_pairs_and_the_delta_boundary(self):
        base = dict(a095=dict(u="2/5", nf="0"), a090=dict(u="3/10", nf="1/20"))
        self.assertEqual(V.t1_outcome(line(**base), TAUS), "HOLDS")  # an increase of exactly delta is allowed
        worse = dict(a095=dict(u="2/5", nf="0"), a090=dict(u="3/10", nf="2/39"))
        self.assertEqual(V.t1_outcome(line(**worse), TAUS), "FAILS")
        down = dict(a095=dict(u="2/5", nf="9/10"), a090=dict(u="3/10", nf="0"))  # new_false falls: no violation
        self.assertEqual(V.t1_outcome(line(**down), TAUS), "HOLDS")
        # a violation between non-adjacent points counts, and so does a pair whose later point has the lower uncertainty
        three = dict(a095=dict(u="2/5", nf="0"), a080=dict(u="3/10", nf="1/50"), a060=dict(u="1/5", nf="3/10"))
        self.assertEqual(V.t1_outcome(line(**three), TAUS), "FAILS")

    def test_undefined_needs_two_feasible_points_with_distinct_uncertainty(self):
        self.assertEqual(V.t1_outcome(line(), TAUS), "UNDEFINED")  # no feasible point
        self.assertEqual(V.t1_outcome(line(a095=dict(u="2/5")), TAUS), "UNDEFINED")  # one
        same = dict(a095=dict(u="2/5", nf="0"), a090=dict(u="2/5", nf="9/10"))  # two, same uncertainty
        self.assertEqual(V.t1_outcome(line(**same), TAUS), "UNDEFINED")
        # an undefined fidelity or new_true makes a point infeasible
        nt_none = line(a095=dict(u="2/5"), a090=dict(u="3/10"))
        nt_none[1]["new_true"] = None
        self.assertEqual(V.t1_outcome(nt_none, TAUS), "UNDEFINED")

    def test_k0_decides_even_when_a_k5_point_would_be_feasible(self):
        k0 = line(a095=dict(u="2/5", nf="0"), a090=dict(u="3/10", nf="1/50"))  # alpha 0.60 infeasible at k = 0
        k5 = line(a095=dict(u="2/5", nf="0"), a090=dict(u="3/10", nf="1/50"), a060=dict(u="1/5", nf="9/10"))
        results = {}
        for a, e0, e5 in zip(ALPHAS, k0, k5):
            results[(a, 0)], results[(a, 5)], results[(a, 10)] = (None, None, e0), (None, None, e5), (None, None, e5)
        n_q = {key: 0 for key in results}
        self.assertEqual(V.k_exacts(results, 0, n_q), k0)
        self.assertEqual(V.k_exacts(results, 5, n_q), k5)
        self.assertEqual(V.t1_outcome(V.k_exacts(results, 0, n_q), TAUS), "HOLDS")  # the k = 0 line decides T-1
        self.assertEqual(V.t1_outcome(V.k_exacts(results, 5, n_q), TAUS), "FAILS")  # the k0 reading (I-6) would not
        self.assertTrue(feasible(k5[ALPHAS.index(0.60)], TAUS) and not feasible(k0[ALPHAS.index(0.60)], TAUS))

    def test_all_points_reading_ignores_feasibility(self):
        # the k = 0 line holds under the bounds; counting every point (I-2) adds the infeasible one with a big increase
        k0 = line(a095=dict(u="2/5", nf="0"), a090=dict(u="3/10", nf="1/50"))
        k0[ALPHAS.index(0.60)] = ex(f="0", u="1/5", nf="9/10")
        self.assertEqual(V.t1_outcome(k0, TAUS), "HOLDS")
        self.assertEqual(V.t1_all_points_outcome(k0), "FAILS")

    def test_the_nt_twin_fails_on_synthetic_arrays_where_the_system_holds(self):
        k0 = line(a095=dict(u="2/5", nf="0"), a090=dict(u="3/10", nf="0"), a085=dict(u="1/5", nf="0"))
        self.assertEqual(V.t1_outcome(k0, TAUS), "HOLDS")
        twin = V.nt_exacts(k0, TAUS)
        self.assertEqual(V.t1_outcome(twin, TAUS), "FAILS")  # new_false rises by 1/2 across the uncertainty span
        self.assertEqual(max(e["new_false"] for e in twin), F(1, 2))
        self.assertEqual(V.NT_TRADE_OFF, F(1, 2))
        self.assertTrue(all(e["n_q"] == 0 for e in twin))  # NT changes new_false only
        one_point = line(a095=dict(u="2/5", nf="0"))
        self.assertEqual(V.t1_outcome(V.nt_exacts(one_point, TAUS), TAUS), "UNDEFINED")

    def test_nt_exceeds_the_one_atom_floor_when_the_lowest_point_has_three_decided_atoms(self):
        # PREREG 6.2: a rise of 1/2 beats the floor 1/n_q for every n_q >= 3 (n_q = 2: 1/2 is not above 1/2)
        for n_q, verdict in ((1, "HOLDS"), (2, "HOLDS"), (3, "FAILS"), (12, "FAILS"), (0, "FAILS")):
            k0 = line(a095=dict(u="2/5", nf="0"), a090=dict(u="3/10", nf="0", nq=n_q))
            self.assertEqual(V.t1_outcome(V.nt_exacts(k0, TAUS), TAUS), verdict, n_q)


class T1FloorTests(unittest.TestCase):
    """The one-atom floor of PREREG 3.2 (R1-1): new_false(q) - new_false(p) <= max(delta, 1/n_q), n_q at q."""

    @staticmethod
    def pair(n_q, nf_q, nf_p="0"):
        # p = alpha 0.95 (u = 2/5), q = alpha 0.90 (u = 3/10): q has the lower uncertainty
        return line(a095=dict(u="2/5", nf=nf_p), a090=dict(u="3/10", nf=nf_q, nq=n_q))

    def test_a_one_atom_increase_passes_and_a_two_atom_increase_fails(self):
        for n_q in (3, 7, 12, 19, 20):  # below 20 decided atoms one atom is more than delta = 1/20
            one, two = F(1, n_q), F(2, n_q)
            self.assertEqual(V.t1_outcome(self.pair(n_q, str(one)), TAUS), "HOLDS", n_q)  # exactly 1/n_q is allowed
            self.assertEqual(V.t1_outcome(self.pair(n_q, str(two)), TAUS), "FAILS", n_q)
            self.assertEqual(V.t1_outcome(self.pair(n_q, str(one + F(1, 1000))), TAUS), "FAILS", n_q)  # just above

    def test_the_tolerance_is_the_larger_of_delta_and_one_atom(self):
        self.assertEqual(V.t1_tolerance(3), F(1, 3))
        self.assertEqual(V.t1_tolerance(19), F(1, 19))
        self.assertEqual(V.t1_tolerance(20), F(1, 20))  # the two are equal at 20
        self.assertEqual(V.t1_tolerance(40), F(1, 20))  # above 20 delta is larger
        self.assertEqual(V.t1_tolerance(0), F(1, 20))  # n_q = 0: delta
        self.assertEqual(V.t1_tolerance(3, floor=False), F(1, 20))  # I-8 and I-9: delta only
        # n_q = 40: 1/40 is below delta, so an increase of 1/20 passes and one just above fails
        self.assertEqual(V.t1_outcome(self.pair(40, "1/20"), TAUS), "HOLDS")
        self.assertEqual(V.t1_outcome(self.pair(40, "2/39"), TAUS), "FAILS")

    def test_n_q_zero_uses_delta(self):
        self.assertEqual(V.t1_outcome(self.pair(0, "1/20"), TAUS), "HOLDS")
        self.assertEqual(V.t1_outcome(self.pair(0, "1/10"), TAUS), "FAILS")  # no floor without decided atoms

    def test_n_q_is_the_one_at_the_later_point_q(self):
        # q = the point with the lower uncertainty; the floor comes from q, not from p
        k0 = line(a095=dict(u="2/5", nf="0", nq=3), a090=dict(u="3/10", nf="1/3", nq=40))
        self.assertEqual(V.t1_outcome(k0, TAUS), "FAILS")  # n_q(q) = 40: tolerance 1/20
        k0 = line(a095=dict(u="2/5", nf="0", nq=40), a090=dict(u="3/10", nf="1/3", nq=3))
        self.assertEqual(V.t1_outcome(k0, TAUS), "HOLDS")  # n_q(q) = 3: tolerance 1/3

    def test_i9_without_the_floor_differs_from_the_main_t1_on_a_constructed_case(self):
        k0 = self.pair(7, "1/7")  # one atom of 7: passes with the floor, fails with delta only
        self.assertEqual(V.t1_outcome(k0, TAUS), "HOLDS")
        self.assertEqual(V.t1_outcome(k0, TAUS, floor=False), "FAILS")  # I-9
        same = self.pair(7, "1/20")  # an increase of exactly delta: both pass
        self.assertEqual((V.t1_outcome(same, TAUS), V.t1_outcome(same, TAUS, floor=False)), ("HOLDS", "HOLDS"))
        self.assertEqual(V.t1_outcome(line(a095=dict(u="2/5")), TAUS, floor=False), "UNDEFINED")  # definedness is the same

    def test_the_floor_reaches_i2_and_the_judge_of_the_gate(self):
        k0 = self.pair(7, "1/7")
        self.assertEqual(V.t1_all_points_outcome(k0), "HOLDS")  # I-2 with the floor
        data = V.t1_data(k0, TAUS)
        self.assertTrue(set(V.DECLARED_KEYS["T-1"]) <= set(data))
        self.assertIs(V.judge_t1(data), True)
        self.assertIs(C.judge_t1(data), False)  # v0.2's judge (delta only) reads the same data and refuses
        self.assertIs(V.JUDGES["T-1"], V.judge_t1)

    def test_malformed_n_q_is_not_judged(self):
        good = V.t1_data(self.pair(7, "1/7"), TAUS)
        self.assertIs(V.judge_t1(good), True)
        for bad in (np.zeros(3, dtype=np.int64), np.full(10, 1.5), np.full(10, -1), np.full(10, np.nan)):
            d = dict(good, n_q=bad)
            self.assertIs(V.judge_t1(d), False)
        d = dict(good)
        del d["n_q"]
        self.assertIs(V.judge_t1(d), False)
        with self.assertRaises(KeyError):
            V.t1_data([{k: v for k, v in e.items() if k != "n_q"} for e in self.pair(7, "1/7")], TAUS)

    def test_i8_takes_an_alpha_as_feasible_when_some_k_is(self):
        # alpha 0.95 is feasible only at k = 5, alpha 0.90 only at k = 10: I-8's feasible set is {0.95, 0.90}
        results = {}
        for a in ALPHAS:
            for k in (0, 5, 10):
                results[(a, k)] = (None, None, ex(**BAD))
        results[(0.95, 0)] = (None, None, ex(f="0", u="2/5", nf="0"))  # infeasible at k = 0 ...
        results[(0.95, 5)] = (None, None, ex(u="2/5", nf="0"))  # ... feasible at k = 5
        results[(0.90, 0)] = (None, None, ex(f="0", u="3/10", nf="1/20"))
        results[(0.90, 10)] = (None, None, ex(u="3/10", nf="1/20"))
        self.assertEqual(V.t1_i8_outcome(results, TAUS), "HOLDS")  # uncertainty and new_false are read at k = 0: 1/20 = delta
        results[(0.90, 0)] = (None, None, ex(f="0", u="3/10", nf="2/39"))
        self.assertEqual(V.t1_i8_outcome(results, TAUS), "FAILS")  # delta only: no floor, whatever n_q is
        results[(0.90, 0)] = (None, None, ex(f="0", u="3/10", nf="2/39", nq=7))
        self.assertEqual(V.t1_i8_outcome(results, TAUS), "FAILS")
        only_k0 = {key: v for key, v in results.items()}
        for a in ALPHAS:
            only_k0[(a, 5)] = only_k0[(a, 10)] = (None, None, ex(**BAD))
        self.assertEqual(V.t1_i8_outcome(only_k0, TAUS), "UNDEFINED")  # no feasible point at any k

    def test_n_q_on_a_development_world_is_a_design_quantity_that_does_not_depend_on_k(self):
        from audit.system import FIXED
        from audit.v03.worldset import build_cached

        world, ctx, enc = build_cached(930001, 940001)
        results = {(a, k): FIXED.evaluate_exact(world, ctx, enc, a, k) for a in (0.9, 0.7, 0.5) for k in (0, 5, 10)}
        n_q = V.n_q_grid(ctx, enc, results)
        self.assertTrue(all(n_q[(a, 0)] == n_q[(a, 5)] == n_q[(a, 10)] for a in (0.9, 0.7, 0.5)))
        # n_q is the denominator of new_false (a boolean check only: no new_false value is shown)
        for key, (out, m, e) in results.items():
            nq, nf = n_q[key], e["new_false"]
            self.assertTrue((nq == 0 and nf == 0) or (nq > 0 and nq % nf.denominator == 0))
        # the verdict view ignores hypotheses (A-6): uncertainty and new_false do not depend on k
        for a in (0.9, 0.7, 0.5):
            self.assertTrue(results[(a, 0)][2]["uncertainty"] == results[(a, 5)][2]["uncertainty"]
                            == results[(a, 10)][2]["uncertainty"])
            self.assertTrue(results[(a, 0)][2]["new_false"] == results[(a, 5)][2]["new_false"]
                            == results[(a, 10)][2]["new_false"])


# ------------------------------------------------------------------------------------------------------ structure
class StructureTests(unittest.TestCase):
    RHO = [0.55, 0.6, 0.65, 0.7, 0.79, 0.8, 0.9, 0.97]

    def test_structure_fields_on_a_synthetic_world(self):
        k0 = line(a080=dict(u="2/5", nf="1/20"), a070=dict(u="3/10", nf="1/10"), a060=dict(u="1/5", nf="1/4"))
        calls = []

        def wrong(lo, hi):
            calls.append((lo, hi))
            return 2

        s = V.t1_structure(k0, TAUS, self.RHO, wrong)
        self.assertEqual(s["feasible_alphas"], [0.80, 0.70, 0.60])
        self.assertTrue(s["defined"])
        self.assertEqual((s["alpha_min"], s["alpha_max"]), (0.60, 0.80))
        self.assertEqual(s["sources_spanned"], 4)  # 0.60, 0.65, 0.70, 0.79: alpha_min <= rho < alpha_max
        self.assertEqual(s["wrong_class_atoms_spanned"], 2)
        self.assertEqual(calls, [(0.60, 0.80)])
        # pairs (p, q) with u(q) < u(p): 0.80->0.70 (+1/20), 0.80->0.60 (+1/5), 0.70->0.60 (+3/20)
        self.assertEqual(s["largest_increase"], F(1, 5))
        self.assertEqual(V.structure_json(s)["largest_increase"], "1/5")
        self.assertEqual(V.t1_outcome(k0, TAUS), "FAILS")

    def test_largest_increase_can_be_negative_and_undefined_worlds_have_no_fields(self):
        k0 = line(a095=dict(u="2/5", nf="3/10"), a090=dict(u="3/10", nf="1/10"))
        s = V.t1_structure(k0, TAUS, self.RHO, lambda lo, hi: 0)
        self.assertEqual(s["largest_increase"], F(-1, 5))
        self.assertEqual(s["sources_spanned"], 1)  # 0.90 <= rho < 0.95: rho = 0.9
        none = V.t1_structure(line(a095=dict(u="2/5")), TAUS, self.RHO, lambda lo, hi: 1 / 0)
        self.assertEqual(none["feasible_alphas"], [0.95])
        self.assertFalse(none["defined"])
        self.assertTrue(all(none[k] is None for k in ("alpha_min", "alpha_max", "sources_spanned",
                                                      "wrong_class_atoms_spanned", "largest_increase")))

    def test_sources_spanned_boundaries_are_exact(self):
        self.assertEqual(V.sources_spanned([0.7, 0.8, 0.75], 0.7, 0.8), 2)  # lo inclusive, hi exclusive
        self.assertEqual(V.sources_spanned([0.55, 0.97], 0.5, 0.95), 1)
        self.assertEqual(V.sources_spanned([], 0.5, 0.95), 0)

    def test_wrong_class_atoms_on_a_real_world_match_a_direct_count(self):
        from audit.v03.worldset import build_cached
        from tesaron.belnap import unit_value
        from tesaron.enums import Belnap

        world, _, enc = build_cached(930001, 940001)
        fn = V.wrong_class_atoms_fn(world, enc.units)
        for lo, hi in ((0.5, 0.95), (0.6, 0.8), (0.7, 0.7)):
            direct = 0
            for atom in world.vocabulary:
                u = enc.units.get(atom)
                if u is None or not atom.pred.startswith("c"):
                    continue
                if unit_value(u, lo) is Belnap.T and unit_value(u, hi) is not Belnap.T and atom not in world.true_atoms:
                    direct += 1
            self.assertEqual(fn(lo, hi), direct)
        self.assertEqual(fn(0.7, 0.7), 0)


# ---------------------------------------------------------------------------------------------------- aggregation
def outcomes(h, f=0, u=0, start=1000):
    return [(start + i, o) for i, o in enumerate(["HOLDS"] * h + ["FAILS"] * f + ["UNDEFINED"] * u)]


def structures(outs, spans=3, wrong=1):
    return [{"defined": o != "UNDEFINED", "sources_spanned": spans if o != "UNDEFINED" else None,
             "wrong_class_atoms_spanned": wrong if o != "UNDEFINED" else None} for _, o in outs]


DS = {"n_draws": 20, "holds": 7, "fails": 11, "insufficient": 2, "defined_min": 30, "defined_max": 47}
# the all_true arm over 50 test worlds (`AG.all_true_summary`): 22 worlds, at three alpha levels
ALL_TRUE = {"n_worlds": 50, "n_worlds_scoring": 22, "n_worlds_feasible": 31,
            "scoring_by_alpha": {"0.95": 6, "0.9": 20, "0.85": 21}}


def agg(test, outs, both=None, **kw):
    if test == "T-1":
        kw.setdefault("structure", structures(outs))
        kw.setdefault("draw_sensitivity", DS)
    if test == "G7":
        kw.setdefault("all_true", ALL_TRUE)
    return AG.aggregate_test(test, outs, both, **kw)


class AggregationTests(unittest.TestCase):
    def test_deterministic_rule(self):
        self.assertEqual(agg("G1", outcomes(50))["verdict"], "HOLDS")
        self.assertEqual(agg("G1", outcomes(16, 0, 34))["verdict"], "HOLDS")
        self.assertEqual(agg("G1", outcomes(15, 0, 35))["verdict"], "INSUFFICIENT")
        r = agg("G1", outcomes(40, 1, 9))
        self.assertEqual((r["verdict"], r["first_failing_world"]), ("FAILS", 1040))
        self.assertEqual(agg("G6", outcomes(5, 1, 44))["verdict"], "FAILS")  # one FAILS world, fewer than 16 defined

    def test_t1_wilson_rule(self):
        self.assertEqual(AG.wilson_lower(45, 50) >= 0.8, True)
        self.assertEqual(AG.wilson_lower(44, 50) >= 0.8, False)  # with 50 defined worlds the rule needs 45 HOLDS
        self.assertEqual(agg("T-1", outcomes(45, 5))["verdict"], "HOLDS")
        r = agg("T-1", outcomes(44, 6))
        self.assertEqual((r["verdict"], r["first_failing_world"]), ("FAILS", 1044))
        self.assertEqual(agg("T-1", outcomes(15, 0, 35))["verdict"], "INSUFFICIENT")

    def test_t1_with_sixteen_defined_worlds(self):
        self.assertEqual(agg("T-1", outcomes(16, 0, 34))["verdict"], "HOLDS")  # 16 of 16: bound ~0.84
        self.assertEqual(agg("T-1", outcomes(15, 1, 34))["verdict"], "FAILS")
        self.assertEqual(agg("T-1", outcomes(14, 1, 35))["verdict"], "INSUFFICIENT")

    def test_undefined_never_counts_as_holds(self):
        a, b = agg("T-1", outcomes(45, 5)), agg("T-1", outcomes(45, 5, 10))
        self.assertEqual((a["n_defined"], b["n_defined"], b["n_undefined"]), (50, 50, 10))
        self.assertEqual(AG.undefined_as_fails(outcomes(45, 5, 10))["n"], 60)

    def test_missing_arms_are_refused(self):
        with self.assertRaises(ValueError):
            AG.aggregate_test("G7", outcomes(50))  # G7a needs the all_true summary (R1-3)
        with self.assertRaises(ValueError):
            AG.aggregate_test("T-1", outcomes(50))
        with self.assertRaises(ValueError):
            AG.aggregate_test("G8", outcomes(50))  # G8 has no verdict in v0.3
        with self.assertRaises(ValueError):
            AG.aggregate_test("T-1", outcomes(50), structure=structures(outcomes(49)), draw_sensitivity=DS)

    def test_draw_sensitivity_counts(self):
        per_draw = [["HOLDS"] * 20 + ["UNDEFINED"] * 30,  # 20 of 20: HOLDS
                    ["HOLDS"] * 10 + ["UNDEFINED"] * 40,  # 10 defined: insufficient
                    ["HOLDS"] * 10 + ["FAILS"] * 10 + ["UNDEFINED"] * 30,  # 10 of 20: FAILS
                    ["HOLDS"] * 44 + ["FAILS"] * 6]  # 44 of 50: FAILS
        d = AG.draw_sensitivity_counts(per_draw)
        self.assertEqual((d["holds"], d["fails"], d["insufficient"]), (1, 2, 1))
        self.assertEqual((d["defined_min"], d["defined_max"]), (10, 50))
        self.assertEqual(d["verdicts"], ["HOLDS", "INSUFFICIENT", "FAILS", "FAILS"])
        self.assertEqual(AG.t1_verdict_of(per_draw[0]), "HOLDS")
        none = AG.draw_sensitivity_counts([])
        self.assertEqual((none["holds"], none["defined_min"]), (0, None))

    def test_a_draw_sensitivity_set_without_a_tau_counts_as_insufficient_worlds(self):
        per_draw = [["HOLDS"] * 45 + ["FAILS"] * 5,  # 45 of 50: HOLDS
                    [AG.NO_TAU] * 50,  # no tau: insufficient worlds, no number of defined worlds
                    ["HOLDS"] * 10 + ["FAILS"] * 10 + ["UNDEFINED"] * 30]
        d = AG.draw_sensitivity_counts(per_draw)
        self.assertEqual((d["holds"], d["fails"], d["insufficient"], d["n_no_tau"]), (1, 1, 1, 1))
        self.assertEqual(d["verdicts"], ["HOLDS", "INSUFFICIENT", "FAILS"])
        self.assertEqual(d["defined"], [50, None, 20])
        self.assertEqual((d["defined_min"], d["defined_max"]), (20, 50))  # the failed set is left out of the range
        only = AG.draw_sensitivity_counts([[AG.NO_TAU] * 50] * 2)
        self.assertEqual((only["insufficient"], only["defined_min"], only["defined_max"]), (2, None, None))
        self.assertEqual(AG.draw_sensitivity_sentence(dict(DS, holds=1, fails=1, insufficient=1)),
                         "Under 20 further calibration draws, T-1's verdict was HOLDS 1 times, FAILS 1 times and "
                         "'insufficient worlds' 1 times (descriptive).")

    def test_structure_counts_and_median(self):
        outs = outcomes(3, 1, 1)
        st = [{"defined": True, "sources_spanned": s, "wrong_class_atoms_spanned": w}
              for s, w in ((1, 0), (4, 2), (2, 0), (7, 1))] + [{"defined": False, "sources_spanned": None,
                                                                "wrong_class_atoms_spanned": None}]
        c = AG.structure_counts(outs, st)
        self.assertEqual((c["n"], c["median"], c["even"], c["min"], c["max"]), (4, "3", True, 1, 7))  # (2 + 4) / 2
        self.assertEqual(c["n_with_wrong_class_atom"], 2)
        odd = AG.structure_counts(outcomes(3), structures(outcomes(3), spans=5))
        self.assertEqual((odd["median"], odd["even"]), ("5", False))
        half = AG.median_of([1, 2, 4, 5])
        self.assertEqual(half, ("3", True))
        self.assertEqual(AG.median_of([1, 2, 3, 6]), ("2.5", True))
        s = AG.structure_sentence(c)
        self.assertIn("a median of 3 (the mean of the two middle values) of the 8 source reliabilities", s)
        self.assertNotIn("the mean of the two middle values", AG.structure_sentence(odd))
        empty = AG.structure_counts(outcomes(0, 0, 3), structures(outcomes(0, 0, 3)))
        self.assertIn("no defined world", AG.structure_sentence(empty))
        with self.assertRaises(ValueError):
            AG.structure_counts(outs, st[:2])

    def test_g8_is_descriptive_only(self):
        g = AG.g8_descriptive(outcomes(20, 10, 2), list(range(32)), [True] * 3 + [False] * 5 + [None] * 24)
        self.assertEqual(g["text"], "G8 (descriptive, no verdict): 20 of 30 defined worlds hold (Wilson lower bound "
                                    f"{AG.wilson_lower(20, 30):.3f}); 2 undefined.")
        self.assertEqual(g["failing_only_through_single_atom_changes"], 3)
        self.assertEqual((g["hyp_count"]["min"], g["hyp_count"]["max"]), (0, 31 - 2))  # only the defined worlds count
        table = AG.verdict_table({t: outcomes(50) for t in (*AG.DETERMINISTIC_TESTS, "T-1")}, structure=structures(
            outcomes(50)), draw_sensitivity=DS, all_true=ALL_TRUE)
        self.assertEqual([r["test"] for r in table["rows"]], ["G1", "G2", "G3", "G4", "G5", "G6", "G7", "T-1"])
        self.assertNotIn("G8", [r["test"] for r in table["rows"]])

    def test_detector_qualifier_only_with_a_holds_verdict(self):
        r = agg("G2", outcomes(50), both=3)
        self.assertEqual(r["detector_qualifier"], "the detector did not separate on 3 worlds")
        self.assertTrue(r["text"].endswith("(the detector did not separate on 3 worlds)"))
        self.assertIsNone(agg("G2", outcomes(40, 10), both=3)["detector_qualifier"])
        self.assertIsNone(agg("G2", outcomes(50), both=0)["detector_qualifier"])


# ---------------------------------------------------------------------------------------------- the fixed wording
class WordingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = norm(PREREG.read_text(encoding="utf-8"))

    def template(self, label: str) -> str:
        m = re.search(r'\*\*' + re.escape(label) + r':\*\* "([^"]*)"', self.text)
        self.assertIsNotNone(m, label)
        return m.group(1)

    @staticmethod
    def fill(template: str, **values) -> str:
        for k, v in values.items():
            template = template.replace(f"<{k}>", str(v))
        return template

    def test_constants_are_in_the_prereg(self):
        self.assertIn(AG.EXPECTED_PARAGRAPH, self.text)
        self.assertIn("the I-8 arm applies v0.2's full rule to the v0.3 worlds.", AG.EXPECTED_PARAGRAPH)
        self.assertIn(AG.G7A_TEMPLATE, self.text)
        self.assertIn(f'"{AG.T1_HOLDS_SENTENCE}"', self.text)
        self.assertIn(AG.LIMITATION, self.text)
        for test in ("G1", "G2", "G3", "G4", "G5", "G6", "G7", "T-1"):
            self.assertIn(AG.CLAIMS[test], self.text, test)
        self.assertIn("(A check of the implementation or of the criterion, not a discovery.)", self.text)
        self.assertEqual(AG.MIN_DEFINED, 16)
        self.assertEqual(AG.WILSON_THRESHOLD, 0.80)
        self.assertEqual(AG.Z_95_ONE_SIDED, 1.6448536269514722)
        self.assertIn("z = 1.6448536269514722", self.text)

    def test_the_t1_claim_states_the_one_atom_floor(self):  # R2-1
        row = re.search(r"\| T-1 \| (Within the reasonable bounds[^|]*?) \((A1, R1-1)\) \|", self.text)
        self.assertIsNotNone(row)
        self.assertEqual(AG.CLAIMS["T-1"], row.group(1))  # the claim column of 3.2 without its trailing parenthesis
        self.assertTrue(AG.CLAIMS["T-1"].endswith("by more than δ or by one wrong conclusion, whichever is larger"))
        self.assertNotEqual(AG.CLAIMS["T-1"], AG.V02_CLAIMS["T-1"])
        self.assertIn(f"- **T-1:** within the reasonable bounds, admitting weaker evidence (lowering α) does not increase the share "
                      f"of new false conclusions by more than δ or by one wrong conclusion, whichever is larger (R1-1).", self.text)
        r = agg("T-1", outcomes(48, 2, 0))
        self.assertIn(f"{AG.CLAIMS['T-1']}. 48 of 50 defined worlds hold", r["text"])
        self.assertNotIn("by more than δ.", r["text"])
        # the gate study carries the same claim as its name (the certificate names what it certifies)
        study = (ROOT / "audit" / "v03" / "gate" / "t1_study.py").read_text(encoding="utf-8")
        self.assertIn('name="T-1: " + CLAIMS["T-1"]', study)
        self.assertIn("from audit.v03.aggregate import CLAIMS", study)

    def test_the_g7a_sentence_says_can_be_excluded(self):  # R2-4
        self.assertIn("only all_false can be excluded by the constraints.", AG.G7A_TEMPLATE)
        self.assertNotIn("is excluded by the constraints", AG.G7A_TEMPLATE)

    def test_deterministic_sentences(self):
        t = self.template("Deterministic test, HOLDS")
        self.assertEqual(agg("G3", outcomes(48, 0, 2))["text"],
                         self.fill(t, Id="G3", claim=AG.CLAIMS["G3"], n_defined=48, n_undefined=2))
        t = self.template("Deterministic test, FAILS")
        self.assertEqual(agg("G3", outcomes(47, 3))["text"], self.fill(t, Id="G3", n_fails=3, n_defined=50, seed=1047))
        g1 = agg("G1", outcomes(47, 3), failed_parts={1047: ["(i)", "(ii)"]})["text"]
        self.assertTrue(g1.endswith(" Failed parts in the first failing world: (i), (ii)."))
        self.assertIn('For G1 it adds: "Failed parts in the first failing world: <parts>."', self.text)
        self.assertEqual(agg("G7", outcomes(50))["id"], "G7a")

    def test_insufficient_sentence(self):
        t = self.template("Insufficient worlds")
        self.assertEqual(agg("G2", outcomes(12, 0, 38))["text"], self.fill(t, Id="G2", n_defined=12))

    def test_t1_sentences(self):
        t = self.template("T-1, HOLDS")
        self.assertTrue(t.startswith("T-1 holds on at least 80% of worlds (one-sided Wilson bound, approximately 95%): "))
        low = f"{AG.wilson_lower(48, 50):.3f}"
        r = agg("T-1", outcomes(48, 2, 0))
        head = self.fill(t, claim=AG.CLAIMS["T-1"], n_holds=48, n_defined=50, b=low, n_undefined=0)
        self.assertTrue(r["text"].startswith(head + " In these worlds"))  # the sentence, then the additional sentences
        t = self.template("T-1, FAILS")
        self.assertIn("this does not show that the per-world rate is below 0.80", t)
        low = f"{AG.wilson_lower(40, 50):.3f}"
        r = agg("T-1", outcomes(40, 10, 5))
        fails = self.fill(t, n_holds=40, n_defined=50, b=low, n_undefined=5, seed=1040)
        self.assertTrue(r["text"].startswith(fails + " In these worlds"))
        self.assertNotIn("does not hold", r["text"])  # v0.3 says "is not demonstrated" for T-1
        self.assertNotIn("T-1 holds:", agg("T-1", outcomes(48, 2, 0))["text"])

    def test_g7a_sentence_goes_with_every_g7a_verdict(self):
        t = self.template("G7a, with every verdict (R1-3)")
        self.assertIn("With n = 0 the parenthesis is omitted.", self.text)
        sentence = self.fill(t, n=22, N=50, levels="0.95, 0.90, 0.85")  # levels in decreasing order
        self.assertEqual(AG.g7a_sentence(ALL_TRUE), sentence)
        for outs, verdict in ((outcomes(50), "HOLDS"), (outcomes(40, 10), "FAILS"), (outcomes(10, 0, 40), "INSUFFICIENT")):
            r = agg("G7", outs)
            self.assertEqual(r["verdict"], verdict)
            self.assertTrue(r["text"].endswith(" " + sentence), verdict)  # printed with every verdict
            self.assertEqual(r["all_true_text"], sentence)
        r = agg("G7", outcomes(48, 0, 2))
        self.assertTrue(r["text"].startswith(f"G7a holds: {AG.CLAIMS['G7']}, in all 48 defined test worlds (2 undefined). "))
        # the detector qualifier stays last
        self.assertTrue(agg("G7", outcomes(50), both=2)["text"].endswith(sentence + " (the detector did not separate on 2 worlds)"))

    def test_g7a_sentence_with_no_scoring_world_omits_the_parenthesis(self):
        t = self.template("G7a, with every verdict (R1-3)")
        none = {"n_worlds": 50, "n_worlds_scoring": 0, "n_worlds_feasible": 3, "scoring_by_alpha": {}}
        s0 = AG.g7a_sentence(none)
        self.assertEqual(s0, self.fill(t.replace(" (at α <levels>)", ""), n=0, N=50))
        self.assertNotIn("(at", s0)
        self.assertTrue(s0.startswith("all_true, not judged, was feasible and scored > 0 on 0 of 50 test worlds; echo,"))
        self.assertTrue(agg("G7", outcomes(50), all_true=none)["text"].endswith(" " + s0))
        # levels are listed in decreasing order, whatever the order of the summary, with two decimals
        some = {"n_worlds": 30, "n_worlds_scoring": 3, "n_worlds_feasible": 3, "scoring_by_alpha": {"0.85": 1, "0.95": 1, "0.9": 1}}
        self.assertIn("on 3 of 30 test worlds (at α 0.95, 0.90, 0.85);", AG.g7a_sentence(some))

    def test_additional_t1_sentences_and_their_order(self):
        # the structure sentence, the draw-sensitivity sentence, then (HOLDS only) the HOLDS sentence, then the qualifier
        m = re.search(r'"(In these worlds T-1 compares graded steps.*?world-false class atom\.)"', self.text)
        self.assertIsNotNone(m)
        tmpl = m.group(1)
        outs = outcomes(44, 5, 3)  # 49 defined worlds: an odd count
        st = structures(outs, spans=3, wrong=1)
        st[0]["sources_spanned"], st[1]["sources_spanned"] = 1, 6
        c = AG.structure_counts(outs, st)
        self.assertEqual(AG.structure_sentence(c), self.fill(tmpl, n=49, m="3", a=1, b=6, c=49))
        even = outcomes(45, 5, 3)  # 50 defined worlds: the sentence says that the median is the mean of the two middle values
        ce = AG.structure_counts(even, structures(even, spans=3, wrong=0))
        self.assertEqual(AG.structure_sentence(ce), self.fill(tmpl, n=50, m="3 (the mean of the two middle values)", a=3, b=3, c=0))
        m = re.search(r'"(Under 20 further calibration draws.*?\(descriptive\)\.)"', self.text)
        self.assertIsNotNone(m)
        self.assertEqual(AG.draw_sensitivity_sentence(DS), self.fill(m.group(1), h=7, f=11, i=2))
        outs, st = even, structures(even, spans=3, wrong=0)
        c = AG.structure_counts(outs, st)
        r = agg("T-1", outs, both=2, structure=st)
        t = r["text"]
        self.assertLess(t.index(AG.structure_sentence(c)), t.index(AG.draw_sensitivity_sentence(DS)))
        self.assertLess(t.index(AG.draw_sensitivity_sentence(DS)), t.index(AG.T1_HOLDS_SENTENCE))
        self.assertLess(t.index(AG.T1_HOLDS_SENTENCE), t.index("(the detector did not separate on 2 worlds)"))
        self.assertTrue(t.endswith("(the detector did not separate on 2 worlds)"))
        fails = agg("T-1", outcomes(40, 10))["text"]
        self.assertIn(AG.structure_sentence(AG.structure_counts(outcomes(40, 10), structures(outcomes(40, 10)))), fails)
        self.assertIn("Under 20 further calibration draws", fails)
        self.assertNotIn(AG.T1_HOLDS_SENTENCE, fails)  # only with a HOLDS
        insuff = agg("T-1", outcomes(10, 0, 40))["text"]
        self.assertTrue(insuff.startswith("T-1: insufficient worlds (10 defined, 16 required); no verdict. In these worlds"))
        self.assertIn("Under 20 further calibration draws", insuff)  # printed with every T-1 verdict
        self.assertNotIn(AG.T1_HOLDS_SENTENCE, insuff)
        self.assertEqual(agg("T-1", outs)["expected_paragraph"], AG.EXPECTED_PARAGRAPH)
        self.assertIsNone(agg("G1", outcomes(50))["expected_paragraph"])

    def test_g8_sentence(self):
        t = self.template("G8, in the descriptive section only")
        g = AG.g8_descriptive(outcomes(25, 20, 5), [3] * 50, [None] * 50)
        self.assertEqual(g["text"], self.fill(t, n_holds=25, n_defined=45, b=f"{AG.wilson_lower(25, 45):.3f}", n_undefined=5))

    def test_the_median_rule_for_an_even_count_is_written_in_the_prereg(self):
        self.assertIn("With an even number of worlds the median is the mean of the two middle values, and \"a median of "
                      "<m>\" is then printed as \"a median of <m> (the mean of the two middle values)\".", self.text)


# ----------------------------------------------------------------------------------------------- the redaction
FORBIDDEN_KEYS = ("new_false", "new_true", "largest_increase", "wrong_class_atoms_spanned", "sources_spanned",
                  "t1_structure", "t1_all_points", "t1_i6", "t1_i7", "t1_i8", "t1_i9", "i8", "i9", "draw_sensitivity",
                  "t1_draw_sensitivity",
                  "g8_hyp_count", "g8_single_atom_only", "g8_whole_grid", "g7b", "g8_descriptive", "T-1", "G8", "NT",
                  "hyp_count", "undefined_as_fails", "expected_paragraph", "structure_text", "structure")
POISON = "987654/123457"


def poisoned_doc() -> dict:
    return {
        "mode": "dev-redacted", "taus": {"tau_main": {"tau_s": "49/57"}, "tau_i6": {"tau_s": "1/2"},
                                         "tau_i8": {"tau_s": "2/3"}},
        "table": {"limitation": "x", "rows": [
            {"test": "G1", "verdict": "HOLDS", "text": "G1 holds: ok"},
            {"test": "T-1", "verdict": "FAILS", "n_holds": 3, "text": f"T-1 does not hold: {POISON}", "structure": {"a": 1}},
            {"test": "G8", "verdict": "FAILS", "text": "G8 does not hold"}]},
        "worlds": [{"world_seed": 930000, "outcomes": {"G1": "HOLDS", "G8": "FAILS", "T-1": "HOLDS"},
                    "twins": {"N1a": {"test": "G1", "outcome": "FAILS"}, "NT": {"test": "T-1", "outcome": "FAILS"}},
                    "descriptive": {"cross_seed": {"share_all": 0.5}, "default_feasible": True,
                                    "t1_structure": {"largest_increase": POISON, "sources_spanned": 3},
                                    "t1_all_points": "FAILS", "t1_i6": "HOLDS", "t1_i7": "HOLDS", "t1_i8": "FAILS",
                                    "t1_i9": "HOLDS", "all_true": {"scores": True}, "n_q": 12,
                                    "t1_draw_sensitivity": ["HOLDS"], "g8_hyp_count": 12, "g8_single_atom_only": True,
                                    "g8_whole_grid": {"all_points_ok": False}, "g7b": {"hypervolume": 0.25},
                                    "metrics": {"new_false": POISON, "new_true": POISON}}}],
        "descriptive": {"draw_sensitivity": {"holds": 7}, "undefined_as_fails": {"T-1": POISON},
                        "detector_diagnostic": {"N1a": {"both_hold": 3}, "NT": {"both_hold": 9}},
                        "default_feasible_worlds": 41},
        "definedness": [{"test": "T-1", "n_defined": 40, "n_undefined": 10}],
        "g8_descriptive": {"text": "G8 (descriptive, no verdict): ...", "hyp_count": {"median": "4"}},
    }


class RedactionTests(unittest.TestCase):
    def test_the_boundary_strips_every_forbidden_field(self):
        out = R.redact_checked(poisoned_doc())
        text = repr(out)
        self.assertNotIn(POISON, text)
        self.assertNotIn("new_false", text.replace("'new_false': 'REDACTED'", ""))
        self.assertEqual(R.find_violations(out), [])
        w = out["worlds"][0]
        self.assertEqual((w["outcomes"]["G8"], w["outcomes"]["T-1"], w["twins"]["NT"]), ("REDACTED",) * 3)
        self.assertEqual(w["outcomes"]["G1"], "HOLDS")  # G1-G7a outcomes may be shown
        self.assertEqual(w["twins"]["N1a"]["outcome"], "FAILS")
        d = w["descriptive"]
        for k in ("t1_structure", "t1_all_points", "t1_i6", "t1_i7", "t1_i8", "t1_i9", "t1_draw_sensitivity",
                  "g8_hyp_count", "g8_single_atom_only", "g8_whole_grid", "g7b"):
            self.assertEqual(d.get(k, "REDACTED"), "REDACTED", k)
        self.assertEqual(d["all_true"], {"scores": True})  # the all_true arm and the denominators n_q may be shown
        self.assertEqual(d["n_q"], 12)
        self.assertEqual(d["metrics"], {"new_false": "REDACTED", "new_true": "REDACTED"})
        self.assertEqual(d["default_feasible"], True)
        self.assertEqual(d["cross_seed"], {"share_all": 0.5})
        rows = out["table"]["rows"]
        self.assertEqual(rows[0]["text"], "G1 holds: ok")
        self.assertEqual(rows[1], {"test": "T-1", "verdict_row": "REDACTED"})
        self.assertEqual(rows[2], {"test": "G8", "verdict_row": "REDACTED"})
        self.assertEqual(out["g8_descriptive"], "REDACTED")
        self.assertEqual(out["descriptive"]["draw_sensitivity"], "REDACTED")
        self.assertEqual(out["descriptive"]["detector_diagnostic"]["NT"], "REDACTED")
        self.assertEqual(out["descriptive"]["detector_diagnostic"]["N1a"], {"both_hold": 3})
        self.assertEqual(out["descriptive"]["default_feasible_worlds"], 41)
        self.assertEqual(out["definedness"], [{"test": "T-1", "n_defined": 40, "n_undefined": 10}])  # definedness counts
        self.assertEqual(out["taus"]["tau_i6"], {"tau_s": "1/2"})  # the I-6 / I-7 / I-8 taus are design quantities
        self.assertEqual(out["taus"]["tau_i8"], {"tau_s": "2/3"})

    def test_the_scan_finds_what_the_boundary_would_have_removed(self):
        raw = poisoned_doc()
        self.assertGreater(len(R.find_violations(raw)), 5)
        with self.assertRaises(AssertionError):
            R.redact_checked({"ok": 1, "note": "the new_false share is ..."})
        for key in FORBIDDEN_KEYS:
            self.assertTrue(R.is_forbidden_key(key), key)
            self.assertEqual(R.redact({key: 1})[key], "REDACTED", key)
            self.assertTrue(R.find_violations({key: 1}), key)
        for key in ("tau_s", "tau_i6", "tau_i8", "tau_alt", "n_q", "all_true", "fidelity", "deviation", "consistency", "uncertainty", "definedness",
                    "default_feasible", "cross_seed", "G1", "G7", "N1a", "world_seed", "four_metrics_k0"):
            self.assertFalse(R.is_forbidden_key(key), key)

    def test_redact_is_a_deep_copy(self):
        raw = poisoned_doc()
        R.redact(raw)
        self.assertEqual(raw["worlds"][0]["outcomes"]["G8"], "FAILS")  # the input is untouched


# ------------------------------------------------------------------------------------------------ N4 and the runner
class N4Tests(unittest.TestCase):
    def test_hash_seeds_are_explicit_in_the_subprocess_call(self):
        self.assertEqual(V.G4_HASHSEEDS, ("0", "1", "4242"))
        self.assertEqual(V.G2_HASHSEEDS, ("0", "1"))
        from audit.v03 import subproc

        seen = []

        def fake_run(cmd, **kw):
            seen.append(kw["env"]["PYTHONHASHSEED"])
            return subprocess.CompletedProcess(cmd, 0, stdout="ab" * 32 + "\n", stderr="")

        with mock.patch.object(subproc.subprocess, "run", fake_run):
            for hs in V.G4_HASHSEEDS:
                subproc.run_hash("output", 930000, 940000, "N4", hs)
        self.assertEqual(seen, ["0", "1", "4242"])

    def test_collect_g4_n4_uses_three_subprocesses_with_those_seeds(self):
        from audit.v03.worldset import WorldRecord, build_cached

        world, ctx, enc = build_cached(930000, 940000)
        rec = WorldRecord(0, 930000, 940000, None, world, ctx, enc, 0)
        calls = []

        def fake(kind, ws, es, system, hs):
            calls.append((kind, ws, es, system, hs))
            return hashlib.sha256(f"{system}{hs}".encode()).hexdigest()

        with mock.patch.object(V, "run_hash_v03", fake):
            data = V.collect_g4_n4(rec, True)
        self.assertEqual([c[3:] for c in calls], [("N4", "0"), ("N4", "1"), ("N4", "4242")])
        self.assertTrue(all(c[:3] == ("output", 930000, 940000) for c in calls))
        self.assertEqual(np.asarray(data["h_sub"]).shape, (3, 2))
        self.assertEqual(np.asarray(data["h_perm"]).shape[0], 0)  # the in-process permutations play no part (A11)
        from audit import checks as C

        self.assertIs(C.judge_g4(data), False)  # different subprocess hashes: the twin FAILS
        same = hashlib.sha256(b"x").hexdigest()
        with mock.patch.object(V, "run_hash_v03", lambda *a: same):
            self.assertIs(C.judge_g4(V.collect_g4_n4(rec, True)), True)  # equal hashes: HOLDS (so the check can separate)

    def test_set_iteration_order_is_a_function_of_the_explicit_hash_seed(self):
        keys = [f"{i}|{j}" for i in range(2) for j in range(8)]
        code = ("from audit.twins._source import SetOrderSource; "
                f"print(SetOrderSource().order({keys!r}))")
        out = {}
        for hs in ("0", "0", "1", "4242"):
            env = dict(os.environ, PYTHONHASHSEED=hs)
            res = subprocess.run([sys.executable, "-B", "-c", code], cwd=ROOT, env=env, capture_output=True, text=True)
            self.assertEqual(res.returncode, 0, res.stderr[-200:])
            out.setdefault(hs, []).append(res.stdout.strip())
        self.assertEqual(len(set(out["0"])), 1)  # the same seed, the same order
        self.assertNotEqual(out["0"][0], out["1"][0])  # other seeds, other orders: this is the twin's fault
        self.assertNotEqual(out["0"][0], out["4242"][0])


class RunnerHelperTests(unittest.TestCase):
    def test_manifest_coverage_filter(self):
        tracked = ["SPEC.md", "audit/a.py", "tests/t.py", "prereg/PREREG_v0.3.md", "prereg/v03/POWER_STUDY.json",
                   "prereg/v03/FREEZE_v0.3.json", "prereg/v03/FREEZE_RECORD.md", "prereg/v03/reviews/r1.json",
                   "prereg/v03/reviews/REVIEW.md", "prereg/v03/TAU_RULE_STUDY.json"]
        got = tracked_manifest_files(tracked)
        self.assertEqual(got, {"SPEC.md", "audit/a.py", "tests/t.py", "prereg/PREREG_v0.3.md",
                               "prereg/v03/POWER_STUDY.json", "prereg/v03/TAU_RULE_STUDY.json"})
        self.assertTrue(STUDY_JSON.fullmatch("prereg/v03/x.json"))
        self.assertFalse(STUDY_JSON.fullmatch("prereg/v03/reviews/x.json"))
        self.assertEqual(MANIFEST_REL, "prereg/v03/FREEZE_v0.3.json")

    def test_real_paths_and_defaults(self):
        from audit.v03 import run_v03 as RV

        self.assertEqual((RV.N_CAL, RV.N_TEST, RV.N_ALT), (40, 50, 20))
        self.assertEqual((RV.SALT_REL, RV.CAL_REL, RV.TAU_REL), ("run/v03/SALT.json", "run/v03/CAL_WORLDS.json",
                                                                   "run/v03/TAU.json"))
        self.assertEqual((RV.OUT_REL, RV.REPRO_REL), ("run/v03", "run/v03_repro"))
        self.assertEqual((RV.REQUIRED_PYTHON if hasattr(RV, "REQUIRED_PYTHON") else (3, 14, 2)), (3, 14, 2))

    def test_overrides_are_refused_in_real_mode(self):
        from audit.v03 import run_v03 as RV

        for argv in (["calibrate", "--n-cal", "8"], ["test", "--n-alt", "2"], ["test", "--no-subprocess"],
                     ["test", "--out", "x"]):
            self.assertEqual(RV.main(argv), RV.EXIT_USAGE, argv)
        self.assertEqual(RV.main(["test", "--dev-redacted"]), RV.EXIT_USAGE)  # --out is required
        self.assertEqual(RV.main(["reproduce", "--dev-redacted", "--out", "x"]), RV.EXIT_USAGE)

    def test_dev_output_may_not_go_into_run(self):
        from audit.v03 import run_v03 as RV

        with self.assertRaises(RV.Refused):
            RV.run_dev("calibrate", RV.ROOT / "run" / "v03_dev", 4, 1, 0, False)


if __name__ == "__main__":
    unittest.main()
