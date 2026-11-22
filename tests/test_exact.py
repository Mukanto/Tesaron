import unittest
from fractions import Fraction
from unittest import mock

import numpy as np

from audit.cache import get_encoding
from audit.exact import (
    DELTA,
    EPS_D,
    EPS_F,
    INVALID,
    ExactTaus,
    compute_taus,
    decode_pairs,
    defined_default_metrics,
    encode_pairs,
    feasible,
    frac_str,
    str_frac,
)
from audit.system import FIXED
from tesaron.criterion import compute_metrics_exact, compute_metrics_for, compute_metrics_for_exact
from tesaron.worlds import WorldGenerationError, WorldParams, generate_world
from tesaron.worlds import generator as world_generator

F = Fraction


class TesaronExactCompanionTests(unittest.TestCase):
    """SPEC S-7: exact companions next to the float metrics; no float value changes."""

    def test_floats_are_unchanged_and_fractions_match_them(self):
        for ws, es in ((900001, 900101), (900002, 900102), (900003, 900103)):
            with self.subTest(world=ws):
                world, ctx, enc = get_encoding(ws, es)
                for alpha, k in ((0.7, 5), (0.9, 0), (0.6, 10)):
                    out = FIXED.decode(FIXED.interface_facts(enc.units, alpha), ctx.rules, ctx.vocabulary, k)
                    from dataclasses import replace

                    c = replace(ctx, alpha=alpha)
                    plain = compute_metrics_for(world, c, enc, out)
                    metrics, exact = compute_metrics_for_exact(world, c, enc, out)
                    self.assertEqual(metrics, plain)
                    for name in ("fidelity", "deviation", "new_true", "new_false", "uncertainty", "validation_agreement"):
                        value, ex = getattr(plain, name), exact[name]
                        if value is None:
                            self.assertIsNone(ex, name)
                        else:
                            self.assertIsInstance(ex, Fraction)
                            self.assertEqual(float(ex), value, name)
                    if plain.consistency is None:
                        self.assertIsNone(exact["consistency"])
                    else:
                        self.assertAlmostEqual(float(exact["consistency"]), plain.consistency, places=14)
                    self.assertAlmostEqual(float(exact["boundary_share"]), plain.boundary_share, places=14)

    def test_the_exact_values_are_ratios_of_the_integer_counts(self):
        world, ctx, enc = get_encoding(900001, 900101)
        out = FIXED.decode(FIXED.interface_facts(enc.units, 0.7), ctx.rules, ctx.vocabulary, 5)
        m, ex = compute_metrics_for_exact(world, ctx, enc, out)
        self.assertEqual(ex["fidelity"].denominator * m.size_I % ex["fidelity"].denominator, 0)
        self.assertEqual(ex["fidelity"], F(round(m.fidelity * m.size_I), m.size_I))
        self.assertEqual(ex["new_true"], F(round(m.new_true * m.size_H), m.size_H))
        self.assertEqual(ex["consistency"], F(round(m.consistency * m.size_K), m.size_K))
        self.assertEqual(ex["uncertainty"], F(round(m.uncertainty * m.size_K), m.size_K))

    def test_compute_metrics_is_the_first_part_of_compute_metrics_exact(self):
        world, ctx, enc = get_encoding(900001, 900101)
        out = FIXED.decode(FIXED.interface_facts(enc.units, 0.7), ctx.rules, ctx.vocabulary, 5)
        kw = dict(truth=world.truth, vocab=ctx.vocabulary, world_rules=world.rules, units=enc.units,
                  validation_units=enc.validation_units, alpha=0.7, epsilon_band=ctx.epsilon_band, output=out)
        from tesaron.criterion import compute_metrics

        self.assertEqual(compute_metrics(**kw), compute_metrics_exact(**kw)[0])


class WorldGenerationErrorTests(unittest.TestCase):
    def test_it_is_a_runtime_error_subclass(self):
        self.assertTrue(issubclass(WorldGenerationError, RuntimeError))

    def test_it_is_raised_when_the_acceptance_loop_is_exhausted(self):
        params = WorldParams(max_attempts=3)
        with mock.patch.object(world_generator, "_accepted", return_value=False):
            with self.assertRaises(WorldGenerationError) as cm:
                generate_world(900001, params)
        self.assertIn("3 attempts", str(cm.exception))
        with self.assertRaises(RuntimeError):  # still caught by existing RuntimeError handlers
            with mock.patch.object(world_generator, "_accepted", return_value=False):
                generate_world(900001, params)

    def test_the_world_set_catches_only_this_error(self):
        from audit import worldset
        from audit.seeds import seeder

        calls = []

        def build(ws, es):
            calls.append(ws)
            if len(calls) == 1:
                raise WorldGenerationError("exhausted")
            return get_encoding(ws, es)

        recs, _ = worldset.generate_valid(1, seeder("dev"), "world-test", "enc-test", "aux", build=build)
        self.assertEqual(len(recs), 1)
        self.assertGreater(len(calls), 1)

        def broken(ws, es):
            raise RuntimeError("some other failure")

        with self.assertRaises(RuntimeError):
            worldset.generate_valid(1, seeder("dev"), "world-test", "enc-test", "aux", build=broken)


class AuditExactTests(unittest.TestCase):
    def ex(self, f=F(9, 10), d=F(0), c=F(1), u=F(1, 5), nt=F(1, 2)):
        return {"fidelity": f, "deviation": d, "consistency": c, "uncertainty": u, "new_true": nt}

    def test_constants_are_exact(self):
        self.assertEqual((EPS_F, EPS_D, DELTA), (F(1, 20), F(1, 50), F(1, 20)))

    def test_feasibility_is_exact_at_the_boundary(self):
        taus = ExactTaus(F(9, 10), F(1, 50), F(1), F(1, 5))
        self.assertTrue(feasible(self.ex(), taus))
        self.assertFalse(feasible(self.ex(f=F(9, 10) - F(1, 10**9)), taus))
        self.assertFalse(feasible(self.ex(d=F(1, 50) + F(1, 10**9)), taus))
        self.assertFalse(feasible(self.ex(u=F(1, 5) + F(1, 10**9)), taus))
        # a float tie that floats cannot resolve: 1/3 vs 0.333...
        t3 = ExactTaus(F(1, 3), F(1), F(0), F(1))
        self.assertTrue(feasible(self.ex(f=F(1, 3)), t3))
        self.assertFalse(feasible(self.ex(f=F(333333333, 10**9)), t3))

    def test_undefined_values_make_a_point_infeasible(self):
        taus = ExactTaus(F(0), F(1), F(0), F(1))
        for key in ("fidelity", "consistency", "uncertainty", "nt"):
            ex = self.ex()
            ex["new_true" if key == "nt" else key] = None
            self.assertFalse(feasible(ex, taus), key)

    def test_compute_taus_is_the_d1_rule(self):
        worlds = [self.ex(f=F(9, 10), d=F(1, 20), c=F(4, 5), u=F(1, 4)),
                  self.ex(f=F(7, 10), d=F(0), c=F(9, 10), u=F(1, 3)),
                  self.ex(f=F(8, 10), d=F(1, 10), c=F(1), u=F(1, 10))]
        taus, info = compute_taus(worlds)
        self.assertEqual((taus.tau_s, taus.tau_d, taus.tau_t, taus.tau_b), (F(7, 10), F(1, 10), F(4, 5), F(1, 3)))
        self.assertEqual(info["n_worlds"], 3)
        with self.assertRaises(ValueError):
            compute_taus(worlds + [self.ex(f=None)])

    def test_defined_default_metrics(self):
        self.assertTrue(defined_default_metrics(self.ex()))
        for key in ("fidelity", "deviation", "consistency", "uncertainty"):
            ex = self.ex()
            ex[key] = None
            self.assertFalse(defined_default_metrics(ex), key)
        self.assertTrue(defined_default_metrics(self.ex(nt=None)))  # D1 uses four metrics only

    def test_tau_json_round_trip_keeps_exact_fractions_next_to_the_floats(self):
        taus = ExactTaus(F(7, 10), F(1, 3), F(4, 5), F(1, 7))
        doc = taus.to_json()
        self.assertEqual(doc["tau_d_exact"], "1/3")
        self.assertEqual(doc["tau_d"], float(F(1, 3)))
        self.assertEqual(ExactTaus.from_json(doc), taus)
        self.assertEqual(str_frac(frac_str(F(6, 4))), F(3, 2))

    def test_pair_arrays_round_trip(self):
        vals = [F(1, 2), None, F(0, 7), F(3, 1)]
        arr = encode_pairs(vals)
        self.assertEqual(arr.dtype, np.int64)
        self.assertEqual(arr.shape, (4, 2))
        self.assertEqual(decode_pairs(arr), [F(1, 2), None, F(0), F(3)])
        bad = np.array([[1.0, 0.0], [np.nan, 1.0], [5.0, 1.0]])
        got = decode_pairs(bad)
        self.assertEqual(got[0], INVALID)
        self.assertEqual(got[1], INVALID)
        self.assertEqual(got[2], INVALID)  # numerator above the ratio bound
        self.assertEqual(decode_pairs(encode_pairs([F(1, 2)] * 6).reshape(2, 3, 2)), [F(1, 2)] * 6)


if __name__ == "__main__":
    unittest.main()
