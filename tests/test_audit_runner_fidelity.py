import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from dataclasses import replace
from fractions import Fraction
from pathlib import Path
from unittest import mock

import numpy as np

from audit import fidelity, run_v02
from audit import freeze as audit_freeze
from audit.cache import get_encoding
from audit.descriptive import cross_seed_agreement, g8_whole_grid, t1_all_points
from audit.exact import ExactTaus
from audit.hashing import encoding_hash, output_hash
from audit.seeds import seeder
from audit.subproc import run_hash
from audit.system import FIXED
from audit.worldset import generate_valid
from tesaron.encoder import encode, encode_from_rows

ROOT = Path(__file__).resolve().parent.parent
SKIP_GIT = os.environ.get("TESARON_SKIP_GIT_TESTS") == "1"


def _records(n=3):
    recs, _ = generate_valid(n, seeder("dev"), "world-test", "enc-test", "aux", build=get_encoding)
    return recs


def _truth_gate():
    try:
        import truth_gate
    except ModuleNotFoundError:
        sys.path.insert(0, os.environ.get("TRUTH_GATE_DIR", r"E:\Claude Projects\kapi-oss"))
        try:
            import truth_gate
        except ModuleNotFoundError:
            return None
    return truth_gate


class FidelityControlTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.recs = _records(3)

    def test_f1_f2_f4_agree_on_development_worlds(self):
        for rec in self.recs:
            with self.subTest(world=rec.world_seed):
                res = fidelity.run_controls(rec)
                self.assertEqual({k: v[0] for k, v in res.items()}, {"F1": True, "F2": True, "F4": True}, res)

    def test_f2_detects_a_different_h(self):
        with mock.patch.object(fidelity, "compute_H", lambda E, truth, rules, vocab: []):
            ok, detail = fidelity.f2_check(self.recs[0])
        self.assertFalse(ok)
        self.assertIn("H differs", detail)

    def test_f4_detects_different_centers_and_different_mu(self):
        rec = self.recs[0]
        shifted = replace(rec.encoding, fit=replace(rec.encoding.fit,
                          centers=tuple((c[0] + 1e-9, c[1]) for c in rec.encoding.fit.centers)))
        self.assertFalse(fidelity.f4_check(replace(rec, encoding=shifted))[0])
        from tesaron.degrees import Membership

        units = dict(rec.encoding.units)
        atom = next(a for a in units if a.pred.startswith("c"))
        units[atom] = replace(units[atom], mu_pos=Membership(min(1.0, units[atom].mu_pos.value + 1e-9)))
        ok, detail = fidelity.f4_check(replace(rec, encoding=replace(rec.encoding, units=units)))
        self.assertFalse(ok)
        self.assertIn("mu_pos", detail)

    def test_f1_compares_with_the_brute_force_closure(self):
        rec = self.recs[0]
        import inspect

        self.assertIn("closure_fact_keys", inspect.getsource(fidelity.f1_details))
        real = fidelity.FIXED.decode

        def broken(facts, rules, vocab, k):
            out = real(facts, rules, vocab, k)
            if k == 0 and out.facts:
                from tesaron.decoder import DecoderOutput

                dropped = dict(list(out.facts.items())[1:])
                return DecoderOutput(dropped, out.hypotheses, out.rounds)
            return out

        with mock.patch.object(fidelity.FIXED, "decode", broken):
            ok, detail = fidelity.f1_check(rec)
        self.assertFalse(ok)
        self.assertIn("brute-force closure", detail)

    def test_f1_detects_a_naive_semi_naive_difference(self):
        real = fidelity.seminaive_eval_with_records

        def broken(facts, rules, vocab):
            r = real(facts, rules, vocab)
            return replace(r, records={}) if r.records else r

        with mock.patch.object(fidelity, "seminaive_eval_with_records", broken):
            ok, detail = fidelity.f1_check(self.recs[0])
        self.assertFalse(ok)
        self.assertIn("naive and semi-naive", detail)


class S6AndSubprocessTests(unittest.TestCase):
    def test_encode_from_rows_is_what_encode_calls(self):
        rec = _records(1)[0]
        enc = encode(rec.world, rec.context)
        again = encode_from_rows(rec.world, rec.context, enc.derive_ids, enc.validate_ids)
        self.assertEqual(again, enc)
        self.assertEqual(encoding_hash(again), encoding_hash(enc))

    def test_smoke_hash_is_unchanged(self):
        res = subprocess.run([sys.executable, "-B", "-m", "tesaron.smoke", "--world-seed", "900001",
                              "--encoder-seed", "900101"], cwd=ROOT, capture_output=True, text=True, timeout=300)
        self.assertEqual(json.loads(res.stdout)["output_hash"],
                         "0c8497d0538043ae325274f7efa202d25b723048b351ce515732094bf8529645")

    def test_subprocess_hash_matches_in_process_for_the_fixed_system(self):
        world, ctx, enc = get_encoding(900001, 900101)
        h = encoding_hash(enc)
        self.assertEqual(run_hash("encoding", 900001, 900101, "fixed", "0"), h)
        self.assertEqual(run_hash("encoding", 900001, 900101, "fixed", "1"), h)
        facts = FIXED.interface_facts(enc.units, 0.7)
        out = output_hash(FIXED.decode(facts, ctx.rules, ctx.vocabulary, 5))
        self.assertEqual(run_hash("output", 900001, 900101, "fixed", "4242"), out)

    def test_n4_depends_on_the_hash_seed(self):
        hashes = {run_hash("output", 900001, 900101, "N4", hs) for hs in ("0", "1", "4242")}
        self.assertGreater(len(hashes), 1)

    def test_layer_two_g2_uses_two_explicit_hash_seeds(self):
        from audit import per_world

        self.assertEqual(per_world.G2_HASHSEEDS, ("0", "1"))
        self.assertEqual(per_world.G4_HASHSEEDS, ("0", "1", "4242"))


class DescriptiveTests(unittest.TestCase):
    def test_cross_seed_agreement(self):
        rec = _records(1)[0]
        same = cross_seed_agreement(rec.world, rec.context, rec.encoding, rec.enc_seed)
        self.assertEqual((same["share_all"], same["share_class"]), (1.0, 1.0))
        other = cross_seed_agreement(rec.world, rec.context, rec.encoding, rec.aux_seed)
        self.assertGreater(other["n_all"], 0)
        self.assertTrue(0.0 <= other["share_all"] <= 1.0)
        self.assertLessEqual(other["n_class"], other["n_all"])

    def test_whole_grid_and_all_points(self):
        F = Fraction
        taus = ExactTaus(F(4, 5), F(1, 20), F(9, 10), F(1, 2))
        good = [{"fidelity": F(9, 10), "deviation": F(0)} for _ in range(30)]
        self.assertEqual(g8_whole_grid(good, taus), {"all_points_ok": True, "n_points_ok": 30, "n_points": 30})
        bad = [dict(g) for g in good]
        bad[3]["fidelity"] = None
        self.assertEqual(g8_whole_grid(bad, taus)["n_points_ok"], 29)
        edge = [{"fidelity": F(4, 5), "deviation": F(1, 20)} for _ in range(30)]  # exactly at tau: still ok
        self.assertTrue(g8_whole_grid(edge, taus)["all_points_ok"])
        pts = [{"uncertainty": F(i + 1, 40), "new_false": F(1, 5)} for i in range(30)]
        self.assertIs(t1_all_points(pts), True)
        pts = [{"uncertainty": F(i + 1, 40), "new_false": F(9, 10) - F(i + 1, 40)} for i in range(30)]
        self.assertIs(t1_all_points(pts), False)
        self.assertIsNone(t1_all_points([{"uncertainty": F(1, 3), "new_false": F(0)} for _ in range(30)]))


class FreezeToolTests(unittest.TestCase):
    def setUp(self):
        (ROOT / "run_dev").mkdir(exist_ok=True)
        self.tmp = Path(tempfile.mkdtemp(dir=ROOT / "run_dev"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _tree(self):
        (self.tmp / "sub").mkdir()
        (self.tmp / "a.txt").write_text("alpha\n", encoding="utf-8")
        (self.tmp / "sub" / "b.py").write_text("print(1)\n", encoding="utf-8")
        (self.tmp / "sub" / "c.json").write_text("{}\n", encoding="utf-8")

    def test_write_and_verify_roundtrip(self):
        self._tree()
        out = self.tmp / "FREEZE.json"
        manifest = audit_freeze.write_manifest([self.tmp / "a.txt", self.tmp / "sub"], str(out), readonly=False)
        self.assertEqual(sorted(manifest["files"]), ["a.txt", "sub/b.py", "sub/c.json"])
        self.assertEqual(manifest["freeze_format"], 1)
        self.assertEqual(audit_freeze.verify_manifest(str(out))[0], [])
        (self.tmp / "a.txt").write_text("changed\n", encoding="utf-8")
        self.assertEqual(audit_freeze.verify_manifest(str(out))[0], ["MODIFIED: a.txt"])
        with self.assertRaises(FileExistsError):
            audit_freeze.write_manifest([self.tmp / "sub"], str(out), readonly=False)

    def test_core_hash_equals_truth_gates_on_a_sample_tree(self):
        tg = _truth_gate()
        if tg is None:
            self.skipTest("truth_gate is not importable")
        from truth_gate import freeze as tg_freeze

        self._tree()
        ours, theirs = self.tmp / "ours.json", self.tmp / "theirs" / "FREEZE.json"
        (self.tmp / "theirs").mkdir()
        # same files, same manifest folder depth: put both manifests next to the files
        ours = self.tmp / "FREEZE_OURS.json"
        theirs = self.tmp / "FREEZE_THEIRS.json"
        files = [str(self.tmp / "a.txt"), str(self.tmp / "sub")]
        m1 = audit_freeze.write_manifest(files, str(ours), readonly=False)
        self.assertEqual(tg_freeze.main(["write", *files, "-o", str(theirs), "--no-readonly"]), 0)
        m2 = json.loads(theirs.read_text(encoding="utf-8"))
        self.assertEqual(m1["files"], m2["files"])
        self.assertEqual(m1["core_sha256"], m2["core_sha256"])
        self.assertEqual(audit_freeze.core_hash(m1["files"]), tg_freeze.core_hash(m2["files"]))
        self.assertEqual(sorted(m1), sorted(m2))
        # each verifier accepts the other's manifest
        self.assertEqual(audit_freeze.verify_manifest(str(theirs))[0], [])
        self.assertEqual(tg_freeze.verify_manifest(str(ours))[0], [])

    def test_cli(self):
        self._tree()
        out = self.tmp / "F.json"
        self.assertEqual(audit_freeze.main(["write", str(self.tmp / "sub"), "-o", str(out), "--no-readonly"]), 0)
        self.assertEqual(audit_freeze.main(["verify", str(out)]), 0)
        (self.tmp / "sub" / "b.py").write_text("x\n", encoding="utf-8")
        self.assertEqual(audit_freeze.main(["verify", str(out)]), 1)
        self.assertEqual(audit_freeze.main(["verify", str(self.tmp / "missing.json")]), 2)


@unittest.skipIf(SKIP_GIT, "TESARON_SKIP_GIT_TESTS=1")
class GitPreconditionTests(unittest.TestCase):
    """The runner's git checks (R2-2), on a temporary repository of their own (never the working directory's)."""

    SALT = "ab" * 32

    def setUp(self):
        (ROOT / "run_dev").mkdir(exist_ok=True)
        self.repo = Path(tempfile.mkdtemp(dir=ROOT / "run_dev"))
        self.g("init", "-q", "-b", "main")

    def tearDown(self):
        shutil.rmtree(self.repo, ignore_errors=True)

    def g(self, *args):
        res = subprocess.run(
            ["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid", "-c", "commit.gpgsign=false", *args],
            cwd=self.repo, capture_output=True, text=True,
        )
        self.assertEqual(res.returncode, 0, res.stderr)
        return res.stdout.strip()

    def write(self, rel, text):
        path = self.repo / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def commit_files(self, message, *rels):
        self.g("add", *rels)
        self.g("commit", "-q", "-m", message)
        return self.g("rev-parse", "HEAD")

    def commit(self, rel, text, message):
        self.write(rel, text)
        return self.commit_files(message, rel)

    def push_ref(self, commit):
        self.g("update-ref", "refs/remotes/origin/main", commit)

    def salt_doc(self, freeze_commit, core, salt=None):
        return json.dumps({"salt": salt or self.SALT, "freeze_commit": freeze_commit, "core_sha256": core,
                           "drawn_by": "Independent", "time": "2026-11-23T00:00:00Z"})

    def freeze(self, extra=()):
        """Frozen files and the manifest in ONE commit (the freeze commit); returns (commit, core)."""
        self.write("audit/a.py", "print('a')\n")
        self.write("tesaron/b.py", "print('b')\n")
        for rel in extra:
            self.write(rel, "x\n")
        files = [self.repo / "audit", self.repo / "tesaron"]
        (self.repo / "prereg").mkdir(exist_ok=True)
        manifest = audit_freeze.write_manifest(files, str(self.repo / "prereg" / "FREEZE_v0.2.json"), readonly=False)
        commit = self.commit_files("freeze", "audit", "tesaron", "prereg/FREEZE_v0.2.json")
        return commit, manifest["core_sha256"]

    def legit(self):
        """freeze, push, salt, CAL_WORLDS and TAU in the right order; returns a dict of the pieces."""
        freeze, core = self.freeze()
        self.push_ref(freeze)
        salt_commit = self.commit("run/SALT.json", self.salt_doc(freeze, core), "salt")
        self.push_ref(salt_commit)
        cal = self.commit("run/CAL_WORLDS.json", "{}", "cal")
        tau = self.commit("run/TAU.json", "{}", "tau")
        self.push_ref(tau)
        return {"freeze": freeze, "core": core, "salt": salt_commit, "cal": cal, "tau": tau}

    def test_the_legitimate_path_passes(self):
        s = self.legit()
        self.assertEqual(run_v02.check_freeze_and_salt(self.repo, s["core"]), (s["freeze"], s["salt"], self.SALT))
        run_v02.check_tau_after_salt(self.repo, s["salt"])

    def test_unique_commit(self):
        self.commit("a.txt", "1", "one")
        with self.assertRaises(run_v02.Refused) as cm:
            run_v02.unique_commit(self.repo, "zzz.txt")
        self.assertIn("no commit touches", str(cm.exception))
        c = run_v02.unique_commit(self.repo, "a.txt")
        self.assertEqual(c, self.g("rev-parse", "HEAD"))
        self.commit("a.txt", "2", "two")
        with self.assertRaises(run_v02.Refused) as cm:
            run_v02.unique_commit(self.repo, "a.txt")
        self.assertIn("2 commits touch", str(cm.exception))

    def test_freeze_commit_must_be_on_the_remote_branch(self):
        before = self.commit("init.txt", "x", "init")
        freeze, core = self.freeze()
        self.commit("run/SALT.json", self.salt_doc(freeze, core), "salt")
        with self.assertRaises(run_v02.Refused) as cm:  # no remote-tracking ref at all
            run_v02.check_freeze_and_salt(self.repo, core)
        self.assertIn("origin/main", str(cm.exception))
        self.push_ref(before)  # the ref exists but is behind the freeze commit
        with self.assertRaises(run_v02.Refused) as cm:
            run_v02.check_freeze_and_salt(self.repo, core)
        self.assertIn("is not on", str(cm.exception))

    def test_manifest_rewritten_in_a_later_commit_is_refused(self):
        s = self.legit()
        (self.repo / "prereg" / "FREEZE_v0.2.json").unlink()
        self.write("audit/c.py", "print('c')\n")
        audit_freeze.write_manifest([self.repo / "audit", self.repo / "tesaron"],
                                    str(self.repo / "prereg" / "FREEZE_v0.2.json"), readonly=False)
        later = self.commit_files("rewrite the manifest", "audit", "prereg/FREEZE_v0.2.json")
        self.push_ref(later)
        with self.assertRaises(run_v02.Refused) as cm:
            run_v02.check_freeze_and_salt(self.repo, s["core"])
        self.assertIn("2 commits touch prereg/FREEZE_v0.2.json", str(cm.exception))

    def test_salt_modified_in_a_later_commit_with_a_valid_salt_is_refused(self):
        s = self.legit()
        later = self.commit("run/SALT.json", self.salt_doc(s["freeze"], s["core"], "cd" * 32), "new salt")
        self.push_ref(later)
        with self.assertRaises(run_v02.Refused) as cm:
            run_v02.check_freeze_and_salt(self.repo, s["core"])
        self.assertIn("2 commits touch run/SALT.json", str(cm.exception))

    def test_salt_core_mismatch_is_refused(self):
        freeze, core = self.freeze()
        self.push_ref(freeze)
        salt_commit = self.commit("run/SALT.json", self.salt_doc(freeze, "0" * 64), "salt")
        self.push_ref(salt_commit)
        with self.assertRaises(run_v02.Refused) as cm:
            run_v02.check_freeze_and_salt(self.repo, core)
        self.assertIn("core_sha256", str(cm.exception))
        # a salt without any core_sha256 is refused too
        self.write("run/SALT.json", json.dumps({"salt": self.SALT, "freeze_commit": freeze}))
        self.g("add", "run/SALT.json")
        self.g("commit", "-q", "--amend", "-m", "salt")
        self.push_ref(self.g("rev-parse", "HEAD"))
        with self.assertRaises(run_v02.Refused):
            run_v02.check_freeze_and_salt(self.repo, core)

    def test_an_uncommitted_edit_to_a_frozen_file_is_refused(self):
        s = self.legit()
        run_v02.check_freeze_and_salt(self.repo, s["core"])
        (self.repo / "audit" / "a.py").write_text("print('changed')\n", encoding="utf-8")
        with self.assertRaises(run_v02.Refused) as cm:  # modified, not staged
            run_v02.check_freeze_and_salt(self.repo, s["core"])
        self.assertIn("frozen file", str(cm.exception))
        self.g("add", "audit/a.py")  # staged, not committed
        with self.assertRaises(run_v02.Refused):
            run_v02.check_freeze_and_salt(self.repo, s["core"])

    def test_a_frozen_file_committed_later_differs_from_the_freeze_commit(self):
        s = self.legit()
        later = self.commit("tesaron/b.py", "print('b2')\n", "edit after the freeze")
        self.push_ref(later)
        with self.assertRaises(run_v02.Refused) as cm:  # committed and clean, but not what the freeze commit holds
            run_v02.check_freeze_and_salt(self.repo, s["core"])
        self.assertIn("differs from its content in the freeze commit", str(cm.exception))

    def test_an_untracked_frozen_file_is_refused(self):
        freeze, core = self.freeze()
        self.push_ref(freeze)
        self.g("rm", "-q", "--cached", "tesaron/b.py")  # listed in the manifest but no longer tracked
        self.g("commit", "-q", "-m", "untrack")
        self.push_ref(self.g("rev-parse", "HEAD"))
        self.commit("run/SALT.json", self.salt_doc(freeze, core), "salt")
        self.push_ref(self.g("rev-parse", "HEAD"))
        with self.assertRaises(run_v02.Refused) as cm:
            run_v02.check_freeze_and_salt(self.repo, core)
        self.assertIn("not tracked", str(cm.exception))

    def test_many_frozen_files_are_checked_in_batches(self):
        names = [f"audit/pkg{i:03d}/module_with_a_long_file_name_{i:03d}.py" for i in range(300)]
        freeze, core = self.freeze(extra=names)
        self.push_ref(freeze)
        paths = run_v02.manifest_repo_paths(self.repo, self.repo / "prereg" / "FREEZE_v0.2.json")
        self.assertGreater(sum(len(x) + 1 for x in paths), 6000)
        self.assertGreater(len(list(run_v02._batches(paths))), 1)
        salt_commit = self.commit("run/SALT.json", self.salt_doc(freeze, core), "salt")
        self.push_ref(salt_commit)
        self.assertEqual(run_v02.check_freeze_and_salt(self.repo, core)[0], freeze)

    def test_batches_respect_the_limit_and_keep_every_path(self):
        paths = [f"p{i}/" + "x" * 50 for i in range(500)]
        batches = list(run_v02._batches(paths, limit=1000))
        self.assertEqual([p for b in batches for p in b], paths)
        self.assertTrue(all(sum(len(p) + 1 for p in b) <= 1000 for b in batches))

    def test_salt_naming_another_commit_or_a_bad_salt_is_refused(self):
        freeze, core = self.freeze()
        self.push_ref(freeze)
        c = self.commit("run/SALT.json", self.salt_doc("0" * 40, core), "salt")
        self.push_ref(c)
        with self.assertRaises(run_v02.Refused) as cm:
            run_v02.check_freeze_and_salt(self.repo, core)
        self.assertIn("does not name the freeze commit", str(cm.exception))

    def test_a_non_hex_salt_is_refused(self):
        freeze, core = self.freeze()
        self.push_ref(freeze)
        c = self.commit("run/SALT.json", self.salt_doc(freeze, core, "not-hex"), "salt")
        self.push_ref(c)
        with self.assertRaises(run_v02.Refused) as cm:
            run_v02.check_freeze_and_salt(self.repo, core)
        self.assertIn("32 random bytes", str(cm.exception))

    def test_salt_in_the_freeze_commit_or_before_it_is_refused(self):
        self.commit("run/SALT.json", self.salt_doc("0" * 40, "0" * 64), "salt first")
        freeze, core = self.freeze()
        self.push_ref(freeze)
        with self.assertRaises(run_v02.Refused) as cm:
            run_v02.check_freeze_and_salt(self.repo, core)
        self.assertIn("descendant", str(cm.exception))

    def test_the_salt_commit_must_be_on_the_remote_branch(self):
        freeze, core = self.freeze()
        self.push_ref(freeze)
        self.commit("run/SALT.json", self.salt_doc(freeze, core), "salt")  # the remote ref stays at the freeze commit
        with self.assertRaises(run_v02.Refused) as cm:
            run_v02.check_freeze_and_salt(self.repo, core)
        self.assertIn("the salt commit", str(cm.exception))

    def test_tau_and_cal_must_be_on_the_remote_branch(self):
        freeze, core = self.freeze()
        self.push_ref(freeze)
        salt_commit = self.commit("run/SALT.json", self.salt_doc(freeze, core), "salt")
        self.push_ref(salt_commit)
        cal = self.commit("run/CAL_WORLDS.json", "{}", "cal")
        self.push_ref(cal)
        self.commit("run/TAU.json", "{}", "tau")  # committed, not pushed
        with self.assertRaises(run_v02.Refused) as cm:
            run_v02.check_tau_after_salt(self.repo, salt_commit)
        self.assertIn("run/TAU.json", str(cm.exception))
        self.push_ref(self.g("rev-parse", "HEAD"))
        run_v02.check_tau_after_salt(self.repo, salt_commit)

    def test_cal_not_on_the_remote_branch_is_refused(self):
        freeze, core = self.freeze()
        self.push_ref(freeze)
        salt_commit = self.commit("run/SALT.json", self.salt_doc(freeze, core), "salt")
        self.push_ref(salt_commit)
        self.commit("run/CAL_WORLDS.json", "{}", "cal")
        self.commit("run/TAU.json", "{}", "tau")
        with self.assertRaises(run_v02.Refused) as cm:
            run_v02.check_tau_after_salt(self.repo, salt_commit)
        self.assertIn("run/CAL_WORLDS.json", str(cm.exception))

    def test_tau_must_be_committed_after_the_salt(self):
        freeze, core = self.freeze()
        self.push_ref(freeze)
        self.commit("run/CAL_WORLDS.json", "{}", "cal too early")
        self.commit("run/TAU.json", "{}", "tau too early")
        salt_commit = self.commit("run/SALT.json", self.salt_doc(freeze, core), "salt")
        self.push_ref(salt_commit)
        with self.assertRaises(run_v02.Refused) as cm:
            run_v02.check_tau_after_salt(self.repo, salt_commit)
        self.assertIn("descendant of the salt commit", str(cm.exception))

    def test_a_modified_or_rewritten_tau_is_refused(self):
        s = self.legit()
        (self.repo / "run" / "TAU.json").write_text("{\"x\": 1}", encoding="utf-8")
        with self.assertRaises(run_v02.Refused):  # modified, not committed
            run_v02.check_tau_after_salt(self.repo, s["salt"])
        later = self.commit("run/TAU.json", "{\"x\": 2}", "tau rewritten")
        self.push_ref(later)
        with self.assertRaises(run_v02.Refused) as cm:  # two commits touch it
            run_v02.check_tau_after_salt(self.repo, s["salt"])
        self.assertIn("2 commits touch run/TAU.json", str(cm.exception))

    def test_no_git_call_touches_the_working_directory(self):
        cwd = os.getcwd()
        s = self.legit()
        run_v02.check_freeze_and_salt(self.repo, s["core"])
        self.assertEqual(os.getcwd(), cwd)


class RunnerTests(unittest.TestCase):
    def setUp(self):
        (ROOT / "run_dev").mkdir(exist_ok=True)
        self.tmp = Path(tempfile.mkdtemp(dir=ROOT / "run_dev"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _freeze(self, files, name="FREEZE.json"):
        out = self.tmp / name
        audit_freeze.write_manifest(files, str(out), readonly=False)
        return out

    def test_real_mode_refuses_without_a_manifest(self):
        had_run = (ROOT / "run").exists()
        with mock.patch.object(run_v02, "MANIFEST", self.tmp / "FREEZE_v0.2.json"), \
                mock.patch.object(run_v02, "check_versions", lambda: None):
            for mode in ("calibrate", "test"):
                self.assertEqual(run_v02.main([mode]), run_v02.EXIT_REFUSED)
        self.assertEqual((ROOT / "run").exists(), had_run)  # a refused run creates nothing

    def test_real_mode_refuses_other_versions(self):
        with mock.patch.object(run_v02.sys, "version_info", (3, 13, 0, "final", 0)):
            with self.assertRaises(run_v02.Refused):
                run_v02.check_versions()
        with mock.patch.object(run_v02.np, "__version__", "2.0.0"):
            with self.assertRaises(run_v02.Refused):
                run_v02.check_versions()
        self.assertEqual(run_v02.REQUIRED_PYTHON, (3, 14, 2))
        self.assertEqual(run_v02.REQUIRED_NUMPY, "2.4.1")

    def test_verify_freeze_cases(self):
        entry = self.tmp / "entry.py"
        other = self.tmp / "other.txt"
        entry.write_text("print(1)\n", encoding="utf-8")
        other.write_text("data\n", encoding="utf-8")
        manifest = self._freeze([entry, other])
        core = run_v02.verify_freeze(manifest, entry)
        self.assertEqual(core, json.loads(manifest.read_text())["core_sha256"])
        other.write_text("changed\n", encoding="utf-8")
        with self.assertRaises(run_v02.Refused) as cm:
            run_v02.verify_freeze(manifest, entry)
        self.assertIn("MODIFIED", str(cm.exception))
        other.write_text("data\n", encoding="utf-8")
        doc = json.loads(manifest.read_text())
        doc["core_sha256"] = "0" * 64
        manifest.write_text(json.dumps(doc), encoding="utf-8")
        with self.assertRaises(run_v02.Refused) as cm:
            run_v02.verify_freeze(manifest, entry)
        self.assertIn("MANIFEST EDITED", str(cm.exception))

    def test_the_runner_itself_must_be_frozen(self):
        listed = self.tmp / "listed.txt"
        listed.write_text("x\n", encoding="utf-8")
        manifest = self._freeze([listed])
        with self.assertRaises(run_v02.Refused) as cm:
            run_v02.verify_freeze(manifest, Path(run_v02.__file__))
        self.assertIn("ENTRY NOT FROZEN", str(cm.exception))

    def test_the_runner_does_not_import_truth_gate(self):
        text = Path(run_v02.__file__).read_text(encoding="utf-8")
        self.assertNotIn("truth_gate", text.replace("Truth_Gate", ""))

    def test_dev_mode_end_to_end(self):
        had_run = (ROOT / "run").exists()
        self.assertEqual(run_v02.main(["calibrate", "--dev", "--n-cal", "3"]), 0)
        self.assertEqual(run_v02.main(["test", "--dev", "--n-test", "2", "--n-cal", "3", "--no-subprocess"]), 0)
        out = ROOT / "run_dev"
        for name in ("CAL_WORLDS.json", "TAU.json", "TEST_WORLDS.json", "RESULTS.json", "VERDICTS.json"):
            self.assertTrue((out / name).is_file(), name)
        tau = json.loads((out / "TAU.json").read_text())
        self.assertEqual(tau["core_sha256"], "dev")
        for n in ("tau_s", "tau_d", "tau_t", "tau_b"):  # exact fractions next to the floats
            num, den = tau[n + "_exact"].split("/")
            self.assertEqual(float(Fraction(int(num), int(den))), tau[n])
        cal = json.loads((out / "CAL_WORLDS.json").read_text())
        self.assertTrue(all(900000 <= w["world_seed"] <= 900999 for w in cal["worlds"]))
        ms = [{k: Fraction(*map(int, v.split("/"))) for k, v in w["metrics_exact"].items() if v} for w in cal["worlds"]]
        self.assertEqual(tau["tau_s_exact"], "%d/%d" % (min(m["fidelity"] for m in ms).numerator, min(m["fidelity"] for m in ms).denominator))
        self.assertEqual(Fraction(*map(int, tau["tau_d_exact"].split("/"))), max(m["deviation"] for m in ms))
        self.assertEqual(Fraction(*map(int, tau["tau_t_exact"].split("/"))), min(m["consistency"] for m in ms))
        self.assertEqual(Fraction(*map(int, tau["tau_b_exact"].split("/"))), max(m["uncertainty"] for m in ms))
        self.assertIn("python", cal["environment"])
        self.assertIn("numpy", cal["environment"])
        self.assertTrue(all(len(w["world_hash"]) == 64 and len(w["encoding_hash"]) == 64 for w in cal["worlds"]))
        tw = json.loads((out / "TEST_WORLDS.json").read_text())
        seeds = sorted(str(w["world_seed"]) for w in tw["worlds"])
        self.assertEqual(sorted(p.stem for p in (out / "outputs_input").glob("*.json")), seeds)
        self.assertEqual(sorted(p.stem for p in (out / "outputs_results").glob("*.json")), seeds)
        blind = json.loads(next((out / "outputs_input").glob("*.json")).read_text())
        for key in ("true_atoms", "units", "validation_units", "rules", "taus", "configs", "alphas", "ks"):
            self.assertIn(key, blind)
        for key in ("metrics", "check_data", "H", "fixed_outcomes", "twin_outcomes"):
            self.assertNotIn(key, blind)  # F3 input is blind
        self.assertEqual(len(blind["configs"]), 30)
        results = json.loads(next((out / "outputs_results").glob("*.json")).read_text())
        for key in ("metrics", "metrics_exact", "check_data", "H", "fixed_outcomes", "controls", "pcm"):
            self.assertIn(key, results)
        verdicts = json.loads((out / "VERDICTS.json").read_text())
        self.assertEqual(len(verdicts["table"]["rows"]), 9)
        self.assertEqual(verdicts["n_test_worlds"], 2)
        self.assertIn("python", verdicts["environment"])
        self.assertEqual(len(verdicts["world_hashes"]), 2)
        self.assertEqual((ROOT / "run").exists(), had_run)  # development mode never touches run/

    def test_dev_only_options_are_refused_in_real_mode(self):
        self.assertEqual(run_v02.main(["test", "--n-test", "2"]), run_v02.EXIT_USAGE)

    def test_test_mode_refuses_a_tau_that_cannot_be_reproduced(self):
        self.assertEqual(run_v02.main(["calibrate", "--dev", "--n-cal", "3"]), 0)
        out = ROOT / "run_dev"
        doc = json.loads((out / "TAU.json").read_text())
        doc["tau_b_exact"] = "99/100"
        (out / "TAU.json").write_text(json.dumps(doc), encoding="utf-8")
        self.assertEqual(run_v02.main(["test", "--dev", "--n-test", "2", "--n-cal", "3", "--no-subprocess"]),
                         run_v02.EXIT_REFUSED)
        self.assertEqual(run_v02.main(["calibrate", "--dev", "--n-cal", "3"]), 0)
        cal = json.loads((out / "CAL_WORLDS.json").read_text())
        cal["worlds"][0]["h_size"] += 1  # CAL_WORLDS.json changed after TAU.json recorded its hash
        (out / "CAL_WORLDS.json").write_text(json.dumps(cal), encoding="utf-8")
        self.assertEqual(run_v02.main(["test", "--dev", "--n-test", "2", "--n-cal", "3", "--no-subprocess"]),
                         run_v02.EXIT_REFUSED)

    def test_a_control_disagreement_stops_the_run_before_any_check(self):
        run_v02.main(["calibrate", "--dev", "--n-cal", "3"])
        out = ROOT / "run_dev"
        for name in ("TEST_WORLDS.json", "RESULTS.json", "VERDICTS.json"):
            (out / name).unlink(missing_ok=True)
        shutil.rmtree(out / "outputs_input", ignore_errors=True)
        with mock.patch.object(run_v02, "run_controls", lambda rec: {"F2": (False, "H differs"), "F1": (True, ""), "F4": (True, "")}), \
                mock.patch.object(run_v02, "evaluate_world", side_effect=AssertionError("checks must not run")):
            code = run_v02.main(["test", "--dev", "--n-test", "2", "--n-cal", "3", "--no-subprocess"])
        self.assertEqual(code, run_v02.EXIT_CONTROL)
        self.assertTrue((out / "STOPPED.json").is_file())
        for name in ("TEST_WORLDS.json", "RESULTS.json", "VERDICTS.json"):
            self.assertFalse((out / name).exists(), name)  # nothing but STOPPED.json is written
        self.assertFalse((out / "outputs_input").exists())

    def test_controls_run_on_all_worlds_before_any_check(self):
        run_v02.main(["calibrate", "--dev", "--n-cal", "3"])
        order = []
        real_controls, real_eval = run_v02.run_controls, run_v02.evaluate_world

        def controls(rec):
            order.append("F")
            return real_controls(rec)

        def evaluate(*a, **k):
            order.append("E")
            return real_eval(*a, **k)

        with mock.patch.object(run_v02, "run_controls", controls), mock.patch.object(run_v02, "evaluate_world", evaluate):
            run_v02.main(["test", "--dev", "--n-test", "2", "--n-cal", "3", "--no-subprocess"])
        self.assertEqual(order, ["F", "F", "E", "E"])


@unittest.skipIf(SKIP_GIT, "TESARON_SKIP_GIT_TESTS=1")
class CertifyDriverTests(unittest.TestCase):
    def setUp(self):
        if _truth_gate() is None:
            self.skipTest("truth_gate is not importable")

    def test_checkout_matches_the_tag_and_is_recorded(self):
        from audit.gate import certify

        commit = certify.check_checkout()
        self.assertRegex(commit, r"^[0-9a-f]{40}$")
        with mock.patch.object(certify.subprocess, "run") as run:
            run.side_effect = [mock.Mock(returncode=0, stdout=commit + "\n"), mock.Mock(returncode=1, stdout="")]
            with self.assertRaises(ValueError):
                certify.check_checkout()  # a difference against v0.5.1 is refused
        with mock.patch.object(certify.subprocess, "run") as run:  # R2-12: modified or untracked files are refused
            run.side_effect = [mock.Mock(returncode=0, stdout=commit + "\n"), mock.Mock(returncode=0, stdout=""),
                               mock.Mock(returncode=0, stdout="?? kapi/scratch.py\n")]
            with self.assertRaises(ValueError) as cm:
                certify.check_checkout()
            self.assertIn("untracked", str(cm.exception))
            status_call = run.call_args_list[2][0][0]
            self.assertIn("--untracked-files=all", status_call)
        with mock.patch.object(certify.subprocess, "run") as run:
            run.side_effect = [mock.Mock(returncode=0, stdout=commit + "\n"), mock.Mock(returncode=0, stdout=""),
                               mock.Mock(returncode=0, stdout="")]
            self.assertEqual(certify.check_checkout(), commit)

    def test_gate_tool_file_lists_certificates_and_hashes(self):
        from audit.gate import certify

        hashes = certify.file_hashes()
        self.assertIn("audit/checks.py", hashes)
        self.assertIn("tesaron/encoder/core.py", hashes)
        self.assertFalse([k for k in hashes if "__pycache__" in k or k.endswith(".pyc") or k.endswith("GATE_TOOL.json")])
        self.assertTrue(all(len(v) == 64 for v in hashes.values()))


class GateStudyTests(unittest.TestCase):
    """The nine gate study files: declared as in PREREG 6.3, deterministic for equal rng, numeric arrays only."""

    IDS = ("g1", "g2", "g3", "g4", "g5", "g6", "g7", "g8", "t1")

    @classmethod
    def setUpClass(cls):
        if _truth_gate() is None:
            raise unittest.SkipTest("truth_gate is not importable")
        cls.studies = {}
        for gid in cls.IDS:
            path = ROOT / "audit" / "gate" / f"{gid}_study.py"
            spec = importlib.util.spec_from_file_location(f"_gate_{gid}", path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            cls.studies[gid] = mod.STUDY

    def test_declarations(self):
        for gid, study in self.studies.items():
            with self.subTest(study=gid):
                self.assertEqual(study.budget.samples, 100)
                self.assertEqual(len(study.criteria), 1)
                self.assertEqual(sorted(study.worlds), ["minus", "plus"])
                self.assertEqual(study.worlds["minus"].derived_from, "plus")
                self.assertRegex(study.worlds["minus"].change, r"twin N")
                self.assertTrue(study.controls and study.controls[0].transform is not None)
                self.assertEqual(study.controls[0].criteria, [study.criteria[0].id])

    def test_worlds_are_deterministic_numeric_and_dev_seeded(self):
        for gid, study in self.studies.items():
            for name in ("plus", "minus"):
                with self.subTest(study=gid, world=name):
                    a = study.worlds[name].generate(np.random.default_rng(900910))
                    b = study.worlds[name].generate(np.random.default_rng(900910))
                    self.assertEqual(list(a), list(b))
                    for k in a:
                        self.assertIsInstance(a[k], np.ndarray)
                        self.assertTrue(np.issubdtype(a[k].dtype, np.number) or a[k].dtype == np.bool_)
                        self.assertTrue(np.array_equal(a[k], b[k], equal_nan=True))
                    ctl = study.controls[0].transform(dict(a), np.random.default_rng(900911))
                    self.assertEqual(sorted(ctl), sorted(a))

    def test_implementation_studies_plus_holds_minus_and_control_fail(self):
        from audit import checks as C

        judge = {"g1": C.judge_g1, "g2": C.judge_g2, "g3": C.judge_g3, "g4": C.judge_g4, "g5": C.judge_g5,
                 "g6": C.judge_g6, "g7": C.judge_g7a}
        for gid, fn in judge.items():
            study = self.studies[gid]
            rng = np.random.default_rng(900912)
            plus = study.worlds["plus"].generate(rng)
            minus = study.worlds["minus"].generate(np.random.default_rng(900913))
            with self.subTest(study=gid):
                self.assertIs(fn(plus), True)
                self.assertIs(fn(minus), False)
                self.assertIsNot(fn(study.controls[0].transform(dict(plus), rng)), True)

    def test_plus_worlds_follow_the_draft_4_design(self):
        import inspect

        from audit.gate import common as G

        self.assertEqual(sorted(G.PLUS_SYSTEMS), ["G8"])  # G7a's plus is the criterion on baselines and oracle
        self.assertEqual(G.T1_WINDOW, (0.80, 0.75, 0.70, 0.65))
        self.assertIn("T1_WINDOW", inspect.getsource(G.window_exacts))
        ex = G.window_exacts(np.random.default_rng(900914))
        self.assertEqual(len(ex), 12)  # four alpha levels times three k
        self.assertTrue(all("uncertainty" in e and "new_false" in e for e in ex))


if __name__ == "__main__":
    unittest.main()
