import unittest

from helpers import A, L, pos

from tesaron.belnap import interface_facts
from tesaron.criterion import Metrics, compute_H, compute_metrics
from tesaron.criterion.wisdom import Taus, is_feasible
from tesaron.decoder import Rule, decode
from tesaron.degrees import Membership
from tesaron.enums import Belnap, Channel, EpistemicStatus
from tesaron.meaning import MeaningUnit

M = Membership
p_a, p_b, p_c, q_a, q_b, q_c = (A("p", "a"), A("p", "b"), A("p", "c"), A("q", "a"), A("q", "b"), A("q", "c"))
VOCAB = frozenset([p_a, p_b, p_c, q_a, q_b, q_c])
RULES = (Rule("R1", L("q", "X"), (L("p", "X"),)),)
TRUTH = {p_a: True, p_b: True, p_c: False, q_a: True, q_b: True, q_c: False}


def U(atom, pos_, neg_, status=EpistemicStatus.OBSERVED):
    return MeaningUnit(atom, M(pos_), M(neg_), ("row",), status)


UNITS = {
    p_a: U(p_a, 0.9, 0.0),   # T
    p_b: U(p_b, 0.3, 0.2),   # U (weak evidence)
    p_c: U(p_c, 0.72, 0.8),  # B, on the boundary band
    q_b: U(q_b, 0.9, 0.0),   # T
    q_c: U(q_c, 0.1, 0.2),   # U
}
VALIDATION = {
    p_a: U(p_a, 0.8, 0.1),   # T, agrees with verdict T
    p_b: U(p_b, 0.9, 0.0),   # T, but verdict is U (hypothesis ignored)
    p_c: U(p_c, 0.1, 0.1),   # U
    q_a: U(q_a, 0.1, 0.9),   # F, disagrees with verdict T
    q_c: U(q_c, 0.8, 0.0),   # T, agrees with verdict T
}


def run(units, truth, rules, vocab, validation, alpha, k, eps=0.05):
    out = decode(interface_facts(units, alpha), rules, vocab, k)
    return out, compute_metrics(
        truth=lambda a: truth[a], vocab=vocab, world_rules=rules, units=units, validation_units=validation,
        alpha=alpha, epsilon_band=eps, output=out,
    )


class HandMadeMetricsTests(unittest.TestCase):
    def test_all_metrics_k5(self):
        out, m = run(UNITS, TRUTH, RULES, VOCAB, VALIDATION, 0.7, 5)
        # decoder sanity (hand-derived): F1 has q(a), q(c) derived; hypothesis POS p(b)
        self.assertEqual([c.fact for c in out.hypotheses], [pos("p", "b")])
        self.assertEqual(
            {a.pred + a.args[0]: out.full(a).value for a in sorted(VOCAB)},
            {"pa": "T", "pb": "T", "pc": "B", "qa": "T", "qb": "T", "qc": "T"},
        )
        self.assertIs(out.verdict(p_b), Belnap.U)
        self.assertEqual((m.size_E, m.size_I, m.size_H, m.size_K), (5, 3, 1, 6))
        self.assertEqual(m.fidelity, 2 / 3)  # I = {p(a), p(c), q(b)}: T ok, B no, T ok
        self.assertEqual(m.deviation, 0.0)  # enc T/F atoms p(a), q(b) are unchanged in full
        self.assertEqual(m.consistency, 1 - 1 / 6)  # p(c) is B
        self.assertEqual(m.uncertainty, 1 / 6)  # only p(b) has verdict U
        self.assertEqual(m.new_true, 1.0)  # H = {q(a)}: verdict T = W
        self.assertEqual(m.new_false, 0.5)  # outside I and decided: q(a) ok, q(c) wrong; p(b) is U
        self.assertEqual((m.x, m.y), (0.5, 1.0))
        self.assertEqual((m.hyp_count, m.hyp_correct), (1, 1))  # p(b): full T, verdict U, W = T
        self.assertEqual(m.validation_agreement, 2 / 3)  # p(a) ok, q(c) ok, q(a) disagrees
        self.assertEqual(m.boundary_share, 0.2)  # p(c) only

    def test_all_metrics_k0(self):
        out, m = run(UNITS, TRUTH, RULES, VOCAB, VALIDATION, 0.7, 0)
        self.assertEqual(out.hypotheses, ())
        self.assertEqual((m.hyp_count, m.hyp_correct), (0, 0))
        self.assertEqual(m.fidelity, 2 / 3)
        self.assertEqual(m.uncertainty, 1 / 6)
        self.assertEqual(m.new_true, 1.0)
        self.assertEqual(m.new_false, 0.5)
        self.assertEqual(m.validation_agreement, 2 / 3)

    def test_sets_depend_on_alpha_only_through_I(self):
        _, m_hi = run(UNITS, TRUTH, RULES, VOCAB, VALIDATION, 0.95, 0)
        self.assertEqual((m_hi.size_E, m_hi.size_H), (5, 1))
        self.assertEqual(m_hi.size_I, 0)  # nothing reaches 0.95
        self.assertIsNone(m_hi.fidelity)
        _, m_lo = run(UNITS, TRUTH, RULES, VOCAB, VALIDATION, 0.1, 0)
        self.assertEqual((m_lo.size_E, m_lo.size_H), (5, 1))
        self.assertGreater(m_lo.size_I, 3)

    def test_deviation_and_empty_H(self):
        s_a = A("s", "a")
        vocab = frozenset([p_a, s_a])
        rules = (Rule("R1", L("p", "X", ch=Channel.NEG), (L("s", "X"),)),)
        truth = {p_a: False, s_a: True}
        units = {p_a: U(p_a, 0.9, 0.0), s_a: U(s_a, 0.9, 0.0)}
        out, m = run(units, truth, rules, vocab, {}, 0.7, 0)
        self.assertIs(out.full(p_a), Belnap.B)  # observed POS, derived NEG
        self.assertEqual(m.size_H, 0)
        self.assertIsNone(m.new_true)
        self.assertEqual(m.deviation, 0.5)  # p(a): enc T, full B
        self.assertEqual(m.fidelity, 0.5)
        self.assertEqual(m.consistency, 0.5)
        self.assertEqual(m.uncertainty, 0.0)
        self.assertEqual(m.new_false, 0.0)  # nothing outside I: denominator 0 -> 0
        self.assertIsNone(m.validation_agreement)
        # infeasible: None new_true
        self.assertFalse(is_feasible(m, Taus(0.0, 1.0, 0.0, 1.0)))

    def test_b_and_u_never_equal_w(self):
        # an atom decided B or U in the output can never count as correct
        units = {p_a: U(p_a, 0.9, 0.9)}  # B
        vocab = frozenset([p_a])
        _, m = run(units, {p_a: True}, (), vocab, {}, 0.7, 0)
        self.assertEqual(m.fidelity, 0.0)
        self.assertEqual(m.consistency, 0.0)
        self.assertEqual(m.deviation, 0.0)  # enc is B, not T/F: not in the denominator

    def test_not_computed_unit_is_in_E_but_not_in_I(self):
        from tesaron.enums import ComputationalStatus

        units = {p_a: U(p_a, 0.99, 0.0, ComputationalStatus.NOT_COMPUTED), p_b: U(p_b, 0.9, 0.0)}
        _, m = run(units, TRUTH, (), VOCAB, {}, 0.7, 0)
        self.assertEqual((m.size_E, m.size_I), (2, 1))


class HSoundnessTests(unittest.TestCase):
    def test_H_hand_example(self):
        H = compute_H([p_a, p_b, p_c, q_b, q_c], TRUTH.__getitem__, RULES, VOCAB)
        self.assertEqual(H, [q_a])

    def test_H_assertion_derived_channel_must_agree_with_world(self):
        bad = dict(TRUTH)
        bad[q_a] = False  # p(a) true but the world says q(a) false: rule unsound for this world
        with self.assertRaises(AssertionError):
            compute_H([p_a], bad.__getitem__, RULES, VOCAB)

    def test_H_assertion_no_atom_with_both_channels(self):
        rules = RULES + (Rule("R2", L("q", "X", ch=Channel.NEG), (L("p", "X"),)),)
        with self.assertRaises(AssertionError):
            compute_H([p_a], TRUTH.__getitem__, rules, VOCAB)

    def test_H_excludes_E_atoms_and_uses_both_channels(self):
        # a NEG-derived atom outside E is in H
        rules = (Rule("R", L("q", "X", ch=Channel.NEG), (L("p", "X"),)),)
        truth = {p_a: True, q_a: False, p_b: True, q_b: False, p_c: False, q_c: False}
        self.assertEqual(compute_H([p_a, q_b], truth.__getitem__, rules, VOCAB), [q_a])

    def test_metrics_compute_H_assertion_in_pipeline(self):
        bad = dict(TRUTH)
        bad[q_a] = False
        with self.assertRaises(AssertionError):
            run(UNITS, bad, RULES, VOCAB, VALIDATION, 0.7, 0)


class WorldRulesForHTests(unittest.TestCase):
    """Revision S-5: H uses the world's rules, never the rules given to the decoder."""

    def test_h_does_not_move_with_context_rules(self):
        from dataclasses import replace
        from unittest import mock

        import tesaron.criterion.metrics as metrics_module
        from tesaron.encoder import Context, encode
        from tesaron.pipeline import evaluate
        from tesaron.worlds import generate_world

        world = generate_world(900001)
        ctx = Context.from_world(world, 900101)
        enc = encode(world, ctx)
        _, base = evaluate(world, ctx, enc)
        self.assertGreater(base.size_H, 0)
        for dropped in range(len(world.rules)):
            rules = tuple(r for i, r in enumerate(world.rules) if i != dropped)
            self.assertNotEqual(rules, world.rules)
            seen = {}
            real = metrics_module.compute_H

            def spy(E, truth, world_rules, vocab, _seen=seen):
                _seen["rules"] = tuple(world_rules)
                return real(E, truth, world_rules, vocab)

            with mock.patch.object(metrics_module, "compute_H", spy):
                _, m = evaluate(world, replace(ctx, rules=rules), enc)
            with self.subTest(dropped=world.rules[dropped].id):
                self.assertEqual(seen["rules"], world.rules)
                self.assertEqual((m.size_H, m.size_K, m.size_E), (base.size_H, base.size_K, base.size_E))

    def test_empty_context_rules_leave_H_unchanged(self):
        from dataclasses import replace

        from tesaron.encoder import Context, encode
        from tesaron.pipeline import evaluate
        from tesaron.worlds import generate_world

        world = generate_world(900002)
        ctx = Context.from_world(world, 900101)
        enc = encode(world, ctx)
        _, base = evaluate(world, ctx, enc)
        _, none = evaluate(world, replace(ctx, rules=()), enc)
        self.assertEqual(none.size_H, base.size_H)
        self.assertEqual(none.size_K, base.size_K)


class PipelineMetricTests(unittest.TestCase):
    def test_world_metrics_are_well_formed(self):
        from dataclasses import replace

        from tesaron.encoder import Context, encode
        from tesaron.pipeline import evaluate
        from tesaron.worlds import generate_world

        for seed in range(900000, 900006):
            world = generate_world(seed)
            ctx = Context.from_world(world, 900101)
            enc = encode(world, ctx)
            for alpha in (0.9, 0.7, 0.5):
                _, m = evaluate(world, replace(ctx, alpha=alpha, k_abduction=5), enc)
                with self.subTest(seed=seed, alpha=alpha):  # also runs the H soundness assertions
                    self.assertIsInstance(m, Metrics)
                    for v in (m.fidelity, m.deviation, m.consistency, m.uncertainty, m.new_true, m.new_false,
                              m.validation_agreement, m.boundary_share):
                        self.assertTrue(v is None or 0.0 <= v <= 1.0)
                    self.assertLessEqual(m.size_I, m.size_E)
                    self.assertEqual(m.size_K, m.size_E + m.size_H)
                    self.assertLessEqual(m.hyp_correct, m.hyp_count)


if __name__ == "__main__":
    unittest.main()
