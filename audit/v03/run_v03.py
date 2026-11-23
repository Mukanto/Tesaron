"""Calibration and test runner for Tesaron v0.3 (PREREG_v0.3 sections 7, 8 and 9).

    py -m audit.v03.run_v03 calibrate      # real mode: writes run/v03/CAL_WORLDS.json and run/v03/TAU.json
    py -m audit.v03.run_v03 test           # real mode: writes run/v03/TEST_WORLDS.json, RESULTS.json, VERDICTS.json,
                                           #            outputs_input/ (the blind F3 inputs) and outputs_results/
    py -m audit.v03.run_v03 reproduce      # real mode, in a clone of the result commit: reruns the test step into
                                           #            run/v03_repro/ and compares sha256 of its VERDICTS.json
    py -m audit.v03.run_v03 calibrate --dev-redacted --out DIR [--n-cal N] [--n-alt N]
    py -m audit.v03.run_v03 test --dev-redacted --out DIR [--n-cal N] [--n-test N] [--n-alt N] [--no-subprocess]

Real mode (PREREG section 8, steps 9-11) refuses to start unless all of this holds:
  - Python 3.14.2 and NumPy 2.4.1;
  - the manifest prereg/v03/FREEZE_v0.3.json verifies (audit/freeze.py) and this file is listed in it;
  - exactly one commit (full history) touches the manifest; it is an ancestor of origin/main (the local remote-tracking ref;
    the runner does no fetch and uses no network); the manifest lists exactly the files that the freeze commit tracks under
    the manifest paths of section 9; the manifest and every frozen file are tracked, unmodified and identical to their
    content in the freeze commit;
  - run/v03/SALT.json is touched by exactly one commit, a strict descendant of the freeze commit and an ancestor of
    origin/main; it is unmodified, names the freeze commit and the core hash of the manifest, and holds a 64-digit salt.
`test` and `reproduce` additionally need run/v03/CAL_WORLDS.json and run/v03/TAU.json, each touched by exactly one commit, a
strict descendant of the salt commit and on origin/main; `test` regenerates the calibration worlds, recomputes every tau
exactly and refuses unless the world records and every tau equal the committed ones.
`test` runs F1, F2 and F4 on all test worlds and on the main calibration worlds first; any disagreement stops the run (only
STOPPED.json is written) and no verdict is given. Everything is held in memory and written only at the end (a crash leaves no
outcome on disk). `reproduce` refuses if run/v03_repro/ exists or if run/v03/VERDICTS.json is not committed and unmodified.

Development mode (`--dev-redacted`): core "dev", the development seed mapping of audit.v03.seeds (930000 upward), no git
checks, and NO PILOT (PREREG section 2): everything printed or written goes through `audit.v03.redact.redact_checked`, which
replaces every new_false / new_true value, T-1 and G8 outcome, T-1 structure field, T-1 verdict row, draw-sensitivity verdict
and I-2 / I-6 / I-7 / I-8 / I-9 outcome by "REDACTED". It writes only DEV_CALIBRATION.json or DEV_TEST.json into --out (never into run/).

Exit codes: 0 done; 2 usage error; 3 a precondition failed; 5 a fidelity control disagreed; 6 not enough valid worlds;
7 reproduce: the rerun's VERDICTS.json differs from the committed one.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import re
import sys
import time
from fractions import Fraction
from pathlib import Path

import numpy as np

from audit import checks as C
from audit import freeze as freeze_tool
from audit.exact import frac_str, hypervolume_exact, pareto_front_exact, pareto_points, feasible
from audit.per_world import exact_json, grid_listing
from audit.run_v02 import (
    ControlDisagreement, EXIT_CONTROL, EXIT_REFUSED, EXIT_REPRO, EXIT_USAGE, EXIT_WORLDS, Refused, _batches,
    _rule_json, _sha, _units_json, _write_json, check_committed_clean, check_pushed, check_tau_after_salt,
    check_versions, env_info, is_ancestor, manifest_repo_paths, unique_commit, verify_freeze, world_record_json,
)
from audit.v03 import redact
from audit.v03.aggregate import (
    all_true_summary, draw_sensitivity_counts, g8_descriptive, t1_verdict_of, undefined_as_fails, verdict_table,
)
from audit.v03.checks import K_CAL, decided_outside_count, f3_structure_json, structure_json
from audit.v03.controls import run_controls_calibration_world, run_controls_test_world
from audit.v03.per_world import ALL_TESTS, TWIN_TEST, TauSet, evaluate_world_v03
from audit.v03.seeds import DEV_CORE, calalt_role, seeder
from audit.v03.tau import (
    TAU_NAMES, calibration_four, d1_first, metrics_to_json, q40, taus_from_json, taus_to_json,
)
from audit.v03.worldset import WorldSetError, generate_valid_v03
from audit.system import FIXED
from tesaron.criterion.metrics import compute_H

ROOT = Path(__file__).resolve().parent.parent.parent
MANIFEST_REL = "prereg/v03/FREEZE_v0.3.json"
SALT_REL = "run/v03/SALT.json"
CAL_REL = "run/v03/CAL_WORLDS.json"
TAU_REL = "run/v03/TAU.json"
OUT_REL = "run/v03"
REPRO_REL = "run/v03_repro"
MANIFEST = ROOT / MANIFEST_REL
N_CAL, N_TEST, N_ALT = 40, 50, 20
# PREREG section 9, files in the manifest: the pre-registration, both specs, the code, the design studies and the tests
MANIFEST_PATHS_V03 = ("prereg/PREREG_v0.3.md", "SPEC.md", "SPEC_v0.3.md", "tesaron", "audit", "prereg/v03",
                      "pyproject.toml", "tests")
STUDY_JSON = re.compile(r"prereg/v03/[^/]+\.json")  # "prereg/v03/*.json": the files directly in the folder
RULE_TEXT = ("Q-40: tau_s = 4th smallest fidelity, tau_t = 4th smallest consistency, tau_d = 4th largest deviation, "
             "tau_b = 4th largest uncertainty over the 40 calibration worlds, duplicates included, exact fractions; main "
             "tau at (alpha0 = 0.7, k = 0); I-6 at (alpha0, k0 = 5); I-7: D1 (min / max) on the first 10 worlds at k = 0; "
             "I-8: D1 on the first 10 worlds at (alpha0, k0 = 5); alt: Q-40 at (alpha0, 0) on each alternative set (null "
             "for a set that did not reach 40 valid worlds within 200 draws)")
OUTPUT_NAMES = ("TEST_WORLDS.json", "RESULTS.json", "VERDICTS.json", "STOPPED.json", "outputs_input", "outputs_results")


# ------------------------------------------------------------------------------------------------ git checks (real mode)
def tracked_manifest_files(tracked: list, manifest_rel: str = MANIFEST_REL) -> set:
    """From the names `git ls-tree -r` gives under the manifest paths, the files the manifest must list. Under
    prereg/v03 these are the .json files directly in that folder (PREREG 9: "prereg/v03/*.json", not the blind-review
    folder, not the freeze record) except the manifest itself, which cannot list itself."""
    out = set()
    for name in tracked:
        if name.startswith("prereg/v03/"):
            if STUDY_JSON.fullmatch(name) and name != manifest_rel:
                out.add(name)
        else:
            out.add(name)
    return out


def check_manifest_coverage_v03(repo: Path, freeze_commit: str, manifest_path: Path) -> None:
    """The manifest lists exactly the files that the freeze commit tracks under the manifest paths of section 9."""
    import subprocess

    tracked = []
    for batch in _batches(list(MANIFEST_PATHS_V03)):
        res = subprocess.run(["git", "ls-tree", "-r", "--name-only", freeze_commit, "--", *batch], cwd=repo,
                             capture_output=True, text=True)
        if res.returncode != 0:
            raise Refused("cannot list the files of the freeze commit")
        tracked += [line for line in res.stdout.splitlines() if line]
    wanted = tracked_manifest_files(tracked)
    listed = set(manifest_repo_paths(repo, manifest_path)) - {manifest_path.resolve().relative_to(repo.resolve()).as_posix()}
    missing, extra = sorted(wanted - listed), sorted(listed - wanted)
    if missing or extra:
        what = [f"tracked but not in the manifest: {missing[0]}"] if missing else []
        what += [f"in the manifest but not tracked under the manifest paths: {extra[0]}"] if extra else []
        raise Refused("the manifest does not cover the frozen tree (" + "; ".join(what) + ")")


def check_freeze_and_salt_v03(repo: Path, core: str):
    """(freeze commit, salt commit, salt); PREREG section 8 step 9."""
    from audit.run_v02 import check_frozen_tree

    manifest_path = repo / MANIFEST_REL
    freeze_commit = unique_commit(repo, MANIFEST_REL)
    check_pushed(repo, freeze_commit)
    check_frozen_tree(repo, freeze_commit, manifest_path)
    check_manifest_coverage_v03(repo, freeze_commit, manifest_path)
    check_committed_clean(repo, SALT_REL)
    salt_commit = unique_commit(repo, SALT_REL)
    if salt_commit == freeze_commit or not is_ancestor(repo, freeze_commit, salt_commit):
        raise Refused(f"{SALT_REL} is not committed in a descendant of the freeze commit")
    check_pushed(repo, salt_commit, "the salt commit")
    try:
        doc = json.loads((repo / SALT_REL).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise Refused(f"{SALT_REL} is not readable JSON") from exc
    if not isinstance(doc, dict) or doc.get("freeze_commit") != freeze_commit:
        raise Refused(f"{SALT_REL} does not name the freeze commit")
    if doc.get("core_sha256") != core:
        raise Refused(f"{SALT_REL} core_sha256 differs from the core hash of the verified manifest")
    salt = doc.get("salt")
    if not isinstance(salt, str) or not re.fullmatch(r"[0-9a-f]{64}", salt):
        raise Refused(f"{SALT_REL} has no salt of 32 random bytes (64 hex digits)")
    return freeze_commit, salt_commit, salt


def real_preconditions(mode: str):
    """(core, salt) after every real-mode check of PREREG section 8 steps 9 and 10."""
    check_versions()
    entry = Path(__file__).resolve()
    core = verify_freeze(MANIFEST, entry)
    _, salt_commit, salt = check_freeze_and_salt_v03(ROOT, core)
    if mode in ("test", "reproduce"):
        check_tau_after_salt(ROOT, salt_commit, TAU_REL, CAL_REL)
    return core, salt


# ------------------------------------------------------------------------------------------------ json helpers
def fr_json(obj):
    """Fractions as "p/q" strings, recursively; everything else as is (for `_write_json`)."""
    if isinstance(obj, Fraction):
        return frac_str(obj)
    if isinstance(obj, dict):
        return {str(k): fr_json(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [fr_json(v) for v in obj]
    return obj


def _roundtrip(obj):
    """The JSON that _write_json would store, read back (stored and regenerated documents then compare equal)."""
    from audit.run_v02 import to_jsonable_keep

    return json.loads(json.dumps(to_jsonable_keep(fr_json(obj)), sort_keys=True, allow_nan=False))


# ------------------------------------------------------------------------------------------------ calibration
@dataclasses.dataclass
class Calibration:
    records: list  # the main calibration WorldRecords (kept: the controls and the blind inputs need them)
    rejected: list
    main_four: list  # four metrics at (alpha0, 0) per main world
    k5_four: list
    alt_docs: list  # per alternative set: {"b", "worlds", "rejected_draws"}
    taus: TauSet


def build_calibration(core: str, salt: str | None, n_cal: int, n_alt: int) -> Calibration:
    """The main calibration set, the alternative sets and every tau (PREREG section 8 step 9). Only the main set's records
    are kept; an alternative set is reduced to its record dicts and its tau."""
    sd = seeder(core, salt)
    records, rejected = generate_valid_v03(n_cal, sd, "world-cal", "enc-cal", calibration=True)
    m0 = [calibration_four(r, K_CAL) for r in records]
    m5 = [calibration_four(r, C.K0) for r in records]
    alt_docs, alt_taus = [], []
    for b in range(n_alt):
        try:
            recs, rej = generate_valid_v03(n_cal, sd, calalt_role("world", b), calalt_role("enc", b), calibration=True)
        except WorldSetError as exc:  # R1-14: a draw-sensitivity set without 40 valid worlds has no tau and never stops the run
            alt_docs.append({"b": b, "worlds": [], "rejected_draws": [], "failed": str(exc)})
            alt_taus.append(None)
            continue
        mb = [calibration_four(r, K_CAL) for r in recs]
        alt_docs.append({"b": b, "worlds": [dict(world_record_json(r), metrics_exact_k0=metrics_to_json(m))
                                            for r, m in zip(recs, mb)], "rejected_draws": rej})
        alt_taus.append(q40(mb))
    taus = TauSet(main=q40(m0), i6=q40(m5), i7=d1_first(m0), i8=d1_first(m5), alt=tuple(alt_taus))
    return Calibration(records, rejected, m0, m5, alt_docs, taus)


def tau_set_json(t: TauSet) -> dict:
    return {"main": taus_to_json(t.main), "i6": taus_to_json(t.i6), "i7": taus_to_json(t.i7), "i8": taus_to_json(t.i8),
            "alt": [None if x is None else taus_to_json(x) for x in t.alt]}


def tau_set_from_json(doc: dict) -> TauSet:
    return TauSet(taus_from_json(doc["main"]), taus_from_json(doc["i6"]), taus_from_json(doc["i7"]),
                  taus_from_json(doc["i8"]), tuple(None if x is None else taus_from_json(x) for x in doc["alt"]))


def calibration_documents(cal: Calibration, core: str) -> tuple[dict, dict]:
    """(CAL_WORLDS.json document, TAU.json document without the hash of the former)."""
    worlds = [dict(world_record_json(r), metrics_exact_k0=metrics_to_json(m0), metrics_exact_k5=metrics_to_json(m5))
              for r, m0, m5 in zip(cal.records, cal.main_four, cal.k5_four)]
    cal_doc = {"core_sha256": core, "environment": env_info(), "rule": RULE_TEXT, "worlds": worlds,
               "rejected_draws": cal.rejected, "alt_sets": cal.alt_docs}
    tau_doc = {"core_sha256": core, "rule": RULE_TEXT, **tau_set_json(cal.taus),
               "info": {"n_cal": len(cal.records), "n_alt": len(cal.alt_docs)}}
    return cal_doc, tau_doc


def run_calibrate(core: str, salt: str | None, out: Path, n_cal: int, n_alt: int) -> dict:
    cal = build_calibration(core, salt, n_cal, n_alt)
    cal_doc, tau_doc = calibration_documents(cal, core)
    _write_json(out / "CAL_WORLDS.json", fr_json(cal_doc), overwrite=False)
    tau_doc["cal_worlds_sha256"] = _sha(out / "CAL_WORLDS.json")
    _write_json(out / "TAU.json", fr_json(tau_doc), overwrite=False)
    return {"n_rejected": len(cal.rejected), "n_alt": n_alt, "taus": cal.taus}


def recheck_calibration(core: str, salt: str, inputs: Path, n_cal: int, n_alt: int) -> Calibration:
    """PREREG step 10: regenerate the calibration worlds and every tau; refuse unless the world records, the rejected draws,
    the alternative sets and every tau equal the committed CAL_WORLDS.json and TAU.json exactly, and the hash of the
    former is the one recorded in the latter."""
    tau_path, cal_path = inputs / "TAU.json", inputs / "CAL_WORLDS.json"
    stored_tau = json.loads(tau_path.read_text(encoding="utf-8"))
    stored_cal = json.loads(cal_path.read_text(encoding="utf-8"))
    if stored_tau.get("core_sha256") != core or stored_cal.get("core_sha256") != core:
        raise Refused("CAL_WORLDS.json or TAU.json was made for another core hash")
    if _sha(cal_path) != stored_tau.get("cal_worlds_sha256"):
        raise Refused("sha256(CAL_WORLDS.json) does not match TAU.json")
    cal = build_calibration(core, salt, n_cal, n_alt)
    cal_doc, tau_doc = calibration_documents(cal, core)
    for key in ("worlds", "rejected_draws", "alt_sets"):
        if _roundtrip(cal_doc[key]) != stored_cal.get(key):
            raise Refused(f"the regenerated calibration {key} differ from CAL_WORLDS.json")
    for key in ("main", "i6", "i7", "i8", "alt"):
        if _roundtrip(tau_doc[key]) != stored_tau.get(key):
            raise Refused(f"the recomputed tau ({key}) differs from TAU.json")
    return cal


# ------------------------------------------------------------------------------------------------ the test step
@dataclasses.dataclass
class TestBundle:
    __test__ = False  # not a pytest class
    records: list
    rejected: list
    controls: dict
    cal_controls: dict
    per_world: list  # [(WorldRecord, evaluation)]
    seconds: list
    table: dict
    g8: dict
    desc: dict
    draw_sensitivity: dict


def run_all_controls(cal: Calibration, records: list, on_stop=None) -> tuple[dict, dict]:
    """F1, F2 and F4 on all test worlds and on the main calibration worlds, before any check runs (PREREG step 10)."""
    cal_ctl, test_ctl = {}, {}
    for kind, recs, fn, sink in (("calibration", cal.records, run_controls_calibration_world, cal_ctl),
                                 ("test", records, run_controls_test_world, test_ctl)):
        for rec in recs:
            sink[rec.world_seed] = fn(rec)
            bad = {k: v[1] for k, v in sink[rec.world_seed].items() if not v[0]}
            if bad:
                if on_stop:
                    on_stop(kind, rec.world_seed, bad)
                raise ControlDisagreement(f"{kind} world {rec.world_seed}: {bad}")
    return cal_ctl, test_ctl


def evaluate_tests(sd, cal: Calibration, n_test: int, subprocess_checks: bool, on_stop=None) -> TestBundle:
    records, rejected = generate_valid_v03(n_test, sd, "world-test", "enc-test", "aux")
    cal_ctl, controls = run_all_controls(cal, records, on_stop)
    per_world, seconds = [], []
    for rec in records:
        t0 = time.perf_counter()
        ev = evaluate_world_v03(rec, cal.taus, sd, subprocess_checks=subprocess_checks, run_twins=True, keep_data=True)
        per_world.append((rec, ev))
        seconds.append(time.perf_counter() - t0)
    per_test = {t: [(rec.world_seed, ev["fixed"][t]["outcome"]) for rec, ev in per_world] for t in ALL_TESTS}
    twin_summary, both = {}, {}
    for name, test in TWIN_TEST.items():
        outcomes = [ev["twins"][name]["outcome"] for _, ev in per_world]
        n_both = sum(ev["fixed"][test]["outcome"] == "HOLDS" and ev["twins"][name]["outcome"] == "HOLDS"
                     for _, ev in per_world)
        twin_summary[name] = {"test": test, "both_hold": n_both, **{o: outcomes.count(o) for o in
                                                                    ("HOLDS", "FAILS", "UNDEFINED")}}
    for test in ALL_TESTS:
        both[test] = sum(
            ev["fixed"][test]["outcome"] == "HOLDS"
            and any(ev["twins"][nm]["outcome"] == "HOLDS" for nm, t in TWIN_TEST.items() if t == test)
            for _, ev in per_world)
    n_alt = len(cal.taus.alt)
    ds = draw_sensitivity_counts([[ev["descriptive"]["t1_draw_sensitivity"][b] for _, ev in per_world]
                                  for b in range(n_alt)])
    structure = [ev["descriptive"]["t1_structure"] for _, ev in per_world]
    all_true = all_true_summary([ev["descriptive"]["all_true"] for _, ev in per_world])
    table = verdict_table(
        per_test, both, failed_parts={rec.world_seed: ev["fixed"]["G1"]["failed_parts"] for rec, ev in per_world},
        structure=structure, draw_sensitivity=ds, all_true=all_true)
    g8 = g8_descriptive(per_test["G8"], [ev["descriptive"]["g8_hyp_count"] for _, ev in per_world],
                        [ev["descriptive"]["g8_single_atom_only"] for _, ev in per_world])
    cross = [ev["descriptive"]["cross_seed"] for _, ev in per_world if ev["descriptive"]["cross_seed"]]
    pooled = lambda n_key, a_key: {"agree": sum(c[a_key] for c in cross), "n": sum(c[n_key] for c in cross)}
    count3 = lambda key: {o: sum(ev["descriptive"][key] == o for _, ev in per_world)
                          for o in ("HOLDS", "FAILS", "UNDEFINED")}
    verdict_of = lambda key: t1_verdict_of([ev["descriptive"][key] for _, ev in per_world])
    desc = {
        "cross_seed_pooled": {"class_atoms": pooled("n_class", "agree_class"), "all_atoms": pooled("n_all", "agree_all")},
        "all_true": all_true,
        "g7b_positive_worlds": sum(ev["descriptive"]["g7b"]["positive"] for _, ev in per_world),
        "g8_whole_grid_all_points_ok": sum(ev["descriptive"]["g8_whole_grid"]["all_points_ok"] for _, ev in per_world),
        "t1_all_points": {"outcomes": count3("t1_all_points"), "verdict": verdict_of("t1_all_points")},
        "t1_i6": {"outcomes": count3("t1_i6"), "verdict": verdict_of("t1_i6")},
        "t1_i7": {"outcomes": count3("t1_i7"), "verdict": verdict_of("t1_i7")},
        "t1_i8": {"outcomes": count3("t1_i8"), "verdict": verdict_of("t1_i8")},
        "t1_i9": {"outcomes": count3("t1_i9"), "verdict": verdict_of("t1_i9")},
        "t1_structure": [dict(world_seed=rec.world_seed, **structure_json(ev["descriptive"]["t1_structure"]))
                         for rec, ev in per_world],
        "default_feasible_worlds": sum(ev["descriptive"]["default_feasible"] for _, ev in per_world),
        "undefined_as_fails": {"T-1": undefined_as_fails(per_test["T-1"])},
        "detector_diagnostic": twin_summary,
        "draw_sensitivity": {k: v for k, v in ds.items()},
    }
    return TestBundle(records, rejected, controls, cal_ctl, per_world, seconds, table, g8, desc, ds)


# ------------------------------------------------------------------------------------------------ documents
def blind_input(rec, ev, calibration: bool) -> dict:  # ev: the evaluation (test) or the decoder output at (alpha0, 0) (calibration)
    """What the F3 agent receives (PREREG 6.1): world truth, rules, units, the full and verdict value lists, the source
    reliabilities, the grid, the draw index and, for a test world, the run's G1-G6 outcomes labelled as given. No metric, no
    H, no tau and no check data. A calibration world is given at (alpha0, 0) only."""
    world, ctx, enc = rec.world, rec.context, rec.encoding
    doc = {
        "role": "calibration" if calibration else "test",
        "world_seed": rec.world_seed, "draw_index": rec.draw,
        "entities": list(world.entities), "n_classes": world.params.n_classes, "n_relations": world.params.n_relations,
        "base_classes": list(world.base_classes), "outliers": list(world.outliers), "overlaps": list(world.overlaps),
        "rules": [_rule_json(r) for r in world.rules],
        "true_atoms": sorted(str(a) for a in world.true_atoms),
        "source_reliabilities": [p.value for p in world.params.source_reliabilities],
        "epsilon_band": ctx.epsilon_band,
        "units": _units_json(enc.units), "validation_units": _units_json(enc.validation_units),
        "default_configuration": [C.ALPHA0, C.K0], "calibration_configuration": [C.ALPHA0, K_CAL],
    }
    if calibration:
        doc.update(alphas=[C.ALPHA0], ks=[K_CAL], configs=grid_listing({(C.ALPHA0, K_CAL): (ev, None, None)}))
    else:
        doc.update(alphas=list(C.ALPHAS), ks=list(C.KS), configs=grid_listing(ev["results"]),
                   given_outcomes_g1_g6={t: ev["fixed"][t]["outcome"] for t in C.TEST_IDS[:6]})
    return doc


def f3_fields(ev, taus) -> dict:
    exact_by_config = {key: res[2] for key, res in ev["results"].items()}
    points = pareto_points(exact_by_config, taus.main)
    return {
        "feasible": [f"{a}|{k}" for (a, k), ex in sorted(exact_by_config.items()) if feasible(ex, taus.main)],
        "pareto_front": [f"{c[0]}|{c[1]}" for c, _, _ in pareto_front_exact(points)],
        "hypervolume": frac_str(hypervolume_exact(points)),
        "outcomes": {"G7a": ev["fixed"]["G7"]["outcome"], "T-1": ev["fixed"]["T-1"]["outcome"]},
        "t1_structure": f3_structure_json(ev["descriptive"]["t1_structure"]),
    }


def run_results(rec, ev, controls: dict, taus) -> dict:
    world, enc = rec.world, rec.encoding
    h = compute_H(sorted(enc.units), world.truth, world.rules, world.vocabulary)
    return {
        "f3": f3_fields(ev, taus), "world_seed": rec.world_seed, "H": [str(a) for a in h],
        "pcm": {"centers": enc.fit.centers, "n_iter": enc.fit.n_iter, "converged": enc.fit.converged,
                "degenerate": enc.fit.degenerate},
        "metrics": {f"{a}|{k}": dataclasses.asdict(m) for (a, k), (_, m, _) in ev["results"].items()},
        "metrics_exact": {f"{a}|{k}": {**exact_json(ex), "n_q": ev["n_q"][(a, k)]}
                          for (a, k), (_, _, ex) in ev["results"].items()},
        "controls": {name: {"ok": ok, "detail": detail} for name, (ok, detail) in controls.items()},
        "check_data": {t: ev["fixed"][t].get("data") for t in C.TEST_IDS},
        "fixed_outcomes": {t: ev["fixed"][t]["outcome"] for t in ALL_TESTS},
        "g1_failed_parts": ev["fixed"]["G1"]["failed_parts"],
        "twin_outcomes": {n: v["outcome"] for n, v in ev["twins"].items()},
        "descriptive": {**ev["descriptive"], "t1_structure": structure_json(ev["descriptive"]["t1_structure"])},
    }


def calibration_results(rec, controls: dict, exact: dict, n_q: int) -> dict:
    """outputs_results/cal_<seed>.json: the controls and the eight exact metrics of a calibration world at (alpha0, 0) with
    the denominator n_q of its new_false, keyed "0.7|0" like the metrics of a test world (the F3 comparison reads them with the
    same code)."""
    return {"world_seed": rec.world_seed,
            "controls": {n: {"ok": ok, "detail": d} for n, (ok, d) in controls.items()},
            "metrics_exact": {f"{C.ALPHA0}|{K_CAL}": {**exact_json(exact), "n_q": n_q}}}


def per_world_doc(rec, ev) -> dict:
    """A world's outcomes and descriptive fields (the RESULTS.json row; the development document before redaction)."""
    d = dict(ev["descriptive"])
    d["t1_structure"] = structure_json(d["t1_structure"])
    return {"world_seed": rec.world_seed, "draw": rec.draw, "h_size": rec.h_size,
            "outcomes": {t: ev["fixed"][t]["outcome"] for t in ALL_TESTS}, "twins": ev["twins"], "descriptive": d}


def definedness(bundle: TestBundle) -> list:
    """Per test: the number of defined and undefined worlds (the one thing about T-1 and G8 that development may show)."""
    rows = []
    for t in ALL_TESTS:
        outs = [ev["fixed"][t]["outcome"] for _, ev in bundle.per_world]
        rows.append({"test": t, "n_defined": sum(o != "UNDEFINED" for o in outs),
                     "n_undefined": sum(o == "UNDEFINED" for o in outs)})
    return rows


def verdicts_document(core: str, bundle: TestBundle, taus: TauSet) -> dict:
    return {"core_sha256": core, "environment": env_info(), "table": bundle.table, "g8_descriptive": bundle.g8,
            "descriptive": bundle.desc, "n_test_worlds": len(bundle.per_world), "n_rejected_draws": len(bundle.rejected),
            "world_hashes": {r.world_seed: world_record_json(r) for r, _ in bundle.per_world}}


# ------------------------------------------------------------------------------------------------ real steps
def run_test(core: str, salt: str, out: Path, n_cal: int, n_test: int, n_alt: int, inputs: Path,
             subprocess_checks: bool = True) -> dict:
    """The real test step. Nothing is written until the verdict table and the descriptive summary have been built; the
    only exception is STOPPED.json, written when a fidelity control disagrees."""
    for name in ("TAU.json", "CAL_WORLDS.json"):
        if not (inputs / name).is_file():
            raise Refused(f"{inputs / name} not found: run calibrate first")
    existing = [name for name in OUTPUT_NAMES if (out / name).exists()]
    if existing:
        raise Refused(f"{out} already holds {', '.join(existing)}; a real run never overwrites its outputs")
    cal = recheck_calibration(core, salt, inputs, n_cal, n_alt)
    sd = seeder(core, salt)

    def on_stop(kind, seed_, bad):
        _write_json(out / "STOPPED.json", {"kind": kind, "world_seed": seed_, "disagreements": bad}, overwrite=True)

    bundle = evaluate_tests(sd, cal, n_test, subprocess_checks, on_stop)
    docs = [(out / "TEST_WORLDS.json", {"core_sha256": core, "environment": env_info(),
                                       "worlds": [world_record_json(r) for r in bundle.records],
                                       "rejected_draws": bundle.rejected})]
    for rec in cal.records:  # the blind inputs and the results of the calibration worlds, at (alpha0, 0)
        out0 = FIXED.evaluate_exact(rec.world, rec.context, rec.encoding, C.ALPHA0, K_CAL)
        docs.append((out / "outputs_input" / f"cal_{rec.world_seed}.json", blind_input(rec, out0[0], True)))
        n_q0 = decided_outside_count(rec.encoding.units, rec.context.vocabulary, out0[0], C.ALPHA0)
        docs.append((out / "outputs_results" / f"cal_{rec.world_seed}.json",
                     calibration_results(rec, bundle.cal_controls[rec.world_seed], out0[2], n_q0)))
    for rec, ev in bundle.per_world:
        docs.append((out / "outputs_input" / f"{rec.world_seed}.json", blind_input(rec, ev, False)))
        docs.append((out / "outputs_results" / f"{rec.world_seed}.json",
                     run_results(rec, ev, bundle.controls[rec.world_seed], cal.taus)))
    docs.append((out / "RESULTS.json", {"core_sha256": core, "taus": tau_set_json(cal.taus),
                                        "worlds": [per_world_doc(r, ev) for r, ev in bundle.per_world]}))
    docs.append((out / "VERDICTS.json", verdicts_document(core, bundle, cal.taus)))
    for path, doc in docs:  # only now does anything reach the disk
        _write_json(path, fr_json(doc), overwrite=False)
    return {"table": bundle.table, "seconds": bundle.seconds, "n_worlds": len(bundle.per_world)}


def reproduce(root: Path, core: str, salt: str, test_fn=None) -> dict:
    """PREREG step 11: rerun the test step into run/v03_repro/ and compare the SHA-256 of the two VERDICTS.json files."""
    run_dir, out = root / OUT_REL, root / REPRO_REL
    if out.exists():
        raise Refused(f"{out} already exists; reproduce never overwrites")
    check_committed_clean(root, f"{OUT_REL}/VERDICTS.json")
    (test_fn or run_test)(core, salt, out, N_CAL, N_TEST, N_ALT, run_dir)
    repro, original = _sha(out / "VERDICTS.json"), _sha(run_dir / "VERDICTS.json")
    return {"equal": repro == original, "repro_sha256": repro, "run_sha256": original}


# ------------------------------------------------------------------------------------------------ development mode
def dev_calibration_document(cal: Calibration) -> dict:
    """The development calibration document (before redaction): taus and the four feasibility metrics. Nothing in it is
    forbidden, but it goes through the boundary all the same."""
    return {
        "mode": "dev-redacted", "n_cal": len(cal.records), "n_rejected_cal": len(cal.rejected),
        "taus": {"tau_main": taus_to_json(cal.taus.main), "tau_i6": taus_to_json(cal.taus.i6),
                 "tau_i7": taus_to_json(cal.taus.i7), "tau_i8": taus_to_json(cal.taus.i8),
                 "tau_alt": [None if t is None else taus_to_json(t) for t in cal.taus.alt]},
        "worlds": [{"draw": r.draw, "world_seed": r.world_seed, "four_metrics_k0": metrics_to_json(m)}
                   for r, m in zip(cal.records, cal.main_four)],
        "alt_sets": [{"b": a["b"], "n_rejected": len(a["rejected_draws"]), "failed": "failed" in a} for a in cal.alt_docs],
    }


def dev_test_document(cal: Calibration, bundle: TestBundle) -> dict:
    """The development test document (before redaction): the real verdicts document plus per-world rows."""
    return {
        "mode": "dev-redacted", "n_cal": len(cal.records), "n_test": len(bundle.per_world), "n_alt": len(cal.taus.alt),
        "n_rejected_test": len(bundle.rejected), "n_rejected_cal": len(cal.rejected),
        "taus": {"tau_main": taus_to_json(cal.taus.main), "tau_i6": taus_to_json(cal.taus.i6),
                 "tau_i7": taus_to_json(cal.taus.i7), "tau_i8": taus_to_json(cal.taus.i8)},
        "definedness": definedness(bundle),
        "table": bundle.table, "g8_descriptive": bundle.g8, "descriptive": bundle.desc,
        "worlds": [per_world_doc(r, ev) for r, ev in bundle.per_world],
        "seconds_total": sum(bundle.seconds),
    }


def dev_summary_lines(doc: dict) -> list:
    """Console lines from a REDACTED document (the only thing development prints)."""
    lines = [f"dev-redacted run: {doc.get('n_cal')} calibration worlds, {doc.get('n_test', '-')} test worlds, "
             f"{doc.get('n_alt', len(doc.get('taus', {}).get('tau_alt', [])))} alternative sets"]
    for name, t in doc["taus"].items():
        if isinstance(t, dict):
            lines.append(f"  {name}: " + ", ".join(f"{k} {t[k]}" for k in TAU_NAMES))
    for row in doc.get("definedness", []):
        lines.append(f"  definedness {row['test']}: {row['n_defined']} defined, {row['n_undefined']} undefined")
    for row in doc.get("table", {}).get("rows", []):
        lines.append("  " + (row["text"] if "text" in row else f"{row['test']}: {row['verdict_row']}"))
    return lines


def run_dev(mode: str, out: Path, n_cal: int, n_test: int, n_alt: int, subprocess_checks: bool) -> list:
    """The development runner. Returns the console lines. The only output path is `redact_checked`."""
    if str(out.resolve()).lower().startswith(str((ROOT / "run").resolve()).lower()):
        raise Refused("development output must not go into run/")
    out.mkdir(parents=True, exist_ok=True)
    sd = seeder(DEV_CORE)
    t0 = time.perf_counter()
    cal = build_calibration(DEV_CORE, None, n_cal, n_alt)
    if mode == "calibrate":
        doc = redact.redact_checked(dev_calibration_document(cal))
        name = "DEV_CALIBRATION.json"
    else:
        bundle = evaluate_tests(sd, cal, n_test, subprocess_checks)
        doc = redact.redact_checked(dev_test_document(cal, bundle))
        name = "DEV_TEST.json"
    doc["runtime_seconds"] = round(time.perf_counter() - t0, 1)
    with open(out / name, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(doc, fh, indent=1, sort_keys=True, allow_nan=False)
        fh.write("\n")
    return dev_summary_lines(doc) + [f"runtime {doc['runtime_seconds']} s; wrote {out / name}"]


# ------------------------------------------------------------------------------------------------ main
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="py -m audit.v03.run_v03", description=__doc__.split("\n\n")[0])
    ap.add_argument("mode", choices=("calibrate", "test", "reproduce"))
    ap.add_argument("--dev-redacted", action="store_true", help="development mode, all output redacted (needs --out)")
    ap.add_argument("--out", type=Path, help="development output folder (outside run/)")
    ap.add_argument("--n-cal", type=int, default=N_CAL, help="development mode only")
    ap.add_argument("--n-test", type=int, default=N_TEST, help="development mode only")
    ap.add_argument("--n-alt", type=int, default=N_ALT, help="development mode only")
    ap.add_argument("--no-subprocess", action="store_true", help="development mode only")
    args = ap.parse_args(argv)
    dev_only = (args.n_cal, args.n_test, args.n_alt) != (N_CAL, N_TEST, N_ALT) or args.no_subprocess or args.out
    if not args.dev_redacted and dev_only:
        print("--n-cal, --n-test, --n-alt, --no-subprocess and --out are for --dev-redacted only", file=sys.stderr)
        return EXIT_USAGE
    if args.dev_redacted and (args.mode == "reproduce" or args.out is None):
        print("--dev-redacted needs --out DIR, and reproduce is a real-mode command", file=sys.stderr)
        return EXIT_USAGE
    try:
        if args.dev_redacted:
            check_versions()
            try:
                lines = run_dev(args.mode, args.out, args.n_cal, args.n_test, args.n_alt, not args.no_subprocess)
            except (Refused, ControlDisagreement, WorldSetError):
                raise
            except Exception as exc:  # development never prints a message that could carry a withheld value
                import traceback

                msg = str(exc)
                if re.search(r"\d+/\d+|new_|Fraction", msg):
                    msg = "<message withheld>"
                print(f"dev run crashed: {type(exc).__name__}: {msg}", file=sys.stderr)
                print("".join(traceback.format_tb(exc.__traceback__)), file=sys.stderr)
                return 1
            if hasattr(sys.stdout, "reconfigure"):  # the G7a sentence has an alpha; a Windows console may be cp1254 or cp1252
                sys.stdout.reconfigure(encoding="utf-8")
            for line in lines:
                print(line)
            return 0
        core, salt = real_preconditions(args.mode)
        out = ROOT / OUT_REL
        if args.mode == "reproduce":
            info = reproduce(ROOT, core, salt)
            print(f"{OUT_REL}/VERDICTS.json    sha256 {info['run_sha256']}")
            print(f"{REPRO_REL}/VERDICTS.json sha256 {info['repro_sha256']}")
            print("REPRODUCED: byte-identical" if info["equal"] else "NOT REPRODUCED: the files differ")
            if not info["equal"]:
                return EXIT_REPRO
        elif args.mode == "calibrate":
            info = run_calibrate(core, salt, out, N_CAL, N_ALT)
            print(f"calibrated on {N_CAL} worlds and {N_ALT} alternative sets ({info['n_rejected']} draws rejected); "
                  f"wrote {out}/TAU.json")
        else:
            info = run_test(core, salt, out, N_CAL, N_TEST, N_ALT, out)
            secs = info["seconds"]
            print(f"tested {info['n_worlds']} worlds in {sum(secs):.1f} s; wrote {out}/VERDICTS.json")
        verify_freeze(MANIFEST, Path(__file__).resolve())  # the freeze must still hold after the run
    except Refused as exc:
        print(f"refusing: {exc}", file=sys.stderr)
        return EXIT_REFUSED
    except ControlDisagreement as exc:
        print(f"STOP: a fidelity control disagrees ({exc}); no verdict is given", file=sys.stderr)
        return EXIT_CONTROL
    except WorldSetError as exc:
        print(f"STOP: {exc}", file=sys.stderr)
        return EXIT_WORLDS
    return 0


if __name__ == "__main__":
    sys.exit(main())
