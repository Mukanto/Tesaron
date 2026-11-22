"""Calibration and test runner for Tesaron v0.2 (PREREG sections 7, 8 and 9, draft 5).

    py -m audit.run_v02 calibrate         # real mode: writes run/CAL_WORLDS.json and run/TAU.json
    py -m audit.run_v02 test              # real mode: writes run/TEST_WORLDS.json, run/outputs_input/, run/outputs_results/,
                                          #            run/RESULTS.json, run/VERDICTS.json
    py -m audit.run_v02 reproduce         # real mode, in a clone of the result commit: reruns the test step into run_repro/
                                          #            and compares sha256(run_repro/VERDICTS.json) with run/VERDICTS.json
    py -m audit.run_v02 calibrate --dev   # development mode: core "dev", salt "dev", seeds in 900000-900999, run_dev/
    py -m audit.run_v02 test --dev [--n-test N] [--n-cal N] [--no-subprocess]

Real mode refuses to start unless all of this holds (R1-3, R1-4, R1-14):
  - Python 3.14.2 and NumPy 2.4.1;
  - the freeze manifest prereg/FREEZE_v0.2.json verifies (audit/freeze.py), and this file is listed in it;
  - exactly one commit touches the manifest (the freeze commit); it is an ancestor of origin/main (a local
    remote-tracking ref; no fetch, no network); the manifest and every file it lists are tracked, unmodified and identical
    to their content in the freeze commit;
  - run/SALT.json is touched by exactly one commit, in a descendant of the freeze commit and an ancestor of origin/main;
    it is unmodified and names the freeze commit ("freeze_commit") and the core hash of the manifest ("core_sha256").
`test` additionally needs run/CAL_WORLDS.json and run/TAU.json, each touched by one commit in a descendant of the salt
commit and an ancestor of origin/main; it regenerates the calibration worlds, recomputes tau exactly, and refuses unless
the result equals TAU.json and sha256(CAL_WORLDS.json) matches.
`reproduce` runs all of these real-mode checks, reads run/SALT.json, run/CAL_WORLDS.json and run/TAU.json, refuses if
run_repro/ exists or if run/VERDICTS.json is not committed unmodified, runs the test step into run_repro/ and compares the
SHA-256 of run_repro/VERDICTS.json with that of run/VERDICTS.json; exit code 0 iff they are equal (7 if not).
`test` runs F1, F2 and F4 on all test worlds first; any disagreement stops the run (only STOPPED.json is written) and no
verdict is given. A crash ends the run with no verdict (R1-12). Development mode has no git checks and writes only to
run_dev/.

Exit codes: 0 done; 2 usage error; 3 a precondition failed; 5 a fidelity control disagreed; 6 not enough valid worlds;
7 reproduce: the rerun's VERDICTS.json differs from the committed one.
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import platform
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

from audit import checks as C
from audit import freeze as freeze_tool
from audit.aggregate import QUANTITATIVE_TESTS, undefined_as_fails, verdict_table
from audit.cache import get_encoding
from audit.exact import ExactTaus, compute_taus, frac_str, hypervolume_exact, pareto_front_exact, pareto_points
from audit.fidelity import run_controls
from audit.hashing import encoding_hash
from audit.per_world import TWIN_TEST, evaluate_world, exact_json, grid_listing
from audit.prefreeze_check import MANIFEST_PATHS
from audit.seeds import DEV_CORE, DEV_SALT, seeder
from audit.tau import default_exact
from audit.worldset import WorldSetError, generate_valid
from tesaron.serialize import canonical_hash

ROOT = Path(__file__).resolve().parent.parent
MANIFEST_REL = "prereg/FREEZE_v0.2.json"
MANIFEST = ROOT / MANIFEST_REL
REQUIRED_PYTHON = (3, 14, 2)
REQUIRED_NUMPY = "2.4.1"
REMOTE_REF = "origin/main"
N_CAL, N_TEST = 10, 30
EXIT_USAGE, EXIT_REFUSED, EXIT_CONTROL, EXIT_WORLDS, EXIT_REPRO = 2, 3, 5, 6, 7


class Refused(Exception):
    pass


class ControlDisagreement(Exception):
    pass


# ------------------------------------------------------------------------------------------------ environment
def env_info() -> dict:
    return {"python": sys.version, "numpy": np.__version__, "platform": platform.platform()}


def check_versions() -> None:
    if tuple(sys.version_info[:3]) != REQUIRED_PYTHON or np.__version__ != REQUIRED_NUMPY:
        raise Refused(
            f"needs Python {'.'.join(map(str, REQUIRED_PYTHON))} and NumPy {REQUIRED_NUMPY}, "
            f"found Python {sys.version.split()[0]} and NumPy {np.__version__}"
        )


# ------------------------------------------------------------------------------------------------ freeze and git
def verify_freeze(manifest_path: Path = MANIFEST, entry: Path | None = None) -> str:
    """Verify the freeze manifest with audit/freeze.py and return its core_sha256. Raises Refused if the manifest is
    missing, unreadable or broken, or if the entry file (this runner) is not listed in it."""
    if not manifest_path.is_file():
        raise Refused(f"freeze manifest not found: {manifest_path}")
    try:
        manifest = freeze_tool.load_manifest(str(manifest_path))
        problems, _ = freeze_tool.verify_manifest(str(manifest_path))
    except (OSError, ValueError) as exc:
        raise Refused(f"cannot read the freeze manifest: {type(exc).__name__}") from exc
    if problems:
        raise Refused("freeze check failed: " + "; ".join(problems))
    if entry is not None:
        import os

        rel = os.path.relpath(str(entry.resolve()), str(manifest_path.resolve().parent)).replace(os.sep, "/")
        if rel not in manifest["files"]:
            raise Refused(f"ENTRY NOT FROZEN: {rel} is not listed in the manifest")
    core = manifest.get("core_sha256")
    if not isinstance(core, str) or not core:
        raise Refused("the manifest has no core_sha256")
    return core


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True)


def unique_commit(repo: Path, rel: str) -> str:
    """The one commit that touches a file (R2-2). Refuses unless exactly one commit in the history of HEAD touches
    it: a manifest, salt or tau file that was rewritten, deleted or re-added later has no unique commit."""
    res = _git(repo, "log", "--full-history", "--format=%H", "--", rel)
    commits = [c for c in res.stdout.split() if c]
    if res.returncode != 0 or not commits:
        raise Refused(f"no commit touches {rel}")
    if len(commits) != 1:
        raise Refused(f"{len(commits)} commits touch {rel}; exactly one is allowed")
    return commits[0]


def is_ancestor(repo: Path, ancestor: str, descendant: str) -> bool:
    return _git(repo, "merge-base", "--is-ancestor", ancestor, descendant).returncode == 0


def check_committed_clean(repo: Path, rel: str) -> None:
    """The file is tracked, committed and unmodified."""
    if _git(repo, "ls-files", "--error-unmatch", rel).returncode != 0:
        raise Refused(f"{rel} is not tracked by git")
    if _git(repo, "cat-file", "-e", f"HEAD:{rel}").returncode != 0:
        raise Refused(f"{rel} is not committed")
    status = _git(repo, "status", "--porcelain", "--", rel)
    if status.returncode != 0 or status.stdout.strip():
        raise Refused(f"{rel} is modified or staged but not committed")


def check_pushed(repo: Path, commit: str, what: str = "the freeze commit", remote_ref: str = REMOTE_REF) -> None:
    """The commit is an ancestor of the local remote-tracking branch. The runner sees only that local ref: it does no
    fetch and uses no network, so it cannot tell that the remote really holds the commit (PREREG section 8)."""
    if _git(repo, "rev-parse", "--verify", "--quiet", remote_ref).returncode != 0:
        raise Refused(f"the remote-tracking ref {remote_ref} does not exist")
    if not is_ancestor(repo, commit, remote_ref):
        raise Refused(f"{what} {commit} is not on {remote_ref}")


def _batches(paths, limit: int = 6000):
    """Chunks of paths whose joined length stays below the Windows command-line limit."""
    batch, size = [], 0
    for path in paths:
        if batch and size + len(path) + 1 > limit:
            yield batch
            batch, size = [], 0
        batch.append(path)
        size += len(path) + 1
    if batch:
        yield batch


def manifest_repo_paths(repo: Path, manifest_path: Path) -> list[str]:
    """Repository-relative POSIX paths of the manifest and of every file it lists."""
    manifest = freeze_tool.load_manifest(str(manifest_path))
    base = manifest_path.resolve().parent
    root = repo.resolve()
    paths = []
    for rel in sorted(manifest["files"]):
        try:
            paths.append((base / rel).resolve().relative_to(root).as_posix())
        except ValueError as exc:
            raise Refused(f"{rel} lies outside the repository") from exc
    try:
        paths.append(manifest_path.resolve().relative_to(root).as_posix())
    except ValueError as exc:
        raise Refused("the manifest lies outside the repository") from exc
    return sorted(set(paths))


def check_frozen_tree(repo: Path, freeze_commit: str, manifest_path: Path) -> None:
    """R2-2: the manifest and every frozen file are tracked, unmodified, and identical to their content in the freeze
    commit (so the tree that was verified is the tree that was committed and pushed)."""
    for batch in _batches(manifest_repo_paths(repo, manifest_path)):
        tracked = _git(repo, "ls-files", "--error-unmatch", "--", *batch)
        if tracked.returncode != 0:
            raise Refused("a frozen file is not tracked by git: " + (tracked.stderr.strip().splitlines() or ["?"])[0])
        status = _git(repo, "status", "--porcelain", "--", *batch)
        if status.returncode != 0 or status.stdout.strip():
            raise Refused("a frozen file is modified, staged or untracked: " + status.stdout.strip().splitlines()[0])
        diff = _git(repo, "diff", "--quiet", freeze_commit, "--", *batch)
        if diff.returncode != 0:
            raise Refused("a frozen file differs from its content in the freeze commit")


def check_manifest_coverage(repo: Path, freeze_commit: str, manifest_path: Path, paths=MANIFEST_PATHS) -> None:
    """R3-7: the manifest lists exactly the files that the freeze commit tracks under the manifest paths of PREREG section 9
    (`git ls-tree -r --name-only <freeze> -- <paths>`): a manifest written from a subset is refused, and so is a frozen
    tree with a tracked file that the manifest does not hash."""
    tracked = set()
    for batch in _batches(list(paths)):
        res = _git(repo, "ls-tree", "-r", "--name-only", freeze_commit, "--", *batch)
        if res.returncode != 0:
            raise Refused("cannot list the files of the freeze commit")
        tracked.update(line for line in res.stdout.splitlines() if line)
    listed = set(manifest_repo_paths(repo, manifest_path)) - {manifest_path.resolve().relative_to(repo.resolve()).as_posix()}
    missing, extra = sorted(tracked - listed), sorted(listed - tracked)
    if missing or extra:
        what = [f"tracked but not in the manifest: {missing[0]}"] if missing else []
        what += [f"in the manifest but not tracked under the manifest paths: {extra[0]}"] if extra else []
        raise Refused("the manifest does not cover the frozen tree (" + "; ".join(what) + ")")


def check_freeze_and_salt(repo: Path, core: str, manifest_rel: str = MANIFEST_REL, salt_rel: str = "run/SALT.json",
                          manifest_paths=MANIFEST_PATHS):
    """(freeze commit, salt commit, salt). The freeze commit is the unique commit that touches the manifest; it is on
    the remote branch; the manifest and the frozen files equal their content in it. The salt file is touched by exactly
    one commit, which is a strict descendant of the freeze commit and on the remote branch; the file is unmodified, names
    the freeze commit and the core hash of the verified manifest, and holds a 64-digit hex salt."""
    manifest_path = repo / manifest_rel
    freeze_commit = unique_commit(repo, manifest_rel)
    check_pushed(repo, freeze_commit)
    check_frozen_tree(repo, freeze_commit, manifest_path)
    check_manifest_coverage(repo, freeze_commit, manifest_path, manifest_paths)
    check_committed_clean(repo, salt_rel)
    salt_commit = unique_commit(repo, salt_rel)
    if salt_commit == freeze_commit or not is_ancestor(repo, freeze_commit, salt_commit):
        raise Refused("run/SALT.json is not committed in a descendant of the freeze commit")
    check_pushed(repo, salt_commit, "the salt commit")
    try:
        doc = json.loads((repo / salt_rel).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise Refused("run/SALT.json is not readable JSON") from exc
    if not isinstance(doc, dict) or doc.get("freeze_commit") != freeze_commit:
        raise Refused("run/SALT.json does not name the freeze commit")
    if doc.get("core_sha256") != core:
        raise Refused("run/SALT.json core_sha256 differs from the core hash of the verified manifest")
    salt = doc.get("salt")
    if not isinstance(salt, str) or not re.fullmatch(r"[0-9a-f]{64}", salt):
        raise Refused("run/SALT.json has no salt of 32 random bytes (64 hex digits)")
    return freeze_commit, salt_commit, salt


def check_tau_after_salt(repo: Path, salt_commit: str, tau_rel: str = "run/TAU.json",
                         cal_rel: str = "run/CAL_WORLDS.json") -> None:
    """run/CAL_WORLDS.json and run/TAU.json: each touched by exactly one commit, committed unmodified, in a strict
    descendant of the salt commit, and on the remote branch."""
    for rel in (cal_rel, tau_rel):
        check_committed_clean(repo, rel)
        commit = unique_commit(repo, rel)
        if commit == salt_commit or not is_ancestor(repo, salt_commit, commit):
            raise Refused(f"{rel} is not committed in a descendant of the salt commit")
        check_pushed(repo, commit, f"the commit of {rel}")


# ------------------------------------------------------------------------------------------------ io
def _write_json(path: Path, obj, overwrite: bool) -> None:
    if path.exists() and not overwrite:
        raise Refused(f"{path} already exists; a real run never overwrites its outputs")
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(to_jsonable_keep(obj), fh, indent=1, sort_keys=True, allow_nan=False)
        fh.write("\n")


def to_jsonable_keep(obj):
    """JSON-ready copy with full float precision (no rounding), NaN and infinity as null."""
    if isinstance(obj, dict):
        return {str(k): to_jsonable_keep(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [to_jsonable_keep(v) for v in obj]
    if isinstance(obj, float):
        return obj if obj == obj and obj not in (float("inf"), float("-inf")) else None
    if hasattr(obj, "item") and not isinstance(obj, (str, bytes)):
        return to_jsonable_keep(obj.item())
    if hasattr(obj, "name") and hasattr(obj, "value") and not isinstance(obj, (str, int, float)):
        return obj.name
    return obj


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# ------------------------------------------------------------------------------------------------ payloads
def _rule_json(rule) -> dict:
    lit = lambda l: {"pred": l.pred, "args": list(l.args), "channel": l.channel.name}
    return {"id": rule.id, "head": lit(rule.head), "body": [lit(l) for l in rule.body]}


def _units_json(units) -> dict:
    return {
        str(a): [u.mu_pos.value, u.mu_neg.value, u.status.name, list(u.provenance)] for a, u in sorted(units.items())
    }


def world_record_json(rec) -> dict:
    return {"draw": rec.draw, "world_seed": rec.world_seed, "enc_seed": rec.enc_seed, "aux_seed": rec.aux_seed,
            "h_size": rec.h_size, "world_hash": canonical_hash(rec.world),
            "encoding_hash": encoding_hash(rec.encoding)}


def blind_input(rec, taus: ExactTaus, ev) -> dict:
    """What the F3 agent receives (PREREG 6.1): world truth, rules, units, the full and verdict value lists of every
    configuration, tau and the grid. No metric, no H and no check data. The only outcomes in it are the run's G1-G6
    per-world outcomes, labelled as given: the agent does not recompute them and needs them only to recompute the verdict
    table. The draw index of the world is given too (the table's first failing world is the one with the smallest draw
    index). Nothing about G7a, G8 or T-1 and nothing else from the run's results."""
    world, ctx, enc = rec.world, rec.context, rec.encoding
    return {
        "world_seed": rec.world_seed,
        "draw_index": rec.draw,
        "entities": list(world.entities),
        "n_classes": world.params.n_classes,
        "n_relations": world.params.n_relations,
        "base_classes": list(world.base_classes),
        "outliers": list(world.outliers),
        "overlaps": list(world.overlaps),
        "rules": [_rule_json(r) for r in world.rules],
        "true_atoms": sorted(str(a) for a in world.true_atoms),
        "epsilon_band": ctx.epsilon_band,
        "units": _units_json(enc.units),
        "validation_units": _units_json(enc.validation_units),
        "taus": {n: frac_str(getattr(taus, n)) for n in ("tau_s", "tau_d", "tau_t", "tau_b")},
        "alphas": list(C.ALPHAS),
        "ks": list(C.KS),
        "default_configuration": [C.ALPHA0, C.K0],
        "configs": grid_listing(ev["results"]),
        "given_outcomes_g1_g6": {
            t_: ev["fixed"][t_]["outcome"] for t_ in C.TEST_IDS[:6]
        },
    }


T1_STRUCTURE_FIELDS = ("some_alpha_le_060_feasible", "alpha_ge_085_feasible", "t1_window_pairs", "t1_crossing_pairs",
                       "t1_cross_080_085")


def f3_fields(ev, taus: ExactTaus) -> dict:
    """The per-world fields that the F3 agent also computes (audit/f3/OUTPUT_SCHEMA.json), from the run's exact metrics:
    the feasible set, the Pareto front, the hypervolume as p/q and the G7a, G8 and T-1 outcomes."""
    exact_by_config = {key: res[2] for key, res in ev["results"].items()}
    points = pareto_points(exact_by_config, taus)
    return {
        "feasible": [f"{a}|{k}" for (a, k), ex in sorted(exact_by_config.items()) if C.feasible(ex, taus)],
        "pareto_front": [f"{c[0]}|{c[1]}" for c, _, _ in pareto_front_exact(points)],
        "hypervolume": frac_str(hypervolume_exact(points)),
        "outcomes": {"G7a": ev["fixed"]["G7"]["outcome"], "G8": ev["fixed"]["G8"]["outcome"],
                     "T-1": ev["fixed"]["T-1"]["outcome"]},
        "t1_structure": {k: ev["descriptive"]["t1_structure"][k] for k in T1_STRUCTURE_FIELDS},
    }


def run_results(rec, ev, controls: dict, taus: ExactTaus) -> dict:
    """The run's own numbers, compared with the F3 agent's results by audit/f3_compare.py after the agent has written
    them."""
    from tesaron.criterion.metrics import compute_H

    world, enc = rec.world, rec.encoding
    h = compute_H(sorted(enc.units), world.truth, world.rules, world.vocabulary)
    return {
        "f3": f3_fields(ev, taus),
        "world_seed": rec.world_seed,
        "H": [str(a) for a in h],
        "pcm": {"centers": enc.fit.centers, "n_iter": enc.fit.n_iter, "converged": enc.fit.converged,
                "degenerate": enc.fit.degenerate},
        "metrics": {f"{a}|{k}": dataclasses.asdict(m) for (a, k), (_, m, _) in ev["results"].items()},
        "metrics_exact": {f"{a}|{k}": exact_json(ex) for (a, k), (_, _, ex) in ev["results"].items()},
        "controls": {name: {"ok": ok, "detail": detail} for name, (ok, detail) in controls.items()},
        "check_data": {t: ev["fixed"][t].get("data") for t in C.TEST_IDS},
        "fixed_outcomes": {t: ev["fixed"][t]["outcome"] for t in C.TEST_IDS},
        "g1_failed_parts": ev["fixed"]["G1"]["failed_parts"],
        "twin_outcomes": {n: v["outcome"] for n, v in ev["twins"].items()},
        "descriptive": ev["descriptive"],
    }


# ------------------------------------------------------------------------------------------------ steps
def build_calibration(core: str, salt: str | None, dev: bool, n_cal: int):
    """(records, rejected, taus, info, exacts): the calibration worlds and tau by D1."""
    sd = seeder(core, salt)
    records, rejected = generate_valid(
        n_cal, sd, "world-cal", "enc-cal", build=get_encoding if dev else None, calibration=True
    )
    exacts = [default_exact(r) for r in records]
    taus, info = compute_taus(exacts)
    return records, rejected, taus, info, exacts


def calibration_worlds(records, exacts) -> list:
    return [dict(world_record_json(r), metrics_exact=exact_json(ex)) for r, ex in zip(records, exacts)]


def _roundtrip(obj):
    """The JSON that _write_json would store, read back (so that stored and regenerated documents compare equal)."""
    return json.loads(json.dumps(to_jsonable_keep(obj), sort_keys=True, allow_nan=False))


def run_calibrate(core: str, salt: str | None, out: Path, dev: bool, n_cal: int) -> dict:
    records, rejected, taus, info, exacts = build_calibration(core, salt, dev, n_cal)
    cal = {
        "core_sha256": core,
        "environment": env_info(),
        "rule": "D1: tau_s = min fidelity, tau_d = max deviation, tau_t = min consistency, tau_b = max uncertainty, "
                "exact fractions, fixed system at (alpha0 = 0.7, k0 = 5)",
        "worlds": calibration_worlds(records, exacts),
        "rejected_draws": rejected,
    }
    _write_json(out / "CAL_WORLDS.json", cal, overwrite=dev)
    tau_doc = {
        "core_sha256": core,
        "rule": "D1",
        **taus.to_json(),
        "info": info,
        "cal_worlds_sha256": _sha(out / "CAL_WORLDS.json"),
    }
    _write_json(out / "TAU.json", tau_doc, overwrite=dev)
    return {"taus": taus, "n_rejected": len(rejected)}


def recheck_calibration(core: str, salt: str | None, out: Path, dev: bool, n_cal: int) -> ExactTaus:
    """R1-4 and R3-7: regenerate the calibration worlds, recompute tau, and refuse unless tau equals TAU.json exactly,
    sha256(CAL_WORLDS.json) matches the hash recorded in TAU.json, and the regenerated world records (seeds, hashes,
    metrics) and rejected draws equal CAL_WORLDS.json."""
    tau_doc = json.loads((out / "TAU.json").read_text(encoding="utf-8"))
    if tau_doc.get("core_sha256") != core:
        raise Refused("TAU.json was made for another core hash")
    stored = ExactTaus.from_json(tau_doc)
    if _sha(out / "CAL_WORLDS.json") != tau_doc.get("cal_worlds_sha256"):
        raise Refused("sha256(CAL_WORLDS.json) does not match TAU.json")
    records, rejected, taus, _, exacts = build_calibration(core, salt, dev, n_cal)
    if taus != stored:
        raise Refused("the recomputed tau differs from TAU.json")
    cal = json.loads((out / "CAL_WORLDS.json").read_text(encoding="utf-8"))
    if _roundtrip(calibration_worlds(records, exacts)) != cal.get("worlds") or _roundtrip(rejected) != cal.get(
            "rejected_draws"):
        raise Refused("the regenerated calibration worlds differ from CAL_WORLDS.json")
    return stored


OUTPUT_NAMES = ("TEST_WORLDS.json", "RESULTS.json", "VERDICTS.json", "STOPPED.json", "outputs_input", "outputs_results")


def run_test(core: str, salt: str | None, out: Path, dev: bool, n_cal: int, n_test: int,
             subprocess_checks: bool, inputs: Path | None = None) -> dict:
    """The test step. `inputs` is the folder that holds CAL_WORLDS.json and TAU.json (default: `out`). Nothing is written
    until the verdict table and the descriptive summary have been built (R3-6): a failure before that point leaves no
    outcome on disk; the only exception is STOPPED.json, written when a fidelity control disagrees."""
    inputs = inputs or out
    tau_path = inputs / "TAU.json"
    if not tau_path.is_file():
        raise Refused(f"{tau_path} not found: run calibrate first")
    taus = recheck_calibration(core, salt, inputs, dev, n_cal)
    sd = seeder(core, salt)
    if dev:  # development outputs are scratch: start from a clean folder
        for name in ("outputs", "outputs_input", "outputs_results"):
            shutil.rmtree(out / name, ignore_errors=True)
        (out / "STOPPED.json").unlink(missing_ok=True)
    else:  # a real run never overwrites its outputs: refuse before any work is done
        existing = [name for name in OUTPUT_NAMES if (out / name).exists()]
        if existing:
            raise Refused(f"{out} already holds {', '.join(existing)}; a real run never overwrites its outputs")
    records, rejected = generate_valid(
        n_test, sd, "world-test", "enc-test", "aux", build=get_encoding if dev else None
    )
    # R1-12: F1, F2 and F4 on ALL test worlds first; on any disagreement nothing but STOPPED.json is written
    controls = {}
    for rec in records:
        controls[rec.world_seed] = run_controls(rec)
        bad = {k: v[1] for k, v in controls[rec.world_seed].items() if not v[0]}
        if bad:
            _write_json(out / "STOPPED.json", {"world_seed": rec.world_seed, "disagreements": bad}, overwrite=True)
            raise ControlDisagreement(f"world {rec.world_seed}: {bad}")
    # R2-11, R3-6: everything is held in memory; the table and the summary are built before any output is written.
    per_world, timings, pending = [], [], []
    for rec in records:
        t0 = time.perf_counter()
        ev = evaluate_world(rec, taus, sd, subprocess_checks=subprocess_checks, run_twins=True, keep_data=True)
        pending.append((rec.world_seed, blind_input(rec, taus, ev), run_results(rec, ev, controls[rec.world_seed], taus)))
        per_world.append((rec, ev))
        timings.append(time.perf_counter() - t0)

    per_test = {t: [(rec.world_seed, ev["fixed"][t]["outcome"]) for rec, ev in per_world] for t in C.TEST_IDS}
    twin_summary, both = {}, {}
    for name, test in TWIN_TEST.items():
        outcomes = [ev["twins"][name]["outcome"] for _, ev in per_world]
        both_n = sum(
            ev["fixed"][test]["outcome"] == "HOLDS" and ev["twins"][name]["outcome"] == "HOLDS" for _, ev in per_world
        )
        twin_summary[name] = {"test": test, "both_hold": both_n, **{o: outcomes.count(o) for o in ("HOLDS", "FAILS", "UNDEFINED")}}
    for test in C.TEST_IDS:
        n = sum(
            ev["fixed"][test]["outcome"] == "HOLDS"
            and any(ev["twins"][nm]["outcome"] == "HOLDS" for nm, t in TWIN_TEST.items() if t == test)
            for _, ev in per_world
        )
        both[test] = n
    table = verdict_table(
        per_test, both,
        failed_parts={rec.world_seed: ev["fixed"]["G1"]["failed_parts"] for rec, ev in per_world},
        structure=[ev["descriptive"]["t1_structure"] for _, ev in per_world],
        n_hypotheses=[ev["fixed"]["G8"]["n_hypotheses"] for _, ev in per_world],
    )
    cross = [ev["descriptive"]["cross_seed"] for _, ev in per_world if ev["descriptive"]["cross_seed"]]
    pooled = lambda k_n, k_a: (sum(c[k_a] for c in cross), sum(c[k_n] for c in cross))
    desc = {
        "cross_seed_pooled": {
            "class_atoms": dict(zip(("agree", "n"), pooled("n_class", "agree_class"))),
            "all_atoms": dict(zip(("agree", "n"), pooled("n_all", "agree_all"))),
        },
        "g7b_positive_worlds": sum(ev["descriptive"]["g7b"]["positive"] for _, ev in per_world),
        "g8_whole_grid_all_points_ok": sum(ev["descriptive"]["g8_whole_grid"]["all_points_ok"] for _, ev in per_world),
        "g8_failing_only_through_single_atom_changes": sum(
            ev["descriptive"]["g8_single_atom_only"] is True for _, ev in per_world
        ),
        "t1_all_points": {o: sum(ev["descriptive"]["t1_all_points"] == o for _, ev in per_world)
                          for o in ("HOLDS", "FAILS", "UNDEFINED")},
        "t1_structure": [dict(world_seed=rec.world_seed, **ev["descriptive"]["t1_structure"]) for rec, ev in per_world],
        "default_feasible_worlds": sum(ev["descriptive"]["default_feasible"] for _, ev in per_world),
        "undefined_as_fails": {t: undefined_as_fails(per_test[t]) for t in QUANTITATIVE_TESTS},
        "detector_diagnostic": twin_summary,
    }
    documents = [
        (out / "TEST_WORLDS.json",
         {"core_sha256": core, "environment": env_info(), "worlds": [world_record_json(r) for r in records],
          "rejected_draws": rejected}),
    ]
    for seed_, blind, results in pending:
        documents.append((out / "outputs_input" / f"{seed_}.json", blind))
        documents.append((out / "outputs_results" / f"{seed_}.json", results))
    documents.append((
        out / "RESULTS.json",
        {"core_sha256": core, "taus": taus.to_json(),
         "worlds": [{"world_seed": rec.world_seed, "fixed": {t: ev["fixed"][t]["outcome"] for t in C.TEST_IDS},
                     "twins": ev["twins"], "descriptive": ev["descriptive"]} for rec, ev in per_world]},
    ))
    documents.append((
        out / "VERDICTS.json",
        {"core_sha256": core, "environment": env_info(), "table": table, "descriptive": desc,
         "n_test_worlds": len(per_world), "n_rejected_draws": len(rejected),
         "world_hashes": {r.world_seed: world_record_json(r) for r, _ in per_world}},
    ))
    for path, doc in documents:  # only now does anything reach the disk
        _write_json(path, doc, overwrite=dev)
    return {"table": table, "seconds_per_world": timings, "n_worlds": len(per_world)}


def reproduce(root: Path, core: str, salt: str, out_name: str = "run_repro", test_fn=None) -> dict:
    """R3-6: rerun the test step of a real run into root/run_repro/, reading SALT-derived worlds, CAL_WORLDS.json and
    TAU.json from root/run/, and compare the SHA-256 of the two VERDICTS.json files. Refuses if run_repro/ exists or
    if run/VERDICTS.json is not committed and unmodified (the folder is a clone of the result commit)."""
    run_dir, out = root / "run", root / out_name
    if out.exists():
        raise Refused(f"{out} already exists; reproduce never overwrites")
    check_committed_clean(root, "run/VERDICTS.json")
    (test_fn or run_test)(core, salt, out, False, N_CAL, N_TEST, True, inputs=run_dir)
    repro, original = _sha(out / "VERDICTS.json"), _sha(run_dir / "VERDICTS.json")
    return {"equal": repro == original, "repro_sha256": repro, "run_sha256": original}


# ------------------------------------------------------------------------------------------------ main
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="py -m audit.run_v02", description=__doc__.split("\n\n")[0])
    ap.add_argument("mode", choices=("calibrate", "test", "reproduce"))
    ap.add_argument("--dev", action="store_true", help="development mode (core 'dev', output in run_dev/)")
    ap.add_argument("--n-cal", type=int, default=N_CAL, help="development mode only")
    ap.add_argument("--n-test", type=int, default=N_TEST, help="development mode only")
    ap.add_argument("--no-subprocess", action="store_true", help="development mode only")
    args = ap.parse_args(argv)
    if not args.dev and (args.n_cal != N_CAL or args.n_test != N_TEST or args.no_subprocess):
        print("--n-cal, --n-test and --no-subprocess are for development mode only", file=sys.stderr)
        return EXIT_USAGE
    if args.dev and args.mode == "reproduce":
        print("reproduce is a real-mode command (run it in a clone of the result commit)", file=sys.stderr)
        return EXIT_USAGE
    entry = Path(__file__).resolve()
    try:
        if args.dev:
            core, salt, out = DEV_CORE, DEV_SALT, ROOT / "run_dev"
        else:
            check_versions()
            core = verify_freeze(MANIFEST, entry)
            _, salt_commit, salt = check_freeze_and_salt(ROOT, core)
            if args.mode in ("test", "reproduce"):
                check_tau_after_salt(ROOT, salt_commit)
            out = ROOT / "run"
        if args.mode == "reproduce":
            info = reproduce(ROOT, core, salt)
            print(f"run/VERDICTS.json    sha256 {info['run_sha256']}")
            print(f"run_repro/VERDICTS.json sha256 {info['repro_sha256']}")
            print("REPRODUCED: byte-identical" if info["equal"] else "NOT REPRODUCED: the files differ")
            if not info["equal"]:
                return EXIT_REPRO
        elif args.mode == "calibrate":
            info = run_calibrate(core, salt, out, args.dev, args.n_cal)
            print(f"calibrated on {args.n_cal} worlds ({info['n_rejected']} draws rejected); wrote {out}/TAU.json")
        else:
            info = run_test(core, salt, out, args.dev, args.n_cal, args.n_test, subprocess_checks=not args.no_subprocess)
            secs = info["seconds_per_world"]
            print(f"tested {info['n_worlds']} worlds in {sum(secs):.1f} s ({sum(secs) / len(secs):.1f} s per world); "
                  f"wrote {out}/VERDICTS.json")
        if not args.dev:  # the freeze must still hold after the run
            verify_freeze(MANIFEST, entry)
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
