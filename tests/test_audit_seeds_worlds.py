import hashlib
import unittest
from fractions import Fraction
from unittest import mock

from audit import worldset
from audit.cache import get_encoding
from audit.seeds import DEV_CORE, DEV_SALT, ROLES, dev_seed, seed, seeder
from audit.worldset import WorldSetError, check_valid, generate_valid
from tesaron.encoder import Context, encode
from tesaron.worlds import generate_world


class SeedTests(unittest.TestCase):
    CORE = "0123456789abcdef" * 4
    SALT = "fedcba9876543210" * 4

    def test_formula_and_known_vector(self):
        digest = hashlib.sha256(f"{self.CORE}|{self.SALT}|world-test|7".encode()).digest()
        expected = 1_000_000 + int.from_bytes(digest[:8], "big") % 10**9
        self.assertEqual(seed(self.CORE, self.SALT, "world-test", 7), expected)
        # known vectors, computed once and frozen here
        self.assertEqual(seed("abc", "salt", "world-test", 0), 359663300)
        self.assertEqual(seed("0" * 64, "1" * 64, "perm", 3), 92693960)

    def test_the_salt_changes_every_seed(self):
        a = seed(self.CORE, self.SALT, "aux", 1)
        self.assertNotEqual(a, seed(self.CORE, "0" * 64, "aux", 1))
        with self.assertRaises(ValueError):
            seed(self.CORE, "", "aux", 1)

    def test_range_disjoint_from_development_seeds(self):
        for role in ROLES:
            for i in range(50):
                s = seed("f" * 64, self.SALT, role, i)
                self.assertGreaterEqual(s, 1_000_000)
                self.assertLess(s, 1_000_000 + 10**9)

    def test_roles_and_indices_differ(self):
        values = {seed(self.CORE, self.SALT, r, i) for r in ROLES for i in range(10)}
        self.assertEqual(len(values), len(ROLES) * 10)
        self.assertNotEqual(seed(self.CORE, self.SALT, "world-test", 0), seed("b" * 64, self.SALT, "world-test", 0))

    def test_n2_role(self):
        self.assertIn("n2", ROLES)
        digest = hashlib.sha256((self.CORE + "|" + self.SALT + "|n2|2").encode()).digest()
        self.assertEqual(seed(self.CORE, self.SALT, "n2", 2), 1_000_000 + int.from_bytes(digest[:8], "big") % 10**9)
        self.assertTrue(900000 <= dev_seed("n2", 5) <= 900999)

    def test_bad_arguments(self):
        with self.assertRaises(ValueError):
            seed("x", "y", "no-such-role", 0)
        with self.assertRaises(ValueError):
            seed("x", "y", "aux", -1)
        with self.assertRaises(ValueError):
            seed("x", "y", "aux", True)

    def test_dev_mapping_is_inside_the_development_range(self):
        for role in ROLES:
            for i in range(100):
                self.assertTrue(900000 <= dev_seed(role, i) <= 900999)
        h = int.from_bytes(hashlib.sha256(f"{DEV_CORE}|{DEV_SALT}|aux|4".encode()).digest()[:8], "big")
        self.assertEqual(dev_seed("aux", 4), 900000 + h % 1000)
        self.assertIs(seeder("dev"), dev_seed)
        self.assertEqual(seeder("c" * 64, self.SALT)("aux", 2), seed("c" * 64, self.SALT, "aux", 2))


class WorldSetTests(unittest.TestCase):
    def test_dev_worlds_are_valid_and_deterministic(self):
        sd = seeder("dev")
        a, rej_a = generate_valid(4, sd, "world-test", "enc-test", "aux", build=get_encoding)
        b, rej_b = generate_valid(4, sd, "world-test", "enc-test", "aux", build=get_encoding)
        self.assertEqual([r.world_seed for r in a], [r.world_seed for r in b])
        self.assertEqual(rej_a, rej_b)
        for r in a:
            self.assertTrue(900000 <= r.world_seed <= 900999 and 900000 <= r.enc_seed <= 900999)
            ok, _, h = check_valid(r.world, r.context, r.encoding)
            self.assertTrue(ok)
            self.assertGreaterEqual(h, 10)
            self.assertTrue(r.encoding.fit.usable)
            self.assertEqual(r.aux_seed, sd("aux", r.draw))

    def test_invalid_world_is_replaced_by_the_next_derived_seed(self):
        sd = seeder("dev")
        first = sd("world-test", 0)
        real = worldset.check_valid

        def fake(world, ctx, enc):
            if world.seed == first:
                return False, "h_too_small", 3
            return real(world, ctx, enc)

        with mock.patch.object(worldset, "check_valid", fake):
            recs, rej = generate_valid(3, sd, "world-test", "enc-test", build=get_encoding)
        self.assertEqual(rej[0], {"draw": 0, "world_seed": first, "reason": "h_too_small"})
        self.assertNotIn(first, [r.world_seed for r in recs])
        self.assertEqual(recs[0].draw, 1)  # draw 1 (the next derived seed) took the place of draw 0
        self.assertEqual([r.draw for r in recs][:2], [1, 2])
        self.assertEqual(recs[0].world_seed, sd("world-test", 1))

    def test_at_most_200_draws_then_the_run_stops(self):
        sd = seeder("dev")
        with mock.patch.object(worldset, "check_valid", lambda w, c, e: (False, "h_too_small", 0)):
            with self.assertRaises(WorldSetError):
                generate_valid(2, sd, "world-test", "enc-test", max_draws=6, build=get_encoding)
        self.assertEqual(worldset.MAX_DRAWS, 200)

    def test_d5_rules_on_real_worlds(self):
        world = generate_world(900001)
        ok, reason, h = check_valid(world, *_ctx_enc(world, 900101))
        self.assertTrue(ok and h >= 10)
        # PCM not usable (does not converge in one iteration) is invalid
        ctx = Context.from_world(world, 900101, max_iter=1, tol=0.0)
        enc = encode(world, ctx)
        self.assertEqual(check_valid(world, ctx, enc)[:2], (False, "pcm_unusable"))

    def test_a_calibration_world_with_an_undefined_default_metric_is_invalid(self):
        world = generate_world(900001)
        ctx, enc = _ctx_enc(world, 900101)
        self.assertTrue(check_valid(world, ctx, enc, calibration=True)[0])
        undefined = {"fidelity": None, "deviation": Fraction(0), "consistency": Fraction(1), "uncertainty": Fraction(1, 2)}
        with mock.patch("audit.system.System.evaluate_exact", lambda *a, **k: (None, None, undefined)):
            self.assertEqual(check_valid(world, ctx, enc, calibration=True)[:2], (False, "undefined_default_metric"))
            self.assertTrue(check_valid(world, ctx, enc)[0])  # only calibration worlds are tested for it

    def test_only_the_dedicated_exception_replaces_a_world(self):
        from tesaron.worlds import WorldGenerationError

        sd = seeder("dev")

        def failing(ws, es):
            raise WorldGenerationError("no acceptable world")

        def crashing(ws, es):
            raise RuntimeError("some other failure")

        with self.assertRaises(WorldSetError):  # every draw fails the generator: replaced until the limit
            generate_valid(2, sd, "world-test", "enc-test", max_draws=4, build=failing)
        with self.assertRaises(RuntimeError) as cm:  # any other RuntimeError is not "an invalid world"
            generate_valid(2, sd, "world-test", "enc-test", max_draws=4, build=crashing)
        self.assertNotIsInstance(cm.exception, WorldSetError)

    def test_h_threshold_is_ten(self):
        world = generate_world(900001)
        ctx, enc = _ctx_enc(world, 900101)
        with mock.patch.object(worldset, "compute_H", lambda *a: list(range(9))):
            self.assertEqual(check_valid(world, ctx, enc)[:2], (False, "h_too_small"))
        with mock.patch.object(worldset, "compute_H", lambda *a: list(range(10))):
            self.assertTrue(check_valid(world, ctx, enc)[0])


def _ctx_enc(world, enc_seed):
    ctx = Context.from_world(world, enc_seed)
    return ctx, encode(world, ctx)


if __name__ == "__main__":
    unittest.main()
