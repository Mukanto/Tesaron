import unittest
from helpers import A, L, neg, pos, rng_for

from tesaron.belnap import interface_facts
from tesaron.decoder import Rule, abduce, decode, ranked_candidates, seminaive_eval
from tesaron.encoder import Context, encode
from tesaron.enums import Belnap, Channel, EpistemicStatus
from tesaron.worlds import generate_world

ENTS = "abcde"
# s(d) is deliberately outside the vocabulary
VOCAB = frozenset(
    A(p, e) for p in ("p", "q", "s", "t", "z", "y", "v") for e in ENTS if not (p == "s" and e == "d")
)
RULES = [
    Rule("R1", L("q", "X"), (L("p", "X"), L("s", "X"))),
    Rule("R2", L("z", "X"), (L("s", "X"), L("t", "X"))),
    Rule("R3", L("y", "X"), (L("t", "X"), L("s", "X", ch=Channel.NEG))),
    Rule("R4", L("v", "X"), (L("s", "X"),)),
]
INTERFACE = {
    # a: q, z observed, p, t present, s missing: s(a) completes R1 and R2 (score 2)
    pos("q", "a"): ("r1",), pos("p", "a"): ("r2",), pos("z", "a"): ("r3",), pos("t", "a"): ("r4",),
    # b: q observed, p missing, s present: p(b) completes R1 (score 1); s(b) gives v(b) DERIVED
    pos("q", "b"): ("r5",), pos("s", "b"): ("r6",),
    # c: y observed, t present, not-s missing: NEG s(c) completes R3 (score 1)
    pos("y", "c"): ("r7",), pos("t", "c"): ("r8",),
    # d: q observed, p present, but s(d) is outside the vocabulary: no candidate
    pos("q", "d"): ("r9",), pos("p", "d"): ("r10",),
    # e: q observed, p present, but s(e) is already refuted (value F, not U): no candidate
    pos("q", "e"): ("r11",), pos("p", "e"): ("r12",), neg("s", "e"): ("r13",),
}


class AbductionHandMadeTests(unittest.TestCase):
    def setUp(self):
        self.f1 = seminaive_eval(INTERFACE, RULES, VOCAB)
        self.cands = ranked_candidates(self.f1, set(INTERFACE), RULES, VOCAB)

    def test_expected_candidates_and_scores(self):
        self.assertEqual(
            [(c.fact, c.score) for c in self.cands],
            [(pos("s", "a"), 2), (pos("p", "b"), 1), (neg("s", "c"), 1)],
        )
        self.assertEqual(self.cands[0].instances, (("R1", ("a",)), ("R2", ("a",))))

    def test_candidates_are_only_u_atoms_in_vocabulary(self):
        for c in self.cands:
            atom = c.fact[1]
            self.assertIn(atom, VOCAB)
            self.assertNotIn((Channel.POS, atom), self.f1)
            self.assertNotIn((Channel.NEG, atom), self.f1)
        atoms = {c.fact[1] for c in self.cands}
        self.assertNotIn(A("s", "e"), atoms)  # refuted: value F
        self.assertNotIn(A("s", "b"), atoms)  # present: value T
        self.assertNotIn(A("s", "d"), atoms)  # out of vocabulary

    def test_cap_k_is_respected(self):
        for k, n in ((0, 0), (1, 1), (2, 2), (3, 3), (10, 3)):
            got = abduce(self.f1, set(INTERFACE), RULES, VOCAB, k)
            self.assertEqual(len(got), n)
            self.assertEqual([c.fact for c in got], [c.fact for c in self.cands[:n]])
            out = decode(INTERFACE, RULES, VOCAB, k)
            self.assertEqual(len(out.hypotheses), n)
        with self.assertRaises(ValueError):
            abduce(self.f1, set(INTERFACE), RULES, VOCAB, -1)

    def test_ranking_is_deterministic(self):
        rng = rng_for(900600)
        want = [(c.fact, c.score, c.instances) for c in self.cands]
        for _ in range(10):
            facts = sorted(INTERFACE)
            rng.shuffle(facts)
            rules = list(RULES)
            rng.shuffle(rules)
            f1 = seminaive_eval(facts, rules, VOCAB)
            got = ranked_candidates(f1, set(facts), rules, VOCAB)
            self.assertEqual([(c.fact, c.score, c.instances) for c in got], want)

    def test_tie_break_is_channel_pred_args_ascending(self):
        # both score 1: (POS, p(b)) before (NEG, s(c)) because POS < NEG
        self.assertEqual([c.fact for c in self.cands[1:]], [pos("p", "b"), neg("s", "c")])
        # same channel: pred, then args
        rules = [
            Rule("A", L("q", "X"), (L("p", "X"), L("s", "X"))),
        ]
        vocab = frozenset(A(p, e) for p in "pqs" for e in "ab")
        iface = {pos("q", "a"): (), pos("q", "b"): (), pos("p", "a"): (), pos("p", "b"): ()}
        f1 = seminaive_eval(iface, rules, vocab)
        got = ranked_candidates(f1, set(iface), rules, vocab)
        self.assertEqual([c.fact for c in got], [pos("s", "a"), pos("s", "b")])

    def test_pass2_facts_are_hypotheses_and_verdict_ignores_them(self):
        out = decode(INTERFACE, RULES, VOCAB, 5)
        s_a = A("s", "a")
        self.assertEqual(out.status_of(Channel.POS, s_a), EpistemicStatus.HYPOTHESIS)
        self.assertEqual(out.facts[(Channel.POS, s_a)].score, 2)
        self.assertEqual(out.status_of(Channel.NEG, A("s", "c")), EpistemicStatus.HYPOTHESIS)
        # v(a) is new in pass 2 (from the hypothesis s(a)): HYPOTHESIS with a derivation record
        v_a = out.facts[(Channel.POS, A("v", "a"))]
        self.assertEqual(v_a.status, EpistemicStatus.HYPOTHESIS)
        self.assertEqual(v_a.derivation, ("R4", (pos("s", "a"),)))
        # pass-1 facts keep their status: v(b) DERIVED, observed facts OBSERVED
        self.assertEqual(out.status_of(Channel.POS, A("v", "b")), EpistemicStatus.DERIVED)
        self.assertEqual(out.status_of(Channel.POS, A("q", "a")), EpistemicStatus.OBSERVED)
        self.assertEqual(out.facts[(Channel.POS, A("q", "a"))].provenance, ("r1",))
        # full counts hypotheses, verdict does not
        for atom in (s_a, A("v", "a"), A("p", "b")):
            self.assertIs(out.full(atom), Belnap.T)
            self.assertIs(out.verdict(atom), Belnap.U)
        self.assertIs(out.full(A("s", "c")), Belnap.F)
        self.assertIs(out.verdict(A("s", "c")), Belnap.U)
        self.assertIs(out.verdict(A("v", "b")), Belnap.T)

    def test_k0_means_no_abduction(self):
        out = decode(INTERFACE, RULES, VOCAB, 0)
        self.assertEqual(out.hypotheses, ())
        self.assertFalse([f for f, i in out.facts.items() if i.status is EpistemicStatus.HYPOTHESIS])
        for atom in sorted(VOCAB):
            self.assertIs(out.full(atom), out.verdict(atom))

    def test_both_observed_and_derived_keeps_observed(self):
        iface = {pos("p", "a"): ("r1",), pos("q", "a"): ("r2",), pos("s", "a"): ("r3",)}
        out = decode(iface, RULES, VOCAB, 0)  # R1 derives q(a), which is also observed
        self.assertEqual(out.status_of(Channel.POS, A("q", "a")), EpistemicStatus.OBSERVED)
        self.assertEqual(out.facts[(Channel.POS, A("q", "a"))].provenance, ("r2",))

    def test_only_ground_missing_literals(self):
        # head q(X) <- p(X), s(X, Y): missing s(a, Y) is not ground -> no existential guessing
        rules = [Rule("R", L("q", "X"), (L("p", "X"), L("s", "X", "Y")))]
        vocab = frozenset([A("q", "a"), A("p", "a")] + [A("s", "a", y) for y in "bc"])
        iface = {pos("q", "a"): (), pos("p", "a"): ()}
        f1 = seminaive_eval(iface, rules, vocab)
        self.assertEqual(ranked_candidates(f1, set(iface), rules, vocab), [])
        # but if p(X) is the missing one and s(X, Y) is present, Y is bound by the present literal
        iface2 = {pos("q", "a"): (), pos("s", "a", "b"): ()}
        f2 = seminaive_eval(iface2, rules, vocab)
        self.assertEqual(
            [c.fact for c in ranked_candidates(f2, set(iface2), rules, vocab)], [pos("p", "a")]
        )

    def test_head_must_be_observed_not_merely_derived(self):
        rules = [
            Rule("R1", L("q", "X"), (L("p", "X"),)),
            Rule("R2", L("z", "X"), (L("q", "X"), L("t", "X"))),
        ]
        vocab = frozenset(A(p, "a") for p in "pqzt")
        iface = {pos("p", "a"): (), pos("z", "a"): ()}  # q(a) is DERIVED, z(a) observed, t(a) missing
        f1 = seminaive_eval(iface, rules, vocab)
        self.assertEqual([c.fact for c in ranked_candidates(f1, set(iface), rules, vocab)], [pos("t", "a")])
        # with q(a) derived but z(a) not observed there is nothing to explain
        iface = {pos("p", "a"): ()}
        f1 = seminaive_eval(iface, rules, vocab)
        self.assertEqual(ranked_candidates(f1, set(iface), rules, vocab), [])


class AbductionOnWorldTests(unittest.TestCase):
    def test_invariants_on_generated_worlds(self):
        for seed in (900001, 900002, 900003):
            world = generate_world(seed)
            ctx = Context.from_world(world, 900101)
            enc = encode(world, ctx)
            for alpha in (0.9, 0.7, 0.5):
                iface = interface_facts(enc.units, alpha)
                for k in (0, 1, 5, 10):
                    out = decode(iface, ctx.rules, ctx.vocabulary, k)
                    with self.subTest(seed=seed, alpha=alpha, k=k):
                        self.assertLessEqual(len(out.hypotheses), k)
                        hyp_facts = {c.fact for c in out.hypotheses}
                        for fact, info in out.facts.items():
                            if fact in hyp_facts:
                                self.assertIs(info.status, EpistemicStatus.HYPOTHESIS)
                            if info.status is EpistemicStatus.HYPOTHESIS:
                                # hypotheses never overwrite observed/derived facts
                                self.assertNotIn(fact, iface)
                        # candidates concern atoms whose pass-1 value is U
                        for c in out.hypotheses:
                            atom = c.fact[1]
                            for ch in Channel:
                                info = out.facts.get((ch, atom))
                                if info is not None and (ch, atom) != c.fact:
                                    self.assertIs(info.status, EpistemicStatus.HYPOTHESIS)
                        # verdict uses only OBSERVED / DERIVED facts
                        for atom in sorted(ctx.vocabulary):
                            solid = [
                                (ch, atom) in out.facts
                                and out.facts[(ch, atom)].status is not EpistemicStatus.HYPOTHESIS
                                for ch in (Channel.POS, Channel.NEG)
                            ]
                            self.assertIs(out.verdict(atom), Belnap.from_channels(*solid))
                        # deterministic
                        again = decode(iface, ctx.rules, ctx.vocabulary, k)
                        self.assertEqual(again.facts, out.facts)
                        self.assertEqual(again.hypotheses, out.hypotheses)


if __name__ == "__main__":
    unittest.main()
