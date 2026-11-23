"""F1 and F4 on v0.3 development worlds (PREREG_v0.3 section 6.1): the pre-freeze file has no forbidden value (section 2)."""

import json
import re
import tempfile
import unittest
from pathlib import Path

from audit.v03 import f4_prefreeze as F4

ROOT = Path(__file__).resolve().parent.parent
FORBIDDEN = re.compile(r"new_false|new_true|T-1|G8|hypervolume|largest|increase|draw_sens|t1_|i2|i6|i7|i8|i9", re.I)


class F4PrefreezeTests(unittest.TestCase):
    def test_a_small_run_has_the_documented_fields_and_no_forbidden_name(self):
        doc = F4.build_document(2)
        self.assertEqual(doc["n_worlds"], 2)
        self.assertTrue(doc["every_comparison_equal"])
        seeds = [w["world_seed"] for w in doc["worlds"]]
        self.assertTrue(seeds == sorted(seeds) and seeds[0] >= 930000)
        for w in doc["worlds"]:
            self.assertEqual(set(w["f4"]), set(F4.F4_KEYS))
            self.assertEqual(set(w["f1"]), set(F4.F1_KEYS))
            self.assertEqual(w["enc_seed"], w["world_seed"] + 10000)
        self.assertIsNone(FORBIDDEN.search(json.dumps(doc)))

    def test_the_output_is_lf_and_goes_where_it_is_told(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "f4.json"
            self.assertEqual(F4.main(["--out", str(out), "--n-worlds", "1"]), 0)
            self.assertNotIn(b"\r", out.read_bytes())

    def test_the_committed_file_if_present(self):
        path = ROOT / "prereg" / "v03" / "F4_PREFREEZE.json"
        if not path.is_file():
            self.skipTest("F4_PREFREEZE.json is not written yet")
        text = path.read_text(encoding="utf-8")
        self.assertIsNone(FORBIDDEN.search(text))
        doc = json.loads(text)
        self.assertEqual(doc["n_worlds"], 20)
        self.assertTrue(doc["every_comparison_equal"])
        self.assertNotIn("\r", text)


if __name__ == "__main__":
    unittest.main()
