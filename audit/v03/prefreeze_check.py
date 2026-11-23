"""Pre-freeze check of Tesaron v0.3 (PREREG_v0.3 sections 6.3 and 8 step 6): refuses the freeze unless the tree about to be
frozen is the tree the gate certified, git tracks exactly what the freeze would hash, and the pre-registration and the design
studies are in their final state.

    py -m audit.v03.prefreeze_check [--gate-tool] [--tracked] [--status] [--studies] [--v02] [--repo PATH]

With no option every check runs. Each prints its problems; the exit code is 0 only if all that ran are clean.

1. GATE_TOOL.json (`audit/v03/gate/GATE_TOOL.json`): its "files" table equals the current SHA-256 of every file in audit/ and
   tesaron/ (the table `audit.v03.gate.certify` writes; any file added, removed or changed since `certify all --verify` is listed),
   and (R1-5) it lists all eight study ids, each with `verify_exit` 0, verdict FALSIFIABLE (unless the verdict is WEAK and the
   optional waiver file `audit/v03/gate/WAIVERS.json` waives it: that file is absent (no waiver) or a JSON object from the
   driver's study id (g1-g7, t1) to a non-empty written reason; any other form is refused and waives nothing; only a WEAK
   verdict can be waived, R2-5) and a body hash equal to that of the committed `<id>.cert.json`, and its tag is v0.5.1.
2. Tracked files: the files the freeze verifier would hash (`audit.v03.freeze.manifest_files`) are exactly the git-tracked files
   under the PREREG section 9 manifest paths (for prereg/v03/ only the .json files directly in it, except the manifest). And every
   such file's working bytes equal its staged blob (`git cat-file blob :<path>`), so a fresh clone reproduces them.
3. Status: the third line of prereg/PREREG_v0.3.md and of SPEC_v0.3.md is the frozen status line of section 8 step 6 (each file
   its own), and neither "not frozen" (in any case) nor "DRAFT" (in capitals) occurs in the first 12 lines of either (post-run
   audit A10, R1-6).
4. Design studies: each study whose numbers the pre-registration prints (S1, S1b, S2, the power study, the all_true study and the n_q study) is
   rerun with the tree to be frozen, into a temporary folder, and its JSON equals the committed one apart from the
   `runtime_seconds` field (post-run audit A2, R1-7). Each study runs in its own fresh interpreter, started from the repository;
   they run in parallel.
5. v0.2's manifest prereg/FREEZE_v0.2.json still verifies.
It never writes into the repository, commits or fetches (the studies write only into a temporary folder). Exit codes: 0 all
hold, 1 something differs, 2 usage or I/O error.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from audit import freeze as base_freeze
from audit.prefreeze_check import _git_lines, gate_file_hashes, staged_blobs
from audit.v03 import freeze as v03_freeze

REPO = Path(__file__).resolve().parent.parent.parent
GATE_TOOL_REL = "audit/v03/gate/GATE_TOOL.json"
WAIVERS_REL = "audit/v03/gate/WAIVERS.json"
GATE_IDS = ("g1", "g2", "g3", "g4", "g5", "g6", "g7", "t1")  # the eight studies (audit.v03.gate.certify.IDS)
GATE_TAG = "v0.5.1"
GATE_VERDICT = "FALSIFIABLE"
PREREG_REL = "prereg/PREREG_v0.3.md"
SPEC_REL = "SPEC_v0.3.md"
V02_MANIFEST_REL = "prereg/FREEZE_v0.2.json"
# PREREG section 8 step 6, exactly: the frozen status line of each file
FROZEN_STATUS_LINE = (
    "**Status: FROZEN.** The manifest is `prereg/v03/FREEZE_v0.3.json`; the freeze commit, its date and the core hash are in "
    "`prereg/v03/FREEZE_RECORD.md`. The drafts and their changes are listed in §10."
)
SPEC_FROZEN_STATUS_LINE = (
    "**Status: FROZEN** with `prereg/PREREG_v0.3.md`, by the manifest `prereg/v03/FREEZE_v0.3.json`; see "
    "`prereg/v03/FREEZE_RECORD.md`."
)
STATUS_FILES = ((PREREG_REL, FROZEN_STATUS_LINE), (SPEC_REL, SPEC_FROZEN_STATUS_LINE))
STATUS_LINE_NO = 3
STATUS_WINDOW = 12
BANNED_PHRASES = (("not frozen", False), ("DRAFT", True))  # (phrase, case-sensitive)
# the design studies whose numbers the pre-registration prints: name -> (module, committed JSON)
STUDIES = {
    "S1": ("audit.design.v03_world_study", "prereg/v03/WORLD_STUDY.json"),
    "S1b": ("audit.design.v03_overlap_study", "prereg/v03/OVERLAP_STUDY.json"),
    "S2": ("audit.design.v03_tau_rule_study", "prereg/v03/TAU_RULE_STUDY.json"),
    "power study": ("audit.design.v03_power_study", "prereg/v03/POWER_STUDY.json"),
    "all_true study": ("audit.design.v03_all_true_study", "prereg/v03/ALL_TRUE_STUDY.json"),
    "n_q study": ("audit.design.v03_nq_study", "prereg/v03/NQ_STUDY.json"),
}
IGNORED_KEY = "runtime_seconds"
STUDY_TIMEOUT = 3600


# ------------------------------------------------------------------------------------------------ 1. GATE_TOOL
WEAK_VERDICT = "WEAK"  # the only verdict a waiver can cover (PREREG 6.3, R2-5)


def read_waivers(repo: Path) -> tuple:
    """(waived ids, problems) of the author's waiver file (PREREG 6.3, R1-5, R2-5). The file is absent (no waiver, no problem) or
    a JSON object whose keys are the driver's study ids (`GATE_IDS`: g1-g7 and t1; "G7a" or "T-1" are not ids) and whose values
    are non-empty strings, the written reasons (a reason of whitespace only is empty). Any other form is refused: it is a
    problem, and then nothing is waived. A waiver can cover only a WEAK verdict (`check_certificates`)."""
    path = repo / WAIVERS_REL
    if not path.exists():
        return set(), []
    name = f"{WAIVERS_REL} (refused, nothing is waived)"
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return set(), [f"{name}: cannot read it ({type(exc).__name__})"]
    if not isinstance(doc, dict):
        return set(), [f"{name}: it is not a JSON object from study id to written reason"]
    problems = []
    for key, reason in doc.items():
        if key not in GATE_IDS:
            problems.append(f"{name}: {key!r} is not a study id of the driver ({', '.join(GATE_IDS)})")
        elif not isinstance(reason, str) or not reason.strip():
            problems.append(f"{name}: the reason for {key} is not a non-empty string")
    return (set() if problems else set(doc)), problems


def check_certificates(doc: dict, repo: Path = REPO) -> list:
    """Problems of the certificate part of a parsed GATE_TOOL.json (R1-5): all eight study ids; each with verify_exit 0,
    verdict FALSIFIABLE (unless it is WEAK and waived, `read_waivers`), and a body hash equal to that of the committed `<id>.cert.json`; tag v0.5.1."""
    problems = []
    if doc.get("tag") != GATE_TAG:
        problems.append(f"GATE_TOOL tag is {doc.get('tag')!r}, not {GATE_TAG}")
    certs = doc.get("certificates")
    if not isinstance(certs, dict):
        return problems + ["GATE_TOOL has no certificates"]
    waived, waiver_problems = read_waivers(repo)
    problems += waiver_problems
    for gid in GATE_IDS:
        entry = certs.get(gid)
        if not isinstance(entry, dict):
            problems.append(f"GATE_TOOL has no certificate for {gid}")
            continue
        exit_code = entry.get("verify_exit")
        if not isinstance(exit_code, int) or isinstance(exit_code, bool) or exit_code != 0:
            problems.append(f"certificate {gid}: verify_exit is {exit_code!r}, not 0")
        verdict = entry.get("verdict")
        if verdict != GATE_VERDICT and not (gid in waived and verdict == WEAK_VERDICT):
            why = "a waiver covers only WEAK" if gid in waived else "no waiver"
            problems.append(f"certificate {gid}: verdict is {verdict!r}, not {GATE_VERDICT} ({why})")
        cert_rel = f"audit/v03/gate/{gid}.cert.json"
        try:
            committed = json.loads((repo / cert_rel).read_text(encoding="utf-8")).get("body_sha256")
        except (OSError, ValueError):
            problems.append(f"cannot read {cert_rel}")
            continue
        if entry.get("body_sha256") != committed:
            problems.append(f"certificate {gid}: the body hash in GATE_TOOL differs from {cert_rel}")
    for gid in sorted(set(certs) - set(GATE_IDS)):
        problems.append(f"GATE_TOOL lists an unknown study id: {gid}")
    return problems


def check_gate_tool(repo: Path = REPO) -> list:
    """Problems of audit/v03/gate/GATE_TOOL.json against the current files and the certificates, as strings (empty if it
    holds)."""
    path = repo / GATE_TOOL_REL
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
        recorded = doc.get("files")
    except (OSError, ValueError, AttributeError) as exc:
        return [f"cannot read {GATE_TOOL_REL}: {type(exc).__name__}"]
    if not isinstance(recorded, dict):
        return [f"{GATE_TOOL_REL} has no file table"]
    current = gate_file_hashes(repo)
    problems = check_certificates(doc, repo)
    for rel in sorted(set(recorded) | set(current)):
        if rel not in current:
            problems.append(f"GATE_TOOL lists a file that is gone: {rel}")
        elif rel not in recorded:
            problems.append(f"file not in GATE_TOOL: {rel}")
        elif recorded[rel] != current[rel]:
            problems.append(f"changed since the gate ran: {rel}")
    return problems


# ------------------------------------------------------------------------------------------------ 2. tracked files
def tracked_manifest_set(repo: Path) -> set:
    """The git-tracked files under the PREREG section 9 manifest paths that the manifest must list."""
    tracked = []
    for rel in (*v03_freeze.FROZEN_PATHS, v03_freeze.STUDY_FOLDER):
        if (repo / rel).exists():
            tracked += _git_lines(repo, "ls-files", "--", rel)
    return {rel for rel in tracked if not rel.startswith(v03_freeze.STUDY_FOLDER + "/") or v03_freeze.is_study_json(rel)}


def check_tracked_set(repo: Path = REPO) -> list:
    """Problems of the frozen file set against git's tracked files, as strings (empty if they are equal and every working file
    equals its staged blob)."""
    missing = [rel for rel in v03_freeze.FROZEN_PATHS if not (repo / rel).exists()]
    problems = [f"listed path does not exist: {rel}" for rel in missing]
    walked = set(v03_freeze.manifest_files(repo)) if not missing else set()
    tracked = tracked_manifest_set(repo)
    for rel in sorted(walked - tracked):
        problems.append(f"would enter the manifest but is not tracked by git: {rel}")
    for rel in sorted(tracked - walked):
        problems.append(f"tracked by git but not hashed by the freeze walk: {rel}")
    both = sorted(walked & tracked)
    blobs = staged_blobs(repo, both) if both else {}
    for rel in both:
        blob = blobs[rel]
        if blob is None or hashlib.sha256((repo / rel).read_bytes()).digest() != hashlib.sha256(blob).digest():
            problems.append(f"the working file differs from its staged blob (line endings or an edit): {rel}")
    return problems


# ------------------------------------------------------------------------------------------------ 3. status line
def check_status_line(repo: Path = REPO) -> list:
    """Problems with the header of the pre-registration and of the spec: line 3 of each must be its own frozen status line
    (section 8 step 6), and "not frozen" (any case) and "DRAFT" (capitals) must not occur in the first 12 lines of either
    (post-run audit A10, R1-6)."""
    problems = []
    for rel, frozen in STATUS_FILES:
        try:
            text = (repo / rel).read_text(encoding="utf-8")
        except OSError as exc:
            problems.append(f"cannot read {rel}: {type(exc).__name__}")
            continue
        lines = text.split("\n")
        if len(lines) < STATUS_LINE_NO or lines[STATUS_LINE_NO - 1] != frozen:
            got = lines[STATUS_LINE_NO - 1] if len(lines) >= STATUS_LINE_NO else "<no such line>"
            problems.append(f"line {STATUS_LINE_NO} of {rel} is not the frozen status line: {got[:80]!r}")
        for n, line in enumerate(lines[:STATUS_WINDOW], 1):
            for phrase, case_sensitive in BANNED_PHRASES:
                if (phrase in line) if case_sensitive else (phrase.lower() in line.lower()):
                    problems.append(f'line {n} of {rel} contains "{phrase}"')
    return problems


# ------------------------------------------------------------------------------------------------ 4. design studies
STUDY_CODE = (
    "import importlib, sys\n"
    "from pathlib import Path\n"
    "mod = importlib.import_module(sys.argv[1])\n"
    "mod.OUT = Path(sys.argv[2])\n"
    "sys.exit(mod.main([]))\n"
)


def strip_runtime(obj):
    """A deep copy of a parsed study JSON without any `runtime_seconds` field."""
    if isinstance(obj, dict):
        return {k: strip_runtime(v) for k, v in obj.items() if k != IGNORED_KEY}
    if isinstance(obj, list):
        return [strip_runtime(v) for v in obj]
    return obj


def first_difference(a, b, path: str = ""):
    """The path of the first difference between two parsed JSON values (None if equal)."""
    if type(a) is not type(b):
        return path or "/"
    if isinstance(a, dict):
        for key in sorted(set(a) | set(b)):
            if key not in a or key not in b:
                return f"{path}/{key}"
            d = first_difference(a[key], b[key], f"{path}/{key}")
            if d is not None:
                return d
        return None
    if isinstance(a, list):
        if len(a) != len(b):
            return f"{path} (length {len(a)} against {len(b)})"
        for i, (x, y) in enumerate(zip(a, b)):
            d = first_difference(x, y, f"{path}[{i}]")
            if d is not None:
                return d
        return None
    return None if a == b else (path or "/")


def run_study(repo: Path, module: str, out: Path):
    """Start one design study in a fresh interpreter, from the repository, writing its JSON to `out`. Returns the Popen."""
    env = {**os.environ, "PYTHONPATH": str(repo), "PYTHONDONTWRITEBYTECODE": "1"}
    return subprocess.Popen([sys.executable, "-B", "-c", STUDY_CODE, module, str(out)], cwd=repo, env=env,
                            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)


def check_studies(repo: Path = REPO, tmp_root=None, starter=run_study, studies=None) -> list:
    """Rerun every design study into a temporary folder (in parallel) and compare its JSON with the committed one, ignoring
    only `runtime_seconds`. Returns the problems as strings. `starter` and `studies` are for tests."""
    studies = STUDIES if studies is None else studies
    problems = []
    with tempfile.TemporaryDirectory(prefix="prefreeze_studies_", dir=tmp_root) as folder:
        running = {}
        for name, (module, rel) in studies.items():
            if not (repo / rel).is_file():
                problems.append(f"{name}: the committed {rel} does not exist")
                continue
            out = Path(folder) / Path(rel).name
            running[name] = (starter(repo, module, out), out, rel)
        for name, (proc, out, rel) in running.items():
            try:
                _, err = proc.communicate(timeout=STUDY_TIMEOUT)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.communicate()
                problems.append(f"{name}: the rerun did not finish within {STUDY_TIMEOUT} s")
                continue
            if proc.returncode != 0:
                problems.append(f"{name}: the rerun failed (exit {proc.returncode}): {(err or '').strip()[-200:]}")
                continue
            try:
                rerun = strip_runtime(json.loads(out.read_text(encoding="utf-8")))
                committed = strip_runtime(json.loads((repo / rel).read_text(encoding="utf-8")))
            except (OSError, ValueError) as exc:
                problems.append(f"{name}: cannot read the JSON ({type(exc).__name__})")
                continue
            diff = first_difference(rerun, committed)
            if diff is not None:
                problems.append(f"{name}: the rerun differs from the committed {rel} (first difference at {diff})")
    return problems


# ------------------------------------------------------------------------------------------------ 5. v0.2's manifest
def check_v02_manifest(repo: Path = REPO) -> list:
    path = repo / V02_MANIFEST_REL
    try:
        problems, _ = base_freeze.verify_manifest(str(path))
    except (OSError, ValueError) as exc:
        return [f"cannot verify {V02_MANIFEST_REL}: {type(exc).__name__}"]
    return [f"{V02_MANIFEST_REL}: {p}" for p in problems]


# ------------------------------------------------------------------------------------------------ main
CHECKS = ("gate-tool", "tracked", "status", "studies", "v02")


def run_checks(repo: Path, selected: tuple, tmp_root=None) -> list:
    problems = []
    if "gate-tool" in selected:
        problems += check_gate_tool(repo)
    if "tracked" in selected:
        problems += check_tracked_set(repo)
    if "status" in selected:
        problems += check_status_line(repo)
    if "v02" in selected:
        problems += check_v02_manifest(repo)
    if "studies" in selected:
        problems += check_studies(repo, tmp_root)
    return problems


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="py -m audit.v03.prefreeze_check", description=__doc__.split("\n\n")[0])
    for name in CHECKS:
        ap.add_argument(f"--{name}", action="store_true", help=f"run the {name} check")
    ap.add_argument("--repo", default=str(REPO), help="the repository (default: this one; for trial runs on a copy)")
    ap.add_argument("--tmp-root", default=None, help="folder for the temporary study output")
    args = ap.parse_args(argv)
    selected = tuple(n for n in CHECKS if getattr(args, n.replace("-", "_"))) or CHECKS
    try:
        problems = run_checks(Path(args.repo), selected, args.tmp_root)
    except OSError as exc:
        print(f"cannot check: {exc}", file=sys.stderr)
        return 2
    for p in problems:
        print(p)
    print("PRE-FREEZE CHECK FAILED" if problems else "PRE-FREEZE CHECK OK")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
