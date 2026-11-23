"""F3 materials of v0.3 (audit/v03/f3/*, audit/v03/f3_compare.py) on synthetic fixtures (PREREG_v0.3 section 6.1).

The fixtures are made of made-up metric values pushed through the runner's own functions (`f3_fields`, `verdict_table`,
`t1_structure`), so the files have the run's format. No v0.3 world is read: nothing here touches a T-1 or G8 value of a real
world (PREREG section 2, no pilot). The tests on a development world read key names and types only."""

import copy
import json
import re
import tempfile
import unittest
from fractions import Fraction as F
from pathlib import Path

from audit.exact import ExactTaus, frac_str
from audit.v03 import aggregate as AG
from audit.v03 import checks as V
from audit.v03 import f3_compare as FC
from audit.v03 import run_v03 as RV
from audit.v03.tau import q40, taus_to_json

ROOT = Path(__file__).resolve().parent.parent
F3_DIR = ROOT / "audit" / "v03" / "f3"
SCHEMA = json.loads((F3_DIR / "OUTPUT_SCHEMA.json").read_text(encoding="utf-8"))
INSTRUCTIONS = (F3_DIR / "INSTRUCTIONS_F3.md").read_text(encoding="utf-8")
ALPHAS = V.ALPHAS
KS = (0, 5, 10)
TAUS = ExactTaus(F(7, 10), F(1, 10), F(1, 2), F(1))
N_TEST, N_CAL = 20, 5


def metrics(i, k, nf_slope, fid_drop, cons=F(9, 10)):
    """Made-up exact metrics at alpha index i (0 = 0.95) and k. Fidelity falls with i, uncertainty falls with i, new_false
    rises with i."""
    return {"fidelity": 1 - F(i * fid_drop, 100) - F(k, 1000), "deviation": F(i, 200) + F(k, 1000), "consistency": cons,
            "uncertainty": F(10 - i, 20), "new_true": F(1, 2) + F(i, 40), "new_false": F(i * nf_slope, 100),
            "validation_agreement": F(3, 4), "boundary_share": F(i, 10), "n_q": 6 + 2 * i}  # n_q: an int, the denominator of new_false


def exj(ex):
    """The run's JSON form of exact metrics: fractions as "p/q" strings, n_q a plain integer."""
    return {k: (None if v is None else (v if k == "n_q" else frac_str(v))) for k, v in ex.items()}


def make_test_world(j):
    """(run document, agent document) of synthetic test world j. World 0 has no feasible point (T-1 undefined)."""
    nf_slope = (0, 1, 2, 1, 3)[j % 5]
    cons = F(1, 10) if j == 0 else F(9, 10)  # world 0: consistency below tau_t everywhere, so no feasible point
    results = {(a, k): (None, None, metrics(i, k, nf_slope, 3, cons)) for i, a in enumerate(ALPHAS) for k in KS}
    exacts_k0 = [results[(a, 0)][2] for a in ALPHAS]
    rel = [round(0.55 + 0.05 * s, 3) for s in range(8)]
    structure = V.t1_structure(exacts_k0, TAUS, rel, lambda lo, hi: 1 if j % 2 else 0)
    ev = {"results": results,
          "fixed": {"G7": {"outcome": "HOLDS"}, "T-1": {"outcome": V.t1_outcome(exacts_k0, TAUS)}},
          "descriptive": {"t1_structure": structure}}
    taus = RV.TauSet(TAUS, TAUS, TAUS, TAUS)
    f3 = RV.fr_json(RV.f3_fields(ev, taus))
    seed = 1_000_000 + 17 * j
    mex = {f"{a}|{k}": exj(ex) for (a, k), (_, _, ex) in results.items()}
    run = {"world_seed": seed, "f3": f3, "metrics_exact": mex}
    agent = {"world_seed": seed, "metrics": copy.deepcopy(mex), **copy.deepcopy(f3)}
    return seed, run, agent, ev["fixed"]["T-1"]["outcome"], structure


def cal_world(c):
    seed = 2_000_000 + c
    ex = exj(metrics(3, 0, 1, 3 + c))
    return seed, {"world_seed": seed, "metrics_exact": {"0.7|0": ex}}, {"world_seed": seed, "metrics": {"0.7|0": dict(ex)}}


def write(path: Path, doc):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=1, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def build(root: Path):
    """Write a run folder and an agent folder that agree everywhere."""
    run, agent = root / "run", root / "agent"
    per_test = {t: [] for t in ("G1", "G2", "G3", "G4", "G5", "G6", "G7", "T-1")}
    structures = []
    for j in range(N_TEST):
        seed, rdoc, adoc, t1, structure = make_test_world(j)
        write(run / "outputs_results" / f"{seed}.json", rdoc)
        write(agent / f"{seed}.json", adoc)
        for t in per_test:
            per_test[t].append((seed, t1 if t == "T-1" else ("FAILS" if t == "G1" and j == 4 else "HOLDS")))
        structures.append(structure)
    for c in range(N_CAL):
        seed, rdoc, adoc = cal_world(c)
        write(run / "outputs_results" / f"cal_{seed}.json", rdoc)
        write(agent / f"cal_{seed}.json", adoc)
    ds = AG.draw_sensitivity_counts([[o for _, o in per_test["T-1"]]] * 3)
    all_true = {"n_worlds": N_TEST, "n_worlds_scoring": 0, "n_worlds_feasible": 0, "scoring_by_alpha": {}}
    table = AG.verdict_table(per_test, structure=structures, draw_sensitivity=ds, all_true=all_true)
    write(run / "VERDICTS.json", {"table": json.loads(json.dumps(table))})
    tau_doc = taus_to_json(TAUS)
    write(run / "TAU.json", {"main": tau_doc})
    write(agent / "tau.json", {k: tau_doc[k] for k in FC.TAU_NAMES})
    rows = []
    for row in table["rows"]:
        rows.append({k: (None if row.get("wilson_lower") is None else f"{row['wilson_lower']:.3f}") if k == "wilson_lower"
                     else row.get(k) for k in ("test", "verdict", "n_holds", "n_fails", "n_undefined", "n_defined",
                                               "wilson_lower", "first_failing_world")})
    counts = next(r for r in table["rows"] if r["test"] == "T-1")["structure"]
    write(agent / "verdict_table.json", {"rows": rows, "t1_structure_counts": {k: counts[k] for k in FC.STRUCTURE_COUNT_FIELDS}})
    return run, agent


class CompareTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self.run_dir, self.agent = build(self.root)

    def compare(self):
        return FC.compare_dirs(self.run_dir, self.agent)

    def edit(self, path: Path, fn):
        doc = json.loads(path.read_text(encoding="utf-8"))
        fn(doc)
        write(path, doc)

    def agent_file(self, j=2):
        return self.agent / f"{make_test_world(j)[0]}.json"

    def test_the_fixture_has_every_kind_of_world(self):
        outs = [make_test_world(j)[3] for j in range(N_TEST)]
        self.assertIn("UNDEFINED", outs)
        self.assertTrue({"HOLDS", "FAILS"} <= set(outs))

    def test_a_self_comparison_has_no_disagreement(self):
        out = self.compare()
        self.assertEqual(out["n_disagreements"], 0)
        self.assertTrue(out["all_equal"])
        self.assertEqual((out["n_worlds_run"], out["n_worlds_agent"]), (N_TEST, N_TEST))
        self.assertEqual((out["n_calibration_worlds_run"], out["n_calibration_worlds_agent"]), (N_CAL, N_CAL))
        self.assertEqual(out["affected_tests"], [])
        self.assertEqual(set(out["n_disagreements_by_affected_test"]), set(FC.ALL_TESTS))

    def test_a_perturbed_tau_affects_t1_and_g7a(self):
        self.edit(self.agent / "tau.json", lambda d: d.update(tau_s="3/5"))
        out = self.compare()
        self.assertEqual(out["n_disagreements"], 1)
        self.assertEqual(out["disagreements"][0]["field"], "tau.tau_s")
        self.assertEqual(out["disagreements"][0]["affected_tests"], ["G7a", "T-1"])
        self.assertEqual(out["affected_tests"], ["G7a", "T-1"])
        self.assertTrue(out["disagreements"][0]["affects_verdict"])
        self.edit(self.agent / "tau.json", lambda d: d.update(tau_s="7/10"))  # restored
        self.assertEqual(self.compare()["n_disagreements"], 0)

    def test_a_tau_string_that_is_not_in_lowest_terms_is_a_disagreement(self):
        self.edit(self.agent / "tau.json", lambda d: d.update(tau_d="2/20"))  # equal as a number, not as a string
        self.assertEqual(self.compare()["affected_tests"], ["G7a", "T-1"])

    def test_a_perturbed_g1_row_affects_g1_and_the_summary_says_so(self):
        def bump(doc):
            next(r for r in doc["rows"] if r["test"] == "G1")["n_holds"] += 1
        self.edit(self.agent / "verdict_table.json", bump)
        out = self.compare()
        self.assertEqual(out["n_disagreements"], 1)
        self.assertEqual(out["disagreements"][0]["affected_tests"], ["G1"])
        self.assertEqual(out["affected_tests"], ["G1"])  # post-run audit A7: the summary counts G1 to G6 rows
        self.assertEqual(out["n_disagreements_by_affected_test"]["G1"], 1)
        self.assertEqual(out["n_disagreements_by_affected_test"]["G7a"], 0)

    def test_rows_of_g2_to_g6_and_g7_are_counted_too(self):
        for test, label in (("G3", "G3"), ("G6", "G6"), ("G7", "G7a"), ("T-1", "T-1")):
            self.run_dir, self.agent = build(self.root / test)
            self.edit(self.agent / "verdict_table.json",
                      lambda d, t=test: next(r for r in d["rows"] if r["test"] == t).update(first_failing_world=1))
            out = self.compare()
            self.assertEqual(out["affected_tests"], [label])
            self.assertEqual(out["n_disagreements_by_affected_test"][label], out["n_disagreements"])

    def test_a_missing_world_affects_g7a_and_t1(self):
        self.agent_file(3).unlink()
        out = self.compare()
        self.assertEqual(out["n_disagreements"], 1)
        self.assertEqual(out["disagreements"][0]["field"], "world file")
        self.assertEqual(out["affected_tests"], ["G7a", "T-1"])

    def test_an_extra_world_and_a_missing_calibration_world_affect_g7a_and_t1(self):
        write(self.agent / "999999.json", {"world_seed": 999999})
        self.assertEqual(self.compare()["affected_tests"], ["G7a", "T-1"])
        (self.agent / "999999.json").unlink()
        next(self.agent.glob("cal_*.json")).unlink()
        out = self.compare()
        self.assertEqual((out["n_disagreements"], out["affected_tests"]), (1, ["G7a", "T-1"]))
        self.assertEqual(out["disagreements"][0]["field"], "calibration world file")

    def test_a_missing_tau_or_table_file(self):
        (self.agent / "tau.json").unlink()
        self.assertEqual(self.compare()["affected_tests"], ["G7a", "T-1"])
        (self.agent / "verdict_table.json").unlink()
        self.assertEqual(self.compare()["affected_tests"], list(FC.ALL_TESTS))

    def test_a_perturbed_hypervolume_affects_no_test(self):
        self.edit(self.agent_file(), lambda d: d.update(hypervolume="1/1000"))
        out = self.compare()
        self.assertEqual(out["n_disagreements"], 1)
        self.assertEqual(out["disagreements"][0]["field"], "hypervolume")
        self.assertEqual(out["disagreements"][0]["affected_tests"], [])
        self.assertFalse(out["disagreements"][0]["affects_verdict"])
        self.assertEqual((out["n_affecting_verdict"], out["affected_tests"]), (0, []))
        self.assertFalse(out["all_equal"])  # a disagreement with no affected test is still reported

    def test_the_front_and_the_two_other_metrics_affect_no_test(self):
        def edit(doc):
            doc["pareto_front"] = doc["pareto_front"][::-1] + ["0.5|10"]
            for cfg in doc["metrics"]:
                doc["metrics"][cfg]["validation_agreement"] = None
                doc["metrics"][cfg]["boundary_share"] = "1/3"
        self.edit(self.agent_file(), edit)
        out = self.compare()
        self.assertGreater(out["n_disagreements"], 60)
        self.assertEqual((out["n_affecting_verdict"], out["affected_tests"]), (0, []))

    def test_a_perturbed_metric_or_feasible_set_affects_g7a_and_t1_and_a_structure_field_t1_only(self):
        cases = ((lambda d: d["metrics"]["0.8|5"].update(new_false="1/7"), "metrics[0.8|5].new_false", ["G7a", "T-1"]),
                 (lambda d: d["metrics"]["0.8|5"].update(fidelity=None), "metrics[0.8|5].fidelity", ["G7a", "T-1"]),
                 (lambda d: d["metrics"]["0.8|5"].update(n_q=99), "metrics[0.8|5].n_q", ["T-1"]),  # R1-1, R2-8: T-1 only
                 (lambda d: d["metrics"]["0.8|0"].update(n_q="12"), "metrics[0.8|0].n_q", ["T-1"]),  # a type difference
                 (lambda d: d["feasible"].append("0.5|10"), "feasible", ["G7a", "T-1"]),
                 (lambda d: d["t1_structure"].update(sources_spanned=99), "t1_structure.sources_spanned", ["T-1"]),
                 (lambda d: d["t1_structure"].update(largest_increase="1/99"), "t1_structure.largest_increase", ["T-1"]),
                 (lambda d: d["t1_structure"].update(feasible_alphas=["0.5"]), "t1_structure.feasible_alphas", ["T-1"]))
        for n, (fn, field, tests) in enumerate(cases):
            self.run_dir, self.agent = build(self.root / f"case{n}")
            self.edit(self.agent_file(4), fn)
            out = self.compare()
            self.assertEqual([d["field"] for d in out["disagreements"]], [field])
            self.assertEqual(out["affected_tests"], tests, field)

    def test_the_n_q_of_a_test_world_affects_t1_only(self):  # R2-8
        self.edit(self.agent_file(4), lambda d: d["metrics"]["0.8|5"].pop("n_q"))  # a missing n_q is a disagreement too
        out = self.compare()
        self.assertEqual([d["field"] for d in out["disagreements"]], ["metrics[0.8|5].n_q"])
        self.assertEqual(out["disagreements"][0]["affected_tests"], ["T-1"])
        self.assertTrue(out["disagreements"][0]["affects_verdict"])
        self.assertEqual(out["affected_tests"], ["T-1"])
        self.run_dir, self.agent = build(self.root / "extra_case")  # an unknown metric name keeps the default map
        self.edit(self.agent_file(4), lambda d: d["metrics"]["0.8|5"].update(extra=1))
        self.assertEqual(self.compare()["affected_tests"], ["G7a", "T-1"])

    def test_the_n_q_of_a_calibration_world_affects_no_test(self):  # R2-8: it enters no tau and no test
        path = next(self.agent.glob("cal_*.json"))
        self.edit(path, lambda d: d["metrics"]["0.7|0"].update(n_q=1000))
        out = self.compare()
        self.assertEqual([d["field"] for d in out["disagreements"]], ["metrics[0.7|0].n_q"])
        self.assertEqual(out["disagreements"][0]["affected_tests"], [])
        self.assertFalse(out["disagreements"][0]["affects_verdict"])
        self.assertEqual((out["n_affecting_verdict"], out["affected_tests"]), (0, []))
        self.assertFalse(out["all_equal"])  # a disagreement with no affected test is still reported
        self.edit(path, lambda d: d["metrics"]["0.7|0"].pop("n_q"))  # a missing n_q too
        out = self.compare()
        self.assertEqual((out["n_disagreements"], out["affected_tests"]), (1, []))
        self.edit(path, lambda d: d["metrics"]["0.7|0"].update(n_q=1000, uncertainty="1/3"))  # a real metric still counts
        self.assertEqual(self.compare()["affected_tests"], ["G7a", "T-1"])

    def test_a_perturbed_calibration_metric_affects_g7a_and_t1_except_the_two_descriptive_ones(self):
        path = next(self.agent.glob("cal_*.json"))
        self.edit(path, lambda d: d["metrics"]["0.7|0"].update(uncertainty="1/3"))
        self.assertEqual(self.compare()["affected_tests"], ["G7a", "T-1"])
        self.edit(path, lambda d: d["metrics"]["0.7|0"].update(uncertainty=json.loads(
            (self.run_dir / "outputs_results" / path.name).read_text())["metrics_exact"]["0.7|0"]["uncertainty"],
            boundary_share="9/10"))
        out = self.compare()
        self.assertEqual((out["n_disagreements"], out["affected_tests"]), (1, []))

    def test_an_outcome_disagreement_affects_its_own_test_only(self):
        self.edit(self.agent_file(1), lambda d: d["outcomes"].update({"G7a": "FAILS"}))
        out = self.compare()
        self.assertEqual((out["n_disagreements"], out["affected_tests"]), (1, ["G7a"]))
        self.edit(self.agent_file(1), lambda d: d["outcomes"].update({"G7a": "HOLDS", "T-1": "UNDEFINED"}))
        out = self.compare()
        self.assertEqual(out["affected_tests"], ["T-1"])

    def test_p_over_q_needs_exact_string_equality_and_other_values_exact_equality(self):
        self.edit(self.agent_file(), lambda d: d["metrics"]["0.8|0"].update(fidelity="14/20"))  # 7/10 in lowest terms
        out = self.compare()
        self.assertEqual(out["n_disagreements"], 1)
        # a number where the run has a string, a bool where the run has an int
        self.edit(self.agent_file(5), lambda d: d["metrics"]["0.8|0"].update(deviation=0.1))
        self.edit(self.agent_file(6), lambda d: d["t1_structure"].update(defined=1))
        out = self.compare()
        self.assertEqual(out["n_disagreements"], 3)
        self.assertEqual(out["affected_tests"], ["G7a", "T-1"])

    def test_the_structure_counts_are_compared(self):
        self.edit(self.agent / "verdict_table.json", lambda d: d["t1_structure_counts"].update(median="9"))
        out = self.compare()
        self.assertEqual(out["n_disagreements"], 1)
        self.assertEqual(out["disagreements"][0]["field"], "verdict_table.t1_structure_counts.median")
        self.assertEqual(out["affected_tests"], ["T-1"])  # the structure counts affect T-1 only
        self.edit(self.agent / "verdict_table.json", lambda d: d.pop("t1_structure_counts"))
        out = self.compare()
        self.assertEqual(out["disagreements"][0]["field"], "verdict_table.t1_structure_counts")
        self.assertEqual(out["affected_tests"], ["T-1"])

    def test_an_extra_field_affects_no_test_and_a_wrong_world_seed_does(self):
        self.edit(self.agent_file(), lambda d: d.update(g8="HOLDS"))
        out = self.compare()
        self.assertEqual((out["n_disagreements"], out["affected_tests"]), (1, []))
        self.edit(self.agent_file(), lambda d: (d.pop("g8"), d.update(world_seed=5)))
        self.assertEqual(self.compare()["affected_tests"], ["G7a", "T-1"])

    def test_the_cli_exit_codes_and_the_output_file(self):
        out = self.root / "F3_COMPARE.json"
        self.assertEqual(FC.main([str(self.run_dir), str(self.agent), "-o", str(out)]), 0)
        doc = json.loads(out.read_text(encoding="utf-8"))
        self.assertTrue(doc["all_equal"])
        self.assertNotIn("\r", out.read_text(encoding="utf-8"))  # LF
        self.edit(self.agent / "tau.json", lambda d: d.update(tau_b="1/2"))
        self.assertEqual(FC.main([str(self.run_dir), str(self.agent), "-o", str(out)]), 1)
        self.assertEqual(FC.main([str(self.run_dir), str(self.root / "nowhere")]), 2)


class SchemaTests(unittest.TestCase):
    """The agent's files, which equal the run's format, validate against OUTPUT_SCHEMA.json."""

    @classmethod
    def setUpClass(cls):
        try:
            import jsonschema
        except ImportError:  # pragma: no cover
            raise unittest.SkipTest("jsonschema is not installed")
        cls.jsonschema = jsonschema
        cls._tmp = tempfile.TemporaryDirectory()
        cls.run_dir, cls.agent = build(Path(cls._tmp.name))

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def validate(self, part: str, doc):
        schema = {"definitions": SCHEMA["definitions"], **SCHEMA[part]}
        self.jsonschema.validate(doc, schema)

    def test_synthetic_outputs_validate(self):
        for p in self.agent.glob("*.json"):
            doc = json.loads(p.read_text(encoding="utf-8"))
            if p.stem == "tau":
                self.validate("tau_file", doc)
            elif p.stem == "verdict_table":
                self.validate("verdict_table_file", doc)
            elif p.stem.startswith("cal_"):
                self.validate("calibration_world_file", doc)
            else:
                self.validate("per_world_file", doc)

    def test_the_schema_refuses_what_it_should(self):
        doc = json.loads(next(p for p in self.agent.glob("*.json") if p.stem[0].isdigit()).read_text(encoding="utf-8"))
        for fn in (lambda d: d["outcomes"].update(G8="HOLDS"), lambda d: d["metrics"]["0.95|0"].update(fidelity=0.5),
                   lambda d: d.update(hypervolume="-1/2"), lambda d: d["t1_structure"].update(alpha_min=0.5),
                   lambda d: d["t1_structure"].pop("largest_increase")):
            bad = copy.deepcopy(doc)
            fn(bad)
            with self.assertRaises(self.jsonschema.ValidationError):
                self.validate("per_world_file", bad)
        neg = copy.deepcopy(doc)
        neg["t1_structure"]["largest_increase"] = "-1/20"  # the largest increase may be negative
        self.validate("per_world_file", neg)

    def test_the_schema_requires_n_q_as_a_plain_integer(self):
        doc = json.loads(next(p for p in self.agent.glob("*.json") if p.stem[0].isdigit()).read_text(encoding="utf-8"))
        self.assertIn("n_q", SCHEMA["definitions"]["metrics"]["required"])
        for fn in (lambda d: d["metrics"]["0.95|0"].pop("n_q"), lambda d: d["metrics"]["0.95|0"].update(n_q="3/1"),
                   lambda d: d["metrics"]["0.95|0"].update(n_q=-1), lambda d: d["metrics"]["0.95|0"].update(n_q=1.5),
                   lambda d: d["metrics"]["0.95|0"].update(n_q=None)):
            bad = copy.deepcopy(doc)
            fn(bad)
            with self.assertRaises(self.jsonschema.ValidationError):
                self.validate("per_world_file", bad)
        zero = copy.deepcopy(doc)
        zero["metrics"]["0.95|0"]["n_q"] = 0
        self.validate("per_world_file", zero)  # n_q = 0 is a value

    def test_the_schema_and_the_comparison_name_the_same_fields(self):
        props = SCHEMA["per_world_file"]["properties"]
        self.assertEqual(set(props), set(FC.WORLD_FIELDS))
        self.assertEqual(set(props["t1_structure"]["properties"]), set(FC.T1_STRUCTURE_FIELDS))
        self.assertEqual(set(props["outcomes"]["properties"]), set(FC.OUTCOME_TESTS))
        self.assertEqual(set(SCHEMA["definitions"]["metrics"]["properties"]), set(FC.METRIC_TESTS))
        self.assertEqual(set(SCHEMA["tau_file"]["properties"]), set(FC.TAU_NAMES))
        self.assertEqual(set(SCHEMA["verdict_table_file"]["properties"]["t1_structure_counts"]["properties"]),
                         set(FC.STRUCTURE_COUNT_FIELDS))
        self.assertEqual(set(SCHEMA["calibration_world_file"]["properties"]), set(FC.CAL_FIELDS))
        self.assertEqual(set(SCHEMA["verdict_table_file"]["properties"]["rows"]["items"]["properties"]["test"]["enum"]),
                         set(AG.DETERMINISTIC_TESTS + AG.QUANTITATIVE_TESTS))
        self.assertNotIn("G8", json.dumps(SCHEMA["verdict_table_file"]["properties"]["rows"]))


class InstructionsTests(unittest.TestCase):
    """The instructions say what the schema, the comparison and PREREG section 6.1 say."""

    def test_the_instructions_are_the_four_baseline_g7a_without_all_true(self):
        text = " ".join(INSTRUCTIONS.split())
        self.assertIn("G7a has **four** baselines", text)
        self.assertIn("all_false, all_unknown and all_both are F, U and B", text)
        self.assertIn("Do **not** compute all_true", text)
        self.assertNotIn("five baselines", text)

    def test_the_instructions_fix_the_float_rules_and_tau(self):
        text = " ".join(INSTRUCTIONS.split())
        self.assertIn("IEEE doubles", text)
        self.assertIn("0.04999999999999993", text)  # A8: the boundary band is an IEEE-double comparison
        self.assertIn("`tau_s` is the 4th smallest fidelity and `tau_t` the 4th smallest consistency", text)
        self.assertIn("`tau_d` is the 4th largest deviation and `tau_b` the 4th largest uncertainty", text)
        self.assertIn("z = 1.6448536269514722", text)
        self.assertIn("read at k = 0 only", text)

    def test_what_f3_does_not_cover_is_listed(self):
        text = " ".join(INSTRUCTIONS.split())
        for item in ("the G1 to G6 outcomes (given)", "G8 and its summaries", "the all_true arm", "G7b",
                     "cross-seed agreement", "(I-2)", "(I-6)", "(I-7)", "(I-8)", "(I-9)", "draw-sensitivity",
                     "detector diagnostic"):
            self.assertIn(item, text)

    def test_the_instructions_give_n_q_and_the_one_atom_floor(self):
        text = " ".join(INSTRUCTIONS.split())
        self.assertIn("max(1/20, 1/n_q)", text)
        self.assertIn("when n_q is 0 the bound is 1/20", text)
        self.assertIn("`n_q`, a ninth value at every configuration", text)
        self.assertNotIn("new_false(q) - new_false(p) <= 1/20.", text)  # v0.2's tolerance alone is no longer the rule
        self.assertIn("`n_q`, which is a plain JSON integer", text)


class RunnerFormatTests(unittest.TestCase):
    """The runner's outputs_input and outputs_results documents have the fields the instructions and the schema name. Key names
    and types only: no value of a development world is read or printed."""

    @classmethod
    def setUpClass(cls):
        from audit import checks as C
        from audit.system import FIXED
        from audit.v03.per_world import evaluate_world_v03
        from audit.v03.seeds import DEV_CORE, seeder
        from audit.v03.worldset import generate_valid_v03

        sd = seeder(DEV_CORE)
        cls.C, cls.FIXED = C, FIXED
        cls.cal = RV.build_calibration(DEV_CORE, None, 5, 0)
        cls.rec = generate_valid_v03(1, sd, "world-test", "enc-test", "aux")[0][0]
        cls.ev = evaluate_world_v03(cls.rec, cls.cal.taus, sd, subprocess_checks=False, run_twins=False, keep_data=False)

    def test_the_test_input_has_the_documented_fields(self):
        doc = RV.blind_input(self.rec, self.ev, False)
        self.assertEqual(set(doc), {"role", "world_seed", "draw_index", "entities", "n_classes", "n_relations",
                                    "base_classes", "outliers", "overlaps", "rules", "true_atoms", "source_reliabilities",
                                    "epsilon_band", "units", "validation_units", "default_configuration",
                                    "calibration_configuration", "alphas", "ks", "configs", "given_outcomes_g1_g6"})
        self.assertEqual(doc["alphas"], list(self.C.ALPHAS))
        self.assertEqual(doc["ks"], [0, 5, 10])
        self.assertEqual(set(doc["configs"]), {f"{a}|{k}" for a in self.C.ALPHAS for k in (0, 5, 10)})
        for cfg in doc["configs"].values():
            self.assertEqual(set(cfg), {"full", "verdict"})
        text = INSTRUCTIONS
        for name in doc:
            self.assertIn(f"`{name}`", text, name)

    def test_the_calibration_input_has_one_configuration_and_no_given_outcomes(self):
        rec = self.cal.records[0]
        out0 = self.FIXED.evaluate_exact(rec.world, rec.context, rec.encoding, self.C.ALPHA0, 0)
        doc = RV.blind_input(rec, out0[0], True)
        self.assertEqual((doc["role"], doc["alphas"], doc["ks"], list(doc["configs"])), ("calibration", [0.7], [0], ["0.7|0"]))
        self.assertNotIn("given_outcomes_g1_g6", doc)
        self.assertEqual(list(doc["calibration_configuration"]), [0.7, 0])
        json.dumps(RV.fr_json(doc), allow_nan=False)

    def test_the_run_results_carry_the_fields_the_comparison_reads(self):
        res = RV.fr_json(RV.run_results(self.rec, self.ev, {"F1": (True, "")}, self.cal.taus))
        self.assertEqual(set(res["f3"]), {"feasible", "pareto_front", "hypervolume", "outcomes", "t1_structure"})
        self.assertEqual(set(res["f3"]["outcomes"]), set(FC.OUTCOME_TESTS))
        self.assertEqual(set(res["f3"]["t1_structure"]), set(FC.T1_STRUCTURE_FIELDS))
        self.assertEqual(set(res["metrics_exact"]), {f"{a}|{k}" for a in self.C.ALPHAS for k in (0, 5, 10)})
        for m in res["metrics_exact"].values():
            self.assertEqual(set(m), set(FC.METRIC_TESTS))
            self.assertTrue(isinstance(m["n_q"], int) and not isinstance(m["n_q"], bool) and m["n_q"] >= 0)
        s = res["f3"]["t1_structure"]
        # types only: alpha levels are strings, never floats (no float is compared), and defined is a bool
        self.assertTrue(all(isinstance(a, str) for a in s["feasible_alphas"]))
        self.assertTrue(isinstance(s["defined"], bool))
        self.assertTrue(all(isinstance(s[k], (str, type(None))) for k in ("alpha_min", "alpha_max", "largest_increase")))
        self.assertTrue(isinstance(s["feasible_alphas"], list))

    def test_the_calibration_results_file_is_keyed_like_the_test_results(self):
        rec = self.cal.records[0]
        ex = self.FIXED.evaluate_exact(rec.world, rec.context, rec.encoding, self.C.ALPHA0, 0)[2]
        out = self.FIXED.evaluate_exact(rec.world, rec.context, rec.encoding, self.C.ALPHA0, 0)[0]
        n_q = V.decided_outside_count(rec.encoding.units, rec.context.vocabulary, out, self.C.ALPHA0)
        doc = RV.fr_json(RV.calibration_results(rec, {"F1": (True, "")}, ex, n_q))
        self.assertEqual(set(doc), {"world_seed", "controls", "metrics_exact"})
        self.assertEqual(list(doc["metrics_exact"]), ["0.7|0"])
        self.assertEqual(set(doc["metrics_exact"]["0.7|0"]), set(FC.METRIC_TESTS))
        self.assertTrue(isinstance(doc["metrics_exact"]["0.7|0"]["n_q"], int))


class StructureJsonTests(unittest.TestCase):
    def test_f3_structure_json_spells_alphas_as_config_keys(self):
        s = V.t1_structure([metrics_ex(i) for i in range(10)], TAUS, [0.6, 0.7], lambda lo, hi: 0)
        j = V.f3_structure_json(s)
        self.assertTrue(all(isinstance(a, str) for a in j["feasible_alphas"]))
        self.assertEqual(j["feasible_alphas"], [str(a) for a in s["feasible_alphas"]])
        self.assertEqual(j["alpha_min"], str(s["alpha_min"]))
        self.assertEqual(j["alpha_max"], "0.95")
        self.assertIn("0.9", j["feasible_alphas"])  # "0.9", not "0.90": the spelling of the configuration keys
        self.assertIsInstance(j["largest_increase"], str)
        undefined = V.f3_structure_json(V.t1_structure([metrics_ex(9, bad=True)] * 10, TAUS, [0.6], lambda lo, hi: 0))
        self.assertEqual((undefined["defined"], undefined["alpha_min"], undefined["alpha_max"], undefined["largest_increase"]),
                         (False, None, None, None))


def metrics_ex(i, bad=False):
    return metrics(i, 0, 1, 3, F(1, 10) if bad else F(9, 10))


if __name__ == "__main__":
    unittest.main()
