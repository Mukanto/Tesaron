import unittest
from collections import Counter

from helpers import brute_closure, brute_instances

from tesaron.atoms import Atom
from tesaron.degrees import Probability
from tesaron.enums import Channel
from tesaron.serialize import canonical_hash
from tesaron.worlds import WorldParams, generate_world

SEEDS = list(range(900000, 900020))


class WorldTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.worlds = {s: generate_world(s) for s in SEEDS}

    def test_vocabulary_size(self):
        w = self.worlds[900000]
        self.assertEqual(len(w.vocabulary), 60 + 3 * 380)
        self.assertEqual(w.entities[0], "e00")
        self.assertEqual(w.entities[-1], "e19")

    def test_deterministic_per_seed(self):
        for s in SEEDS[:5]:
            again = generate_world(s)
            self.assertEqual(canonical_hash(again), canonical_hash(self.worlds[s]))
        self.assertNotEqual(canonical_hash(self.worlds[900000]), canonical_hash(self.worlds[900001]))

    def test_acceptance_conditions_hold(self):
        for s, w in self.worlds.items():
            with self.subTest(seed=s):
                true = w.true_atoms
                # independent least model of the positive rules
                start = {Atom(f"c{k}", (e,)) for e, k in zip(w.entities, w.base_classes)} | set(w.base_facts)
                positive = [r for r in w.rules if r.head.channel is Channel.POS]
                self.assertEqual(set(true), brute_closure(start, positive, w.entities, w.vocabulary))
                self.assertEqual(sorted(r.id for r in w.rules), ["R1", "R2", "R3", "R4", "R5", "R6"])
                for rule in w.rules:
                    insts = brute_instances(rule, true, w.entities)
                    if rule.head.channel is Channel.NEG:
                        heads = [Atom(rule.head.pred, tuple(t[a] for a in rule.head.args)) for t in insts]
                        # consistency: no true body together with a true head atom
                        self.assertFalse(any(h in true for h in heads), rule.id)
                        # fires: true body and false head atom
                        self.assertTrue(any(h not in true for h in heads), rule.id)
                    else:
                        self.assertTrue(insts, rule.id)  # fires at least once

    def test_rule_templates(self):
        for w in self.worlds.values():
            r = {x.id: x for x in w.rules}
            # R1: c_j(Y) <- r_a(X,Y) & c_i(X)
            self.assertEqual(r["R1"].head.args, ("Y",))
            self.assertEqual([l.args for l in r["R1"].body], [("X", "Y"), ("X",)])
            # R2: r_b(X,Y) <- r_a(X,Y) & c_i(X), a != b
            self.assertNotEqual(r["R2"].head.pred, r["R2"].body[0].pred)
            self.assertEqual(r["R2"].head.args, ("X", "Y"))
            # R3: r_b(Y,X) <- r_a(X,Y), a != b
            self.assertNotEqual(r["R3"].head.pred, r["R3"].body[0].pred)
            self.assertEqual(r["R3"].head.args, ("Y", "X"))
            # R4: r_c(X,Z) <- r_a(X,Y) & r_b(Y,Z)
            self.assertEqual(r["R4"].head.args, ("X", "Z"))
            self.assertEqual([l.args for l in r["R4"].body], [("X", "Y"), ("Y", "Z")])
            # R5: not r_a(X,Y) <- r_b(X,Y) & c_i(X), a != b
            self.assertIs(r["R5"].head.channel, Channel.NEG)
            self.assertNotEqual(r["R5"].head.pred, r["R5"].body[0].pred)
            # R6: not c_j(X) <- c_i(X), i != j
            self.assertIs(r["R6"].head.channel, Channel.NEG)
            self.assertNotEqual(r["R6"].head.pred, r["R6"].body[0].pred)

    def test_no_reflexive_relation_atoms(self):
        for w in self.worlds.values():
            for a in w.true_atoms:
                if a.pred.startswith("r"):
                    self.assertNotEqual(a.args[0], a.args[1])
            for a in w.base_facts:
                self.assertNotEqual(a.args[0], a.args[1])
            for row in w.report_rows:
                self.assertNotEqual(row.atom.args[0], row.atom.args[1])
            for a in w.vocabulary:
                if a.pred.startswith("r"):
                    self.assertNotEqual(a.args[0], a.args[1])

    def test_classes_balanced_one_base_class_each(self):
        for w in self.worlds.values():
            self.assertEqual(len(w.base_classes), 20)
            counts = Counter(w.base_classes)
            self.assertEqual(sorted(counts), [0, 1, 2])
            self.assertLessEqual(max(counts.values()) - min(counts.values()), 1)
            self.assertEqual(sorted(counts.values()), [6, 7, 7])

    def test_outliers_and_overlaps(self):
        for w in self.worlds.values():
            self.assertEqual(len(w.outliers), 2)
            self.assertEqual(len(w.overlaps), 2)
            self.assertFalse(set(w.outliers) & set(w.overlaps))
            self.assertTrue(set(w.outliers) | set(w.overlaps) <= set(w.entities))

    def test_special_entities_are_stratified_by_class(self):
        from math import ceil

        p = WorldParams()
        cap = ceil((p.n_outliers + p.n_overlaps) / p.n_classes)
        for seed in range(900000, 900100):
            w = generate_world(seed)
            special = set(w.outliers) | set(w.overlaps)
            self.assertEqual(len(special), p.n_outliers + p.n_overlaps)
            per_class = Counter(w.base_classes[w.entities.index(e)] for e in special)
            with self.subTest(seed=seed):
                self.assertLessEqual(max(per_class.values()), cap)
                self.assertEqual(sorted(per_class.values()), [1, 1, 2])  # defaults: 2, 1 and 1
                normal = Counter(
                    k for e, k in zip(w.entities, w.base_classes) if e not in special
                )
                self.assertGreaterEqual(min(normal.values()), 4)

    def test_feature_rows(self):
        w = self.worlds[900000]
        self.assertEqual(len(w.feature_rows), 100)
        self.assertEqual([f.row_id for f in w.feature_rows], [f"f{i:04d}" for i in range(100)])
        self.assertEqual([f.entity for f in w.feature_rows], [e for e in w.entities for _ in range(5)])
        self.assertTrue(all(len(f.x) == 2 for f in w.feature_rows))
        protos = w.params.prototypes()
        self.assertAlmostEqual(protos[0][0], 3.0)
        self.assertAlmostEqual(protos[0][1], 0.0)
        for p in protos:
            self.assertAlmostEqual((p[0] ** 2 + p[1] ** 2) ** 0.5, 3.0)

    def test_report_rows(self):
        for w in self.worlds.values():
            self.assertEqual([r.row_id for r in w.report_rows], [f"r{i:04d}" for i in range(len(w.report_rows))])
            base = set(w.base_facts)
            for r in w.report_rows:
                self.assertIn(r.source, ("s0", "s1", "s2"))
                self.assertTrue(r.atom.pred.startswith("r"))  # no class atoms
                # derived-but-not-base true atoms are never considered
                if w.truth(r.atom):
                    self.assertIn(r.atom, base)
            self.assertEqual(sorted(w.source_reliabilities), ["s0", "s1", "s2"])
            self.assertTrue(all(isinstance(p, Probability) for p in w.source_reliabilities.values()))

    def test_truth_api(self):
        w = self.worlds[900000]
        some_true = sorted(w.true_atoms)[0]
        self.assertTrue(w.truth(some_true))
        false_atom = next(a for a in sorted(w.vocabulary) if a not in w.true_atoms)
        self.assertFalse(w.truth(false_atom))
        with self.assertRaises(ValueError):
            w.truth(Atom("r0", ("e00", "e00")))

    def test_max_attempts_raises(self):
        with self.assertRaises(RuntimeError):
            generate_world(900000, WorldParams(max_attempts=0))

    def test_acceptance_attempts_are_recorded(self):
        for w in self.worlds.values():
            self.assertTrue(1 <= w.attempts <= w.params.max_attempts)


if __name__ == "__main__":
    unittest.main()
