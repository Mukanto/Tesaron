"""Tests of the draft 5 repairs (blind review 2): independent abduction / relation units / interface facts (R2-6), the F3
comparison (R2-7), the pre-freeze check (R2-12), the calibration-draw study (R2-4), the T-1 structure (R2-3), the held
outputs (R2-11), the exact Pareto front and hypervolume, and the printed claims (R2-9)."""

import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest
from dataclasses import replace
from collections import namedtuple
from fractions import Fraction
from pathlib import Path
from types import SimpleNamespace as NS
from unittest import mock

import numpy as np

from audit import checks as C
from audit import f3_compare, fidelity, prefreeze_check, run_v02
from audit.cache import get_encoding
from audit.exact import (
    ExactTaus,
    hypervolume_exact,
    pareto_front_exact,
    pareto_points,
)
from audit.indep import (
    compare_interface_facts,
    compare_relation_units,
    enumerate_candidates,
    interface_facts,
    relation_units,
    top_k,
)
from audit.seeds import seeder
from audit.worldset import generate_valid
from tesaron.decoder import DecoderOutput

ROOT = Path(__file__).resolve().parent.parent
SKIP_GIT = os.environ.get("TESARON_SKIP_GIT_TESTS") == "1"
F = Fraction


def _records(n=2):
    recs, _ = generate_valid(n, seeder("dev"), "world-test", "enc-test", "aux", build=get_encoding)
    return recs


# ------------------------------------------------------------------------------------------ independent abduction
def lit(pred, args, ch="POS"):
    return NS(pred=pred, args=tuple(args), channel=NS(name=ch))


def rule(rid, head, body):
    return NS(id=rid, head=head, body=tuple(body))


Atom = namedtuple("Atom", "pred args")


def atom(pred, *args):
    return Atom(pred, tuple(args))


def fact(ch, pred, *args):
    return (ch, pred, tuple(args))


ENTITIES = ["e1", "e2", "e3"]
VOCAB = [atom(p, e) for p in "pqrsm" for e in ENTITIES] + [atom("k", a, b) for a in ENTITIES for b in ENTITIES]


class IndependentAbductionTests(unittest.TestCase):
    def enumerate(self, f1, observed, rules, vocab=VOCAB):
        return enumerate_candidates(f1, observed, rules, vocab, ENTITIES)

    def test_a_missing_ground_literal_is_a_candidate_with_score_one(self):
        r1 = rule("R1", lit("p", "X"), [lit("q", "X"), lit("s", "X")])
        obs = {fact("POS", "p", "e1"), fact("POS", "q", "e1")}
        self.assertEqual(self.enumerate(obs, obs, [r1]), [(1, fact("POS", "s", "e1"))])

    def test_the_head_must_be_observed_not_merely_derived(self):
        r1 = rule("R1", lit("p", "X"), [lit("q", "X"), lit("s", "X")])
        f1 = {fact("POS", "p", "e1"), fact("POS", "q", "e1")}
        self.assertEqual(self.enumerate(f1, {fact("POS", "q", "e1")}, [r1]), [])  # p(e1) is in F1 but not OBSERVED

    def test_exactly_one_body_literal_missing(self):
        r1 = rule("R1", lit("p", "X"), [lit("q", "X"), lit("s", "X"), lit("r", "X")])
        obs = {fact("POS", "p", "e1"), fact("POS", "q", "e1")}  # s and r both missing: not a candidate
        self.assertEqual(self.enumerate(obs, obs, [r1]), [])
        all_present = obs | {fact("POS", "s", "e1"), fact("POS", "r", "e1")}
        self.assertEqual(self.enumerate(all_present, all_present, [r1]), [])  # nothing missing

    def test_no_existential_guessing(self):
        # Y occurs only in the missing literal m(Y): the instance is excluded
        r = rule("R", lit("p", "X"), [lit("q", "X"), lit("m", "Y")])
        obs = {fact("POS", "p", "e1"), fact("POS", "q", "e1")}
        self.assertEqual(self.enumerate(obs, obs, [r]), [])
        # Y bound by another present body literal k(X, Y): allowed, one candidate per Y
        r2 = rule("R2", lit("p", "X"), [lit("k", ["X", "Y"]), lit("m", "Y")])
        obs2 = {fact("POS", "p", "e1"), fact("POS", "k", "e1", "e2"), fact("POS", "k", "e1", "e3")}
        got = self.enumerate(obs2, obs2, [r2])
        self.assertEqual(sorted(f for _, f in got), [fact("POS", "m", "e2"), fact("POS", "m", "e3")])
        # a variable bound by the head alone is bound
        r3 = rule("R3", lit("p", "X"), [lit("q", "X"), lit("s", "X")])
        self.assertEqual(len(self.enumerate({fact("POS", "p", "e2"), fact("POS", "q", "e2")},
                                            {fact("POS", "p", "e2"), fact("POS", "q", "e2")}, [r3])), 1)

    def test_the_candidate_atom_must_be_in_the_vocabulary_and_have_no_value(self):
        r1 = rule("R1", lit("p", "X"), [lit("q", "X"), lit("s", "X")])
        obs = {fact("POS", "p", "e1"), fact("POS", "q", "e1")}
        no_s = [a for a in VOCAB if a.pred != "s"]
        self.assertEqual(self.enumerate(obs, obs, [r1], vocab=no_s), [])  # not in the vocabulary
        with_neg = obs | {fact("NEG", "s", "e1")}  # s(e1) has a NEG fact: its value is not U
        self.assertEqual(self.enumerate(with_neg, with_neg, [r1]), [])
        self.assertEqual(self.enumerate(obs | {fact("POS", "s", "e2")}, obs, [r1]), [(1, fact("POS", "s", "e1"))])

    def test_a_missing_negative_literal_is_a_candidate_in_its_channel(self):
        obs = {fact("POS", "p", "e1"), fact("POS", "q", "e1")}
        r1 = rule("R1", lit("p", "X"), [lit("q", "X"), lit("s", "X", ch="NEG")])
        self.assertEqual(self.enumerate(obs, obs, [r1]), [(1, fact("NEG", "s", "e1"))])

    def test_score_counts_distinct_rule_and_theta(self):
        r1 = rule("R1", lit("p", "X"), [lit("q", "X"), lit("s", "X")])
        r2 = rule("R2", lit("p", "X"), [lit("r", "X"), lit("s", "X")])
        obs = {fact("POS", "p", "e1"), fact("POS", "q", "e1"), fact("POS", "r", "e1")}
        self.assertEqual(self.enumerate(obs, obs, [r1, r2]), [(2, fact("POS", "s", "e1"))])
        # one rule, two substitutions that complete the same atom: m(e1) from X = e2 and X = e3
        r3 = rule("R3", lit("p", "X"), [lit("k", ["X", "Y"]), lit("m", "Y")])
        obs3 = {fact("POS", "p", "e2"), fact("POS", "p", "e3"), fact("POS", "k", "e2", "e1"), fact("POS", "k", "e3", "e1")}
        self.assertEqual(self.enumerate(obs3, obs3, [r3]), [(2, fact("POS", "m", "e1"))])

    def test_ranking_score_then_channel_then_pred_then_args(self):
        rules = [
            rule("A", lit("p", "X"), [lit("q", "X"), lit("s", "X")]),
            rule("B", lit("p", "X"), [lit("r", "X"), lit("s", "X")]),
            rule("C", lit("p", "X"), [lit("q", "X"), lit("m", "X", ch="NEG")]),
            rule("D", lit("p", "X"), [lit("q", "X"), lit("m", "X")]),
        ]
        obs = {fact("POS", "p", "e1"), fact("POS", "q", "e1"), fact("POS", "r", "e1"),
               fact("POS", "p", "e2"), fact("POS", "q", "e2")}
        got = self.enumerate(obs, obs, rules)
        # s(e1): 2 (rules A, B); s(e2): 1; POS m(e1): 1; POS m(e2): 1; NEG m(e1): 1; NEG m(e2): 1
        self.assertEqual(got[0], (2, fact("POS", "s", "e1")))
        self.assertEqual([f for s, f in got[1:]], [
            fact("POS", "m", "e1"), fact("POS", "m", "e2"), fact("POS", "s", "e2"),  # POS before NEG, then pred, args
            fact("NEG", "m", "e1"), fact("NEG", "m", "e2"),
        ])

    def test_top_k(self):
        ranked = [(3, "a"), (2, "b"), (1, "c")]
        self.assertEqual(top_k(ranked, 0), [])
        self.assertEqual(top_k(ranked, 2), [(3, "a"), (2, "b")])
        self.assertEqual(top_k(ranked, 10), ranked)

    def test_it_agrees_with_the_decoder_on_a_real_world(self):
        from audit.indep import closure_fact_keys
        from audit.system import FIXED
        from tesaron.decoder import ranked_candidates, seminaive_eval_with_records

        rec = _records(1)[0]
        rules, vocab = tuple(rec.context.rules), rec.context.vocabulary
        facts = FIXED.interface_facts(rec.encoding.units, 0.7)
        keys = {(c.name, a.pred, tuple(a.args)) for c, a in facts}
        pass1 = closure_fact_keys(set(facts), rules, vocab, rec.world.entities)
        ranked = enumerate_candidates(pass1, keys, rules, vocab, rec.world.entities)
        dec = ranked_candidates(seminaive_eval_with_records(set(facts), rules, vocab).facts, set(facts), rules, vocab)
        self.assertGreater(len(ranked), 0)
        self.assertEqual(ranked, [(c.score, (c.fact[0].name, c.fact[1].pred, tuple(c.fact[1].args))) for c in dec])

    def test_the_independent_modules_do_not_import_the_code_they_check(self):
        for name in ("abduction.py", "units.py", "h_closure.py", "pcm_loop.py"):
            text = (ROOT / "audit" / "indep" / name).read_text(encoding="utf-8")
            code = "\n".join(line for line in text.splitlines() if re.match(r"\s*(from|import)\s", line))
            for banned in ("tesaron.decoder", "tesaron.encoder", "tesaron.belnap", "tesaron"):
                self.assertNotIn(banned, code, (name, banned))


# ------------------------------------------------------------------------------------------ independent units
class IndependentUnitsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rec = _records(1)[0]

    def args(self, units=None, ids=None):
        r = self.rec
        return (r.world, r.encoding.derive_ids if ids is None else ids, r.context.vocabulary,
                r.encoding.units if units is None else units)

    def test_relation_units_are_equal_on_a_real_world(self):
        self.assertEqual(compare_relation_units(*self.args()), [])
        rel = relation_units(self.rec.world, self.rec.encoding.derive_ids, self.rec.context.vocabulary)
        n = sum(1 for a in self.rec.encoding.units if not a.pred.startswith("c"))
        self.assertEqual(len(rel), n)
        for mu_pos, mu_neg, prov in rel.values():
            self.assertTrue(0.0 <= mu_pos <= 1.0 and 0.0 <= mu_neg <= 1.0 and prov)

    def test_a_changed_degree_provenance_or_extra_or_missing_unit_is_found(self):
        from tesaron.degrees import Membership

        units = dict(self.rec.encoding.units)
        rel_atoms = [a for a in units if not a.pred.startswith("c")]
        a = rel_atoms[0]
        degree = dict(units)
        degree[a] = replace(units[a], mu_pos=Membership(min(1.0, units[a].mu_pos.value + 1e-9)
                                                        if units[a].mu_pos.value < 1 else 0.5))
        self.assertTrue(any("relation unit" in p for p in compare_relation_units(*self.args(degree))))
        prov = dict(units)
        prov[a] = replace(units[a], provenance=tuple(reversed(units[a].provenance)) + ("r9999",))
        self.assertTrue(compare_relation_units(*self.args(prov)))
        missing = {k: v for k, v in units.items() if k != a}
        self.assertTrue(any("missing" in p for p in compare_relation_units(*self.args(missing))))
        extra = dict(units)
        extra[type(a)("r0", ("zz", "yy"))] = units[a]
        self.assertTrue(any("extra" in p for p in compare_relation_units(*self.args(extra))))

    def test_interface_facts_by_the_belnap_table_with_equality_counting(self):
        unit = lambda pos, neg, status="OBSERVED": NS(mu_pos=pos, mu_neg=neg, status=NS(name=status), provenance=("x1",))
        units = {atom("p", "e1"): unit(0.7, 0.7), atom("p", "e2"): unit(0.9, 0.1), atom("p", "e3"): unit(0.1, 0.8),
                 atom("q", "e1"): unit(0.99, 0.99, "NOT_COMPUTED"), atom("q", "e2"): unit(0.2, 0.2)}
        got = interface_facts(units, 0.7)
        self.assertEqual(sorted(got), [("NEG", "p", ("e1",)), ("NEG", "p", ("e3",)), ("POS", "p", ("e1",)),
                                       ("POS", "p", ("e2",))])  # p(e1) is B at alpha 0.7: equality counts
        self.assertEqual(sorted(interface_facts(units, 0.71)), [("NEG", "p", ("e3",)), ("POS", "p", ("e2",))])
        self.assertEqual(interface_facts(units, 0.95), {})  # the NOT_COMPUTED unit gives nothing

    def test_interface_facts_agree_with_the_decoder_interface_on_a_real_world(self):
        from audit.system import FIXED

        for alpha in C.ALPHAS:
            facts = FIXED.interface_facts(self.rec.encoding.units, alpha)
            self.assertEqual(compare_interface_facts(self.rec.encoding.units, alpha, facts), [])
        facts = dict(FIXED.interface_facts(self.rec.encoding.units, 0.7))
        gone = next(iter(facts))
        del facts[gone]
        self.assertTrue(any("missing interface fact" in p for p in compare_interface_facts(
            self.rec.encoding.units, 0.7, facts)))
        facts = dict(FIXED.interface_facts(self.rec.encoding.units, 0.7))
        facts[next(iter(facts))] = ("wrong",)
        self.assertTrue(any("provenance" in p for p in compare_interface_facts(self.rec.encoding.units, 0.7, facts)))


# ------------------------------------------------------------------------------------------ F1 and F4 detection
class ExtendedFidelityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rec = _records(1)[0]

    def test_all_controls_agree(self):
        self.assertTrue(fidelity.f1_details(self.rec)["ok"])
        d = fidelity.f4_details(self.rec)
        self.assertTrue(d["ok"], d["problems"])
        self.assertTrue(d["relation_units_equal"] and d["interface_facts_equal"])
        self.assertGreater(d["n_relation_units"], 0)

    def test_f1_detects_a_wrong_candidate_score_or_order(self):
        real = fidelity.ranked_candidates

        def rescored(f1, observed, rules, vocab):
            cands = real(f1, observed, rules, vocab)
            return [replace(cands[0], score=cands[0].score + 1)] + cands[1:] if cands else cands

        with mock.patch.object(fidelity, "ranked_candidates", rescored):
            ok, detail = fidelity.f1_check(self.rec)
        self.assertFalse(ok)
        self.assertIn("ranked candidate list", detail)

        def reversed_list(f1, observed, rules, vocab):
            return list(reversed(real(f1, observed, rules, vocab)))

        with mock.patch.object(fidelity, "ranked_candidates", reversed_list):
            self.assertFalse(fidelity.f1_check(self.rec)[0])

    def test_f1_detects_a_wrong_top_k_cut(self):
        real = fidelity.FIXED.decode

        def cap_plus_one(facts, rules, vocab, k):
            return real(facts, rules, vocab, k + 1 if k > 0 else k)

        with mock.patch.object(fidelity.FIXED, "decode", cap_plus_one):
            ok, detail = fidelity.f1_check(self.rec)
        self.assertFalse(ok)
        self.assertIn("top-k", detail)

    def test_f1_detects_reordered_hypotheses(self):
        real = fidelity.FIXED.decode

        def reorder(facts, rules, vocab, k):
            out = real(facts, rules, vocab, k)
            if len(out.hypotheses) < 2:
                return out
            return DecoderOutput(out.facts, tuple(reversed(out.hypotheses)), out.rounds)

        with mock.patch.object(fidelity.FIXED, "decode", reorder):
            ok, detail = fidelity.f1_check(self.rec)
        self.assertFalse(ok)
        self.assertIn("top-k", detail)

    def test_f1_detects_a_wrong_fact_status(self):
        from tesaron.decoder import FactInfo
        from tesaron.enums import EpistemicStatus

        real = fidelity.FIXED.decode

        def flip(facts, rules, vocab, k):
            out = real(facts, rules, vocab, k)
            if k != 0:
                return out
            infos = dict(out.facts)
            key = next((f for f, i in infos.items() if i.status is EpistemicStatus.DERIVED), None)
            if key is not None:
                infos[key] = FactInfo(EpistemicStatus.OBSERVED, provenance=("x",))
            return DecoderOutput(infos, out.hypotheses, out.rounds)

        with mock.patch.object(fidelity.FIXED, "decode", flip):
            ok, detail = fidelity.f1_check(self.rec)
        self.assertFalse(ok)
        self.assertIn("status", detail)

    def test_f4_detects_a_relation_unit_change(self):
        from tesaron.degrees import Membership

        enc = self.rec.encoding
        atom_ = next(a for a in enc.units if not a.pred.startswith("c"))
        units = dict(enc.units)
        units[atom_] = replace(enc.units[atom_], mu_neg=Membership(0.123456))
        ok, detail = fidelity.f4_check(replace(self.rec, encoding=replace(enc, units=units)))
        self.assertFalse(ok)
        self.assertIn("relation units", detail)

    def test_f4_detects_a_wrong_interface_fact(self):
        real = fidelity.FIXED.interface_facts

        def drop_one(units, alpha):
            facts = dict(real(units, alpha))
            if alpha == 0.7:
                facts.pop(next(iter(facts)))
            return facts

        with mock.patch.object(fidelity.FIXED, "interface_facts", drop_one):
            ok, detail = fidelity.f4_check(self.rec)
        self.assertFalse(ok)
        self.assertIn("interface facts", detail)

    def test_the_prefreeze_file_records_every_comparison(self):
        doc = json.loads((ROOT / "prereg" / "F4_PREFREEZE.json").read_text(encoding="utf-8"))
        self.assertEqual(doc["n_worlds"], 20)
        for key in ("f4_floats_within_tolerance", "f4_relation_units_all_equal", "f4_interface_facts_all_equal",
                    "f1_all_equal", "every_comparison_equal"):
            self.assertIs(doc[key], True, key)
        self.assertGreater(doc["n_candidates_compared"], 0)
        self.assertEqual(doc["n_configurations_compared"], 20 * 30)
        self.assertNotIn("HOLDS", json.dumps(doc))


# ------------------------------------------------------------------------------------------ exact Pareto and hypervolume
class ExactParetoTests(unittest.TestCase):
    def test_front_order_and_hypervolume(self):
        pts = [(("a", 0), F(1, 2), F(1, 2)), (("b", 0), F(1, 4), F(3, 4)), (("c", 0), F(1, 4), F(1, 2)),  # c dominated
               (("d", 0), F(1, 2), F(1, 2))]  # equal to a: both stay, ordered by config
        front = pareto_front_exact(pts)
        self.assertEqual([p[0] for p in front], [("a", 0), ("d", 0), ("b", 0)])
        self.assertEqual(hypervolume_exact(pts), F(1, 4) * F(3, 4) + F(1, 4) * F(1, 2))
        self.assertEqual(hypervolume_exact([]), F(0))
        self.assertEqual(hypervolume_exact([(("z", 0), F(0), F(1))]), F(0))

    def test_points_need_feasibility_and_a_defined_new_true(self):
        ex = lambda nt, nf="0": {"fidelity": F(9, 10), "deviation": F(0), "consistency": F(1), "uncertainty": F(1, 10),
                                 "new_true": nt, "new_false": F(nf)}
        taus = ExactTaus(F(4, 5), F(1, 50), F(9, 10), F(1, 2))
        by = {(0.9, 0): ex(F(1, 2)), (0.8, 0): ex(None), (0.7, 0): dict(ex(F(1, 2)), fidelity=F(1, 10))}
        self.assertEqual([c for c, _, _ in pareto_points(by, taus)], [(0.9, 0)])

    def test_the_exact_values_match_the_float_functions_of_tesaron(self):
        from audit.system import FIXED
        from tesaron.criterion.wisdom import hypervolume, make_point, pareto_front

        rec = _records(1)[0]
        results = FIXED.evaluate_grid(rec.world, rec.context, rec.encoding, C.GRID)
        by = {k: r[2] for k, r in results.items()}
        taus = ExactTaus(F(1, 2), F(1, 5), F(1, 2), F(1))  # lenient: many feasible points
        pts = pareto_points(by, taus)
        self.assertGreater(len(pts), 3)
        fl = [make_point(k, r[1], taus.floats()) for k, r in results.items()]
        self.assertEqual([p[0] for p in pareto_front_exact(pts)], [p.config for p in pareto_front(fl)])
        self.assertAlmostEqual(float(hypervolume_exact(pts)), hypervolume(pareto_front(fl)), places=12)


# ------------------------------------------------------------------------------------------ F3
class F3CompareTests(unittest.TestCase):
    def setUp(self):
        (ROOT / "run_dev").mkdir(exist_ok=True)
        self.tmp = Path(tempfile.mkdtemp(dir=ROOT / "run_dev"))
        self.run_dir, self.agent_dir = self.tmp / "run", self.tmp / "agent"
        (self.run_dir / "outputs_results").mkdir(parents=True)
        self.agent_dir.mkdir()
        self.metrics = {"fidelity": "4/5", "deviation": "0/1", "consistency": "1/1", "uncertainty": "1/10",
                        "new_true": "1/2", "new_false": None, "validation_agreement": "3/4", "boundary_share": "1/7"}
        self.world = {
            "metrics_exact": {"0.7|5": dict(self.metrics), "0.7|0": dict(self.metrics)},
            "f3": {"feasible": ["0.7|0", "0.7|5"], "pareto_front": ["0.7|5", "0.7|0"], "hypervolume": "3/8",
                   "outcomes": {"G7a": "HOLDS", "G8": "FAILS", "T-1": "UNDEFINED"},
                   "t1_structure": {"some_alpha_le_060_feasible": False, "alpha_ge_085_feasible": True,
                                    "t1_window_pairs": True, "t1_crossing_pairs": None, "t1_cross_080_085": False}},
        }
        self.rows = {t: {"test": t, "verdict": "HOLDS", "n_holds": 30, "n_fails": 0, "n_undefined": 0, "n_defined": 30,
                         "wilson_lower": None, "first_failing_world": None} for t in ("G1", "G7")}
        self.rows["G8"] = {"test": "G8", "verdict": "FAILS", "n_holds": 3, "n_fails": 27, "n_undefined": 0,
                           "n_defined": 30, "wilson_lower": 0.0661234, "first_failing_world": 1007}
        self.write_run(self.world)
        self.write_agent(self.agent_world())

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def agent_world(self):
        return {"world_seed": 1, "metrics": json.loads(json.dumps(self.world["metrics_exact"])),
                "feasible": ["0.7|5", "0.7|0"], "pareto_front": list(self.world["f3"]["pareto_front"]),
                "hypervolume": "3/8", "outcomes": dict(self.world["f3"]["outcomes"]),
                "t1_structure": dict(self.world["f3"]["t1_structure"])}

    def write_run(self, world, seed="1"):
        (self.run_dir / "outputs_results" / f"{seed}.json").write_text(json.dumps(world), encoding="utf-8")
        (self.run_dir / "VERDICTS.json").write_text(json.dumps({"table": {"rows": list(self.rows.values())}}),
                                                    encoding="utf-8")

    def write_agent(self, world, seed="1", table=True):
        (self.agent_dir / f"{seed}.json").write_text(json.dumps(world), encoding="utf-8")
        if table:
            rows = [dict(r, wilson_lower=None if r["wilson_lower"] is None else f"{r['wilson_lower']:.3f}")
                    for r in self.rows.values()]
            (self.agent_dir / "verdict_table.json").write_text(json.dumps({"rows": rows}), encoding="utf-8")

    def compare(self):
        return f3_compare.compare_dirs(self.run_dir, self.agent_dir)

    def test_matching_results_have_no_disagreement_and_exit_zero(self):
        doc = self.compare()
        self.assertTrue(doc["all_equal"])
        self.assertEqual((doc["n_disagreements"], doc["n_affecting_verdict"]), (0, 0))
        self.assertEqual(f3_compare.main([str(self.run_dir), str(self.agent_dir)]), 0)
        self.assertTrue((self.run_dir / "F3_COMPARE.json").is_file())
        self.assertEqual(json.loads((self.run_dir / "F3_COMPARE.json").read_text())["n_disagreements"], 0)

    def test_the_feasible_set_is_compared_as_a_set_and_the_front_as_a_list(self):
        w = self.agent_world()
        w["feasible"] = ["0.7|0", "0.7|5"]  # another order: equal
        self.write_agent(w)
        self.assertTrue(self.compare()["all_equal"])
        w["pareto_front"] = ["0.7|0", "0.7|5"]  # the order of the front matters
        self.write_agent(w)
        d = self.compare()["disagreements"]
        self.assertEqual([x["field"] for x in d], ["pareto_front"])
        self.assertFalse(d[0]["affects_verdict"])

    def test_a_metric_mismatch_is_exact_and_flagged(self):
        w = self.agent_world()
        w["metrics"]["0.7|5"]["fidelity"] = "8/10"  # equal as a number, not as a string
        self.write_agent(w)
        d = self.compare()["disagreements"]
        self.assertEqual(len(d), 1)
        self.assertEqual((d[0]["field"], d[0]["run"], d[0]["agent"], d[0]["affects_verdict"]),
                         ("metrics[0.7|5].fidelity", "4/5", "8/10", True))
        self.assertEqual(f3_compare.main([str(self.run_dir), str(self.agent_dir)]), 1)

    def test_fields_that_no_verdict_uses_do_not_affect_the_verdict(self):
        w = self.agent_world()
        w["metrics"]["0.7|0"]["validation_agreement"] = "1/2"
        w["metrics"]["0.7|0"]["boundary_share"] = None
        w["hypervolume"] = "1/2"
        self.write_agent(w)
        d = self.compare()
        self.assertEqual((d["n_disagreements"], d["n_affecting_verdict"]), (3, 0))
        self.assertTrue(all(not x["affects_verdict"] for x in d["disagreements"]))
        self.assertEqual(f3_compare.main([str(self.run_dir), str(self.agent_dir)]), 1)  # still not zero

    def test_null_against_string_and_missing_fields(self):
        w = self.agent_world()
        w["metrics"]["0.7|5"]["new_false"] = "0/1"  # the run says undefined
        del w["metrics"]["0.7|0"]["uncertainty"]
        del w["metrics"]["0.7|0"]
        self.write_agent(w)
        fields = {x["field"] for x in self.compare()["disagreements"]}
        self.assertIn("metrics[0.7|5].new_false", fields)
        self.assertIn("metrics[0.7|0]", fields)

    def test_outcomes_and_the_feasible_set_affect_the_verdict(self):
        w = self.agent_world()
        w["outcomes"]["G8"] = "HOLDS"
        w["feasible"] = ["0.7|5"]
        self.write_agent(w)
        d = {x["field"]: x["affects_verdict"] for x in self.compare()["disagreements"]}
        self.assertEqual(d, {"feasible": True, "outcomes.G8": True})

    def test_a_missing_or_an_extra_world_is_a_disagreement(self):
        (self.agent_dir / "1.json").unlink()
        d = self.compare()
        self.assertEqual([(x["field"], x["agent"], x["affects_verdict"]) for x in d["disagreements"]],
                         [("world file", "<missing>", True)])
        self.write_agent(self.agent_world())
        self.write_agent(self.agent_world(), seed="2")
        d = self.compare()
        self.assertEqual([x["world_seed"] for x in d["disagreements"]], ["2"])

    def test_the_verdict_table_is_compared_field_by_field(self):
        (self.agent_dir / "verdict_table.json").unlink()
        self.assertEqual(self.compare()["disagreements"][0]["field"], "verdict_table.json")
        self.write_agent(self.agent_world())
        table = json.loads((self.agent_dir / "verdict_table.json").read_text())
        for row in table["rows"]:
            if row["test"] == "G8":
                row["wilson_lower"] = "0.067"  # the run prints 0.066
                row["n_holds"] = 4
            if row["test"] == "G1":
                row["verdict"] = "FAILS"
        del table["rows"][-2]  # drop G7
        (self.agent_dir / "verdict_table.json").write_text(json.dumps(table), encoding="utf-8")
        d = {x["field"]: x["affects_verdict"] for x in self.compare()["disagreements"]}
        self.assertEqual(set(d), {"verdict_table[G8].wilson_lower", "verdict_table[G8].n_holds",
                                  "verdict_table[G1].verdict", "verdict_table[G7]"})
        self.assertTrue(all(d.values()))

    def test_the_wilson_bound_is_compared_as_printed(self):
        self.assertEqual(f3_compare.run_table_rows({"table": {"rows": [dict(self.rows["G8"])]}})["G8"]["wilson_lower"],
                         "0.066")

    def test_an_unreadable_run_folder_is_a_usage_error(self):
        self.assertEqual(f3_compare.main([str(self.tmp / "nope"), str(self.agent_dir)]), 2)

    def test_schema_and_instruction_files_exist_and_agree_with_the_comparison(self):
        schema = json.loads((ROOT / "audit" / "f3" / "OUTPUT_SCHEMA.json").read_text(encoding="utf-8"))
        per_world = schema["per_world_file"]
        self.assertEqual(sorted(per_world["required"]),
                         sorted(["world_seed", "metrics", "feasible", "pareto_front", "hypervolume", "outcomes",
                                 "t1_structure"]))
        self.assertEqual(sorted(schema["definitions"]["metrics"]["required"]),
                         sorted(f3_compare.VERDICT_METRICS + f3_compare.OTHER_METRICS))
        self.assertEqual(sorted(per_world["properties"]["outcomes"]["required"]), sorted(f3_compare.OUTCOME_TESTS))
        self.assertEqual(sorted(schema["verdict_table_file"]["properties"]["rows"]["items"]["required"]),
                         sorted(("test",) + f3_compare.TABLE_FIELDS))
        text = (ROOT / "audit" / "f3" / "INSTRUCTIONS_F3.md").read_text(encoding="utf-8")
        self.assertIn("OUTPUT_SCHEMA.json", text)
        self.assertFalse((ROOT / "audit" / "f3" / "INSTRUCTIONS_F3_DRAFT.md").exists())


# ------------------------------------------------------------------------------------------ runner: F3 inputs, held outputs
class RunnerRepairTests(unittest.TestCase):
    def setUp(self):
        (ROOT / "run_dev").mkdir(exist_ok=True)
        self.out = ROOT / "run_dev"
        self.assertEqual(run_v02.main(["calibrate", "--dev", "--n-cal", "3"]), 0)

    def run_test(self):
        return run_v02.main(["test", "--dev", "--n-test", "2", "--n-cal", "3", "--no-subprocess"])

    def test_blind_input_has_the_given_g1_g6_outcomes_and_nothing_else_of_the_run(self):
        self.assertEqual(self.run_test(), 0)
        blind = json.loads(next((self.out / "outputs_input").glob("*.json")).read_text())
        given = blind["given_outcomes_g1_g6"]
        self.assertEqual(sorted(given), ["G1", "G2", "G3", "G4", "G5", "G6"])
        self.assertTrue(all(v in ("HOLDS", "FAILS", "UNDEFINED") for v in given.values()))
        text = json.dumps(blind)
        for forbidden in ("G7", "G8", "T-1", "fixed_outcomes", "twin_outcomes", "check_data", "metrics", "feasible",
                          "hypervolume", "pareto", "n_hypotheses", "failed_parts"):
            self.assertNotIn(forbidden, text, forbidden)

    def test_run_results_carry_the_f3_fields_and_the_verdict_text_the_structure(self):
        self.assertEqual(self.run_test(), 0)
        results = json.loads(next((self.out / "outputs_results").glob("*.json")).read_text())
        f3 = results["f3"]
        self.assertEqual(sorted(f3), ["feasible", "hypervolume", "outcomes", "pareto_front", "t1_structure"])
        self.assertRegex(f3["hypervolume"], r"^[0-9]+/[1-9][0-9]*$")
        self.assertEqual(sorted(f3["outcomes"]), ["G7a", "G8", "T-1"])
        self.assertTrue(set(f3["pareto_front"]) <= set(f3["feasible"]))
        verdicts = json.loads((self.out / "VERDICTS.json").read_text())
        rows = {r["test"]: r for r in verdicts["table"]["rows"]}
        self.assertIn("Structure (I-5): of ", rows["T-1"]["structure_text"])
        self.assertIsNotNone(rows["G8"]["hypotheses"])
        self.assertIn("Hypotheses at (α₀, k = 10) over the defined worlds", rows["G8"]["text"])

    def test_an_agent_built_from_the_run_matches_and_a_corrupted_one_does_not(self):
        self.assertEqual(self.run_test(), 0)
        agent = self.out / "agent_test"
        shutil.rmtree(agent, ignore_errors=True)
        agent.mkdir()
        try:
            for path in (self.out / "outputs_results").glob("*.json"):
                res = json.loads(path.read_text())
                doc = {"world_seed": int(path.stem), "metrics": res["metrics_exact"], **res["f3"]}
                (agent / path.name).write_text(json.dumps(doc), encoding="utf-8")
            verdicts = json.loads((self.out / "VERDICTS.json").read_text())
            rows = f3_compare.run_table_rows(verdicts)
            (agent / "verdict_table.json").write_text(
                json.dumps({"rows": [dict(test=t, **v) for t, v in rows.items()]}), encoding="utf-8")
            self.assertTrue(f3_compare.compare_dirs(self.out, agent)["all_equal"])
            first = sorted(agent.glob("[0-9]*.json"))[0]
            doc = json.loads(first.read_text())
            key = next(iter(doc["metrics"]))
            doc["metrics"][key]["new_true"] = "1/1" if doc["metrics"][key]["new_true"] != "1/1" else "0/1"
            first.write_text(json.dumps(doc), encoding="utf-8")
            d = f3_compare.compare_dirs(self.out, agent)
            self.assertEqual(d["n_affecting_verdict"], 1)
        finally:
            shutil.rmtree(agent, ignore_errors=True)

    def test_a_crash_in_the_world_loop_leaves_no_outcome_on_disk(self):
        real = run_v02.evaluate_world
        calls = []

        def crash_on_second(*a, **k):
            calls.append(1)
            if len(calls) == 2:
                raise RuntimeError("boom")
            return real(*a, **k)

        for name in ("RESULTS.json", "VERDICTS.json"):
            (self.out / name).unlink(missing_ok=True)
        shutil.rmtree(self.out / "outputs_input", ignore_errors=True)
        shutil.rmtree(self.out / "outputs_results", ignore_errors=True)
        with mock.patch.object(run_v02, "evaluate_world", crash_on_second):
            with self.assertRaises(RuntimeError):
                self.run_test()
        self.assertEqual(len(calls), 2)
        self.assertFalse((self.out / "outputs_input").exists())
        self.assertFalse((self.out / "outputs_results").exists())
        self.assertFalse((self.out / "RESULTS.json").exists())
        self.assertFalse((self.out / "VERDICTS.json").exists())


# ------------------------------------------------------------------------------------------ T-1 structure (descriptive)
class T1StructureDescriptiveTests(unittest.TestCase):
    TAUS = ExactTaus(F(0), F(1), F(0), F(1))  # everything with a defined uncertainty is feasible

    def exacts(self, u_by_alpha, nf_by_alpha):
        out = []
        for a, k in C.GRID:
            out.append({"fidelity": F(1), "deviation": F(0), "consistency": F(1), "new_true": F(1, 2),
                        "uncertainty": u_by_alpha.get(a), "new_false": nf_by_alpha.get(a, F(0))})
        return out

    def test_the_two_upper_flags_and_the_080_085_pairs(self):
        from audit.descriptive import t1_structure

        a = lambda *xs: {x: F(i + 1, 20) for i, x in enumerate(xs)}
        # feasible alphas 0.90 and 0.80 only; the lower uncertainty (0.90) has new_false 0.30, the higher (0.80) 0.20
        ex = self.exacts({0.9: F(1, 10), 0.8: F(1, 5)}, {0.9: F(3, 10), 0.8: F(1, 5)})
        s = t1_structure(ex, self.TAUS)
        self.assertEqual(s["feasible_alphas"], [0.9, 0.8])
        self.assertIs(s["alpha_ge_085_feasible"], True)
        self.assertIs(s["some_alpha_le_060_feasible"], False)
        self.assertIs(s["t1_cross_080_085"], False)  # new_false(0.90) - new_false(0.80) = 0.10 > 0.05
        self.assertIsNone(s["t1_crossing_pairs"])  # no pair crosses 0.60/0.65
        self.assertIsNone(s["t1_window_pairs"])  # only one alpha inside 0.65-0.80
        # no alpha >= 0.85 feasible
        s = t1_structure(self.exacts({0.8: F(1, 5), 0.7: F(1, 10)}, {}), self.TAUS)
        self.assertIs(s["alpha_ge_085_feasible"], False)
        self.assertIsNone(s["t1_cross_080_085"])
        self.assertIs(s["t1_window_pairs"], True)
        # a pair across 0.85/0.80 that holds
        s = t1_structure(self.exacts({0.85: F(1, 10), 0.8: F(1, 5)}, {0.85: F(1, 5), 0.8: F(1, 5)}), self.TAUS)
        self.assertIs(s["t1_cross_080_085"], True)
        self.assertIs(s["alpha_ge_085_feasible"], True)  # 0.85 counts
        # alpha 0.60 feasible, the 0.60/0.65 pair
        s = t1_structure(self.exacts({0.65: F(1, 5), 0.6: F(1, 10)}, {0.65: F(0), 0.6: F(1, 2)}), self.TAUS)
        self.assertIs(s["some_alpha_le_060_feasible"], True)
        self.assertIs(s["t1_crossing_pairs"], False)
        self.assertEqual(sorted(s), ["alpha_ge_085_feasible", "feasible_alphas", "some_alpha_le_060_feasible",
                                     "t1_cross_080_085", "t1_crossing_pairs", "t1_window_pairs"])


# ------------------------------------------------------------------------------------------ pre-freeze check
class PrefreezeCheckTests(unittest.TestCase):
    def setUp(self):
        (ROOT / "run_dev").mkdir(exist_ok=True)
        self.repo = Path(tempfile.mkdtemp(dir=ROOT / "run_dev"))
        for rel, text in (("audit/a.py", "a\n"), ("audit/sub/b.py", "b\n"), ("tesaron/c.py", "c\n"),
                          ("tests/t.py", "t\n"), ("SPEC.md", "spec\n")):
            path = self.repo / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(text.encode("utf-8"))  # LF, whatever the platform's text mode does
        (self.repo / "audit" / "gate").mkdir(exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.repo, ignore_errors=True)

    def write_gate_tool(self):
        doc = {"files": prefreeze_check.gate_file_hashes(self.repo)}
        (self.repo / "audit" / "gate" / "GATE_TOOL.json").write_text(json.dumps(doc), encoding="utf-8")

    def test_gate_tool_matches_the_tree(self):
        self.write_gate_tool()
        self.assertEqual(prefreeze_check.check_gate_tool(self.repo), [])
        self.assertEqual(sorted(prefreeze_check.gate_file_hashes(self.repo)),
                         ["audit/a.py", "audit/sub/b.py", "tesaron/c.py"])

    def test_gate_tool_names_changed_added_and_removed_files(self):
        self.write_gate_tool()
        (self.repo / "audit" / "a.py").write_text("changed\n", encoding="utf-8")
        (self.repo / "tesaron" / "new.py").write_text("n\n", encoding="utf-8")
        (self.repo / "audit" / "sub" / "b.py").unlink()
        problems = prefreeze_check.check_gate_tool(self.repo)
        self.assertEqual(sorted(problems), sorted([
            "changed since the gate ran: audit/a.py", "file not in GATE_TOOL: tesaron/new.py",
            "GATE_TOOL lists a file that is gone: audit/sub/b.py"]))

    def test_caches_quick_certificates_and_the_gate_tool_itself_are_not_hashed(self):
        self.write_gate_tool()
        (self.repo / "audit" / "__pycache__").mkdir()
        (self.repo / "audit" / "__pycache__" / "a.cpython-314.pyc").write_bytes(b"x")
        (self.repo / "audit" / "gate" / "g1.quick.cert.json").write_text("{}", encoding="utf-8")
        self.assertEqual(prefreeze_check.check_gate_tool(self.repo), [])

    def test_the_certify_driver_uses_the_same_hash_table(self):
        try:
            from audit.gate import certify
        except ModuleNotFoundError:
            self.skipTest("truth_gate is not importable")
        self.assertEqual(certify.file_hashes(), prefreeze_check.gate_file_hashes(ROOT))

    def test_a_missing_or_unreadable_gate_tool_is_a_problem(self):
        self.assertTrue(prefreeze_check.check_gate_tool(self.repo)[0].startswith("cannot read"))
        (self.repo / "audit" / "gate" / "GATE_TOOL.json").write_text("{}", encoding="utf-8")
        self.assertEqual(prefreeze_check.check_gate_tool(self.repo), ["audit/gate/GATE_TOOL.json has no file table"])

    def git(self, *args):
        res = subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid",
                              "-c", "commit.gpgsign=false", *args], cwd=self.repo, capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, res.stderr)

    @unittest.skipIf(SKIP_GIT, "TESARON_SKIP_GIT_TESTS=1")
    def test_tracked_file_set_against_the_freeze_walk(self):
        paths = ("SPEC.md", "tesaron", "audit", "tests")
        self.git("init", "-q", "-b", "main")
        self.git("add", ".")
        self.git("commit", "-q", "-m", "all")
        self.assertEqual(prefreeze_check.check_tracked_set(self.repo, paths), [])
        # an untracked quick certificate would enter the manifest
        (self.repo / "audit" / "gate" / "g1.quick.cert.json").write_text("{}", encoding="utf-8")
        self.assertEqual(prefreeze_check.check_tracked_set(self.repo, paths),
                         ["would enter the manifest but is not tracked by git: audit/gate/g1.quick.cert.json"])
        # so would an ignored scratch file
        (self.repo / ".gitignore").write_text("*.scratch\n", encoding="utf-8")
        self.git("add", ".gitignore")
        self.git("commit", "-q", "-m", "ignore")
        (self.repo / "tests" / "x.scratch").write_text("s\n", encoding="utf-8")
        problems = prefreeze_check.check_tracked_set(self.repo, paths)
        self.assertIn("would enter the manifest but is not tracked by git: tests/x.scratch", problems)
        # a tracked cache file that the walk would not hash
        (self.repo / "audit" / "__pycache__").mkdir()
        (self.repo / "audit" / "__pycache__" / "a.pyc").write_bytes(b"x")
        self.git("add", "-f", "audit/__pycache__/a.pyc")
        problems = prefreeze_check.check_tracked_set(self.repo, paths)
        self.assertIn("tracked by git but not hashed by the freeze walk: audit/__pycache__/a.pyc", problems)
        # a listed path that does not exist
        self.assertIn("listed path does not exist: prereg/DRAW_STUDY.json",
                      prefreeze_check.check_tracked_set(self.repo, paths + ("prereg/DRAW_STUDY.json",)))

    def test_main_exit_codes(self):
        with mock.patch.object(prefreeze_check, "check_gate_tool", return_value=[]), \
                mock.patch.object(prefreeze_check, "check_tracked_set", return_value=[]):
            self.assertEqual(prefreeze_check.main([]), 0)
        with mock.patch.object(prefreeze_check, "check_gate_tool", return_value=["changed since the gate ran: x"]), \
                mock.patch.object(prefreeze_check, "check_tracked_set", return_value=[]):
            self.assertEqual(prefreeze_check.main(["--gate-tool"]), 1)
            self.assertEqual(prefreeze_check.main(["--tracked"]), 0)


# ------------------------------------------------------------------------------------------ calibration-draw study
class DrawStudyTests(unittest.TestCase):
    def test_need_is_the_least_count_the_wilson_rule_accepts(self):
        from audit import aggregate
        from audit.design import draw_study as D

        self.assertIsNone(D.need(15))
        for n, expected in ((16, 16), (19, 19), (20, 19), (28, 26), (29, 27), (30, 28)):
            self.assertEqual(D.need(n), expected, n)
        for n in range(16, 31):
            h = D.need(n)
            self.assertGreaterEqual(aggregate.wilson_lower(h, n), 0.80)
            self.assertLess(aggregate.wilson_lower(h - 1, n), 0.80)  # the least

    def test_p_holds_is_a_binomial_tail(self):
        from audit.design import draw_study as D

        self.assertEqual(D.p_holds(15, 0.95), 0.0)  # fewer than 16 defined worlds: no verdict
        self.assertAlmostEqual(D.p_holds(16, 1.0), 1.0)
        self.assertAlmostEqual(D.p_holds(30, 0.5), sum(
            __import__("math").comb(30, j) for j in range(28, 31)) / 2**30)
        self.assertAlmostEqual(D.p_holds(30, 0.95), 0.8122, places=3)
        self.assertLess(D.p_holds(30, 0.80), D.p_holds(30, 0.90))

    def test_draw_counts_on_synthetic_worlds(self):
        from audit.design import draw_study as D

        taus = ExactTaus(F(4, 5), F(1, 20), F(9, 10), F(1, 2))
        good = lambda u: {"fidelity": F(9, 10), "deviation": F(0), "consistency": F(1), "uncertainty": u,
                          "new_true": F(1, 2), "new_false": F(0)}
        bad = dict(good(F(1, 10)), fidelity=F(1, 10))
        world = lambda feas_at, oracle_ok=True: {
            "seed": 1,
            "fixed": {(a, k): (good(F(1, 10) + F(len(str(a)), 100)) if (a, k) in feas_at else bad) for a, k in C.GRID},
            "oracle": {a: (good(F(1, 10)) if oracle_ok else bad) for a in C.ALPHAS},
        }
        w_two = world({(0.95, 0), (0.7, 5)})  # two feasible points; uncertainty differs by alpha string length
        w_one = world({(0.7, 5)})
        w_none = world(set(), oracle_ok=False)
        w_default = world({(C.ALPHA0, C.K0), (0.5, 0)})
        got = D.draw_counts(taus, [w_two, w_one, w_none, w_default])
        self.assertEqual(got, {"n_t1_defined": 1, "n_no_feasible": 1, "n_default_feasible": 3, "n_alpha_ge_085": 1,
                               "n_g7a_defined": 3})

    def test_summarize(self):
        from audit.design import draw_study as D

        draws = [{"draw": i, "tau": {"tau_s": "4/5", "tau_d": "1/20", "tau_t": "9/10", "tau_b": f"{i + 1}/10"},
                  "n_t1_defined": n, "n_no_feasible": 0, "n_default_feasible": 20, "n_alpha_ge_085": i,
                  "n_g7a_defined": 30} for i, n in enumerate((10, 20, 30, 30))]
        s = D.summarize(draws)
        self.assertEqual(s["counts"]["n_t1_defined"], {"min": 10, "median": 25.0, "max": 30})
        self.assertEqual(s["p_insufficient"], 0.25)
        self.assertEqual(s["tau"]["tau_b"]["median"]["exact"], "1/4")  # the mean of 2/10 and 3/10
        self.assertAlmostEqual(s["tau"]["tau_b"]["max"]["float"], 0.4)
        expected = (0 + D.p_holds(20, 0.95) + 2 * D.p_holds(30, 0.95)) / 4
        self.assertAlmostEqual(s["p_holds_given_rate"]["0.95"], expected)
        self.assertEqual([r["n"] for r in s["need_table"]], list(range(16, 31)))

    def test_the_study_file_holds_design_quantities_only(self):
        doc = json.loads((ROOT / "prereg" / "DRAW_STUDY.json").read_text(encoding="utf-8"))
        self.assertEqual(doc["n_draws"], 40)
        self.assertEqual(len(doc["draws"]), 40)
        self.assertEqual(len(doc["test_world_seeds"]), 30)
        self.assertEqual(doc["rng"], "numpy PCG64(1729)")
        keys = {k for d in doc["draws"] for k in d}
        self.assertEqual(keys, {"draw", "tau", "n_t1_defined", "n_no_feasible", "n_default_feasible",
                                "n_alpha_ge_085", "n_g7a_defined"})
        for d in doc["draws"]:
            self.assertTrue(all(re.fullmatch(r"[0-9]+/[1-9][0-9]*", v) for v in d["tau"].values()))
        text = json.dumps(doc)
        for forbidden in ("new_false", "HOLDS", "FAILS", "le_060"):
            self.assertNotIn(forbidden, text, forbidden)
        source = (ROOT / "audit" / "design" / "draw_study.py").read_text(encoding="utf-8")
        for forbidden in ("judge_t1", "judge_g8", "collect_t1", "collect_g8", "<= 0.60", "BOUNDARY_LOW"):
            self.assertNotIn(forbidden, source, forbidden)


# ------------------------------------------------------------------------------------------ printed texts
class PrintedTextTests(unittest.TestCase):
    def test_claims_equal_the_prereg_claims(self):
        from audit.aggregate import CLAIMS

        self.assertEqual(CLAIMS["G2"], "Encoding is reproducible in the same context (same machine, same NumPy build)")
        self.assertEqual(CLAIMS["G3"], "A meaning unit needs its data (necessity)")
        self.assertEqual(CLAIMS["G4"],
                         "The decoder gives the same output for the same input (same machine, same NumPy build)")
        self.assertEqual(CLAIMS["G7"], "None of the five degenerate baselines of SPEC §10 (echo, all_true, all_false, "
                                       "all_unknown, all_both) gets a positive score under the wisdom criterion")
        prereg = ROOT / "prereg" / "PREREG_v0.2.md"
        if prereg.is_file():
            text = prereg.read_text(encoding="utf-8")
            for test in ("G2", "G3", "G4", "G7"):
                self.assertIn(CLAIMS[test], text, test)

    def test_every_gate_study_name_is_its_label_and_the_claim_with_a_lower_case_first_letter(self):
        from audit.aggregate import CLAIMS, LABEL

        found = {}
        for path in sorted((ROOT / "audit" / "gate").glob("*_study.py")):
            text = path.read_text(encoding="utf-8")
            found[path.name] = re.search(r'name="([^"]+)",', text).group(1)
        self.assertEqual(len(found), 9)
        files = {"G1": "g1", "G2": "g2", "G3": "g3", "G4": "g4", "G5": "g5", "G6": "g6", "G7": "g7", "G8": "g8",
                 "T-1": "t1"}
        self.assertEqual(sorted(files), sorted(CLAIMS))
        for test, gid in files.items():
            claim = CLAIMS[test]
            expected = f"{LABEL.get(test, test)}: {claim[0].lower()}{claim[1:]}"
            self.assertEqual(found[f"{gid}_study.py"], expected, test)

    def test_no_text_in_the_audit_layer_says_no_degenerate_strategy(self):
        for path in list((ROOT / "audit").rglob("*.py")) + [ROOT / "audit" / "README.md"]:
            self.assertNotIn("no degenerate strategy", path.read_text(encoding="utf-8").lower(), path.name)

    def test_the_system_docstring_names_s7(self):
        from audit import system

        self.assertIn("S-1..S-7", system.System.__doc__)


if __name__ == "__main__":
    unittest.main()
