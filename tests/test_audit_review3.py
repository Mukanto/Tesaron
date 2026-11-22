"""Tests of the draft 5 repairs for blind review 3: line endings and clone reproducibility (R3-1), the F3 map from a field
to the tests it affects (R3-2), the extra F3 fields (R3-3), the held outputs and the rerun (R3-6), the runner residues
(R3-7), the extra F4 parts (R3-8) and the printed texts (R3-9, R3-5, R3-10)."""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from dataclasses import replace
from fractions import Fraction
from pathlib import Path
from types import SimpleNamespace as NS
from unittest import mock

from audit import checks as C
from audit import clone_verify, f3_compare, fidelity, prefreeze_check, run_v02
from audit import freeze as audit_freeze
from audit.cache import get_encoding
from audit.indep import (
    class_units,
    compare_class_units,
    compare_relation_units,
    independent_fit,
    relation_units,
)
from audit.indep.pcm_loop import min_pairwise_distance
from audit.seeds import seeder
from audit.worldset import generate_valid

ROOT = Path(__file__).resolve().parent.parent
SKIP_GIT = os.environ.get("TESARON_SKIP_GIT_TESTS") == "1"
F = Fraction


def _records(n=1):
    recs, _ = generate_valid(n, seeder("dev"), "world-test", "enc-test", "aux", build=get_encoding)
    return recs


class TempDirMixin:
    def make_tmp(self):
        (ROOT / "run_dev").mkdir(exist_ok=True)
        self.tmp = Path(tempfile.mkdtemp(dir=ROOT / "run_dev"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        return self.tmp


class GitRepoMixin(TempDirMixin):
    def make_repo(self, name="repo"):
        base = self.make_tmp()
        self.repo = base / name
        self.repo.mkdir()
        self.git("init", "-q", "-b", "main")
        return self.repo

    def git(self, *args, check=True):
        res = subprocess.run(
            ["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid", "-c", "commit.gpgsign=false", *args],
            cwd=self.repo, capture_output=True, text=True,
        )
        if check:
            self.assertEqual(res.returncode, 0, res.stderr)
        return res.stdout.strip()

    def write(self, rel, text, crlf=False):
        path = self.repo / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        data = text.encode("utf-8")
        path.write_bytes(data.replace(b"\n", b"\r\n") if crlf else data)

    def commit_all(self, message):
        self.git("add", "-A")
        self.git("commit", "-q", "-m", message)
        return self.git("rev-parse", "HEAD")


# ------------------------------------------------------------------------------------------ R3-1 line endings
class LineEndingTests(unittest.TestCase):
    def test_the_repository_fixes_lf_in_gitattributes(self):
        self.assertEqual((ROOT / ".gitattributes").read_bytes(), b"* text=auto eol=lf\n")

    def test_no_file_of_the_repository_contains_crlf(self):
        bad = []
        for folder, dirs, files in os.walk(ROOT):
            dirs[:] = [d for d in dirs if d not in (".git", "run_dev", "run_repro", "__pycache__")]
            for name in files:
                data = (Path(folder) / name).read_bytes()
                if b"\x00" not in data and b"\r\n" in data:
                    bad.append(str((Path(folder) / name).relative_to(ROOT)))
        self.assertEqual(bad, [])

    def test_the_freeze_docstring_carries_the_truth_gate_warning(self):
        self.assertIn("A tool that rewrites line endings", audit_freeze.__doc__)
        self.assertIn("autocrlf", audit_freeze.__doc__)
        self.assertIn("changes the\nhash", audit_freeze.__doc__)

    def test_certify_rewrites_a_certificate_with_lf_and_nothing_else(self):
        try:
            from audit.gate import certify
        except ModuleNotFoundError:
            self.skipTest("truth_gate is not importable")
        original = (ROOT / "audit" / "gate" / "g2.cert.json").read_bytes()
        tmp = ROOT / "run_dev" / "crlf_cert.json"
        (ROOT / "run_dev").mkdir(exist_ok=True)
        try:
            tmp.write_bytes(original.replace(b"\n", b"\r\n"))
            self.assertTrue(certify.rewrite_lf(tmp))
            self.assertEqual(tmp.read_bytes(), original)
            self.assertFalse(certify.rewrite_lf(tmp))  # idempotent
            self.assertFalse(certify.rewrite_lf(ROOT / "run_dev" / "does_not_exist.json"))
        finally:
            tmp.unlink(missing_ok=True)

    def test_the_certificates_still_verify_in_their_lf_form(self):
        try:
            import truth_gate  # noqa: F401
        except ModuleNotFoundError:
            self.skipTest("truth_gate is not importable")
        doc = json.loads((ROOT / "audit" / "gate" / "g2.cert.json").read_text(encoding="utf-8"))
        self.assertIn("body_sha256", doc)
        self.assertNotIn(b"\r", (ROOT / "audit" / "gate" / "g2.cert.json").read_bytes())

    def test_files_written_by_the_audit_code_are_written_with_lf(self):
        for rel, needle in (("audit/f4_prefreeze.py", 'newline="\\n"'), ("audit/design/draw_study.py", 'newline="\\n"'),
                            ("audit/gate/certify.py", "newline=chr(10)"), ("audit/f3_compare.py", 'newline="\\n"'),
                            ("audit/run_v02.py", 'newline="\\n"'), ("audit/freeze.py", 'newline="\\n"')):
            text = (ROOT / rel).read_text(encoding="utf-8")
            self.assertIn(needle, text, rel)
        for rel in ("audit/f4_prefreeze.py", "audit/design/draw_study.py", "audit/gate/certify.py"):
            self.assertNotIn(".write_text(json", (ROOT / rel).read_text(encoding="utf-8"), rel)

    def test_f4_prefreeze_writes_lf_bytes(self):
        from audit import f4_prefreeze

        tmp = ROOT / "run_dev" / "f4_lf_test.json"
        (ROOT / "run_dev").mkdir(exist_ok=True)
        try:
            with mock.patch.object(f4_prefreeze, "OUT", tmp), mock.patch.object(f4_prefreeze, "N_WORLDS", 2):
                self.assertEqual(f4_prefreeze.main([]), 0)
            data = tmp.read_bytes()
            self.assertNotIn(b"\r", data)
            self.assertTrue(data.endswith(b"}\n"))
        finally:
            tmp.unlink(missing_ok=True)


@unittest.skipIf(SKIP_GIT, "TESARON_SKIP_GIT_TESTS=1")
class StagedBlobTests(GitRepoMixin, unittest.TestCase):
    PATHS = ("audit", "tesaron")

    def setUp(self):
        self.make_repo()
        self.git("config", "core.autocrlf", "true")  # the machine default that R3-1 is about
        self.write("audit/a.py", "a = 1\n")
        self.write("tesaron/b.py", "b = 2\n")
        self.git("add", "-A")

    def test_equal_bytes_pass(self):
        self.assertEqual(prefreeze_check.check_tracked_set(self.repo, self.PATHS), [])

    def test_a_working_file_with_crlf_against_an_lf_blob_is_found(self):
        self.write("audit/a.py", "a = 1\n", crlf=True)
        self.git("add", "-A")  # autocrlf stores LF
        self.assertEqual(
            prefreeze_check.check_tracked_set(self.repo, self.PATHS),
            ["the working file differs from its staged blob (line endings or an edit): audit/a.py"])

    def test_an_edit_after_staging_is_found(self):
        self.write("tesaron/b.py", "b = 3\n")
        problems = prefreeze_check.check_tracked_set(self.repo, self.PATHS)
        self.assertEqual(problems, ["the working file differs from its staged blob (line endings or an edit): tesaron/b.py"])

    def test_a_gitattributes_eol_lf_keeps_blob_and_working_bytes_equal(self):
        self.write(".gitattributes", "* text=auto eol=lf\n")
        self.git("add", "-A")
        self.assertEqual(prefreeze_check.check_tracked_set(self.repo, self.PATHS), [])

    def test_staged_blobs_parse_binary_empty_and_missing_paths(self):
        data = bytes(range(256)) + b"\n\r\n tail"
        (self.repo / "audit" / "bin.dat").write_bytes(data)
        (self.repo / "audit" / "empty.txt").write_bytes(b"")
        self.git("add", "-A")
        got = prefreeze_check.staged_blobs(self.repo, ["audit/bin.dat", "audit/empty.txt", "audit/nope.py", "audit/a.py"])
        self.assertEqual(got["audit/bin.dat"], data)
        self.assertEqual(got["audit/empty.txt"], b"")
        self.assertIsNone(got["audit/nope.py"])
        self.assertEqual(got["audit/a.py"], b"a = 1\n")


@unittest.skipIf(SKIP_GIT, "TESARON_SKIP_GIT_TESTS=1")
class CloneVerifyTests(GitRepoMixin, unittest.TestCase):
    def build(self, attributes=None):
        self.make_repo()
        for rel in ("audit/__init__.py", "audit/freeze.py"):  # the clone verifies with its own verifier
            self.write(rel, (ROOT / rel).read_text(encoding="utf-8"))
        self.write("tesaron/b.py", "b = 2\n")
        if attributes is not None:
            self.write(".gitattributes", attributes)
        (self.repo / "prereg").mkdir()
        audit_freeze.write_manifest([self.repo / "audit", self.repo / "tesaron"],
                                    str(self.repo / "prereg" / "FREEZE_v0.2.json"), readonly=False)
        return self.commit_all("freeze")

    def run_clone(self):
        shutil.rmtree(self.tmp / "clones", ignore_errors=True)
        (self.tmp / "clones").mkdir()
        result = clone_verify.clone_and_verify(self.repo, tmp_root=str(self.tmp / "clones"))
        self.assertEqual(list((self.tmp / "clones").iterdir()), [])  # the temporary folder is removed
        return result

    def test_a_clean_repository_verifies_and_the_clone_head_is_printed(self):
        head = self.build(attributes="* text=auto eol=lf\n")
        result = self.run_clone()
        self.assertTrue(result["ok"], result["output"])
        self.assertEqual(result["head"], head)
        self.assertIn("FREEZE OK", result["output"])
        out = clone_verify.main(["--repo", str(self.repo), "--tmp-root", str(self.tmp / "clones")])
        self.assertEqual(out, 0)

    def test_a_clone_that_converts_line_endings_does_not_verify(self):
        # the manifest was hashed over LF bytes, but a checkout that converts to CRLF gives other bytes
        self.build(attributes="* text eol=crlf\n")
        shutil.rmtree(self.repo / "audit" / "__pycache__", ignore_errors=True)
        manifest = json.loads((self.repo / "prereg" / "FREEZE_v0.2.json").read_text(encoding="utf-8"))
        self.assertIn("../tesaron/b.py", manifest["files"])
        result = self.run_clone()
        self.assertFalse(result["ok"])
        self.assertIn("MODIFIED", result["output"])
        self.assertEqual(clone_verify.main(["--repo", str(self.repo), "--tmp-root", str(self.tmp / "clones")]), 1)

    def test_a_file_changed_after_the_manifest_does_not_verify(self):
        self.build(attributes="* text=auto eol=lf\n")
        self.write("tesaron/b.py", "b = 3\n")
        self.commit_all("edit after the freeze")
        result = self.run_clone()
        self.assertFalse(result["ok"])
        self.assertIn("MODIFIED: ../tesaron/b.py", result["output"])

    def test_a_missing_manifest_is_an_error_not_a_pass(self):
        self.build(attributes="* text=auto eol=lf\n")
        self.git("rm", "-q", "prereg/FREEZE_v0.2.json")
        self.git("commit", "-q", "-m", "drop the manifest")
        result = self.run_clone()
        self.assertFalse(result["ok"])
        self.assertEqual(clone_verify.main(["--repo", str(self.repo), "--tmp-root", str(self.tmp / "clones")]), 2)

    def test_it_never_writes_into_the_repository(self):
        self.build(attributes="* text=auto eol=lf\n")
        before = self.git("status", "--porcelain", "--untracked-files=all")
        self.run_clone()
        self.assertEqual(self.git("status", "--porcelain", "--untracked-files=all"), before)


# ------------------------------------------------------------------------------------------ R3-2, R3-3 F3 map
class F3AffectedTestsTests(TempDirMixin, unittest.TestCase):
    def setUp(self):
        tmp = self.make_tmp()
        self.run_dir, self.agent_dir = tmp / "run", tmp / "agent"
        (self.run_dir / "outputs_results").mkdir(parents=True)
        self.agent_dir.mkdir()
        metrics = {"fidelity": "4/5", "deviation": "0/1", "consistency": "1/1", "uncertainty": "1/10", "new_true": "1/2",
                   "new_false": "0/1", "validation_agreement": "3/4", "boundary_share": "1/7"}
        self.run_world = {
            "metrics_exact": {"0.7|5": dict(metrics)},
            "f3": {"feasible": ["0.7|5"], "pareto_front": ["0.7|5"], "hypervolume": "3/8",
                   "outcomes": {"G7a": "HOLDS", "G8": "FAILS", "T-1": "UNDEFINED"},
                   "t1_structure": {"some_alpha_le_060_feasible": False, "alpha_ge_085_feasible": True,
                                    "t1_window_pairs": True, "t1_crossing_pairs": None, "t1_cross_080_085": False}},
        }
        self.agent_world = {"world_seed": 1, "metrics": {"0.7|5": dict(metrics)}, "feasible": ["0.7|5"],
                            "pareto_front": ["0.7|5"], "hypervolume": "3/8",
                            "outcomes": dict(self.run_world["f3"]["outcomes"]),
                            "t1_structure": dict(self.run_world["f3"]["t1_structure"])}
        self.rows = {t: {"test": t, "verdict": "HOLDS", "n_holds": 30, "n_fails": 0, "n_undefined": 0, "n_defined": 30,
                         "wilson_lower": None, "first_failing_world": None} for t in ("G1", "G7", "G8", "T-1")}

    def write(self, agent_world=None, rows=None, agent_rows=None):
        (self.run_dir / "outputs_results" / "1.json").write_text(json.dumps(self.run_world), encoding="utf-8")
        (self.run_dir / "VERDICTS.json").write_text(json.dumps({"table": {"rows": list((rows or self.rows).values())}}),
                                                    encoding="utf-8")
        (self.agent_dir / "1.json").write_text(json.dumps(agent_world or self.agent_world), encoding="utf-8")
        (self.agent_dir / "verdict_table.json").write_text(
            json.dumps({"rows": list((agent_rows or rows or self.rows).values())}), encoding="utf-8")

    def only(self, **changes):
        """One disagreement from changing the agent's world; returns (field, affected_tests, affects_verdict)."""
        world = json.loads(json.dumps(self.agent_world))
        for path, value in changes.items():
            node = world
            parts = path.split("/")
            for part in parts[:-1]:
                node = node[part]
            node[parts[-1]] = value
        self.write(agent_world=world)
        d = f3_compare.compare_dirs(self.run_dir, self.agent_dir)["disagreements"]
        self.assertEqual(len(d), 1, d)
        return d[0]["field"], d[0]["affected_tests"], d[0]["affects_verdict"]

    def test_the_fixed_map_for_the_metrics(self):
        for metric, tests in (("fidelity", ["G8", "T-1"]), ("deviation", ["G8", "T-1"]), ("consistency", ["T-1"]),
                              ("uncertainty", ["T-1"]), ("new_true", ["T-1"]), ("new_false", ["T-1"]),
                              ("validation_agreement", []), ("boundary_share", [])):
            field, affected, flag = self.only(**{f"metrics/0.7|5/{metric}": "9/10"})
            self.assertEqual((field, affected, flag), (f"metrics[0.7|5].{metric}", tests, bool(tests)), metric)

    def test_the_fixed_map_for_the_world_fields(self):
        self.assertEqual(self.only(feasible=[])[1:], (["T-1"], True))
        self.assertEqual(self.only(pareto_front=[])[1:], ([], False))
        self.assertEqual(self.only(hypervolume="1/2")[1:], ([], False))
        for test in ("G7a", "G8", "T-1"):
            self.assertEqual(self.only(**{f"outcomes/{test}": "HOLDS" if test != "G7a" else "FAILS"})[1:],
                             ([test], True), test)
        for name, value in (("some_alpha_le_060_feasible", True), ("alpha_ge_085_feasible", False),
                            ("t1_window_pairs", False), ("t1_crossing_pairs", True), ("t1_cross_080_085", None)):
            field, affected, flag = self.only(**{f"t1_structure/{name}": value})
            self.assertEqual((field, affected, flag), (f"t1_structure.{name}", ["T-1"], True), name)

    def test_a_type_difference_counts_and_extra_fields_change_nothing(self):
        self.assertEqual(self.only(**{"t1_structure/t1_window_pairs": "true"})[1:], (["T-1"], True))  # bool against str
        self.assertEqual(self.only(note="free text")[1:], ([], False))
        self.assertEqual(self.only(world_seed=2)[1:], (["G7a", "G8", "T-1"], True))

    def test_a_missing_or_extra_world_or_file_affects_every_test(self):
        self.write()
        (self.agent_dir / "1.json").unlink()
        d = f3_compare.compare_dirs(self.run_dir, self.agent_dir)["disagreements"]
        self.assertEqual([(x["field"], x["affected_tests"]) for x in d], [("world file", ["G7a", "G8", "T-1"])])
        self.write()
        (self.agent_dir / "7.json").write_text(json.dumps(self.agent_world), encoding="utf-8")
        d = f3_compare.compare_dirs(self.run_dir, self.agent_dir)["disagreements"]
        self.assertEqual([(x["world_seed"], x["affected_tests"]) for x in d], [("7", ["G7a", "G8", "T-1"])])
        self.write()
        (self.agent_dir / "7.json").unlink()
        (self.agent_dir / "verdict_table.json").unlink()
        d = f3_compare.compare_dirs(self.run_dir, self.agent_dir)["disagreements"]
        self.assertEqual([(x["field"], x["affected_tests"]) for x in d], [("verdict_table.json", ["G7a", "G8", "T-1"])])

    def test_a_missing_metric_configuration_affects_g8_and_t1(self):
        world = json.loads(json.dumps(self.agent_world))
        world["metrics"] = {}
        self.write(agent_world=world)
        d = f3_compare.compare_dirs(self.run_dir, self.agent_dir)["disagreements"]
        self.assertEqual([(x["field"], x["affected_tests"]) for x in d], [("metrics[0.7|5]", ["G8", "T-1"])])

    def test_every_verdict_table_row_maps_to_its_own_test(self):
        for test, label in (("G1", "G1"), ("G7", "G7a"), ("G8", "G8"), ("T-1", "T-1")):
            for field, value in (("verdict", "FAILS"), ("n_holds", 12), ("wilson_lower", "0.500"),
                                 ("first_failing_world", 1005)):
                agent_rows = json.loads(json.dumps(self.rows))
                agent_rows[test][field] = value
                self.write(rows=self.rows, agent_rows=agent_rows)
                d = f3_compare.compare_dirs(self.run_dir, self.agent_dir)["disagreements"]
                self.assertEqual(len(d), 1, (test, field))
                self.assertEqual(d[0]["field"], f"verdict_table[{test}].{field}")
                # G1 is not one of the three F3 outcome tests, but its row is still a verdict-table row
                self.assertEqual(d[0]["affected_tests"], [label])
                self.assertTrue(d[0]["affects_verdict"])

    def test_first_failing_world_is_compared_in_the_table(self):
        self.assertIn("first_failing_world", f3_compare.TABLE_FIELDS)
        rows = f3_compare.run_table_rows({"table": {"rows": [dict(self.rows["G8"], wilson_lower=0.5, first_failing_world=1003)]}})
        self.assertEqual(rows["G8"]["first_failing_world"], 1003)
        self.assertEqual(rows["G8"]["wilson_lower"], "0.500")

    def test_the_summary_counts_disagreements_per_test(self):
        world = json.loads(json.dumps(self.agent_world))
        world["metrics"]["0.7|5"]["fidelity"] = "9/10"  # G8 and T-1
        world["metrics"]["0.7|5"]["new_true"] = "9/10"  # T-1
        world["hypervolume"] = "1/9"  # none
        self.write(agent_world=world)
        doc = f3_compare.compare_dirs(self.run_dir, self.agent_dir)
        self.assertEqual(doc["n_disagreements"], 3)
        self.assertEqual(doc["n_affecting_verdict"], 2)
        self.assertEqual(doc["affected_tests"], ["G8", "T-1"])
        self.assertEqual(doc["n_disagreements_by_affected_test"], {"G7a": 0, "G8": 1, "T-1": 2})
        self.assertEqual(f3_compare.main([str(self.run_dir), str(self.agent_dir)]), 1)

    def test_schema_and_instructions_cover_the_new_fields(self):
        schema = json.loads((ROOT / "audit" / "f3" / "OUTPUT_SCHEMA.json").read_text(encoding="utf-8"))
        structure = schema["per_world_file"]["properties"]["t1_structure"]
        self.assertEqual(sorted(structure["required"]), sorted(f3_compare.T1_STRUCTURE_FIELDS))
        self.assertEqual(structure["properties"]["alpha_ge_085_feasible"], {"type": "boolean"})
        self.assertEqual(structure["properties"]["t1_window_pairs"], {"type": ["boolean", "null"]})
        row = schema["verdict_table_file"]["properties"]["rows"]["items"]
        self.assertEqual(sorted(row["required"]), sorted(("test",) + f3_compare.TABLE_FIELDS))
        self.assertEqual(row["properties"]["first_failing_world"]["type"], ["integer", "null"])
        text = (ROOT / "audit" / "f3" / "INSTRUCTIONS_F3.md").read_text(encoding="utf-8")
        for needle in ("draw_index", "first_failing_world", "SPEC.md` (sections 1, 5, 6, 7.1, 7.2, 8, 9 and 10)",
                       "oracle too has the same value in `full` and `verdict`", "t1_cross_080_085",
                       "NOTES.md is reported with F3_COMPARE.json and changes\nnothing"):
            self.assertIn(needle, text, needle)
        for name in f3_compare.T1_STRUCTURE_FIELDS:
            self.assertIn(name, text, name)

    def test_the_t1_structure_fields_of_the_run_match_the_comparison_list(self):
        self.assertEqual(tuple(run_v02.T1_STRUCTURE_FIELDS), tuple(f3_compare.T1_STRUCTURE_FIELDS))


# ------------------------------------------------------------------------------------------ R3-6 held outputs, rerun
class RunnerOutputTests(unittest.TestCase):
    def setUp(self):
        (ROOT / "run_dev").mkdir(exist_ok=True)
        self.out = ROOT / "run_dev"
        self.assertEqual(run_v02.main(["calibrate", "--dev", "--n-cal", "3"]), 0)
        for name in run_v02.OUTPUT_NAMES:
            if (self.out / name).is_dir():
                shutil.rmtree(self.out / name)
            else:
                (self.out / name).unlink(missing_ok=True)

    def run_test(self):
        return run_v02.main(["test", "--dev", "--n-test", "2", "--n-cal", "3", "--no-subprocess"])

    def test_nothing_is_written_when_the_table_cannot_be_built(self):
        with mock.patch.object(run_v02, "verdict_table", side_effect=RuntimeError("boom")):
            with self.assertRaises(RuntimeError):
                self.run_test()
        for name in run_v02.OUTPUT_NAMES:
            self.assertFalse((self.out / name).exists(), name)  # not even TEST_WORLDS.json

    def test_nothing_is_written_when_the_summary_cannot_be_built(self):
        with mock.patch.object(run_v02, "undefined_as_fails", side_effect=RuntimeError("boom")):
            with self.assertRaises(RuntimeError):
                self.run_test()
        for name in run_v02.OUTPUT_NAMES:
            self.assertFalse((self.out / name).exists(), name)

    def test_the_outputs_are_all_written_after_the_table_exists(self):
        order = []
        real_write, real_table = run_v02._write_json, run_v02.verdict_table

        def table(*a, **k):
            order.append("table")
            return real_table(*a, **k)

        def write(path, obj, overwrite):
            order.append("write")
            return real_write(path, obj, overwrite)

        with mock.patch.object(run_v02, "verdict_table", table), mock.patch.object(run_v02, "_write_json", write):
            self.assertEqual(self.run_test(), 0)
        self.assertEqual(order[0], "table")
        self.assertEqual(order.count("table"), 1)
        self.assertEqual(set(order[1:]), {"write"})
        self.assertGreaterEqual(len(order), 1 + 1 + 2 * 2 + 2)  # TEST_WORLDS, 2 x 2 per-world files, RESULTS, VERDICTS

    def test_a_real_run_refuses_to_overwrite_before_any_work(self):
        real_tau = run_v02.ExactTaus(F(4, 5), F(1, 20), F(9, 10), F(1, 2))
        for name in ("VERDICTS.json", "outputs_input", "STOPPED.json"):
            target = self.out / name
            if name.endswith(".json"):
                target.write_text("{}", encoding="utf-8")
            else:
                target.mkdir()
            with mock.patch.object(run_v02, "recheck_calibration", return_value=real_tau), \
                    mock.patch.object(run_v02, "generate_valid", side_effect=AssertionError("no work expected")):
                with self.assertRaises(run_v02.Refused) as cm:
                    run_v02.run_test("c" * 64, "s" * 64, self.out, False, 3, 2, False)
            self.assertIn(name, str(cm.exception))
            self.assertIn("never overwrites", str(cm.exception))
            if target.is_dir():
                target.rmdir()
            else:
                target.unlink()

    def test_the_blind_input_has_the_draw_index_and_the_table_has_first_failing_world(self):
        self.assertEqual(self.run_test(), 0)
        blinds = [json.loads(p.read_text()) for p in sorted((self.out / "outputs_input").glob("*.json"))]
        tests = json.loads((self.out / "TEST_WORLDS.json").read_text())["worlds"]
        for blind in blinds:
            draw = next(w["draw"] for w in tests if w["world_seed"] == blind["world_seed"])
            self.assertEqual(blind["draw_index"], draw)
        rows = json.loads((self.out / "VERDICTS.json").read_text())["table"]["rows"]
        for row in rows:
            self.assertIn("first_failing_world", row)
            self.assertTrue(row["first_failing_world"] is None or isinstance(row["first_failing_world"], int))
        results = json.loads(next((self.out / "outputs_results").glob("*.json")).read_text())
        structure = results["f3"]["t1_structure"]
        self.assertEqual(sorted(structure), sorted(f3_compare.T1_STRUCTURE_FIELDS))
        self.assertIs(structure["some_alpha_le_060_feasible"] in (True, False), True)

    def test_the_regenerated_calibration_worlds_must_equal_cal_worlds_json(self):
        cal_path, tau_path = self.out / "CAL_WORLDS.json", self.out / "TAU.json"
        cal = json.loads(cal_path.read_text(encoding="utf-8"))
        cal["worlds"][0]["world_hash"] = "0" * 64  # a changed world record ...
        cal_path.write_text(json.dumps(cal), encoding="utf-8")
        tau = json.loads(tau_path.read_text(encoding="utf-8"))
        tau["cal_worlds_sha256"] = run_v02._sha(cal_path)  # ... with the sha link kept consistent
        tau_path.write_text(json.dumps(tau), encoding="utf-8")
        self.assertEqual(self.run_test(), run_v02.EXIT_REFUSED)
        with self.assertRaises(run_v02.Refused) as cm:
            run_v02.recheck_calibration("dev", "dev", self.out, True, 3)
        self.assertIn("regenerated calibration worlds differ", str(cm.exception))
        # rejected draws are compared too
        self.assertEqual(run_v02.main(["calibrate", "--dev", "--n-cal", "3"]), 0)
        cal = json.loads(cal_path.read_text(encoding="utf-8"))
        cal["rejected_draws"] = cal["rejected_draws"] + [{"draw": 99, "world_seed": 1, "reason": "x"}]
        cal_path.write_text(json.dumps(cal), encoding="utf-8")
        tau = json.loads(tau_path.read_text(encoding="utf-8"))
        tau["cal_worlds_sha256"] = run_v02._sha(cal_path)
        tau_path.write_text(json.dumps(tau), encoding="utf-8")
        with self.assertRaises(run_v02.Refused):
            run_v02.recheck_calibration("dev", "dev", self.out, True, 3)
        self.assertEqual(run_v02.main(["calibrate", "--dev", "--n-cal", "3"]), 0)
        run_v02.recheck_calibration("dev", "dev", self.out, True, 3)  # the unmodified files pass

    def test_reproduce_is_not_a_development_command(self):
        self.assertEqual(run_v02.main(["reproduce", "--dev"]), run_v02.EXIT_USAGE)
        with mock.patch.object(run_v02, "check_versions", side_effect=run_v02.Refused("stop")):
            self.assertEqual(run_v02.main(["reproduce"]), run_v02.EXIT_REFUSED)


@unittest.skipIf(SKIP_GIT, "TESARON_SKIP_GIT_TESTS=1")
class ReproduceTests(GitRepoMixin, unittest.TestCase):
    def setUp(self):
        self.make_repo()
        self.write("run/VERDICTS.json", '{"verdict": "x"}\n')
        self.write("run/SALT.json", "{}\n")
        self.commit_all("result")
        self.calls = []

    def test_equal_files_are_reproduced_and_the_inputs_come_from_run(self):
        def rerun(core, salt, out, dev, n_cal, n_test, subprocess_checks, inputs=None):
            self.calls.append((core, salt, out.name, dev, n_cal, n_test, subprocess_checks, inputs.name))
            out.mkdir()
            (out / "VERDICTS.json").write_bytes((self.repo / "run" / "VERDICTS.json").read_bytes())

        info = run_v02.reproduce(self.repo, "core", "salt", test_fn=rerun)
        self.assertTrue(info["equal"])
        self.assertEqual(info["repro_sha256"], info["run_sha256"])
        self.assertEqual(self.calls, [("core", "salt", "run_repro", False, run_v02.N_CAL, run_v02.N_TEST, True, "run")])

    def test_different_bytes_are_not_reproduced(self):
        def rerun(core, salt, out, dev, n_cal, n_test, subprocess_checks, inputs=None):
            out.mkdir()
            (out / "VERDICTS.json").write_text('{"verdict": "y"}\n', encoding="utf-8")

        info = run_v02.reproduce(self.repo, "core", "salt", test_fn=rerun)
        self.assertFalse(info["equal"])
        self.assertNotEqual(info["repro_sha256"], info["run_sha256"])

    def test_a_line_ending_difference_is_a_difference(self):
        def rerun(core, salt, out, dev, n_cal, n_test, subprocess_checks, inputs=None):
            out.mkdir()
            (out / "VERDICTS.json").write_bytes(b'{"verdict": "x"}\r\n')  # git diff would hide this

        self.assertFalse(run_v02.reproduce(self.repo, "c", "s", test_fn=rerun)["equal"])

    def test_it_refuses_if_run_repro_exists(self):
        (self.repo / "run_repro").mkdir()
        with self.assertRaises(run_v02.Refused) as cm:
            run_v02.reproduce(self.repo, "c", "s", test_fn=lambda *a, **k: self.fail("must not run"))
        self.assertIn("already exists", str(cm.exception))

    def test_it_refuses_if_the_committed_verdicts_are_modified_or_missing(self):
        self.write("run/VERDICTS.json", '{"verdict": "edited"}\n')
        with self.assertRaises(run_v02.Refused):
            run_v02.reproduce(self.repo, "c", "s", test_fn=lambda *a, **k: self.fail("must not run"))
        self.git("checkout", "--", "run/VERDICTS.json")
        self.git("rm", "-q", "-f", "run/VERDICTS.json")
        self.git("commit", "-q", "-m", "drop")
        with self.assertRaises(run_v02.Refused):
            run_v02.reproduce(self.repo, "c", "s", test_fn=lambda *a, **k: self.fail("must not run"))


# ------------------------------------------------------------------------------------------ R3-7 runner residues
@unittest.skipIf(SKIP_GIT, "TESARON_SKIP_GIT_TESTS=1")
class RunnerResidueTests(GitRepoMixin, unittest.TestCase):
    SALT = "ab" * 32

    def setUp(self):
        self.make_repo()

    def test_unique_commit_uses_the_full_history(self):
        self.write("f.txt", "1\n")
        self.commit_all("A")
        self.git("checkout", "-q", "-b", "side")
        self.write("f.txt", "2\n")
        self.commit_all("B touches f on the side branch")
        self.git("checkout", "-q", "main")
        self.write("g.txt", "g\n")
        self.commit_all("C")
        self.git("merge", "-q", "-s", "ours", "side", "-m", "merge keeping main's content")
        simplified = self.git("log", "--format=%H", "--", "f.txt").split()
        self.assertEqual(len(simplified), 1)  # default history simplification hides the side-branch commit
        with self.assertRaises(run_v02.Refused) as cm:
            run_v02.unique_commit(self.repo, "f.txt")
        self.assertIn("commits touch f.txt", str(cm.exception))

    def freeze(self, paths_to_freeze=("audit", "tesaron"), extra=()):
        self.write("audit/a.py", "a = 1\n")
        self.write("tesaron/b.py", "b = 2\n")
        self.write("tests/t.py", "t = 3\n")
        self.write("SPEC.md", "spec\n")
        for rel in extra:
            self.write(rel, "x\n")
        (self.repo / "prereg").mkdir(exist_ok=True)
        manifest = audit_freeze.write_manifest([self.repo / p for p in paths_to_freeze],
                                               str(self.repo / "prereg" / "FREEZE_v0.2.json"), readonly=False)
        commit = self.commit_all("freeze")
        self.git("update-ref", "refs/remotes/origin/main", commit)
        return commit, manifest["core_sha256"]

    def with_salt(self, commit, core):
        self.write("run/SALT.json", json.dumps({"salt": self.SALT, "freeze_commit": commit, "core_sha256": core}))
        c = self.commit_all("salt")
        self.git("update-ref", "refs/remotes/origin/main", c)

    def test_a_manifest_from_a_subset_of_the_paths_is_refused(self):
        commit, core = self.freeze(paths_to_freeze=("audit", "tesaron"))  # tests/ and SPEC.md are tracked but not frozen
        self.with_salt(commit, core)
        with self.assertRaises(run_v02.Refused) as cm:
            run_v02.check_freeze_and_salt(self.repo, core)
        self.assertIn("does not cover the frozen tree", str(cm.exception))
        self.assertIn("tracked but not in the manifest", str(cm.exception))

    def test_the_full_set_of_manifest_paths_is_accepted(self):
        commit, core = self.freeze(paths_to_freeze=("audit", "tesaron", "tests", "SPEC.md"))
        self.with_salt(commit, core)
        self.assertEqual(run_v02.check_freeze_and_salt(self.repo, core)[0], commit)

    def test_a_manifest_that_lists_a_file_outside_the_paths_is_refused(self):
        commit, core = self.freeze(paths_to_freeze=("audit", "tesaron", "tests", "SPEC.md", "extra.txt"),
                                   extra=("extra.txt",))
        self.with_salt(commit, core)
        with self.assertRaises(run_v02.Refused) as cm:
            run_v02.check_freeze_and_salt(self.repo, core)
        self.assertIn("in the manifest but not tracked under the manifest paths", str(cm.exception))

    def test_a_tracked_file_added_under_a_manifest_path_after_the_manifest_is_refused(self):
        commit, core = self.freeze(paths_to_freeze=("audit", "tesaron", "tests", "SPEC.md"))
        # the freeze commit itself must hold the file: put it in the same commit by amending
        self.write("audit/forgotten.py", "x = 1\n")
        self.git("add", "-A")
        self.git("commit", "-q", "--amend", "-m", "freeze")
        commit = self.git("rev-parse", "HEAD")
        self.git("update-ref", "refs/remotes/origin/main", commit)
        self.with_salt(commit, core)
        with self.assertRaises(run_v02.Refused) as cm:
            run_v02.check_freeze_and_salt(self.repo, core)
        self.assertIn("audit/forgotten.py", str(cm.exception))

    def test_the_default_manifest_paths_are_those_of_prereg_section_9(self):
        self.assertEqual(tuple(prefreeze_check.MANIFEST_PATHS), (
            "prereg/PREREG_v0.2.md", "SPEC.md", "tesaron", "audit", "prereg/F4_PREFREEZE.json",
            "prereg/DRAW_STUDY.json", "pyproject.toml", "tests"))


# ------------------------------------------------------------------------------------------ R3-8 F4 additions
class ExtendedF4Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rec = _records(1)[0]

    def test_the_independent_fit_agrees_with_the_encoder_flags(self):
        enc = self.rec.encoding
        centers, iterations, converged, degenerate = independent_fit(self.rec.world, self.rec.context, enc.derive_ids)
        self.assertEqual((iterations, converged, degenerate), (enc.fit.n_iter, enc.fit.converged, enc.fit.degenerate))
        d = fidelity.f4_details(self.rec)
        self.assertTrue(d["pcm_flags_equal"] and d["class_units_equal"] and d["ok"], d["problems"])
        self.assertGreater(d["n_class_units"], 0)

    def test_the_degeneracy_check_is_recomputed_from_the_spec_rule(self):
        row = lambda i, x: NS(row_id=f"f{i:03d}", entity="e", x=x)
        world = NS(feature_rows=[row(i, (0.01 * i, 0.0)) for i in range(10)])
        ctx = NS(prototypes=((0.0, 0.0), (10.0, 0.0)), eta=(1.0, 1.0), m=2.0, max_iter=200, tol=1e-9)
        centers, iterations, converged, degenerate = independent_fit(world, ctx, [r.row_id for r in world.feature_rows])
        self.assertTrue(converged)
        self.assertTrue(degenerate)  # both centers collapse onto the points: closer than half the prototype distance
        self.assertLess(min_pairwise_distance(centers), 0.5 * min_pairwise_distance([[0.0, 0.0], [10.0, 0.0]]))
        spread = NS(feature_rows=[row(i, (0.0, 0.0)) for i in range(5)] + [row(i + 5, (10.0, 0.0)) for i in range(5)])
        ctx2 = NS(prototypes=((0.0, 0.0), (10.0, 0.0)), eta=(1.0, 1.0), m=2.0, max_iter=200, tol=1e-9)
        self.assertFalse(independent_fit(spread, ctx2, [r.row_id for r in spread.feature_rows])[3])
        self.assertAlmostEqual(min_pairwise_distance([[0.0, 0.0], [3.0, 4.0], [10.0, 10.0]]), 5.0)

    def test_f4_detects_a_wrong_pcm_flag_or_iteration_count(self):
        enc = self.rec.encoding
        for change in ({"n_iter": enc.fit.n_iter + 1}, {"converged": not enc.fit.converged},
                       {"degenerate": not enc.fit.degenerate}):
            rec = replace(self.rec, encoding=replace(enc, fit=replace(enc.fit, **change)))
            ok, detail = fidelity.f4_check(rec)
            self.assertFalse(ok, change)
            self.assertIn("PCM flags", detail)

    def test_f4_detects_a_wrong_class_unit_status_or_provenance(self):
        from tesaron.enums import ComputationalStatus

        enc = self.rec.encoding
        atom = next(a for a in enc.units if a.pred.startswith("c"))
        units = dict(enc.units)
        units[atom] = replace(enc.units[atom], status=ComputationalStatus.NOT_COMPUTED)
        ok, detail = fidelity.f4_check(replace(self.rec, encoding=replace(enc, units=units)))
        self.assertFalse(ok)
        self.assertIn("class units", detail)
        units = dict(enc.units)
        units[atom] = replace(enc.units[atom], provenance=tuple(enc.units[atom].provenance[:-1]))
        self.assertFalse(fidelity.f4_check(replace(self.rec, encoding=replace(enc, units=units)))[0])
        units = {a: u for a, u in enc.units.items() if a != atom}  # a missing class unit
        self.assertFalse(fidelity.f4_check(replace(self.rec, encoding=replace(enc, units=units)))[0])

    def test_class_units_follow_spec_section_5_step_5(self):
        enc = self.rec.encoding
        expected = class_units(self.rec.world, enc.derive_ids, self.rec.world.params.n_classes, True)
        self.assertEqual(compare_class_units(self.rec.world, enc.derive_ids, self.rec.world.params.n_classes, True,
                                             enc.units), [])
        entities = {a.args[0] for a in enc.units if a.pred.startswith("c")}
        self.assertEqual({e for (_, (e,)) in expected}, entities)  # only entities with a D_derive feature row
        self.assertTrue(all(status == "OBSERVED" for _, status in expected.values()))
        self.assertTrue(all(s == "NOT_COMPUTED" for _, s in class_units(
            self.rec.world, enc.derive_ids, self.rec.world.params.n_classes, False).values()))

    def test_the_relation_support_is_taken_from_the_world_not_from_the_context(self):
        enc, ctx = self.rec.encoding, self.rec.context
        from tesaron.degrees import Membership
        from tesaron.encoder import encode_from_rows

        halved = replace(ctx, support={k: Membership(v.value * 0.5) for k, v in ctx.support.items()})
        enc2 = encode_from_rows(self.rec.world, halved, enc.derive_ids, enc.validate_ids)
        # the independent units ignore ctx.support (they read world.source_reliabilities), so the tampered encoder differs
        problems = compare_relation_units(self.rec.world, enc.derive_ids, ctx.vocabulary, enc2.units)
        self.assertTrue(problems)
        self.assertEqual(compare_relation_units(self.rec.world, enc.derive_ids, ctx.vocabulary, enc.units), [])
        rel = relation_units(self.rec.world, enc.derive_ids, ctx.vocabulary)
        reliabilities = {p.value for p in self.rec.world.source_reliabilities.values()}
        self.assertTrue({mu for mu_pos, mu_neg, _ in rel.values() for mu in (mu_pos, mu_neg)} <= reliabilities | {0.0})
        rec = replace(self.rec, context=halved, encoding=enc2)
        self.assertFalse(fidelity.f4_check(rec)[0])

    def test_the_prefreeze_file_records_the_new_comparisons(self):
        doc = json.loads((ROOT / "prereg" / "F4_PREFREEZE.json").read_text(encoding="utf-8"))
        for key in ("f4_pcm_flags_all_equal", "f4_class_units_all_equal", "every_comparison_equal"):
            self.assertIs(doc[key], True, key)
        self.assertTrue(all(w["f4"]["pcm_flags_equal"] and w["f4"]["class_units_equal"] for w in doc["worlds"]))


# ------------------------------------------------------------------------------------------ R3-9, R3-10 texts
class TextTests(unittest.TestCase):
    def test_readme_describes_every_audit_module_of_this_draft(self):
        text = (ROOT / "audit" / "README.md").read_text(encoding="utf-8")
        for needle in ("DRAFT 5", "indep/abduction.py", "indep/units.py", "indep/pcm_loop.py", "indep/h_closure.py",
                       "fidelity.py", "f3/INSTRUCTIONS_F3.md", "f3/OUTPUT_SCHEMA.json", "f3_compare.py",
                       "prefreeze_check.py", "clone_verify.py", "design/draw_study.py", "reproduce", "LF"):
            self.assertIn(needle, text, needle)
        listed = set(re.findall(r"`([A-Za-z0-9_/]+\.py)`", text))
        for path in sorted((ROOT / "audit").glob("*.py")):
            if path.name != "__init__.py":
                self.assertTrue(path.name in text or f"{path.stem}/" in text, path.name)
        self.assertIn("run_v02.py", listed)

    def test_gitignore_has_run_repro(self):
        self.assertIn("run_repro/", (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines())


if __name__ == "__main__":
    unittest.main()
