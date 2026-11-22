import operator
import unittest

import numpy as np

from tesaron.atoms import Atom
from tesaron.degrees import Membership, Probability, support_degrees_from_world, tconorm_max, tnorm_min
from tesaron.encoder import Context, encode
from tesaron.enums import EpistemicStatus
from tesaron.meaning import MeaningUnit
from tesaron.worlds import generate_world


class MembershipProbabilityTests(unittest.TestCase):
    def test_arithmetic_raises_type_error(self):
        for cls in (Membership, Probability):
            a, b = cls(0.3), cls(0.6)
            for op in (operator.add, operator.sub, operator.mul, operator.truediv):
                with self.subTest(cls=cls.__name__, op=op.__name__):
                    with self.assertRaises(TypeError):
                        op(a, b)
                    with self.assertRaises(TypeError):
                        op(a, 2)
                    with self.assertRaises(TypeError):
                        op(2, a)
                    with self.assertRaises(TypeError):
                        op(a, 0.5)
                    with self.assertRaises(TypeError):
                        op(0.5, a)
            with self.assertRaises(TypeError):
                -a

    def test_mixing_raises_type_error(self):
        m, p = Membership(0.5), Probability(0.5)
        for op in (operator.lt, operator.le, operator.gt, operator.ge, operator.eq, operator.ne,
                   operator.add, operator.mul):
            with self.subTest(op=op.__name__):
                with self.assertRaises(TypeError):
                    op(m, p)
                with self.assertRaises(TypeError):
                    op(p, m)
        with self.assertRaises(TypeError):
            Membership(p)
        with self.assertRaises(TypeError):
            Probability(m)
        with self.assertRaises(TypeError):
            tconorm_max(m, p)
        with self.assertRaises(TypeError):
            tnorm_min(p)

    def test_out_of_range_raises(self):
        for cls in (Membership, Probability):
            for bad in (-0.001, 1.0000001, 2, -1, float("nan"), float("inf")):
                with self.subTest(cls=cls.__name__, bad=bad):
                    with self.assertRaises(ValueError):
                        cls(bad)
            cls(0.0), cls(1.0), cls(0), cls(1), cls(np.float64(0.5))
            with self.assertRaises(TypeError):
                cls("0.5")
            with self.assertRaises(TypeError):
                cls(True)

    def test_comparisons_and_value(self):
        m = Membership(0.7)
        self.assertEqual(m.value, 0.7)
        self.assertTrue(m >= 0.7 and m <= 0.7 and m == 0.7)
        self.assertTrue(m > 0.6 and m < 0.8 and m != 0.8)
        self.assertTrue(0.6 < m and 0.8 > m)
        self.assertTrue(m > Membership(0.2) and Membership(0.2) < m and m == Membership(0.7))
        self.assertTrue(m >= 0)  # plain int threshold
        self.assertFalse(m == "0.7")

    def test_immutable(self):
        m = Membership(0.4)
        with self.assertRaises(AttributeError):
            m.value = 0.5
        with self.assertRaises(AttributeError):
            m._value = 0.5

    def test_tconorm_max_idempotent_and_tnorm_min(self):
        a, b, c = Membership(0.2), Membership(0.9), Membership(0.5)
        self.assertEqual(tconorm_max(a, a), a)
        self.assertEqual(tconorm_max(b, b, b), b)
        self.assertEqual(tconorm_max(a, b, c), Membership(0.9))
        self.assertEqual(tconorm_max(a), a)
        self.assertEqual(tconorm_max(), Membership(0.0))
        self.assertEqual(tnorm_min(a, b, c), Membership(0.2))
        self.assertEqual(tnorm_min(b, b), b)
        self.assertEqual(tnorm_min(a), a)
        self.assertEqual(tnorm_min(), Membership(1.0))
        self.assertIsInstance(tconorm_max(a, b), Membership)
        with self.assertRaises(TypeError):
            tconorm_max(0.3, 0.4)
        with self.assertRaises(TypeError):
            tnorm_min(0.3, a)

    def test_support_conversion(self):
        w = generate_world(900001)
        sup = support_degrees_from_world(w)
        self.assertEqual(sorted(sup), sorted(w.source_reliabilities))
        for s, m in sup.items():
            self.assertIsInstance(m, Membership)
            self.assertEqual(m.value, w.source_reliabilities[s].value)
        doc = support_degrees_from_world.__doc__
        self.assertIn(
            "v0 modelling choice: the context's support degree for a source equals, numerically, the "
            "generator's probability that the source reports correctly; in the encoder it is a membership "
            "degree and is only combined with max",
            " ".join(doc.split()),
        )


class EncoderRejectsNonMembershipTests(unittest.TestCase):
    def setUp(self):
        self.world = generate_world(900001)
        self.ctx = Context.from_world(self.world, 900101)

    def test_encode_rejects_plain_floats_and_probabilities(self):
        from dataclasses import replace

        for bad in (0.9, Probability(0.9), 1):
            sup = dict(self.ctx.support)
            sup["s0"] = bad
            with self.subTest(bad=repr(bad)):
                with self.assertRaises(TypeError):
                    encode(self.world, replace(self.ctx, support=sup))

    def test_meaning_unit_rejects_non_membership(self):
        atom = Atom("c0", ("e00",))
        for bad in (0.5, Probability(0.5)):
            with self.assertRaises(TypeError):
                MeaningUnit(atom, bad, Membership(0.0), (), EpistemicStatus.OBSERVED)
            with self.assertRaises(TypeError):
                MeaningUnit(atom, Membership(0.0), bad, (), EpistemicStatus.OBSERVED)

    def test_interface_rejects_non_membership(self):
        from tesaron.belnap import to_value

        with self.assertRaises(TypeError):
            to_value(0.9, Membership(0.0), 0.7)
        with self.assertRaises(TypeError):
            to_value(Membership(0.9), Probability(0.0), 0.7)


if __name__ == "__main__":
    unittest.main()
