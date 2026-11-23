"""Tests that run the v0.3 pipeline on a few development worlds (seeds 930000 upward). They look at structure, types and the
redaction boundary only: no assertion reads, prints or compares a T-1 or G8 value of a development world (PREREG_v0.3
section 2, no pilot)."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from audit import checks as C
from audit.system import FIXED
from audit.v03 import aggregate as AG
from audit.v03 import checks as V
from audit.v03 import controls, redact
from audit.v03 import run_v03 as RV
from audit.v03.per_world import ALL_TESTS, TWIN_TEST, TauSet, evaluate_world_v03
from audit.v03.seeds import DEV_CORE, seeder
from audit.v03.tau import d1_first
from audit.v03.worldset import WorldSetError, build_cached, generate_valid_v03

ROOT = Path(__file__).resolve().parent.parent
VALID = {"HOLDS", "FAILS", "UNDEFINED"}


def run_v03_state() -> tuple:
    """Existence and mtime of run/v03 and of everything in it. The folder exists after step 8 of PREREG section 8, so a test
    compares the state before and after instead of asserting that it is absent (R2-2)."""
    base = ROOT / "run" / "v03"
    if not base.exists():
        return (False, ())
    return (True, tuple(sorted((p.relative_to(base).as_posix(), p.stat().st_mtime_ns) for p in [base, *base.rglob("*")])))


class WorldSetTests(unittest.TestCase):
    def test_sets_are_valid_replaced_and_deterministic(self):
        sd = seeder(DEV_CORE)
        recs, rej = generate_valid_v03(3, sd, "world-test", "enc-test", "aux")
        again, _ = generate_valid_v03(3, sd, "world-test", "enc-test", "aux")
        self.assertEqual([r.world_seed for r in recs], [r.world_seed for r in again])
        self.assertTrue(all(r.world_seed == 930000 + r.draw and r.enc_seed == r.world_seed + 10000 for r in recs))
        self.assertTrue(all(r.aux_seed == r.world_seed + 20000 for r in recs))
        self.assertEqual(len(recs) + len(rej), recs[-1].draw + 1)  # a rejected draw is replaced by the next index
        self.assertTrue(all(r.h_size >= 10 and r.encoding.fit.usable for r in recs))
        cal, _ = generate_valid_v03(2, sd, "world-cal", "enc-cal", calibration=True)
        self.assertEqual(cal[0].world_seed, 930100 + cal[0].draw)
        self.assertIsNone(cal[0].aux_seed)

    def test_the_cap_stops_the_run(self):
        sd = seeder(DEV_CORE)
        with self.assertRaises(WorldSetError):
            generate_valid_v03(5, sd, "world-test", "enc-test", max_draws=3)  # 5 worlds cannot come from 3 draws
        with mock.patch("audit.v03.worldset.defined_default_metrics", lambda ex: False):  # every calibration world invalid
            with self.assertRaises(WorldSetError):
                generate_valid_v03(1, sd, "world-cal", "enc-cal", max_draws=4, calibration=True)
        recs, rej = generate_valid_v03(1, sd, "world-cal", "enc-cal", calibration=True)
        self.assertEqual(len(recs), 1)

    def test_a_generator_failure_is_a_rejected_draw(self):
        from tesaron.worlds import WorldGenerationError

        calls = []

        def build(ws, es):
            calls.append(ws)
            if len(calls) == 1:
                raise WorldGenerationError("x")
            return build_cached(ws, es)

        recs, rej = generate_valid_v03(1, seeder(DEV_CORE), "world-test", "enc-test", build=build)
        self.assertEqual(rej[0], {"draw": 0, "world_seed": 930000, "reason": "generator_failed"})
        self.assertEqual(recs[0].draw, 1)

    def test_the_encoder_seed_offset_and_the_v03_world(self):
        world, ctx, enc = build_cached(930000, 940000)
        self.assertEqual(len(world.params.source_reliabilities), 8)
        self.assertEqual(world.params.overlap_fraction, 0.8)
        self.assertEqual(ctx.encoder_seed, 940000)


class ControlsTests(unittest.TestCase):
    def test_controls_agree_on_a_development_world(self):
        rec = generate_valid_v03(1, seeder(DEV_CORE), "world-cal", "enc-cal", calibration=True)[0][0]
        for name, (ok, detail) in controls.run_controls_calibration_world(rec).items():
            self.assertTrue(ok, f"{name}: {detail}")
        ok, detail = controls.f1_restricted(rec)
        self.assertTrue(ok, detail)
        ok, detail = controls.f1_restricted(rec, alphas=(0.5, 0.9), ks=(0, 5, 10))
        self.assertTrue(ok, detail)


class PerWorldTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sd = seeder(DEV_CORE)
        cls.rec = generate_valid_v03(1, sd, "world-test", "enc-test", "aux")[0][0]
        cls.cal = RV.build_calibration(DEV_CORE, None, 5, 2)
        cls.sd = sd
        cls.ev = evaluate_world_v03(cls.rec, cls.cal.taus, sd, subprocess_checks=False, run_twins=True, keep_data=True)

    def test_shape_of_the_evaluation(self):
        ev = self.ev
        self.assertEqual(set(ev["fixed"]), set(ALL_TESTS))
        self.assertTrue(all(ev["fixed"][t]["outcome"] in VALID for t in ALL_TESTS))
        self.assertEqual(set(ev["twins"]), set(TWIN_TEST))
        self.assertTrue(all(v["outcome"] in VALID and v["test"] == TWIN_TEST[n] for n, v in ev["twins"].items()))
        self.assertEqual(len(ev["results"]), 30)
        self.assertEqual(len(ev["exacts_k0"]), 10)
        d = ev["descriptive"]
        self.assertEqual(len(d["t1_draw_sensitivity"]), 2)
        for key in ("t1_all_points", "t1_i6", "t1_i7", "t1_i8", "t1_i9"):
            self.assertIn(d[key], VALID)
        self.assertTrue(all(o in VALID for o in d["t1_draw_sensitivity"]))
        # n_q, the denominators of new_false, are design quantities: ten per k, whole numbers, the same at every k
        self.assertEqual(set(ev["n_q"]), set(ev["results"]))
        self.assertTrue(all(isinstance(n, int) and n >= 0 for n in ev["n_q"].values()))
        self.assertTrue(all(ev["n_q"][(a, 0)] == ev["n_q"][(a, 5)] == ev["n_q"][(a, 10)] for a in C.ALPHAS))
        self.assertTrue(all(e["n_q"] == ev["n_q"][(a, 0)] for a, e in zip(C.ALPHAS, ev["exacts_k0"])))
        self.assertIsInstance(d["default_feasible"], bool)
        self.assertIsInstance(d["g8_hyp_count"], int)
        self.assertIn("feasible_alphas", d["t1_structure"])
        # the structure arm is defined exactly when T-1 is
        self.assertTrue(d["t1_structure"]["defined"] == (ev["fixed"]["T-1"]["outcome"] != "UNDEFINED"))
        # G1-G6 are implementation tests: the fixed system must not fail them on a development world
        for t in ("G1", "G2", "G3", "G4", "G5", "G6"):
            self.assertNotEqual(ev["fixed"][t]["outcome"], "FAILS", t)

    def test_t1_reads_the_k0_line_only(self):
        ev = self.ev
        k0 = V.k_exacts(ev["results"], 0, ev["n_q"])
        direct = V.judge_t1(V.t1_data(k0, self.cal.taus.main))
        # bare booleans: a failure must not print a development outcome of T-1
        self.assertTrue(ev["fixed"]["T-1"]["outcome"] == {True: "HOLDS", False: "FAILS", None: "UNDEFINED"}[direct])
        # the arms that change one rule are the same reading with another tau, k or tolerance (I-9: delta only)
        d = ev["descriptive"]
        self.assertTrue(d["t1_i9"] == V.t1_outcome(k0, self.cal.taus.main, floor=False))
        self.assertTrue(d["t1_i8"] == V.t1_i8_outcome(ev["results"], self.cal.taus.i8))
        self.assertTrue(d["t1_i6"] == V.t1_outcome(V.k_exacts(ev["results"], 5, ev["n_q"]), self.cal.taus.i6))

    def test_blind_inputs_carry_no_metric_h_or_tau(self):
        test_doc = RV.blind_input(self.rec, self.ev, False)
        for forbidden in ("taus", "metrics", "H", "new_false", "new_true", "fidelity", "check_data"):
            self.assertNotIn(forbidden, test_doc)
        self.assertEqual(len(test_doc["source_reliabilities"]), 8)
        self.assertEqual(len(test_doc["configs"]), 30)
        self.assertEqual(set(test_doc["given_outcomes_g1_g6"]), {"G1", "G2", "G3", "G4", "G5", "G6"})
        self.assertEqual(test_doc["draw_index"], self.rec.draw)
        cal = self.cal.records[0]
        out0 = FIXED.evaluate_exact(cal.world, cal.context, cal.encoding, C.ALPHA0, 0)
        cal_doc = RV.blind_input(cal, out0[0], True)
        self.assertEqual(list(cal_doc["configs"]), ["0.7|0"])
        self.assertNotIn("given_outcomes_g1_g6", cal_doc)
        self.assertEqual(cal_doc["role"], "calibration")
        self.assertEqual(len(json.dumps(RV.fr_json(cal_doc))) > 0, True)

    def test_run_results_and_documents_are_json_ready(self):
        res = RV.run_results(self.rec, self.ev, {"F1": (True, "")}, self.cal.taus)
        json.dumps(RV.fr_json(res), allow_nan=False)
        self.assertEqual(set(res["f3"]), {"feasible", "pareto_front", "hypervolume", "outcomes", "t1_structure"})
        json.dumps(RV.fr_json(RV.per_world_doc(self.rec, self.ev)), allow_nan=False)


class CalibrationTests(unittest.TestCase):
    def test_calibration_sets_taus_and_documents(self):
        cal = RV.build_calibration(DEV_CORE, None, 6, 2)
        self.assertEqual(len(cal.records), 6)
        self.assertEqual(len(cal.alt_docs), 2)
        self.assertEqual(len(cal.taus.alt), 2)
        self.assertTrue(all(len(a["worlds"]) == 6 for a in cal.alt_docs))
        starts = [a["worlds"][0]["world_seed"] for a in cal.alt_docs]
        self.assertEqual(starts[0] // 200, 931000 // 200)  # alternative blocks start at 931000 and 931200
        self.assertEqual([s // 200 for s in starts], [4655, 4656])
        cal_doc, tau_doc = RV.calibration_documents(cal, DEV_CORE)
        self.assertEqual(set(cal_doc), {"core_sha256", "environment", "rule", "worlds", "rejected_draws", "alt_sets"})
        self.assertEqual(set(tau_doc), {"core_sha256", "rule", "main", "i6", "i7", "i8", "alt", "info"})
        self.assertEqual(RV.tau_set_from_json(tau_doc), cal.taus)
        again = RV.build_calibration(DEV_CORE, None, 6, 2)
        self.assertEqual(RV._roundtrip(RV.calibration_documents(again, DEV_CORE)[0]["alt_sets"]),
                         RV._roundtrip(cal_doc["alt_sets"]))
        # no new_false or new_true leaves a calibration world
        self.assertNotIn("new_false", json.dumps(RV.fr_json(cal_doc)))
        self.assertNotIn("new_true", json.dumps(RV.fr_json(cal_doc)))
        i7 = cal.taus.i7  # D1 on (up to) the first 10 of the worlds
        self.assertEqual(i7.tau_s, min(m["fidelity"] for m in cal.main_four))
        # I-8 (R1-8): D1 on the first 10 worlds at (alpha0, k0 = 5), computed in calibrate; fewer than 10 worlds: all of them
        i8 = cal.taus.i8
        self.assertEqual((i8.tau_s, i8.tau_t), (min(m["fidelity"] for m in cal.k5_four[:10]),
                                                min(m["consistency"] for m in cal.k5_four[:10])))
        self.assertEqual((i8.tau_d, i8.tau_b), (max(m["deviation"] for m in cal.k5_four[:10]),
                                                max(m["uncertainty"] for m in cal.k5_four[:10])))
        self.assertEqual(i8, d1_first(cal.k5_four))
        self.assertEqual(RV.tau_set_from_json(RV.tau_set_json(cal.taus)).i8, i8)
        self.assertEqual(cal_doc["worlds"][0]["metrics_exact_k5"].keys(), cal_doc["worlds"][0]["metrics_exact_k0"].keys())
        self.assertEqual(cal.taus.main.tau_d, sorted((m["deviation"] for m in cal.main_four), reverse=True)[3])


class FailedAlternativeSetTests(unittest.TestCase):
    """R1-14: a draw-sensitivity set that does not reach 40 valid worlds within 200 draws has no tau and counts as "insufficient
    worlds" in that arm; it never stops the run. The failure is forced (the generator is patched for one alternative set)."""

    FAILING = "world-calalt-1"
    CORE, SALT = "c" * 64, "5" * 64

    def patched(self):
        real = RV.generate_valid_v03

        def fake(n, sd, world_role, *args, **kw):
            if world_role == self.FAILING:
                raise WorldSetError("only 3 valid worlds of 40 within 200 draws (197 rejected)")
            return real(n, sd, world_role, *args, **kw)

        return mock.patch.object(RV, "generate_valid_v03", fake)

    def test_the_failed_set_has_no_tau_and_the_others_do(self):
        with self.patched():
            cal = RV.build_calibration(DEV_CORE, None, 5, 3)
        self.assertEqual(len(cal.taus.alt), 3)
        self.assertIsNone(cal.taus.alt[1])
        self.assertTrue(cal.taus.alt[0] is not None and cal.taus.alt[2] is not None)
        failed = cal.alt_docs[1]
        self.assertEqual((failed["b"], failed["worlds"], failed["rejected_draws"]), (1, [], []))
        self.assertIn("only 3 valid worlds of 40", failed["failed"])
        self.assertNotIn("failed", cal.alt_docs[0])
        # the documents hold a null tau and round-trip
        tau_json = RV.tau_set_json(cal.taus)
        self.assertIsNone(tau_json["alt"][1])
        self.assertEqual(RV.tau_set_from_json(RV._roundtrip(tau_json)), cal.taus)
        # the development calibration document says it without a number
        doc = redact.redact_checked(RV.dev_calibration_document(cal))
        self.assertEqual([a["failed"] for a in doc["alt_sets"]], [False, True, False])
        self.assertIsNone(doc["taus"]["tau_alt"][1])

    def test_a_world_is_read_under_no_tau_as_no_tau_and_the_arm_counts_it_as_insufficient(self):
        with self.patched():
            cal = RV.build_calibration(DEV_CORE, None, 5, 3)
        sd = seeder(DEV_CORE)
        rec = generate_valid_v03(1, sd, "world-test", "enc-test", "aux")[0][0]
        ev = evaluate_world_v03(rec, cal.taus, sd, subprocess_checks=False, run_twins=False, keep_data=False)
        arms = ev["descriptive"]["t1_draw_sensitivity"]
        self.assertEqual(len(arms), 3)
        self.assertTrue(arms[1] == V.NO_TAU and arms[0] in VALID and arms[2] in VALID)
        counts = AG.draw_sensitivity_counts([[a] * 50 for a in arms])
        self.assertEqual((counts["insufficient"] >= 1, counts["n_no_tau"], counts["verdicts"][1]), (True, 1, "INSUFFICIENT"))
        self.assertEqual(counts["n_draws"], 3)

    def test_the_dev_run_goes_on_and_the_real_steps_recheck_the_null_tau(self):
        with self.patched():
            with tempfile.TemporaryDirectory() as tmp:
                lines = RV.run_dev("test", Path(tmp), 5, 2, 3, False)  # the run is not stopped by the failed set
                doc = json.loads((Path(tmp) / "DEV_TEST.json").read_text(encoding="utf-8"))
                self.assertEqual(redact.find_violations(doc), [])
                self.assertEqual(doc["n_alt"], 3)
                self.assertTrue(any("definedness T-1" in ln for ln in lines))
            with tempfile.TemporaryDirectory() as tmp:
                inputs = Path(tmp) / "inputs"
                RV.run_calibrate(self.CORE, self.SALT, inputs, 5, 3)
                tau = json.loads((inputs / "TAU.json").read_text(encoding="utf-8"))
                self.assertIsNone(tau["alt"][1])
                cal = RV.recheck_calibration(self.CORE, self.SALT, inputs, 5, 3)  # regenerated: equal, null tau included
                self.assertIsNone(cal.taus.alt[1])
                # a committed tau where the regenerated one is null (or the other way round) is refused
                tau["alt"][1] = tau["alt"][0]
                (inputs / "TAU.json").write_text(json.dumps(tau, indent=1, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
                with self.assertRaises(RV.Refused):
                    RV.recheck_calibration(self.CORE, self.SALT, inputs, 5, 3)

    def test_the_verdict_table_is_built_with_a_failed_set(self):
        with self.patched():
            cal = RV.build_calibration(DEV_CORE, None, 5, 3)
            bundle = RV.evaluate_tests(seeder(DEV_CORE), cal, 2, False)
        ds = bundle.draw_sensitivity
        self.assertEqual((ds["n_draws"], ds["n_no_tau"]), (3, 1))
        self.assertTrue(ds["insufficient"] >= 1 and ds["verdicts"][1] == "INSUFFICIENT")
        self.assertTrue(isinstance(bundle.table, dict) and len(bundle.table["rows"]) == 8)


class DevRunTests(unittest.TestCase):
    def test_dev_run_outputs_contain_no_forbidden_key_or_value(self):
        run_before = run_v03_state()
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            lines = RV.run_dev("test", out, 5, 3, 2, False)
            lines += RV.run_dev("calibrate", out, 5, 3, 2, False)
            self.assertEqual(sorted(p.name for p in out.iterdir()), ["DEV_CALIBRATION.json", "DEV_TEST.json"])
            for name in ("DEV_TEST.json", "DEV_CALIBRATION.json"):
                text = (out / name).read_text(encoding="utf-8")
                self.assertNotIn("\r", text)  # LF line endings
                doc = json.loads(text)
                text = text.replace(redact.ALLOWED_PHRASES[0], "")  # the fixed G7a sentence names new_true in a definition
                self.assertEqual(redact.find_violations(doc), [])
                for pat in ("new_false", "new_true", "largest_increase", "sources_spanned", "wrong_class",
                            "T-1 holds", "T-1 does not hold", "G8 (descriptive"):
                    self.assertNotIn(pat, text, pat)
            doc = json.loads((out / "DEV_TEST.json").read_text(encoding="utf-8"))
            rows = {r["test"]: r for r in doc["table"]["rows"]}
            self.assertEqual(rows["T-1"], {"test": "T-1", "verdict_row": "REDACTED"})
            self.assertEqual(doc["g8_descriptive"], "REDACTED")
            self.assertEqual({w["outcomes"]["T-1"] for w in doc["worlds"]}, {"REDACTED"})
            self.assertEqual({w["outcomes"]["G8"] for w in doc["worlds"]}, {"REDACTED"})
            self.assertEqual({w["twins"]["NT"] for w in doc["worlds"]}, {"REDACTED"})
            for key in ("t1_all_points", "t1_i6", "t1_i7", "t1_i8", "t1_i9", "t1_draw_sensitivity", "t1_structure"):
                self.assertTrue({w["descriptive"][key] for w in doc["worlds"]} == {"REDACTED"}, key)  # no per-world outcome
            for key in ("t1_all_points", "t1_i6", "t1_i7", "t1_i8", "t1_i9", "t1_structure", "draw_sensitivity"):
                self.assertTrue(doc["descriptive"][key] == "REDACTED", key)  # no aggregate either
            self.assertIn("tau_i8", doc["taus"])  # the I-8 tau is a design quantity
            self.assertTrue(all(isinstance(doc["taus"]["tau_i8"][k], str) for k in ("tau_s", "tau_d", "tau_t", "tau_b")))
            self.assertTrue(all(w["outcomes"][t] in VALID for w in doc["worlds"] for t in ("G1", "G2", "G7")))
            self.assertEqual(doc["definedness"][-1]["test"], "T-1")
            joined = "\n".join(lines).replace(redact.ALLOWED_PHRASES[0], "")
            for pat in ("new_false", "new_true", "T-1 holds", "T-1 does not hold", "T-1 is not demonstrated",
                        "G8 (descriptive", "largest increase", "t1_i8", "t1_i9", "I-8", "I-9"):
                self.assertNotIn(pat, joined, pat)
            self.assertIn("tau_i8", joined)  # taus are printed, outcomes are not
            self.assertIn("all_true, not judged", joined)  # the G7a row carries the all_true sentence
            self.assertIn("T-1: REDACTED", joined)
        self.assertEqual(run_v03_state(), run_before)  # nothing went into run/v03

    def test_the_console_survives_a_legacy_windows_code_page(self):
        """The G7a sentence has an alpha: with the console encoding forced to cp1252 the dev runner must still print it (it
        switches stdout to UTF-8), where it used to die with a UnicodeEncodeError."""
        import os
        import subprocess
        import sys

        with tempfile.TemporaryDirectory() as tmp:
            env = dict(os.environ, PYTHONIOENCODING="cp1252", PYTHONDONTWRITEBYTECODE="1")
            res = subprocess.run([sys.executable, "-B", "-m", "audit.v03.run_v03", "test", "--dev-redacted", "--out", tmp,
                                  "--n-cal", "5", "--n-test", "2", "--n-alt", "1", "--no-subprocess"],
                                 cwd=ROOT, env=env, capture_output=True, timeout=900)
            self.assertEqual(res.returncode, 0, res.stderr.decode("utf-8", "replace")[-300:])
            out = res.stdout.decode("utf-8")
            self.assertIn("all_true, not judged", out)
            self.assertIn("T-1: REDACTED", out)

    def test_every_dev_print_goes_through_the_boundary(self):
        # the runner's only writer in development mode is run_dev, whose document is built by redact_checked
        import inspect

        src = inspect.getsource(RV.run_dev)
        self.assertEqual(src.count("redact.redact_checked("), 2)
        self.assertNotIn("print(", src)
        self.assertIn("dev_summary_lines(doc)", src)


class RealStepsInATempFolderTests(unittest.TestCase):
    """The real calibrate / test steps without the git checks, with a made-up core and salt (so with seeds that are not
    development seeds), into a temporary folder. The files are only counted, hashed and compared, never read for a value."""

    CORE, SALT = "c" * 64, "5" * 64
    SIZES = (5, 2, 2)  # n_cal, n_test, n_alt

    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        cls.root = Path(cls._tmp.name)
        cls.inputs = cls.root / "inputs"
        RV.run_calibrate(cls.CORE, cls.SALT, cls.inputs, cls.SIZES[0], cls.SIZES[2])

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def test_calibration_files(self):
        self.assertEqual(sorted(p.name for p in self.inputs.iterdir()), ["CAL_WORLDS.json", "TAU.json"])
        for p in self.inputs.iterdir():
            self.assertNotIn(b"\r", p.read_bytes())
        cal = json.loads((self.inputs / "CAL_WORLDS.json").read_text(encoding="utf-8"))
        tau = json.loads((self.inputs / "TAU.json").read_text(encoding="utf-8"))
        self.assertEqual((len(cal["worlds"]), len(cal["alt_sets"])), (5, 2))
        self.assertEqual(set(tau), {"core_sha256", "rule", "main", "i6", "i7", "i8", "alt", "info", "cal_worlds_sha256"})
        self.assertEqual(len(tau["alt"]), 2)
        self.assertEqual(tau["cal_worlds_sha256"], RV._sha(self.inputs / "CAL_WORLDS.json"))
        with self.assertRaises(RV.Refused):  # a real run never overwrites
            RV.run_calibrate(self.CORE, self.SALT, self.inputs, 5, 2)
        cal0 = cal["worlds"][0]
        self.assertTrue(1_000_000 <= cal0["world_seed"] < 1_000_000_000 + 1_000_000)
        self.assertEqual(set(cal0["metrics_exact_k0"]), {"fidelity", "deviation", "consistency", "uncertainty"})

    def test_recheck_refuses_a_changed_world_or_tau(self):
        RV.recheck_calibration(self.CORE, self.SALT, self.inputs, *(self.SIZES[0], self.SIZES[2]))  # the untouched files
        for name, mutate in (("TAU.json", lambda d: d["alt"][0].__setitem__("tau_s", "1/1")),
                             ("TAU.json", lambda d: d["main"].__setitem__("tau_b", "1/1")),
                             ("TAU.json", lambda d: d["i8"].__setitem__("tau_d", "1/1")),  # the I-8 tau is rechecked in test
                             ("CAL_WORLDS.json", lambda d: d["alt_sets"][1]["worlds"][0].__setitem__("draw", 99))):
            folder = self.root / f"tamper_{name}_{id(mutate)}"
            folder.mkdir()
            for f in ("TAU.json", "CAL_WORLDS.json"):
                (folder / f).write_bytes((self.inputs / f).read_bytes())
            doc = json.loads((folder / name).read_text(encoding="utf-8"))
            mutate(doc)
            (folder / name).write_text(json.dumps(doc, indent=1, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
            if name == "CAL_WORLDS.json":  # keep the recorded hash consistent so that the world comparison is what refuses
                tau = json.loads((folder / "TAU.json").read_text(encoding="utf-8"))
                tau["cal_worlds_sha256"] = RV._sha(folder / "CAL_WORLDS.json")
                (folder / "TAU.json").write_text(json.dumps(tau, indent=1, sort_keys=True) + "\n", encoding="utf-8",
                                                 newline="\n")
            with self.assertRaises(RV.Refused):
                RV.recheck_calibration(self.CORE, self.SALT, folder, self.SIZES[0], self.SIZES[2])
        with self.assertRaises(RV.Refused):  # another core hash
            RV.recheck_calibration("d" * 64, self.SALT, self.inputs, self.SIZES[0], self.SIZES[2])

    def test_test_step_writes_everything_at_the_end_and_is_reproducible(self):
        n_cal, n_test, n_alt = self.SIZES
        out1, out2 = self.root / "run1", self.root / "run2"
        RV.run_test(self.CORE, self.SALT, out1, n_cal, n_test, n_alt, self.inputs)
        names = sorted(p.name for p in out1.iterdir())
        self.assertEqual(names, ["RESULTS.json", "TEST_WORLDS.json", "VERDICTS.json", "outputs_input", "outputs_results"])
        self.assertEqual(len(list((out1 / "outputs_input").glob("cal_*.json"))), n_cal)
        self.assertEqual(len(list((out1 / "outputs_input").glob("[0-9]*.json"))), n_test)
        self.assertEqual(len(list((out1 / "outputs_results").glob("*.json"))), n_cal + n_test)
        for p in out1.rglob("*.json"):
            self.assertNotIn(b"\r", p.read_bytes(), p.name)
            json.loads(p.read_text(encoding="utf-8"))
        with self.assertRaises(RV.Refused):  # a real run never overwrites its outputs
            RV.run_test(self.CORE, self.SALT, out1, n_cal, n_test, n_alt, self.inputs)
        RV.run_test(self.CORE, self.SALT, out2, n_cal, n_test, n_alt, self.inputs)
        self.assertTrue(RV._sha(out1 / "VERDICTS.json") == RV._sha(out2 / "VERDICTS.json"))  # byte for byte
        self.assertTrue(RV._sha(out1 / "RESULTS.json") == RV._sha(out2 / "RESULTS.json"))

    def test_a_control_disagreement_stops_the_run_and_writes_only_stopped(self):
        out = self.root / "stopped"
        bad = {"F1": (False, "x"), "F2": (True, ""), "F4": (True, "")}
        with mock.patch.object(RV, "run_controls_test_world", lambda rec: bad):
            with self.assertRaises(RV.ControlDisagreement):
                RV.run_test(self.CORE, self.SALT, out, *self.SIZES[:1], 2, self.SIZES[2], self.inputs)
        self.assertEqual([p.name for p in out.iterdir()], ["STOPPED.json"])

    def test_missing_calibration_files_are_refused(self):
        with self.assertRaises(RV.Refused):
            RV.run_test(self.CORE, self.SALT, self.root / "none", 5, 2, 2, self.root / "empty")


if __name__ == "__main__":
    unittest.main()
