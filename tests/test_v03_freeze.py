"""v0.3's freeze writer and verifier, pre-freeze check, clone verifier and gate driver (PREREG_v0.3 sections 6.3, 8 and 9), on
synthetic trees in temporary folders. Nothing here touches the real repository's git state; the tests that need git build their
own scratch repository (and are skipped with TESARON_SKIP_GIT_TESTS=1, like the v0.2 git tests)."""

import json
import os
import re
import shutil
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

from audit import freeze as base_freeze
from audit.v03 import clone_verify as CV
from audit.v03 import freeze as FZ
from audit.v03 import prefreeze_check as PC
from audit.v03.gate import common as GC

ROOT = Path(__file__).resolve().parent.parent
SKIP_GIT = os.environ.get("TESARON_SKIP_GIT_TESTS") == "1"
PREREG = ROOT / "prereg" / "PREREG_v0.3.md"
SPEC = ROOT / "SPEC_v0.3.md"


def rmtree(path):
    def onerror(func, p, _exc):
        os.chmod(p, stat.S_IWRITE)
        func(p)

    shutil.rmtree(path, onerror=onerror)


def put(root: Path, rel: str, text: str = "x\n"):
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.encode("utf-8"))
    return path


def mini_tree(root: Path):
    """A small tree with the PREREG section 9 layout."""
    for rel in ("prereg/PREREG_v0.3.md", "SPEC.md", "SPEC_v0.3.md", "pyproject.toml", "tesaron/a.py", "tesaron/sub/b.py",
                "audit/c.py", "audit/v03/d.py", "tests/test_e.py", "prereg/v03/S1.json", "prereg/v03/S2.json"):
        put(root, rel, f"{rel}\n")
    # not frozen: the freeze record, the reviews, run/, README, a nested json, caches
    for rel in ("prereg/v03/FREEZE_RECORD.md", "prereg/v03/reviews/r1/report.json", "prereg/v03/reviews/notes.md",
                "run/v03/SALT.json", "README.md", "LICENSE", "prereg/PREREG_v0.2.md", "prereg/FREEZE_v0.2.json",
                "audit/__pycache__/x.cpython-314.pyc", "tesaron/__pycache__/y.pyc"):
        put(root, rel, f"{rel}\n")


class ManifestFilesTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(rmtree, self.tmp)
        self.root = Path(self.tmp)
        mini_tree(self.root)

    def test_the_walk_is_the_prereg_section_9_list(self):
        self.assertEqual(FZ.manifest_files(self.root), [
            "SPEC.md", "SPEC_v0.3.md", "audit/c.py", "audit/v03/d.py", "prereg/PREREG_v0.3.md", "prereg/v03/S1.json",
            "prereg/v03/S2.json", "pyproject.toml", "tesaron/a.py", "tesaron/sub/b.py", "tests/test_e.py"])

    def test_the_manifest_itself_and_nested_json_are_not_listed(self):
        put(self.root, FZ.MANIFEST_REL, "{}")
        put(self.root, "prereg/v03/other.txt")
        self.assertNotIn(FZ.MANIFEST_REL, FZ.manifest_files(self.root))
        self.assertFalse(FZ.is_study_json("prereg/v03/reviews/r1/report.json"))
        self.assertFalse(FZ.is_study_json(FZ.MANIFEST_REL))
        self.assertTrue(FZ.is_study_json("prereg/v03/F4_PREFREEZE.json"))

    def test_a_missing_path_is_an_error(self):
        (self.root / "SPEC_v0.3.md").unlink()
        with self.assertRaises(FileNotFoundError):
            FZ.manifest_files(self.root)

    def test_write_and_verify_use_the_v02_algorithm(self):
        manifest = FZ.write(self.root, readonly=False)
        path = self.root / FZ.MANIFEST_REL
        self.assertEqual(manifest["freeze_format"], 1)
        self.assertEqual(manifest["algorithm"], "sha256")
        self.assertEqual(manifest["core_sha256"], base_freeze.core_hash(manifest["files"]))
        # paths are relative to the manifest's folder prereg/v03/
        self.assertIn("../../audit/c.py", manifest["files"])
        self.assertIn("S1.json", manifest["files"])
        self.assertIn("../PREREG_v0.3.md", manifest["files"])
        self.assertEqual(len(manifest["files"]), 11)
        self.assertNotIn(b"\r", path.read_bytes())  # LF
        problems, _ = FZ.verify(self.root, coverage=True)
        self.assertEqual(problems, [])
        self.assertEqual(FZ.main(["verify", "--repo", str(self.root), "--coverage"]), 0)

    def test_write_refuses_to_overwrite(self):
        FZ.write(self.root, readonly=False)
        with self.assertRaises(FileExistsError):
            FZ.write(self.root, readonly=False)
        self.assertEqual(FZ.main(["write", "--no-readonly", "--repo", str(self.root)]), 2)

    def test_verify_finds_a_changed_missing_and_added_file(self):
        FZ.write(self.root, readonly=False)
        (self.root / "audit" / "c.py").write_text("changed\n")
        (self.root / "tests" / "test_e.py").unlink()
        put(self.root, "tests/test_new.py")
        problems, _ = FZ.verify(self.root, coverage=True)
        self.assertIn("MODIFIED: ../../audit/c.py", problems)
        self.assertIn("MISSING: ../../tests/test_e.py", problems)
        self.assertIn("NOT IN THE MANIFEST: tests/test_new.py", problems)
        self.assertIn("IN THE MANIFEST BUT NOT FOUND BY THE WALK: tests/test_e.py", problems)
        self.assertEqual(FZ.main(["verify", "--repo", str(self.root)]), 1)

    def test_the_default_writer_makes_the_files_read_only(self):
        FZ.write(self.root)
        self.assertFalse(os.stat(self.root / "SPEC.md").st_mode & stat.S_IWUSR)
        self.assertFalse(os.stat(self.root / FZ.MANIFEST_REL).st_mode & stat.S_IWUSR)
        self.assertTrue(os.stat(self.root / "README.md").st_mode & stat.S_IWUSR)  # outside the manifest

    def test_the_real_paths(self):
        self.assertEqual(FZ.MANIFEST_REL, "prereg/v03/FREEZE_v0.3.json")
        self.assertEqual(FZ.FROZEN_PATHS, ("prereg/PREREG_v0.3.md", "SPEC.md", "SPEC_v0.3.md", "tesaron", "audit",
                                           "pyproject.toml", "tests"))
        files = FZ.manifest_files(ROOT)
        self.assertTrue(all(not f.startswith("run/") and "__pycache__" not in f for f in files))
        self.assertIn("audit/v03/prefreeze_check.py", files)
        self.assertNotIn("README.md", files)

    def test_the_docstring_lists_every_study_of_section_9(self):  # R2-10
        doc = " ".join(FZ.__doc__.split())
        for study in ("the design studies S1, S1b and S2", "the power study", "the all_true study", "the n_q study", "and F4"):
            self.assertIn(study, doc)
        text = " ".join(PREREG.read_text(encoding="utf-8").split())
        self.assertIn("the design studies S1, S1b and S2, the power study, the all_true study, the n_q study, and F4", text)


class StatusLineTests(unittest.TestCase):
    """The status check covers the pre-registration and the spec (R1-6): each has its own frozen line on line 3."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(rmtree, self.tmp)
        self.root = Path(self.tmp)

    def prereg(self, lines):
        put(self.root, PC.PREREG_REL, "\n".join(lines) + "\n")

    def spec(self, lines):
        put(self.root, PC.SPEC_REL, "\n".join(lines) + "\n")

    def frozen(self):
        return ["# Pre-registration: Tesaron v0.3", "", PC.FROZEN_STATUS_LINE, "", "- **Author:** A.", "- **Date:** d."] + \
               ["body"] * 12

    def frozen_spec(self):
        return ["# Tesaron: spec amendments for v0.3", "", PC.SPEC_FROZEN_STATUS_LINE, "- `SPEC.md` stays.", "", "more"] + \
               ["body"] * 12

    def both(self):
        self.prereg(self.frozen())
        self.spec(self.frozen_spec())

    def test_the_constants_are_the_texts_of_section_8_step_6(self):
        text = " ".join(PREREG.read_text(encoding="utf-8").split())
        self.assertIn(f'exactly: "{PC.FROZEN_STATUS_LINE}"', text)
        self.assertIn(f'exactly, by: "{PC.SPEC_FROZEN_STATUS_LINE}"', text)  # R1-6
        self.assertIn("neither \"not frozen\" (in any case) nor \"DRAFT\" (in capitals)", text)
        self.assertIn("the third line of this file and of `SPEC_v0.3.md` is the frozen status line of §8, step 6", text)
        self.assertNotEqual(PC.FROZEN_STATUS_LINE, PC.SPEC_FROZEN_STATUS_LINE)  # each file has its own line

    # Draft headers stored here, so that the tests do not depend on the stage of the real files (R2-2): the real files
    # are frozen with step 6 of PREREG section 8, and the frozen suite has to pass on the frozen tree.
    DRAFT_PREREG_HEADER = [
        "# Pre-registration: Tesaron v0.3", "", "**Status: DRAFT 3, not frozen.**",
        "- It includes the author's v0.3 decisions.", "- Nothing in this file is final until the freeze in section 9.", "",
        "- **Author:** A.", "- **Date written:** d."]
    DRAFT_SPEC_HEADER = [
        "# Tesaron: spec amendments for v0.3", "", "**Status: DRAFT 1, not frozen** (2026-11-23).",
        "- `SPEC.md`, as frozen in v0.2, stays the authoritative implementation spec."]

    def test_the_draft_headers_are_refused(self):
        self.prereg(self.DRAFT_PREREG_HEADER + ["body"] * 12)
        self.spec(self.frozen_spec())
        problems = PC.check_status_line(self.root)
        self.assertTrue(any("is not the frozen status line" in p and PC.PREREG_REL in p for p in problems))
        self.assertTrue(any('contains "DRAFT"' in p for p in problems))
        self.assertTrue(any('contains "not frozen"' in p for p in problems))
        self.assertFalse(any(PC.SPEC_REL in p for p in problems))  # the spec is fine
        # the draft SPEC header alone is refused too, whatever the pre-registration says
        self.prereg(self.frozen())
        self.spec(self.DRAFT_SPEC_HEADER + ["body"] * 12)
        problems = PC.check_status_line(self.root)
        self.assertTrue(problems)
        self.assertTrue(all(PC.SPEC_REL in p for p in problems))
        self.assertTrue(any("is not the frozen status line" in p for p in problems))
        self.assertTrue(any('contains "DRAFT"' in p for p in problems))
        self.assertTrue(any('contains "not frozen"' in p for p in problems))

    def test_the_real_files_are_judged_by_their_own_line_3(self):
        """Independent of the stage of the working tree (R2-2): a real file whose line 3 is its frozen line has no problem,
        and every other state has at least one (it is a draft). Each file is judged on its own."""
        for rel, path, frozen in ((PC.PREREG_REL, PREREG, PC.FROZEN_STATUS_LINE), (PC.SPEC_REL, SPEC, PC.SPEC_FROZEN_STATUS_LINE)):
            lines = path.read_text(encoding="utf-8").split("\n")
            problems = [p for p in PC.check_status_line(ROOT) if rel in p]
            if lines[2] == frozen:
                self.assertEqual(problems, [], rel)
            else:
                self.assertTrue(problems, rel)
        self.both()
        self.assertEqual(PC.check_status_line(self.root), [])

    def test_each_file_needs_its_own_line(self):
        self.prereg(self.frozen())
        lines = self.frozen_spec()
        lines[2] = PC.FROZEN_STATUS_LINE  # the pre-registration's line in the spec
        self.spec(lines)
        self.assertTrue(any(PC.SPEC_REL in p for p in PC.check_status_line(self.root)))
        self.both()
        self.prereg(self.frozen()[:2] + [PC.SPEC_FROZEN_STATUS_LINE] + self.frozen()[3:])  # the spec's line in the prereg
        self.assertTrue(any(PC.PREREG_REL in p for p in PC.check_status_line(self.root)))

    def test_the_line_must_be_line_3_and_exact(self):
        for rel_set, lines_fn, frozen_line in ((self.prereg, self.frozen, PC.FROZEN_STATUS_LINE),
                                                (self.spec, self.frozen_spec, PC.SPEC_FROZEN_STATUS_LINE)):
            self.both()
            lines = lines_fn()
            rel_set([lines[2]] + lines[:2] + lines[3:])
            self.assertTrue(PC.check_status_line(self.root))
            self.both()
            rel_set(lines_fn()[:2] + [frozen_line + " "] + lines_fn()[3:])
            self.assertTrue(PC.check_status_line(self.root))
            self.both()
            rel_set(["a"])
            self.assertTrue(PC.check_status_line(self.root))

    def test_the_banned_words_and_their_casing_in_both_files(self):
        for put_fn, lines_fn in ((self.prereg, self.frozen), (self.spec, self.frozen_spec)):
            for text, bad in (("The design is NOT FROZEN yet", True), ("not frozen", True), ("DRAFT 2", True),
                              ("Design and draft: Claude", False), ("(draft 1)", False)):
                self.both()
                lines = lines_fn()
                lines[4] = text
                put_fn(lines)
                self.assertEqual(bool(PC.check_status_line(self.root)), bad, text)

    def test_the_window_is_the_first_12_lines_in_both_files(self):
        for put_fn, lines_fn, rel in ((self.prereg, self.frozen, PC.PREREG_REL), (self.spec, self.frozen_spec, PC.SPEC_REL)):
            self.both()
            lines = lines_fn()
            lines[12] = "DRAFT"  # line 13
            put_fn(lines)
            self.assertEqual(PC.check_status_line(self.root), [])
            lines[11] = "DRAFT"  # line 12
            put_fn(lines)
            problems = PC.check_status_line(self.root)
            self.assertEqual(len(problems), 1)
            self.assertIn(rel, problems[0])

    def test_a_missing_file_is_a_problem(self):
        self.assertEqual(len(PC.check_status_line(self.root)), 2)  # neither file exists
        self.prereg(self.frozen())
        self.assertEqual(len(PC.check_status_line(self.root)), 1)  # the spec is missing
        self.assertIn(PC.SPEC_REL, PC.check_status_line(self.root)[0])


class GateToolTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(rmtree, self.tmp)
        self.root = Path(self.tmp)
        mini_tree(self.root)
        self.body = {gid: f"{i:064x}" for i, gid in enumerate(PC.GATE_IDS)}
        for gid, h in self.body.items():  # the committed certificates
            put(self.root, f"audit/v03/gate/{gid}.cert.json", json.dumps({"body": {"verdict": "FALSIFIABLE"}, "body_sha256": h}))

    def certs(self, **override):
        """The "certificates" table of a good GATE_TOOL.json; override maps an id to a dict of changes (or None to drop it)."""
        out = {gid: {"verdict": "FALSIFIABLE", "body_sha256": self.body[gid], "flags": [], "verify_exit": 0}
               for gid in PC.GATE_IDS}
        for gid, change in override.items():
            if change is None:
                del out[gid]
            else:
                out[gid].update(change)
        return out

    def write_tool(self, tag="v0.5.1", **override):
        files = PC.gate_file_hashes(self.root)
        put(self.root, PC.GATE_TOOL_REL, json.dumps({"files": files, "tag": tag, "certificates": self.certs(**override)}))
        return files

    def test_it_holds_when_the_hashes_are_the_current_ones(self):
        files = self.write_tool()
        self.assertEqual(PC.check_gate_tool(self.root), [])
        self.assertNotIn(PC.GATE_TOOL_REL, files)  # the table never lists GATE_TOOL.json itself
        self.assertEqual(sorted(files), sorted(["audit/c.py", "audit/v03/d.py", "tesaron/a.py", "tesaron/sub/b.py",
                                                *(f"audit/v03/gate/{g}.cert.json" for g in PC.GATE_IDS)]))

    def test_a_changed_added_or_removed_file_is_listed(self):
        self.write_tool()
        (self.root / "audit" / "c.py").write_text("changed\n")
        put(self.root, "audit/v03/new.py")
        (self.root / "tesaron" / "a.py").unlink()
        problems = PC.check_gate_tool(self.root)
        self.assertEqual(sorted(problems), sorted([
            "changed since the gate ran: audit/c.py", "file not in GATE_TOOL: audit/v03/new.py",
            "GATE_TOOL lists a file that is gone: tesaron/a.py"]))

    def test_a_quick_certificate_is_not_hashed_but_a_certificate_is(self):
        self.write_tool()
        put(self.root, "audit/v03/gate/g1.quick.cert.json")
        self.assertEqual(PC.check_gate_tool(self.root), [])
        put(self.root, "audit/v03/gate/g9.cert.json")
        self.assertEqual(PC.check_gate_tool(self.root), ["file not in GATE_TOOL: audit/v03/gate/g9.cert.json"])

    def test_a_missing_or_malformed_tool_file(self):
        self.assertTrue(PC.check_gate_tool(self.root)[0].startswith("cannot read"))
        put(self.root, PC.GATE_TOOL_REL, "{}")
        self.assertEqual(PC.check_gate_tool(self.root), [f"{PC.GATE_TOOL_REL} has no file table"])
        put(self.root, PC.GATE_TOOL_REL, "[]")
        self.assertTrue(PC.check_gate_tool(self.root)[0].startswith("cannot read"))

    # ---- R1-5: the certificates ----
    def test_the_eight_ids_are_the_drivers(self):
        self.assertEqual(PC.GATE_IDS, ("g1", "g2", "g3", "g4", "g5", "g6", "g7", "t1"))
        self.assertEqual((PC.GATE_TAG, PC.GATE_VERDICT), ("v0.5.1", "FALSIFIABLE"))

    def test_a_missing_certificate_id_is_refused(self):
        for gid in PC.GATE_IDS:
            self.write_tool(**{gid: None})
            problems = PC.check_gate_tool(self.root)
            self.assertEqual(problems, [f"GATE_TOOL has no certificate for {gid}"], gid)
        put(self.root, PC.GATE_TOOL_REL, json.dumps({"files": PC.gate_file_hashes(self.root), "tag": "v0.5.1"}))
        self.assertEqual(PC.check_gate_tool(self.root), ["GATE_TOOL has no certificates"])

    def test_an_unknown_certificate_id_is_refused(self):
        files = PC.gate_file_hashes(self.root)
        certs = self.certs()
        certs["g8"] = dict(certs["g1"])
        put(self.root, PC.GATE_TOOL_REL, json.dumps({"files": files, "tag": "v0.5.1", "certificates": certs}))
        self.assertEqual(PC.check_gate_tool(self.root), ["GATE_TOOL lists an unknown study id: g8"])

    def test_a_verify_exit_other_than_zero_is_refused(self):
        for bad in (1, 4, None, "0", False):
            self.write_tool(g4={"verify_exit": bad})
            problems = PC.check_gate_tool(self.root)
            self.assertEqual(len(problems), 1, bad)
            self.assertIn("certificate g4: verify_exit", problems[0])
        entry = self.certs()["g4"]
        del entry["verify_exit"]
        files = PC.gate_file_hashes(self.root)
        certs = self.certs()
        certs["g4"] = entry
        put(self.root, PC.GATE_TOOL_REL, json.dumps({"files": files, "tag": "v0.5.1", "certificates": certs}))
        self.assertIn("certificate g4: verify_exit", PC.check_gate_tool(self.root)[0])

    def test_a_weak_verdict_is_refused_unless_the_waiver_file_lists_the_id(self):
        self.write_tool(g2={"verdict": "WEAK"})
        problems = PC.check_gate_tool(self.root)
        self.assertEqual(problems, ["certificate g2: verdict is 'WEAK', not FALSIFIABLE (no waiver)"])
        for other in ("UNSOUND", "INCONCLUSIVE", None):
            self.write_tool(g2={"verdict": other})
            self.assertTrue(PC.check_gate_tool(self.root))
        # a waiver file is an object from the driver's id to the written reason; it is part of the hashed tree: written first
        put(self.root, PC.WAIVERS_REL, json.dumps({"g2": "the author's written reason, 2026-11-24"}))
        self.write_tool(g2={"verdict": "WEAK"})
        self.assertEqual(PC.check_gate_tool(self.root), [])
        put(self.root, PC.WAIVERS_REL, json.dumps({"g3": "a reason"}))  # a waiver for another id waives nothing here
        self.write_tool(g2={"verdict": "WEAK"})
        self.assertEqual(PC.check_gate_tool(self.root), ["certificate g2: verdict is 'WEAK', not FALSIFIABLE (no waiver)"])
        (self.root / PC.WAIVERS_REL).unlink()  # absent: no waiver
        self.write_tool(g2={"verdict": "WEAK"})
        self.assertEqual(len(PC.check_gate_tool(self.root)), 1)

    def test_a_waiver_covers_only_a_weak_verdict(self):  # R2-5
        put(self.root, PC.WAIVERS_REL, json.dumps({"g2": "a written reason"}))
        for other in ("UNSOUND", "NOT_FALSIFIABLE", "UNTESTED", "UNDEFINED", "INCONCLUSIVE", None, "weak"):
            self.write_tool(g2={"verdict": other})
            self.assertEqual(PC.check_gate_tool(self.root),
                             [f"certificate g2: verdict is {other!r}, not FALSIFIABLE (a waiver covers only WEAK)"], other)
        self.write_tool(g2={"verdict": "WEAK"})
        self.assertEqual(PC.check_gate_tool(self.root), [])
        self.write_tool()  # a waiver for a certificate that needs none changes nothing
        self.assertEqual(PC.check_gate_tool(self.root), [])

    def test_every_other_form_of_the_waiver_file_is_refused(self):  # R2-5
        reason = "a written reason"
        bad = {
            "a list of ids": json.dumps(["g2"]),
            "an empty list": json.dumps([]),
            "not json": "not json",
            "an empty file": "",
            "a string": json.dumps("g2"),
            "null": "null",
            "an empty reason": json.dumps({"g2": ""}),
            "a blank reason": json.dumps({"g2": "   "}),
            "a null reason": json.dumps({"g2": None}),
            "a number as reason": json.dumps({"g2": 1}),
            "a true as reason": json.dumps({"g2": True}),
            "a list as reason": json.dumps({"g2": ["a reason"]}),
            "an object as reason": json.dumps({"g2": {"why": reason}}),
            "the test id G7a": json.dumps({"g2": reason, "G7a": reason}),
            "the test id T-1": json.dumps({"g2": reason, "T-1": reason}),
            "an unknown id": json.dumps({"g2": reason, "g8": reason}),
            "an id in capitals": json.dumps({"G2": reason}),
            "one bad entry spoils the file": json.dumps({"g2": reason, "g3": ""}),
        }
        for what, text in bad.items():
            put(self.root, PC.WAIVERS_REL, text)
            self.write_tool(g2={"verdict": "WEAK"})  # the waiver file is part of the hashed tree: written first
            problems = PC.check_gate_tool(self.root)
            self.assertTrue(any("WAIVERS.json (refused, nothing is waived)" in p for p in problems), what)
            self.assertIn("certificate g2: verdict is 'WEAK', not FALSIFIABLE (no waiver)", problems, what)  # nothing is waived
        # and a refused file is a problem even where no verdict needs a waiver
        put(self.root, PC.WAIVERS_REL, json.dumps(["g2"]))
        self.write_tool()
        self.assertEqual(len(PC.check_gate_tool(self.root)), 1)
        # the accepted form, for every id of the driver
        for gid in PC.GATE_IDS:
            put(self.root, PC.WAIVERS_REL, json.dumps({gid: reason}))
            self.write_tool(**{gid: {"verdict": "WEAK"}})
            self.assertEqual(PC.check_gate_tool(self.root), [], gid)

    def test_a_waiver_does_not_excuse_a_failed_verification_or_a_changed_certificate(self):
        put(self.root, PC.WAIVERS_REL, json.dumps({"g2": "a written reason"}))
        self.write_tool(g2={"verdict": "WEAK", "verify_exit": 1})
        self.assertEqual(len(PC.check_gate_tool(self.root)), 1)
        self.write_tool(g2={"verdict": "WEAK", "body_sha256": "f" * 64})
        self.assertEqual(len(PC.check_gate_tool(self.root)), 1)

    def test_a_wrong_or_missing_tag_is_refused(self):
        for tag in ("v0.5.0", "v0.5.2", "", None):
            self.write_tool(tag=tag)
            self.assertEqual(len(PC.check_gate_tool(self.root)), 1, tag)
            self.assertIn("GATE_TOOL tag is", PC.check_gate_tool(self.root)[0])

    def test_a_certificate_body_hash_that_differs_from_the_committed_file_is_refused(self):
        self.write_tool(g6={"body_sha256": "0" * 64})
        self.assertEqual(PC.check_gate_tool(self.root), ["certificate g6: the body hash in GATE_TOOL differs from "
                                                         "audit/v03/gate/g6.cert.json"])
        self.write_tool()
        # the committed certificate changes after the tool file was written: its bytes differ too (the file table)
        put(self.root, "audit/v03/gate/g6.cert.json", json.dumps({"body": {}, "body_sha256": "a" * 64}))
        problems = PC.check_gate_tool(self.root)
        self.assertIn("changed since the gate ran: audit/v03/gate/g6.cert.json", problems)
        self.assertIn("certificate g6: the body hash in GATE_TOOL differs from audit/v03/gate/g6.cert.json", problems)
        (self.root / "audit/v03/gate/g6.cert.json").unlink()
        self.write_tool()
        self.assertIn("cannot read audit/v03/gate/g6.cert.json", PC.check_gate_tool(self.root))

    def test_the_real_driver_writes_what_the_check_reads(self):
        from audit.v03.gate import certify as CE

        self.assertEqual(CE.IDS, PC.GATE_IDS)
        self.assertEqual(CE.TAG, PC.GATE_TAG)
        if not all(CE.cert_path(g).is_file() for g in CE.IDS):
            self.skipTest("certificates are not generated yet")
        payload = CE.tool_payload("c" * 40, {g: 0 for g in CE.IDS})
        self.assertEqual(PC.check_certificates(payload, ROOT), [])  # the real certificates and the real payload agree
        bad = dict(payload, certificates=dict(payload["certificates"], g1=dict(payload["certificates"]["g1"], verify_exit=2)))
        self.assertTrue(PC.check_certificates(bad, ROOT))


class StudyReproductionTests(unittest.TestCase):
    """check_studies with a fake starter: no design study is rerun."""

    class Fake:
        def __init__(self, doc=None, code=0, err="", hang=False):
            self.doc, self.returncode, self.err, self.hang = doc, code, err, hang
            self.out = None

        def communicate(self, timeout=None):
            if self.hang and timeout is not None:
                raise subprocess.TimeoutExpired("x", timeout)
            if self.doc is not None and self.out is not None:
                self.out.write_text(json.dumps(self.doc), encoding="utf-8")
            return "", self.err

        def kill(self):
            self.hang = False

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(rmtree, self.tmp)
        self.root = Path(self.tmp)
        self.committed = {"a": 1, "runtime_seconds": 12.5, "rows": [{"x": [1, 2], "runtime_seconds": 3}]}
        put(self.root, "prereg/v03/S.json", json.dumps(self.committed))
        self.studies = {"S": ("some.module", "prereg/v03/S.json")}

    def run_with(self, fake):
        def starter(repo, module, out):
            fake.out = out
            self.assertEqual((repo, module), (self.root, "some.module"))
            return fake

        return PC.check_studies(self.root, studies=self.studies, starter=starter)

    def test_equal_apart_from_runtime(self):
        rerun = {"a": 1, "runtime_seconds": 999.0, "rows": [{"x": [1, 2], "runtime_seconds": 1}]}
        self.assertEqual(self.run_with(self.Fake(rerun)), [])

    def test_any_other_difference_is_a_problem(self):
        for rerun in ({"a": 2, "runtime_seconds": 1, "rows": [{"x": [1, 2]}]}, {"a": 1, "rows": [{"x": [1, 3]}]},
                      {"a": 1, "rows": [{"x": [1, 2]}], "extra": 0}, {"a": 1, "rows": []}):
            problems = self.run_with(self.Fake(rerun))
            self.assertEqual(len(problems), 1, rerun)
            self.assertIn("S: the rerun differs from the committed prereg/v03/S.json", problems[0])

    def test_a_failed_or_hanging_rerun_and_a_missing_committed_file(self):
        self.assertIn("rerun failed (exit 3)", self.run_with(self.Fake(None, code=3, err="boom"))[0])
        self.assertIn("did not finish", self.run_with(self.Fake(None, hang=True))[0])
        (self.root / "prereg/v03/S.json").unlink()
        self.assertIn("does not exist", self.run_with(self.Fake({}))[0])

    def test_the_five_studies_are_named_and_exist(self):
        self.assertEqual(set(PC.STUDIES), {"S1", "S1b", "S2", "power study", "all_true study",
                                              "n_q study"})  # R1-7, R2-3
        for module, rel in PC.STUDIES.values():
            self.assertTrue((ROOT / rel).is_file(), rel)
            self.assertTrue((ROOT / (module.replace(".", "/") + ".py")).is_file(), module)
            self.assertIn("OUT", open(ROOT / (module.replace(".", "/") + ".py"), encoding="utf-8").read())

    def test_strip_runtime_and_first_difference(self):
        self.assertEqual(PC.strip_runtime(self.committed), {"a": 1, "rows": [{"x": [1, 2]}]})
        self.assertIsNone(PC.first_difference({"a": [1, {"b": 2}]}, {"a": [1, {"b": 2}]}))
        self.assertEqual(PC.first_difference({"a": [1, {"b": 2}]}, {"a": [1, {"b": 3}]}), "/a[1]/b")
        self.assertEqual(PC.first_difference({"a": 1}, {"a": True}), "/a")  # a type change is a difference

    def test_the_subprocess_code_overrides_out_and_runs_main_without_arguments(self):
        self.assertIn("mod.OUT = Path(sys.argv[2])", PC.STUDY_CODE)
        self.assertIn("mod.main([])", PC.STUDY_CODE)


class V02ManifestTests(unittest.TestCase):
    def test_v02_still_verifies_in_this_tree(self):
        self.assertEqual(PC.check_v02_manifest(ROOT), [])

    def test_a_broken_v02_manifest_is_reported(self):
        tmp = tempfile.mkdtemp()
        self.addCleanup(rmtree, tmp)
        root = Path(tmp)
        put(root, "SPEC.md", "a\n")
        (root / "prereg").mkdir()
        base_freeze.write_manifest([str(root / "SPEC.md")], str(root / "prereg" / "FREEZE_v0.2.json"), readonly=False)
        self.assertEqual(PC.check_v02_manifest(root), [])
        (root / "SPEC.md").write_text("b\n")
        self.assertEqual(PC.check_v02_manifest(root), ["prereg/FREEZE_v0.2.json: MODIFIED: ../SPEC.md"])
        self.assertTrue(PC.check_v02_manifest(root / "nowhere")[0].startswith("cannot verify"))


@unittest.skipIf(SKIP_GIT, "TESARON_SKIP_GIT_TESTS=1")
class GitTests(unittest.TestCase):
    """The tracked-set check, the pre-freeze check, the freeze and the clone verifier on a scratch repository."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(rmtree, self.tmp)
        self.root = Path(self.tmp) / "repo"
        self.root.mkdir()
        mini_tree(self.root)
        put(self.root, ".gitattributes", "* text=auto eol=lf\n")
        put(self.root, ".gitignore", "__pycache__/\n*.quick.cert.json\n")
        for rel in ("audit/v03/gate/GATE_TOOL.json",):
            put(self.root, rel, json.dumps({"files": PC.gate_file_hashes(self.root)}))
        self.git("init", "-q", "-b", "main")
        self.git("config", "user.email", "t@example.invalid")
        self.git("config", "user.name", "t")
        self.git("config", "core.autocrlf", "false")

    def git(self, *args):
        res = subprocess.run(["git", *args], cwd=self.root, capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, res.stderr)
        return res.stdout.strip()

    def commit(self, msg="c"):
        self.git("add", "-A")
        self.git("commit", "-q", "-m", msg)

    def test_the_tracked_set_is_exactly_the_walk(self):
        self.commit()
        self.assertEqual(PC.check_tracked_set(self.root), [])
        self.assertEqual(PC.tracked_manifest_set(self.root), set(FZ.manifest_files(self.root)))

    def test_an_untracked_file_a_stray_json_and_an_edit_are_found(self):
        self.commit()
        put(self.root, "audit/scratch.py")  # untracked, would enter the manifest
        put(self.root, "prereg/v03/NEW_STUDY.json")  # a study json that is not tracked
        (self.root / "SPEC.md").write_text("edited\n")  # working bytes differ from the staged blob... after add
        problems = PC.check_tracked_set(self.root)
        self.assertIn("would enter the manifest but is not tracked by git: audit/scratch.py", problems)
        self.assertIn("would enter the manifest but is not tracked by git: prereg/v03/NEW_STUDY.json", problems)
        self.assertIn("the working file differs from its staged blob (line endings or an edit): SPEC.md", problems)

    def test_a_tracked_file_the_walk_would_not_hash_is_found(self):
        put(self.root, "tests/__pycache__/x.pyc", "x")
        self.git("add", "-f", "tests/__pycache__/x.pyc")
        self.commit()
        self.assertIn("tracked by git but not hashed by the freeze walk: tests/__pycache__/x.pyc",
                      PC.check_tracked_set(self.root))

    def test_review_folder_and_freeze_record_are_outside(self):
        self.commit()
        self.assertEqual(PC.check_tracked_set(self.root), [])
        self.assertNotIn("prereg/v03/reviews/r1/report.json", PC.tracked_manifest_set(self.root))
        self.assertNotIn("prereg/v03/FREEZE_RECORD.md", PC.tracked_manifest_set(self.root))

    def test_line_endings_in_the_working_tree_are_found(self):
        self.commit()
        (self.root / "audit" / "c.py").write_bytes(b"audit/c.py\r\n")
        self.assertTrue(any("audit/c.py" in p for p in PC.check_tracked_set(self.root)))

    def test_freeze_then_clone_verify(self):
        for rel in ("audit/__init__.py", "audit/freeze.py"):  # the clone runs its own `audit.freeze verify`
            shutil.copyfile(ROOT / rel, self.root / rel)
        put(self.root, PC.PREREG_REL, "\n".join(["# t", "", PC.FROZEN_STATUS_LINE, ""]) + "\n")
        put(self.root, PC.SPEC_REL, "\n".join(["# t", "", PC.SPEC_FROZEN_STATUS_LINE, ""]) + "\n")
        put(self.root, "prereg/FREEZE_v0.2.json", "{}")  # replaced below by a real v0.2-style manifest
        (self.root / "prereg" / "FREEZE_v0.2.json").unlink()
        base_freeze.write_manifest([str(self.root / "SPEC.md")], str(self.root / "prereg" / "FREEZE_v0.2.json"), readonly=False)
        self.commit("tree")
        self.assertEqual(PC.run_checks(self.root, ("tracked", "status", "v02")), [])
        FZ.write(self.root, readonly=False)
        self.commit("freeze")
        self.assertEqual(FZ.verify(self.root, coverage=True)[0], [])
        results = CV.verify_both(self.root)
        self.assertEqual([rel for rel, _ in results], list(CV.CLONE_RELS))
        self.assertTrue(all(res["ok"] for _, res in results), results)
        self.assertEqual(CV.main(["--repo", str(self.root)]), 0)
        # a change after the freeze commit is committed: the clone no longer verifies
        (self.root / "audit" / "c.py").write_text("changed\n")
        self.commit("after the freeze")
        self.assertEqual(CV.main(["--repo", str(self.root)]), 1)


class GateDriverTests(unittest.TestCase):
    def test_the_study_ids_and_files(self):
        from audit.v03.gate import certify as CE

        self.assertEqual(CE.IDS, ("g1", "g2", "g3", "g4", "g5", "g6", "g7", "t1"))
        for gid in CE.IDS:
            self.assertTrue(CE.study_path(gid).is_file(), gid)
        self.assertEqual(CE.TAG, "v0.5.1")
        self.assertEqual(CE.TOOL_REL, "audit/v03/gate/GATE_TOOL.json")
        self.assertEqual(CE.HERE, ROOT / "audit" / "v03" / "gate")

    def test_the_file_table_is_the_prefreeze_check_s(self):
        from audit.v03.gate import certify as CE

        self.assertEqual(CE.file_hashes(), PC.gate_file_hashes(ROOT))
        self.assertTrue(all(k.startswith(("audit/", "tesaron/")) for k in CE.file_hashes()))
        self.assertNotIn("audit/gate/GATE_TOOL.json", CE.file_hashes())  # v0.2's tool file is never in the table

    def test_the_driver_refuses_without_a_study_id_and_with_an_unknown_one(self):
        from unittest import mock

        from audit.v03.gate import certify as CE

        with mock.patch.object(CE, "check_checkout", side_effect=AssertionError("git was started")) as checkout:
            self.assertEqual(CE.main([]), 4)
            self.assertEqual(CE.main(["g9"]), 4)
            self.assertEqual(CE.main(["g1", "g9"]), 4)  # an unknown id after a good one: nothing has run
            self.assertEqual(CE.main(["all", "g1"]), 4)
            self.assertEqual(CE.main(["--tool-out"]), 4)
            checkout.assert_not_called()  # R1-15: the ids are validated before the checkout (git) is touched

    def test_an_unknown_id_is_refused_with_git_unreachable(self):
        """R1-15 in a fresh interpreter whose PATH holds only the Python directory: no git can be started, and the driver still
        answers with the unknown-id message (exit 4), not with a checkout error."""
        import shutil
        import sys

        py = Path(sys.executable).resolve()
        env = {"PATH": str(py.parent), "SYSTEMROOT": os.environ.get("SYSTEMROOT", ""), "PYTHONDONTWRITEBYTECODE": "1"}
        self.assertIsNone(shutil.which("git", path=env["PATH"]))  # git is unreachable in that environment
        res = subprocess.run([str(py), "-B", "-m", "audit.v03.gate.certify", "g9"], cwd=ROOT, env=env, capture_output=True,
                             text=True, timeout=300)
        self.assertEqual(res.returncode, 4, res.stderr[-300:])
        self.assertIn("unknown study 'g9'", res.stdout)
        self.assertNotIn("kapi-oss checkout commit", res.stdout)
        self.assertNotIn("refusing", res.stderr)

    def test_the_driver_refuses_a_modified_checkout(self):
        from unittest import mock

        from audit.v03.gate import certify as CE

        with mock.patch.object(CE, "check_checkout", side_effect=ValueError("differ from tag")):
            self.assertEqual(CE.main(["g1"]), 4)

    def test_write_gate_tool_goes_where_it_is_told_with_lf(self):
        from audit.v03.gate import certify as CE

        if not all(CE.cert_path(g).is_file() for g in CE.IDS):
            self.skipTest("certificates are not generated yet")
        tmp = tempfile.mkdtemp()
        self.addCleanup(rmtree, tmp)
        real = CE.HERE / "GATE_TOOL.json"

        def state():  # existence and mtime of the real file: it exists after step 6 of PREREG section 8 (R2-2)
            return (real.exists(), real.stat().st_mtime_ns if real.exists() else None)

        before = state()
        out = CE.write_gate_tool("c" * 40, {g: 0 for g in CE.IDS}, Path(tmp) / "GATE_TOOL.json", {"accepted": 1, "skipped_undefined": 2})
        data = out.read_bytes()
        self.assertNotIn(b"\r", data)
        doc = json.loads(data)
        self.assertEqual(doc["kapi_oss_commit"], "c" * 40)
        self.assertEqual(sorted(doc["certificates"]), sorted(CE.IDS))
        self.assertEqual(doc["files"], CE.file_hashes())
        self.assertEqual(doc["t1_plus_world_draws"], {"accepted": 1, "skipped_undefined": 2})
        self.assertEqual(state(), before)  # the real GATE_TOOL.json was neither created nor touched


class GateCommonTests(unittest.TestCase):
    def test_seed_range_and_constants(self):
        self.assertEqual((GC.DEV_LOW, GC.DEV_HIGH), (930000, 931000))
        self.assertEqual(GC.N_GATE_CAL, 40)

    def test_the_studies_draw_from_the_v03_development_range(self):
        import numpy as np

        rng = np.random.Generator(np.random.PCG64(5))
        world, ctx, ws, es = GC.draw_valid_world(rng)
        self.assertTrue(930000 <= ws < 931000 and 930000 <= es < 931000)
        self.assertEqual(len(world.params.source_reliabilities), 8)  # a v0.3 world
        self.assertEqual(world.params.overlap_fraction, 0.8)

    def test_the_t1_plus_world_is_defined_and_has_a_constant_new_false(self):
        import numpy as np

        from audit.exact import feasible

        GC.reset_t1_counts()
        rng = np.random.Generator(np.random.PCG64(7))
        exacts = GC.t1_plus_exacts(rng)
        self.assertEqual(len(exacts), 10)
        # a bare boolean: no development value is shown if this fails
        self.assertTrue(all(ex["new_false"] == GC.CONST_NEW_FALSE for ex in exacts))
        self.assertTrue(all(ex["new_true"] is None or ex["new_true"] == 1 / 2 for ex in exacts))
        self.assertTrue(all(isinstance(ex["n_q"], int) and ex["n_q"] >= 0 for ex in exacts))  # the real n_q is kept
        taus = GC.gate_taus()
        self.assertTrue(len({ex["uncertainty"] for ex in exacts if feasible(ex, taus)}) >= 2)  # T-1 is defined
        self.assertEqual(GC.T1_COUNTS["accepted"], 1)
        self.assertGreaterEqual(GC.T1_COUNTS["skipped_undefined"], 0)

    def test_t1_plus_and_minus_are_paired_and_the_data_have_the_declared_keys(self):
        import numpy as np

        from audit import checks as C

        from audit.v03 import checks as V

        d1 = GC.t1_plus(np.random.Generator(np.random.PCG64(11)))
        d2 = GC.t1_minus(np.random.Generator(np.random.PCG64(11)))
        self.assertTrue(set(V.DECLARED_KEYS["T-1"]) <= set(d1))
        self.assertTrue(set(C.DECLARED_KEYS["T-1"]) <= set(d1))
        self.assertTrue((d1["feasible"] == d2["feasible"]).all())  # the same world, with NT applied
        self.assertTrue((d1["uncertainty"] == d2["uncertainty"]).all())
        self.assertTrue((d1["n_q"] == d2["n_q"]).all())  # NT changes new_false only; the real denominators are kept
        self.assertTrue(V.judge_t1(d1) is True)  # by construction (constant new_false)
        # NT: new_false rises by 1/2 across the uncertainty span; it exceeds the floor unless n_q is at most 2 at the lowest point
        self.assertTrue(V.judge_t1(d2) is False)

    def test_g7a_gate_data_have_four_baselines(self):
        import numpy as np

        from audit.system import FIXED

        world, ctx, _, _ = GC.draw_valid_world(np.random.Generator(np.random.PCG64(3)))
        d = GC.collect_test("G7", FIXED, world, ctx, None)
        self.assertEqual(d["base_feasible"].shape, (4, 10))

    def test_the_gate_studies_have_no_real_new_false_path(self):
        src = (ROOT / "audit" / "v03" / "gate" / "common.py").read_text(encoding="utf-8")
        body = src[src.index("def t1_plus_exacts"):src.index("def t1_plus(")]
        self.assertNotIn('"new_false": ex["new_false"]', body)
        self.assertIn('"new_false": CONST_NEW_FALSE', body)
        self.assertIn('"n_q": V.decided_outside_count(', body)  # the denominators are design quantities and are kept
        self.assertNotIn("print(", body)
        for study in ("t1_study.py",):
            self.assertNotIn("print(", (ROOT / "audit" / "v03" / "gate" / study).read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
