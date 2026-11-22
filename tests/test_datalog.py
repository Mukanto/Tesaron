import unittest

from helpers import A, L, neg, pos, rng_for

from tesaron.decoder import (
    Rule,
    decode,
    ground_instances,
    naive_eval,
    naive_eval_with_records,
    seminaive_eval,
    seminaive_eval_with_records,
)
from tesaron.enums import Belnap, Channel

N_RANDOM = 220  # seeds 900200 .. 900419


def random_program(seed: int):
    rng = rng_for(seed)
    ents = ["a", "b", "c", "d"]
    unary, binary = ["p0", "p1", "p2"], ["q0", "q1"]
    # reflexive binary atoms are outside the vocabulary
    vocab = frozenset(
        [A(p, e) for p in unary for e in ents]
        + [A(q, x, y) for q in binary for x in ents for y in ents if x != y]
    )
    variables = ["X", "Y", "Z"]

    def args_for(pred, pool):
        n = 1 if pred in unary else 2
        out = []
        for _ in range(n):
            if rng.random() < 0.12:
                out.append(ents[int(rng.integers(len(ents)))])
            else:
                out.append(pool[int(rng.integers(len(pool)))])
        return tuple(out)

    allp = unary + binary
    rules = []
    for i in range(int(rng.integers(1, 5))):
        body = []
        for _ in range(int(rng.integers(1, 4))):
            pred = allp[int(rng.integers(len(allp)))]
            ch = Channel.POS if rng.random() < 0.65 else Channel.NEG
            body.append(L(pred, *args_for(pred, variables), ch=ch))
        body_vars = sorted({v for lit in body for v in lit.variables()})
        hpred = allp[int(rng.integers(len(allp)))]
        hch = Channel.POS if rng.random() < 0.6 else Channel.NEG
        pool = body_vars if body_vars else ents
        rules.append(Rule(f"R{i}", L(hpred, *args_for(hpred, pool), ch=hch), tuple(body)))
    facts = set()
    for atom in sorted(vocab):
        if rng.random() < 0.2:
            facts.add((Channel.POS, atom))
        if rng.random() < 0.08:
            facts.add((Channel.NEG, atom))
    return facts, rules, vocab


class EquivalenceTests(unittest.TestCase):
    def test_seminaive_equals_naive_on_random_programs(self):
        nontrivial = 0
        both_channels = 0
        for i in range(N_RANDOM):
            facts, rules, vocab = random_program(900200 + i)
            n = naive_eval_with_records(facts, rules, vocab)
            s = seminaive_eval_with_records(facts, rules, vocab)
            with self.subTest(program=i):
                self.assertEqual(n.facts, s.facts)
                self.assertEqual(naive_eval(facts, rules, vocab), seminaive_eval(facts, rules, vocab))
                self.assertEqual(n.records, s.records)  # same first derivations
                self.assertEqual(n.rounds, s.rounds)
                self.assertLessEqual(n.rounds, 2 * len(vocab) + 1)  # termination bound
            nontrivial += len(n.facts) > len(facts)
            both_channels += any(
                (Channel.POS, a) in n.facts and (Channel.NEG, a) in n.facts for _, a in n.facts
            )
        self.assertGreater(nontrivial, N_RANDOM // 3)  # the programs actually derive things
        self.assertGreater(both_channels, 20)  # and exercise B atoms
        # NEG body literals and NEG heads are present in the generated programs
        all_rules = [r for i in range(N_RANDOM) for r in random_program(900200 + i)[1]]
        self.assertTrue(any(l.channel is Channel.NEG for r in all_rules for l in r.body))
        self.assertTrue(any(r.head.channel is Channel.NEG for r in all_rules))

    def test_shuffled_input_gives_same_fixpoint_and_records(self):
        rng = rng_for(900500)
        for i in range(60):
            facts, rules, vocab = random_program(900200 + i)
            base = seminaive_eval_with_records(facts, rules, vocab)
            base_naive = naive_eval_with_records(facts, rules, vocab)
            for _ in range(3):
                f = sorted(facts)
                rng.shuffle(f)
                r = list(rules)
                rng.shuffle(r)
                again = seminaive_eval_with_records(f, r, vocab)
                again_n = naive_eval_with_records(f, r, vocab)
                self.assertEqual(again.facts, base.facts)
                self.assertEqual(again.records, base.records)
                self.assertEqual(again_n.records, base_naive.records)


class HandMadeTests(unittest.TestCase):
    def test_transitive_closure(self):
        nodes = ["a", "b", "c", "d", "e"]
        vocab = frozenset(
            [A("edge", x, y) for x in nodes for y in nodes] + [A("path", x, y) for x in nodes for y in nodes]
        )
        rules = [
            Rule("T1", L("path", "X", "Y"), (L("edge", "X", "Y"),)),
            Rule("T2", L("path", "X", "Z"), (L("path", "X", "Y"), L("edge", "Y", "Z"))),
        ]
        facts = {pos("edge", "a", "b"), pos("edge", "b", "c"), pos("edge", "c", "d"), pos("edge", "e", "c")}
        expected = set(facts) | {
            pos("path", "a", "b"), pos("path", "b", "c"), pos("path", "c", "d"), pos("path", "e", "c"),
            pos("path", "a", "c"), pos("path", "b", "d"), pos("path", "e", "d"), pos("path", "a", "d"),
        }
        self.assertEqual(naive_eval(facts, rules, vocab), expected)
        self.assertEqual(seminaive_eval(facts, rules, vocab), expected)
        res = seminaive_eval_with_records(facts, rules, vocab)
        self.assertEqual(res.records[pos("path", "a", "d")][0], "T2")
        self.assertEqual(res.records[pos("path", "a", "b")], ("T1", (pos("edge", "a", "b"),)))
        self.assertNotIn(pos("edge", "a", "b"), res.records)  # input facts have no derivation record

    def test_both_channels(self):
        vocab = frozenset(A(p, e) for p in "pqrstw" for e in "ab")
        rules = [
            Rule("R1", L("q", "X", ch=Channel.NEG), (L("p", "X"),)),  # NEG head
            Rule("R2", L("r", "X"), (L("q", "X", ch=Channel.NEG),)),  # NEG body literal
            Rule("R3", L("t", "X"), (L("s", "X"),)),
        ]
        facts = {pos("p", "a"), pos("s", "a"), neg("s", "a"), pos("w", "b")}
        out = seminaive_eval(facts, rules, vocab)
        self.assertEqual(
            out,
            {pos("p", "a"), pos("s", "a"), neg("s", "a"), pos("w", "b"), neg("q", "a"), pos("r", "a"), pos("t", "a")},
        )
        # a NEG literal does not match a POS fact and vice versa (strong negation, not negation as failure)
        self.assertEqual(seminaive_eval({pos("q", "a")}, rules[1:2], vocab), {pos("q", "a")})
        self.assertEqual(seminaive_eval({neg("q", "a")}, rules[1:2], vocab), {neg("q", "a"), pos("r", "a")})
        # nothing follows from the absence of a fact
        self.assertEqual(seminaive_eval(set(), rules[1:2], vocab), set())

    def test_contradiction_gives_b_without_explosion(self):
        vocab = frozenset(A(p, e) for p in "pqrw" for e in "ab")
        rules = [Rule("R1", L("q", "X"), (L("p", "X"),))]
        interface = {pos("p", "a"): ("r1",), neg("p", "a"): ("r2",), pos("w", "b"): ("r3",)}
        out = decode(interface, rules, vocab, 0)
        self.assertIs(out.full(A("p", "a")), Belnap.B)
        self.assertIs(out.verdict(A("p", "a")), Belnap.B)
        self.assertIs(out.full(A("q", "a")), Belnap.T)  # derived from the POS side only
        self.assertIs(out.full(A("w", "b")), Belnap.T)  # unrelated fact unaffected
        for atom in (A("q", "b"), A("r", "a"), A("r", "b"), A("w", "a"), A("p", "b")):
            self.assertIs(out.full(atom), Belnap.U, atom)  # no explosion
        self.assertEqual(set(out.facts), {pos("p", "a"), neg("p", "a"), pos("w", "b"), pos("q", "a")})

    def test_safety_check_raises(self):
        with self.assertRaises(ValueError):
            Rule("bad", L("q", "X", "Y"), (L("p", "X"),))
        with self.assertRaises(ValueError):
            Rule("bad", L("q", "X"), ())
        Rule("ok", L("q", "a"), ())  # a ground head with an empty body is safe
        Rule("ok2", L("q", "a", "X"), (L("p", "X"),))  # constants in the head are fine

    def test_empty_body_ground_rule(self):
        vocab = frozenset([A("q", "a"), A("p", "a")])
        rules = [Rule("F", L("q", "a"), ()), Rule("R", L("p", "X"), (L("q", "X"),))]
        expected = {pos("q", "a"), pos("p", "a")}
        self.assertEqual(naive_eval(set(), rules, vocab), expected)
        self.assertEqual(seminaive_eval(set(), rules, vocab), expected)

    def test_duplicate_rule_ids_rejected(self):
        r = Rule("R", L("q", "X"), (L("p", "X"),))
        with self.assertRaises(ValueError):
            seminaive_eval(set(), [r, r], frozenset())

    def test_vocabulary_filter_discards_out_of_vocabulary_atoms(self):
        vocab = frozenset([A("p", "a"), A("p", "b"), A("q", "a", "b"), A("q", "b", "a")])  # no q(x,x)
        rules = [Rule("R", L("q", "X", "Y"), (L("p", "X"), L("p", "Y")))]
        facts = {pos("p", "a"), pos("p", "b")}
        for f in (naive_eval, seminaive_eval):
            out = f(facts, rules, vocab)
            self.assertEqual(out, facts | {pos("q", "a", "b"), pos("q", "b", "a")})
            self.assertNotIn(pos("q", "a", "a"), out)
        # out-of-vocabulary input atoms are discarded as well
        self.assertEqual(seminaive_eval({pos("zzz", "a")}, rules, vocab), set())

    def test_constants_and_repeated_variables(self):
        vocab = frozenset([A("q", x, y) for x in "ab" for y in "ab"] + [A("s", x) for x in "ab"])
        rules = [Rule("R", L("s", "X"), (L("q", "X", "X"),)), Rule("S", L("s", "b"), (L("q", "a", "X"),))]
        out = seminaive_eval({pos("q", "a", "a"), pos("q", "a", "b"), pos("q", "b", "a")}, rules, vocab)
        self.assertIn(pos("s", "a"), out)
        self.assertIn(pos("s", "b"), out)  # via S: q(a, X) holds
        self.assertEqual(sum(1 for c, a in out if a.pred == "s"), 2)

    def test_termination_bound_on_a_long_chain(self):
        n = 12
        nodes = [f"n{i}" for i in range(n)]
        vocab = frozenset([A("p", x) for x in nodes] + [A("nxt", x, y) for x in nodes for y in nodes if x != y])
        rules = [Rule("R", L("p", "Y"), (L("p", "X"), L("nxt", "X", "Y")))]
        facts = {pos("p", nodes[0])} | {pos("nxt", nodes[i], nodes[i + 1]) for i in range(n - 1)}
        res = seminaive_eval_with_records(facts, rules, vocab)
        self.assertEqual(len([f for f in res.facts if f[1].pred == "p"]), n)
        self.assertEqual(res.rounds, n)  # n-1 rounds that add a fact + one empty round
        self.assertLessEqual(res.rounds, 2 * len(vocab) + 1)
        self.assertEqual(naive_eval_with_records(facts, rules, vocab).rounds, n)

    def test_first_derivation_is_earliest_round_then_smallest_rule_id(self):
        vocab = frozenset(A(p, "a") for p in ("p", "q", "s", "t", "u"))
        rules = [
            Rule("B", L("t", "a"), (L("s", "a"),)),  # t(a) in round 2 via s(a)
            Rule("C", L("t", "a"), (L("p", "a"),)),  # t(a) in round 1 via p(a) ...
            Rule("A", L("t", "a"), (L("q", "a"),)),  # ... and via q(a); A < C, so A wins round 1
            Rule("D", L("s", "a"), (L("p", "a"),)),
        ]
        facts = {pos("p", "a"), pos("q", "a")}
        for f in (naive_eval_with_records, seminaive_eval_with_records):
            res = f(facts, rules, vocab)
            self.assertEqual(res.records[pos("t", "a")], ("A", (pos("q", "a"),)))
            self.assertEqual(res.records[pos("s", "a")], ("D", (pos("p", "a"),)))

    def test_ground_instances_sorted(self):
        rule = Rule("R", L("q", "Y"), (L("e", "X", "Y"),))
        facts = {pos("e", "b", "c"), pos("e", "a", "b"), pos("e", "a", "c")}
        self.assertEqual(
            ground_instances(rule, facts),
            [{"X": "a", "Y": "b"}, {"X": "a", "Y": "c"}, {"X": "b", "Y": "c"}],
        )


if __name__ == "__main__":
    unittest.main()
