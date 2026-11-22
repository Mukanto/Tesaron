import itertools
import unittest

from helpers import A

from tesaron.belnap import boundary_share, enc, encoded_values, interface_facts, on_boundary, to_value, unit_value
from tesaron.decoder import And, Not, Or, b_and, b_not, b_or, evaluate_query
from tesaron.degrees import Membership
from tesaron.enums import Belnap, Channel, ComputationalStatus, EpistemicStatus
from tesaron.meaning import MeaningUnit

M = Membership
T, F, B, U = Belnap.T, Belnap.F, Belnap.B, Belnap.U


def unit(atom, pos, neg, prov=("f0001",), status=EpistemicStatus.OBSERVED):
    return MeaningUnit(atom, M(pos), M(neg), prov, status)


class InterfaceTests(unittest.TestCase):
    def test_four_rows_of_the_table(self):
        self.assertIs(to_value(M(0.9), M(0.1), 0.7), T)
        self.assertIs(to_value(M(0.1), M(0.9), 0.7), F)
        self.assertIs(to_value(M(0.9), M(0.8), 0.7), B)
        self.assertIs(to_value(M(0.1), M(0.2), 0.7), U)

    def test_equality_counts_as_geq(self):
        self.assertIs(to_value(M(0.7), M(0.0), 0.7), T)
        self.assertIs(to_value(M(0.0), M(0.7), 0.7), F)
        self.assertIs(to_value(M(0.7), M(0.7), 0.7), B)
        self.assertIs(to_value(M(0.6999999), M(0.0), 0.7), U)
        self.assertIs(to_value(M(1.0), M(1.0), 1.0), B)
        self.assertIs(to_value(M(0.0), M(0.0), 0.0), B)

    def test_initial_facts(self):
        a, b, c, d = A("p", "a"), A("p", "b"), A("p", "c"), A("p", "d")
        units = {
            a: unit(a, 0.9, 0.0, ("r1",)),
            b: unit(b, 0.0, 0.9, ("r2",)),
            c: unit(c, 0.8, 0.8, ("r3", "r4")),
            d: unit(d, 0.1, 0.1, ("r5",)),
        }
        facts = interface_facts(units, 0.7)
        self.assertEqual(
            facts,
            {
                (Channel.POS, a): ("r1",),
                (Channel.NEG, b): ("r2",),
                (Channel.POS, c): ("r3", "r4"),
                (Channel.NEG, c): ("r3", "r4"),
            },
        )
        self.assertEqual(list(facts), sorted(facts))

    def test_not_computed_unit_produces_no_facts(self):
        a = A("c0", "e00")
        units = {a: unit(a, 0.99, 0.0, status=ComputationalStatus.NOT_COMPUTED)}
        self.assertEqual(interface_facts(units, 0.5), {})
        self.assertIs(unit_value(units[a], 0.5), U)

    def test_enc_is_u_without_unit(self):
        a, b = A("p", "a"), A("p", "b")
        units = {a: unit(a, 0.9, 0.0)}
        self.assertIs(enc(units, a, 0.7), T)
        self.assertIs(enc(units, b, 0.7), U)
        self.assertEqual(encoded_values(units, 0.7), {a: T})

    def test_boundary_band(self):
        a, b, c = A("p", "a"), A("p", "b"), A("p", "c")
        units = {a: unit(a, 0.72, 0.0), b: unit(b, 0.0, 0.66), c: unit(c, 0.9, 0.1)}
        self.assertTrue(on_boundary(units[a], 0.7, 0.05))
        self.assertTrue(on_boundary(units[b], 0.7, 0.05))
        self.assertFalse(on_boundary(units[c], 0.7, 0.05))
        self.assertEqual(boundary_share(units, 0.7, 0.05), 2 / 3)
        self.assertIsNone(boundary_share({}, 0.7, 0.05))
        # strict inequality: exactly epsilon away is not on the boundary
        d = A("p", "d")
        self.assertFalse(on_boundary(unit(d, 0.75, 0.0), 0.5, 0.25))


class ConnectiveTests(unittest.TestCase):
    def test_not(self):
        self.assertEqual([b_not(v) for v in (T, F, B, U)], [F, T, B, U])

    def test_and_or_tables(self):
        # rows/cols in the order T, F, B, U
        and_table = {
            T: [T, F, B, U], F: [F, F, F, F], B: [B, F, B, F], U: [U, F, F, U],
        }
        or_table = {
            T: [T, T, T, T], F: [T, F, B, U], B: [T, B, B, T], U: [T, U, T, U],
        }
        order = [T, F, B, U]
        for a in order:
            for i, b in enumerate(order):
                self.assertIs(b_and(a, b), and_table[a][i], (a, b))
                self.assertIs(b_or(a, b), or_table[a][i], (a, b))

    def test_definition_pos_neg(self):
        for a, b in itertools.product((T, F, B, U), repeat=2):
            self.assertEqual((b_not(a).pos, b_not(a).neg), (a.neg, a.pos))
            self.assertEqual((b_and(a, b).pos, b_and(a, b).neg), (a.pos and b.pos, a.neg or b.neg))
            self.assertEqual((b_or(a, b).pos, b_or(a, b).neg), (a.pos or b.pos, a.neg and b.neg))

    def test_algebra(self):
        for a, b in itertools.product((T, F, B, U), repeat=2):
            self.assertIs(b_not(b_not(a)), a)
            self.assertIs(b_not(b_and(a, b)), b_or(b_not(a), b_not(b)))  # De Morgan
            self.assertIs(b_not(b_or(a, b)), b_and(b_not(a), b_not(b)))
            self.assertIs(b_and(a, b), b_and(b, a))
            self.assertIs(b_or(a, b), b_or(b, a))

    def test_compound_query(self):
        values = {A("p", "a"): T, A("q", "a"): B, A("r", "a"): U}
        look = lambda atom: values.get(atom, U)
        q = And(A("p", "a"), Not(A("q", "a")))
        self.assertIs(evaluate_query(q, look), B)
        self.assertIs(evaluate_query(Or(A("r", "a"), A("p", "a")), look), T)
        self.assertIs(evaluate_query(Not(A("r", "a")), look), U)


if __name__ == "__main__":
    unittest.main()
