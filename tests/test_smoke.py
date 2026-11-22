import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ARGS = ["--world-seed", "900001", "--encoder-seed", "900101"]


def run_smoke(extra_env=None, args=ARGS):
    env = dict(os.environ)
    env.update(extra_env or {})
    return subprocess.run(
        [sys.executable, "-B", "-m", "tesaron.smoke", *args],
        cwd=ROOT, env=env, capture_output=True, text=True, timeout=300,
    )


class SmokeTests(unittest.TestCase):
    def test_output_hash_is_independent_of_pythonhashseed(self):
        hashes = []
        for hs in ("0", "1", "4242"):
            res = run_smoke({"PYTHONHASHSEED": hs})
            self.assertEqual(res.returncode, 0, res.stderr)
            hashes.append(json.loads(res.stdout)["output_hash"])
        self.assertEqual(len(set(hashes)), 1, hashes)
        self.assertEqual(len(hashes[0]), 64)

    def test_summary_content_and_no_files_written(self):
        before = sorted(p.name for p in ROOT.iterdir())
        res = run_smoke()
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertEqual(sorted(p.name for p in ROOT.iterdir()), before)  # nothing written without --out
        d = json.loads(res.stdout)
        self.assertEqual(d["taus"]["label"], "placeholder, not frozen")
        self.assertEqual(
            [d["taus"][k] for k in ("tau_s", "tau_d", "tau_t", "tau_b")], [0.8, 0.05, 0.9, 0.5]
        )
        self.assertEqual(len(d["grid"]), 15)
        self.assertEqual(sorted(d["sets_per_alpha"]), ["0.5", "0.6", "0.7", "0.8", "0.9"])
        for sets in d["sets_per_alpha"].values():
            self.assertEqual(sorted(sets), ["E", "H", "I", "K"])
        for g in d["grid"]:
            self.assertIn("feasible", g)
            for key in ("fidelity", "deviation", "consistency", "uncertainty", "new_true", "new_false",
                        "hyp_count", "hyp_correct", "validation_agreement", "boundary_share"):
                self.assertIn(key, g["metrics"])
        self.assertIn("hypervolume", d)
        self.assertIn("front", d)
        self.assertEqual(sorted(d["baselines"]["0.7"]), ["all_both", "all_false", "all_true", "all_unknown", "echo"])
        self.assertIn("run_time_s", d)
        self.assertEqual(d["world"]["seed"], 900001)

    def test_out_file_option(self):
        out = ROOT / ".smoke_test_out.json"  # inside the repo; removed right away
        try:
            res = run_smoke(args=ARGS + ["--out", str(out)])
            self.assertEqual(res.returncode, 0, res.stderr)
            self.assertEqual(json.loads(out.read_text(encoding="ascii"))["output_hash"], json.loads(res.stdout)["output_hash"])
        finally:
            if out.exists():
                out.unlink()

    def test_seeds_outside_reserved_range_are_rejected(self):
        res = run_smoke(args=["--world-seed", "1", "--encoder-seed", "900101"])
        self.assertNotEqual(res.returncode, 0)
        res = run_smoke(args=["--world-seed", "900001", "--encoder-seed", "901000"])
        self.assertNotEqual(res.returncode, 0)


if __name__ == "__main__":
    unittest.main()
