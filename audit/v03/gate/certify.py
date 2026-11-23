"""Run the Truth_Gate (0.5.1) on one v0.3 gate study, or verify its certificate (PREREG_v0.3 section 6.3).

    py -m audit.v03.gate.certify g1 [--quick]     # writes audit/v03/gate/g1.cert.json (full: 100 samples per stream)
    py -m audit.v03.gate.certify g1 --verify      # re-runs the study and compares the certificate hash
    py -m audit.v03.gate.certify all [--quick]
    py -m audit.v03.gate.certify all --verify [--tool-out PATH]   # also writes GATE_TOOL.json (default: next to this file)

Studies: g1 .. g7 (g7 is G7a) and t1; G8 has no verdict in v0.3 and no study. The driver is v0.2's (`audit.gate.certify`) with
the v0.3 studies: it loads `truth_gate` from the local kapi-oss checkout (the environment variable TRUTH_GATE_DIR, default
E:/Claude Projects/kapi-oss), refuses to run unless truth_gate/, kapi/ and protocol/ are identical to tag v0.5.1 and clean (no
modified, staged or untracked file), and records the checkout's commit. Every module the studies use is imported before the
gate's leak guard is armed.

`all --verify` (just before the freeze, PREREG section 8 step 6) writes GATE_TOOL.json: the kapi-oss commit, every certificate's
verdict and body hash with the exit code of its verification, and the SHA-256 of every file in audit/ and tesaron/. Only the
default location, audit/v03/gate/GATE_TOOL.json, is read by the pre-freeze check; --tool-out is for trial runs.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

# Everything the studies use, imported before the guard is armed (v0.2's list, and the v0.3 modules).
import audit.gate.certify as base  # noqa: F401  (imports the v0.2 modules, truth_gate and the checkout path)
import audit.v03.aggregate  # noqa: F401
import audit.v03.checks  # noqa: F401
import audit.v03.gate.common  # noqa: F401
from audit.v03.gate import common as gate_common  # noqa: E402
import audit.v03.seeds  # noqa: F401
import audit.v03.tau  # noqa: F401
import audit.v03.worlds  # noqa: F401
import audit.v03.worldset  # noqa: F401
import audit.twins.nt  # noqa: F401
import audit.oracle  # noqa: F401
import tesaron.belnap  # noqa: F401
import tesaron.enums  # noqa: F401
from audit.v03.gate import g1_study, g2_study, g3_study, g4_study, g5_study, g6_study, g7_study, t1_study  # noqa: F401,E402

cli = base.cli
HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent.parent
IDS = ("g1", "g2", "g3", "g4", "g5", "g6", "g7", "t1")
TAG = base.TAG
TOOL_REL = "audit/v03/gate/GATE_TOOL.json"


def study_path(gid: str) -> Path:
    return HERE / f"{gid}_study.py"


def cert_path(gid: str) -> Path:
    return HERE / f"{gid}.cert.json"


def check_checkout() -> str:
    """The kapi-oss commit, after refusing (ValueError) a checkout whose truth_gate/, kapi/ or protocol/ differ from tag
    v0.5.1 or hold a modified, staged or untracked file (the check of v0.2's driver)."""
    return base.check_checkout()


def file_hashes() -> dict:
    """SHA-256 of every file in audit/ and tesaron/ (not caches, quick certificates or any GATE_TOOL.json): the definition of
    audit.prefreeze_check.gate_file_hashes, which the pre-freeze check uses to compare."""
    from audit.prefreeze_check import gate_file_hashes

    return gate_file_hashes(REPO)


def tool_payload(commit: str, results: dict, t1_counts: dict | None = None) -> dict:
    """The content of GATE_TOOL.json: certificates' verdicts and hashes, the checkout commit and the file table."""
    certs = {}
    for gid in IDS:
        doc = json.loads(cert_path(gid).read_text(encoding="utf-8"))
        certs[gid] = {
            "verdict": doc["body"]["verdict"],
            "body_sha256": doc["body_sha256"],
            "flags": sorted({f for c in doc["body"]["components"] for f in c["flags"]}),
            "verify_exit": results.get(gid),
        }
    return {
        "tool": "truth_gate",
        "tool_version": cli.TOOL_VERSION,
        "kapi_oss_commit": commit,
        "tag": TAG,
        "tag_check": "truth_gate/, kapi/ and protocol/ identical to the tag and clean (no modified, staged or untracked file)",
        "python": sys.version,
        "t1_plus_world_draws": t1_counts,
        "certificates": certs,
        "files": file_hashes(),
    }


def write_gate_tool(commit: str, results: dict, out: Path | None = None, t1_counts: dict | None = None) -> Path:
    """Write GATE_TOOL.json (LF line endings on every machine) to `out`, default audit/v03/gate/GATE_TOOL.json."""
    out = Path(out) if out else HERE / "GATE_TOOL.json"
    payload = tool_payload(commit, results, t1_counts)
    with open(out, "w", encoding="utf-8", newline=chr(10)) as fh:
        fh.write(json.dumps(payload, indent=1, sort_keys=True) + chr(10))
    return out


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    quick = "--quick" in argv
    verify = "--verify" in argv
    tool_out = None
    if "--tool-out" in argv:
        i = argv.index("--tool-out")
        if i + 1 >= len(argv):
            print("--tool-out needs a path", file=sys.stderr)
            return 4
        tool_out = Path(argv[i + 1])
        del argv[i:i + 2]
    ids = [a for a in argv if not a.startswith("--")]
    if not ids:
        print(__doc__)
        return 4
    for gid in ids:  # R1-15: the study ids are validated before anything starts git (the checkout check)
        if gid != "all" and gid not in IDS:
            print(f"unknown study {gid!r}; known: {', '.join(IDS)}")
            return 4
    if "all" in ids and ids != ["all"]:
        print("'all' stands alone")
        return 4
    try:
        commit = check_checkout()
    except ValueError as exc:
        print(f"refusing: {exc}", file=sys.stderr)
        return 4
    print(f"kapi-oss checkout commit {commit}; truth_gate/, kapi/ and protocol/ identical to tag {TAG}")
    if ids == ["all"]:
        ids = list(IDS)
    worst = 0
    exit_codes: dict = {}
    t1_counts = None
    for gid in ids:
        t0 = time.perf_counter()
        gate_common.reset_t1_counts()
        if verify:
            code = cli.main(["verify", str(cert_path(gid)), str(study_path(gid))])
        else:
            out = cert_path(gid) if not quick else HERE / f"{gid}.quick.cert.json"
            code = cli.main(["check", str(study_path(gid)), "--out", str(out)] + (["--quick"] if quick else []))
            base.rewrite_lf(out)  # truth_gate writes in text mode (CRLF on Windows); the body hash is over the canonical body
        print(f"[{gid}] exit {code}, {time.perf_counter() - t0:.1f} s")
        if gid == "t1":  # definedness only: how many draws the T-1 plus world skipped as undefined (all streams of the study)
            t1_counts = dict(gate_common.T1_COUNTS)
            print(f"[t1] plus-world draws over all streams: {t1_counts['accepted']} worlds taken, "
                  f"{t1_counts['skipped_undefined']} skipped as undefined")
        exit_codes[gid] = code
        worst = max(worst, code)
    if verify and set(ids) == set(IDS) and not quick:
        print(f"wrote {write_gate_tool(commit, exit_codes, tool_out, t1_counts)}")
    return worst


if __name__ == "__main__":
    sys.exit(main())
