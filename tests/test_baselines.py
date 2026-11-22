import unittest
from dataclasses import replace

from tesaron.belnap import enc as enc_value
from tesaron.criterion import PLACEHOLDER_TAUS, compute_metrics_for, is_feasible, make_baselines, make_point, point_score
from tesaron.encoder import Context, encode
from tesaron.enums import Belnap
from tesaron.worlds import generate_world


class BaselineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = []
        for wseed, eseed in ((900001, 900101), (900002, 900102), (900003, 900103)):
            world = generate_world(wseed)
            ctx = Context.from_world(world, eseed)
            cls.cases.append((world, ctx, encode(world, ctx)))

    def metrics_for(self, world, ctx, encoding, alpha, name):
        ctx = replace(ctx, alpha=alpha)
        out = make_baselines(encoding.units, alpha, ctx.vocabulary)[name]
        m = compute_metrics_for(world, ctx, encoding, out)
        return m, make_point((alpha, 0), m, PLACEHOLDER_TAUS)

    def test_output_format(self):
        world, ctx, encoding = self.cases[0]
        bl = make_baselines(encoding.units, 0.7, ctx.vocabulary)
        self.assertEqual(sorted(bl), ["all_both", "all_false", "all_true", "all_unknown", "echo"])
        atom = sorted(ctx.vocabulary)[0]
        for name, val in (("all_true", Belnap.T), ("all_false", Belnap.F), ("all_unknown", Belnap.U), ("all_both", Belnap.B)):
            self.assertIs(bl[name].full(atom), val)
            self.assertIs(bl[name].verdict(atom), val)
        for a in sorted(ctx.vocabulary):
            self.assertIs(bl["echo"].full(a), enc_value(encoding.units, a, 0.7))
            self.assertIs(bl["echo"].verdict(a), bl["echo"].full(a))

    def test_echo_has_zero_new_true_and_zero_hypervolume(self):
        for world, ctx, encoding in self.cases:
            for alpha in (0.9, 0.7, 0.5):
                m, pt = self.metrics_for(world, ctx, encoding, alpha, "echo")
                with self.subTest(alpha=alpha):
                    self.assertGreater(m.size_H, 0)
                    self.assertEqual(m.new_true, 0.0)  # H atoms have no unit, so echo says U
                    self.assertEqual(point_score(pt), 0.0)
                    self.assertEqual(m.hyp_count, 0)
                    self.assertEqual(m.deviation, 0.0)  # full = enc

    def test_unknown_and_both_have_zero_fidelity_and_are_infeasible(self):
        for world, ctx, encoding in self.cases:
            for alpha in (0.9, 0.7, 0.5):
                for name in ("all_unknown", "all_both"):
                    m, pt = self.metrics_for(world, ctx, encoding, alpha, name)
                    with self.subTest(alpha=alpha, name=name):
                        self.assertGreater(m.size_I, 0)
                        self.assertEqual(m.fidelity, 0.0)
                        self.assertFalse(is_feasible(m, PLACEHOLDER_TAUS))
                        self.assertFalse(pt.feasible)
                        self.assertEqual(point_score(pt), 0.0)

    def test_all_unknown_and_all_both_never_count_as_correct(self):
        world, ctx, encoding = self.cases[0]
        m, _ = self.metrics_for(world, ctx, encoding, 0.7, "all_unknown")
        self.assertEqual(m.uncertainty, 1.0)
        self.assertEqual(m.new_true, 0.0)
        self.assertEqual(m.new_false, 0.0)  # nothing decided
        m, _ = self.metrics_for(world, ctx, encoding, 0.7, "all_both")
        self.assertEqual(m.consistency, 0.0)
        self.assertEqual(m.new_true, 0.0)

    def test_all_true_and_all_false_are_fully_decided(self):
        world, ctx, encoding = self.cases[0]
        mt, _ = self.metrics_for(world, ctx, encoding, 0.7, "all_true")
        mf, _ = self.metrics_for(world, ctx, encoding, 0.7, "all_false")
        self.assertEqual(mt.uncertainty, 0.0)
        self.assertEqual(mf.uncertainty, 0.0)
        # most vocabulary atoms are false in the world, so all_true makes many errors
        self.assertGreater(mt.new_false, mf.new_false)
        self.assertGreater(mt.new_false, 0.5)


if __name__ == "__main__":
    unittest.main()
