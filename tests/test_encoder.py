import dataclasses
import unittest
from pathlib import Path
from unittest import mock

import numpy as np

import tesaron.encoder.core as encode_module
from tesaron.atoms import Atom
from tesaron.belnap import interface_facts
from tesaron.degrees import Membership
from tesaron.encoder import Context, encode, pcm_fit, typicality
from tesaron.enums import Channel, ComputationalStatus, EpistemicStatus
from tesaron.serialize import canonical_hash
from tesaron.worlds import WorldParams, generate_world

ETA3 = np.array([0.72, 0.72, 0.72])  # the Context default, 2 * sigma^2 (revision S-2)
PROTOS = np.array(WorldParams().prototypes())


class PCMTests(unittest.TestCase):
    def test_converges_on_hand_made_data(self):
        rng = np.random.Generator(np.random.PCG64(900301))
        clusters = [np.array([0.0, 0.0]), np.array([20.0, 0.0]), np.array([0.0, 20.0])]
        pts = np.vstack([c + 0.3 * rng.standard_normal((20, 2)) for c in clusters])
        init = np.array(clusters) + 0.8  # start off the true centers
        fit = pcm_fit(pts, init, ETA3, 2.0, 100, 1e-6)
        self.assertTrue(fit.converged)
        self.assertLess(fit.n_iter, 100)
        for c, f in zip(clusters, fit.centers):
            self.assertLess(np.linalg.norm(np.array(f) - c), 0.3)

    def test_outlier_typicality_sum_below_half(self):
        rng = np.random.Generator(np.random.PCG64(900302))
        clusters = PROTOS
        pts = np.vstack([c + 0.4 * rng.standard_normal((20, 2)) for c in clusters] + [np.array([[7.0, 0.0]])])
        fit = pcm_fit(pts, PROTOS, ETA3, 2.0, 100, 1e-6)
        self.assertTrue(fit.converged)
        centers = np.array(fit.centers)
        u_out = typicality(np.array([[7.0, 0.0]]), centers, ETA3, 2.0)[0]
        self.assertLess(u_out.sum(), 0.5)
        u_in = typicality(PROTOS[:1], centers, ETA3, 2.0)[0]
        self.assertGreater(u_in.sum(), 1.0)  # a typical point: sum over classes not normalized to 1... > outlier
        self.assertGreater(u_in.max(), 0.9)

    def test_initialization_at_prototypes(self):
        # one iteration from the given initial centers equals the independent hand formula
        pts = np.array([[3.2, 0.1], [2.8, -0.2], [-1.4, 2.7], [-1.6, -2.5], [0.0, 0.1]])
        fit = pcm_fit(pts, PROTOS, ETA3, 2.0, 1, 0.0)
        d2 = ((pts[:, None, :] - PROTOS[None, :, :]) ** 2).sum(axis=2)
        u = 1.0 / (1.0 + d2 / 0.72)
        expected = (u**2).T @ pts / (u**2).sum(axis=0)[:, None]
        np.testing.assert_allclose(np.array(fit.centers), expected, rtol=0, atol=1e-12)
        self.assertEqual(fit.n_iter, 1)

    def test_encoder_passes_prototypes_as_initial_centers(self):
        world = generate_world(900001)
        ctx = Context.from_world(world, 900101)
        self.assertEqual(ctx.prototypes, world.params.prototypes())
        self.assertEqual(ctx.eta, (2 * 0.6**2,) * 3)
        self.assertAlmostEqual(ctx.eta[0], 0.72)
        self.assertEqual(ctx.max_iter, 1000)
        self.assertEqual(Context.from_world(world, 900101, eta=1.5).eta, (1.5, 1.5, 1.5))
        w2 = generate_world(900001, WorldParams(feature_sigma=0.5))
        self.assertEqual(Context.from_world(w2, 900101).eta, (0.5,) * 3)  # follows sigma, not hard-coded
        seen = {}
        real = encode_module.pcm_fit

        def spy(points, init, *a, **k):
            seen["init"] = np.array(init)
            return real(points, init, *a, **k)

        with mock.patch.object(encode_module, "pcm_fit", spy):
            encode(world, ctx)
        np.testing.assert_array_equal(seen["init"], np.array(world.params.prototypes()))

    def test_not_converged_gives_not_computed_and_no_facts(self):
        world = generate_world(900001)
        ctx = Context.from_world(world, 900101, max_iter=1, tol=0.0)
        enc = encode(world, ctx)
        self.assertFalse(enc.fit.converged)
        self.assertEqual(enc.fit.n_iter, 1)
        class_units = [u for a, u in enc.units.items() if a.pred.startswith("c")]
        self.assertTrue(class_units)
        for u in class_units:
            self.assertIs(u.status, ComputationalStatus.NOT_COMPUTED)
        facts = interface_facts(enc.units, 0.5)
        self.assertFalse([f for f in facts if f[1].pred.startswith("c")])
        # relation units are unaffected
        rel_units = [u for a, u in enc.units.items() if a.pred.startswith("r")]
        self.assertTrue(rel_units)
        self.assertTrue(all(u.status is EpistemicStatus.OBSERVED for u in rel_units))


class DegeneracyTests(unittest.TestCase):
    def test_coincident_data_sets_degenerate_flag(self):
        # every point sits on one spot: all fitted centers coincide, although the loop converges
        rng = np.random.Generator(np.random.PCG64(900303))
        pts = np.array([1.0, 1.0]) + 0.05 * rng.standard_normal((40, 2))
        fit = pcm_fit(pts, PROTOS, ETA3, 2.0, 200, 1e-9)
        self.assertTrue(fit.converged)
        self.assertTrue(fit.degenerate)
        self.assertFalse(fit.usable)

    def test_well_separated_data_is_not_degenerate(self):
        rng = np.random.Generator(np.random.PCG64(900304))
        pts = np.vstack([c + 0.3 * rng.standard_normal((20, 2)) for c in PROTOS])
        fit = pcm_fit(pts, PROTOS, ETA3, 2.0, 100, 1e-6)
        self.assertTrue(fit.converged)
        self.assertFalse(fit.degenerate)
        self.assertTrue(fit.usable)

    def test_threshold_is_half_the_smallest_prototype_distance(self):
        init = np.array([[0.0, 0.0], [4.0, 0.0]])  # smallest prototype distance 4 -> threshold 2
        eta = np.array([1.0, 1.0])
        # two tight clusters 1.9 apart: centers stay ~1.9 apart (< 2) -> degenerate
        near = np.array([[0.0, 0.0]] * 5 + [[1.9, 0.0]] * 5)
        far = np.array([[0.0, 0.0]] * 5 + [[3.9, 0.0]] * 5)
        self.assertTrue(pcm_fit(near, init, eta, 2.0, 200, 1e-9).degenerate)
        self.assertFalse(pcm_fit(far, init, eta, 2.0, 200, 1e-9).degenerate)

    def test_degenerate_fit_gives_not_computed_and_no_facts(self):
        world = generate_world(900001)
        ctx = Context.from_world(world, 900101)
        flat = tuple(dataclasses.replace(fr, x=(1.0, 1.0)) for fr in world.feature_rows)
        enc = encode(dataclasses.replace(world, feature_rows=flat), ctx)
        self.assertTrue(enc.fit.converged)
        self.assertTrue(enc.fit.degenerate)
        class_units = [u for a, u in enc.units.items() if a.pred.startswith("c")]
        self.assertTrue(class_units)
        for u in class_units:
            self.assertIs(u.status, ComputationalStatus.NOT_COMPUTED)
        facts = interface_facts(enc.units, 0.5)
        self.assertFalse([f for f in facts if f[1].pred.startswith("c")])
        # relation units are unaffected
        self.assertTrue(any(u.status is EpistemicStatus.OBSERVED for a, u in enc.units.items() if a.pred.startswith("r")))
        # the normal fit on the same world is usable
        good = encode(world, ctx)
        self.assertTrue(good.fit.usable)


class EncoderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.world = generate_world(900001)
        cls.ctx = Context.from_world(cls.world, 900101)
        cls.enc = encode(cls.world, cls.ctx)

    def test_selection_and_split(self):
        w, e = self.world, self.enc
        n_total = len(w.feature_rows) + len(w.report_rows)
        self.assertEqual(len(e.selected_ids), round(0.8 * n_total))
        self.assertEqual(list(e.selected_ids), sorted(e.selected_ids))
        self.assertEqual(len(e.derive_ids), round(0.7 * len(e.selected_ids)))
        self.assertEqual(sorted(e.derive_ids + e.validate_ids), list(e.selected_ids))
        self.assertFalse(set(e.derive_ids) & set(e.validate_ids))
        self.assertEqual(list(e.derive_ids), sorted(e.derive_ids))
        self.assertEqual(list(e.validate_ids), sorted(e.validate_ids))

    def test_same_inputs_same_canonical_hash(self):
        again = encode(generate_world(900001), Context.from_world(generate_world(900001), 900101))
        self.assertEqual(canonical_hash(again), canonical_hash(self.enc))

    def test_different_seed_different_selection(self):
        other = encode(self.world, Context.from_world(self.world, 900102))
        self.assertNotEqual(other.selected_ids, self.enc.selected_ids)
        self.assertNotEqual(canonical_hash(other), canonical_hash(self.enc))

    def test_validation_data_does_not_affect_fit(self):
        validate = set(self.enc.validate_ids)
        garbage = tuple(
            dataclasses.replace(fr, x=(1.0e6 + i, -1.0e6 - 2 * i)) if fr.row_id in validate else fr
            for i, fr in enumerate(self.world.feature_rows)
        )
        self.assertNotEqual(garbage, self.world.feature_rows)
        world2 = dataclasses.replace(self.world, feature_rows=garbage)
        enc2 = encode(world2, self.ctx)
        self.assertEqual(enc2.derive_ids, self.enc.derive_ids)
        self.assertEqual(enc2.validate_ids, self.enc.validate_ids)
        self.assertEqual(enc2.fit, self.enc.fit)  # bit-identical centers, iterations, flag
        self.assertEqual(
            [np.array(c).tobytes() for c in enc2.fit.centers],
            [np.array(c).tobytes() for c in self.enc.fit.centers],
        )
        self.assertEqual(enc2.units, self.enc.units)  # D_derive units do not change either
        self.assertNotEqual(enc2.validation_units, self.enc.validation_units)

    def test_class_units_mu_neg_zero_whatever_mu_pos(self):
        class_units = [u for a, u in self.enc.units.items() if a.pred.startswith("c")]
        self.assertTrue(class_units)
        self.assertTrue(len({u.mu_pos.value for u in class_units}) > 10)
        for u in class_units + [u for a, u in self.enc.validation_units.items() if a.pred.startswith("c")]:
            self.assertEqual(u.mu_neg, Membership(0.0))
            self.assertIsInstance(u.mu_pos, Membership)
            self.assertIs(u.status, EpistemicStatus.OBSERVED)

    def test_no_code_path_derives_mu_neg_from_mu_pos(self):
        src = Path(encode_module.__file__).read_text(encoding="utf-8")
        # the class-unit constructor sets mu_neg to the constant 0 ...
        self.assertIn("mu_neg=Membership(0.0)", src)
        # ... and mu_neg is never computed from mu_pos or from the typicality u
        for line in src.splitlines():
            code = line.split("#")[0]
            if "mu_neg" in code and "=" in code:
                self.assertNotRegex(code, r"mu_pos|\bu\[|1\s*-")
        self.assertIn("FORBIDDEN", src)

    def test_typicalities_not_normalized(self):
        sums = {}
        for a, u in self.enc.units.items():
            if a.pred.startswith("c"):
                sums[a.args[0]] = sums.get(a.args[0], 0.0) + u.mu_pos.value
        self.assertTrue(any(abs(s - 1.0) > 0.05 for s in sums.values()))
        # outliers are far from every prototype: their typicality sum is small
        for e in self.world.outliers:
            if e in sums:
                self.assertLess(sums[e], 0.6)

    def test_class_unit_values_match_hand_computation(self):
        derive = set(self.enc.derive_ids)
        centers = np.array(self.enc.fit.centers)
        e = next(e for e in self.world.entities if any(f.entity == e and f.row_id in derive for f in self.world.feature_rows))
        rows = [f for f in self.world.feature_rows if f.entity == e and f.row_id in derive]
        xbar = np.mean([f.x for f in rows], axis=0)
        for k in range(3):
            d2 = float(((xbar - centers[k]) ** 2).sum())
            expect = 1.0 / (1.0 + d2 / self.ctx.eta[k])
            u = self.enc.units[Atom(f"c{k}", (e,))]
            self.assertAlmostEqual(u.mu_pos.value, expect, places=12)
            self.assertEqual(u.provenance, tuple(f.row_id for f in rows))

    def test_relation_units_match_hand_computation(self):
        derive = set(self.enc.derive_ids)
        sup = self.ctx.support
        by_atom = {}
        for r in self.world.report_rows:
            if r.row_id in derive:
                by_atom.setdefault(r.atom, []).append(r)
        rel_units = {a: u for a, u in self.enc.units.items() if a.pred.startswith("r")}
        self.assertEqual(sorted(rel_units), sorted(by_atom))
        for atom, rows in by_atom.items():
            u = rel_units[atom]
            pos = [sup[r.source].value for r in rows if r.polarity is Channel.POS]
            neg = [sup[r.source].value for r in rows if r.polarity is Channel.NEG]
            self.assertEqual(u.mu_pos.value, max(pos, default=0.0))
            self.assertEqual(u.mu_neg.value, max(neg, default=0.0))
            self.assertEqual(u.provenance, tuple(r.row_id for r in rows))
            self.assertIs(u.status, EpistemicStatus.OBSERVED)

    def test_units_sorted_and_validation_units_exist(self):
        self.assertEqual(list(self.enc.units), sorted(self.enc.units))
        self.assertEqual(list(self.enc.validation_units), sorted(self.enc.validation_units))
        self.assertTrue(self.enc.validation_units)

    def test_entity_without_derive_rows_gets_no_class_units(self):
        world = generate_world(900001, WorldParams(rows_per_entity=1))
        ctx = Context.from_world(world, 900101, derive_fraction=0.3)
        enc = encode(world, ctx)
        derive = set(enc.derive_ids)
        with_rows = {f.entity for f in world.feature_rows if f.row_id in derive}
        self.assertTrue(len(with_rows) < len(world.entities))
        class_entities = {a.args[0] for a in enc.units if a.pred.startswith("c")}
        self.assertEqual(class_entities, with_rows)
        for e in set(world.entities) - with_rows:
            for k in range(3):
                self.assertNotIn(Atom(f"c{k}", (e,)), enc.units)


if __name__ == "__main__":
    unittest.main()
