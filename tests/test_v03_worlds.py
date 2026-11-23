import unittest

from audit.v03.worlds import (
    N_SOURCES, Q_FALSE, Q_TRUE, REL_HIGH, REL_LOW, V03_OVERLAP_FRACTION, V03_RADIUS, build_v03_final,
    generate_world_v03, generate_world_v03_final, v03_params, v03_reliabilities, v03_world_params,
)
from tesaron.degrees import Probability
from tesaron.serialize import canonical_hash
from tesaron.worlds import WorldParams, generate_world

CHANGED = {"n_sources", "source_reliabilities", "q_true", "q_false", "prototype_radius"}
CHANGED_FINAL = CHANGED | {"overlap_fraction"}


class V03WorldTests(unittest.TestCase):
    def test_reliabilities_deterministic_and_in_range(self):
        for seed in (930000, 930001, 5):
            a, b = v03_reliabilities(seed), v03_reliabilities(seed)
            self.assertEqual(a, b)
            self.assertEqual(len(a), 8)
            for p in a:
                self.assertIsInstance(p, Probability)
                self.assertGreaterEqual(p.value, REL_LOW)
                self.assertLessEqual(p.value, REL_HIGH)
                self.assertEqual(p.value, round(p.value, 3))
        self.assertNotEqual(v03_reliabilities(930000), v03_reliabilities(930001))

    def test_params_change_only_the_five_fields(self):
        base, p = WorldParams(), v03_params(930000, 1.5)
        for name in WorldParams.__dataclass_fields__:
            if name in CHANGED:
                continue
            self.assertEqual(getattr(p, name), getattr(base, name), name)
        self.assertEqual(p.n_sources, N_SOURCES)
        self.assertEqual(p.source_reliabilities, v03_reliabilities(930000))
        self.assertEqual(p.q_true, Q_TRUE)
        self.assertEqual(p.q_false, Q_FALSE)
        self.assertEqual(p.prototype_radius, 1.5)

    def test_world_is_deterministic(self):
        a, b = generate_world_v03(930003, 1.25), generate_world_v03(930003, 1.25)
        self.assertEqual(canonical_hash(a), canonical_hash(b))
        self.assertEqual(len(a.source_reliabilities), 8)
        self.assertNotEqual(canonical_hash(a), canonical_hash(generate_world_v03(930003, 1.0)))

    def test_final_params_change_only_the_six_fields(self):
        base, p = WorldParams(), v03_world_params(930007)
        for name in WorldParams.__dataclass_fields__:
            if name not in CHANGED_FINAL:
                self.assertEqual(getattr(p, name), getattr(base, name), name)
        self.assertEqual((V03_RADIUS, V03_OVERLAP_FRACTION), (3.0, 0.8))
        self.assertEqual(p.prototype_radius, 3.0)
        self.assertEqual(p.overlap_fraction, 0.8)
        self.assertEqual(p.source_reliabilities, v03_reliabilities(930007))
        self.assertEqual(p.n_sources, 8)
        self.assertEqual((p.q_true, p.q_false), (Q_TRUE, Q_FALSE))

    def test_final_world_is_deterministic(self):
        a, b = generate_world_v03_final(930002), generate_world_v03_final(930002)
        self.assertEqual(canonical_hash(a), canonical_hash(b))
        self.assertNotEqual(canonical_hash(a), canonical_hash(generate_world_v03(930002, 3.0)))  # overlap differs
        world, ctx, enc = build_v03_final(930002, 940002)
        self.assertEqual(canonical_hash(world), canonical_hash(a))
        self.assertEqual(ctx.encoder_seed, 940002)
        self.assertTrue(enc.units)

    def test_v02_defaults_untouched(self):
        p = WorldParams()
        self.assertEqual(p.n_sources, 3)
        self.assertEqual(p.prototype_radius, 3.0)
        self.assertEqual(p.source_reliabilities, (Probability(0.95), Probability(0.80), Probability(0.60)))
        self.assertEqual((p.q_true, p.q_false), (0.5, 0.02))
        self.assertEqual(canonical_hash(generate_world(930000)), canonical_hash(generate_world(930000, WorldParams())))


if __name__ == "__main__":
    unittest.main()
