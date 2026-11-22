"""Run the Truth_Gate (0.5.1) on one gate study, or verify its certificate.

    py -m audit.gate.certify g1 [--quick]          # writes audit/gate/g1.cert.json (full: 100 samples per stream)
    py -m audit.gate.certify g1 --verify           # re-runs the study and compares the certificate hash
    py -m audit.gate.certify all [--quick]

This is `truth-gate check audit/gate/g1_study.py --out audit/gate/g1.cert.json` (the same command-line code, the same
engine), preceded by importing every audit and tesaron module. The gate's leak guard blocks opening any file while
a study runs, which includes the source file of a module the study imports for the first time; modules that are
already in sys.modules are not opened again. Nothing else is different: the study files, the criteria and the
certificate are the gate's own.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

# Everything the studies use, imported before the guard is armed.
import numpy  # noqa: F401
import audit.checks  # noqa: F401
import audit.descriptive  # noqa: F401
import audit.gate.common  # noqa: F401
import audit.hashing  # noqa: F401
import audit.prefreeze_check  # noqa: F401
import audit.system  # noqa: F401
import audit.twins  # noqa: F401
import audit.worldset  # noqa: F401
import tesaron.criterion  # noqa: F401
import tesaron.decoder  # noqa: F401
import tesaron.encoder  # noqa: F401
import tesaron.encoder.core  # noqa: F401
import tesaron.serialize  # noqa: F401
import tesaron.worlds  # noqa: F401

try:  # truth_gate 0.5.1 is the declared optional dependency
    from truth_gate import cli  # noqa: E402
except ModuleNotFoundError:  # not installed in this interpreter: use a checkout (nothing is installed or copied)
    import os

    sys.path.insert(0, os.environ.get("TRUTH_GATE_DIR", r"E:\Claude Projects\kapi-oss"))
    from truth_gate import cli  # noqa: E402

from audit.prefreeze_check import gate_file_hashes  # noqa: E402

HERE = Path(__file__).resolve().parent
IDS = ("g1", "g2", "g3", "g4", "g5", "g6", "g7", "g8", "t1")


def study_path(gid: str) -> Path:
    return HERE / f"{gid}_study.py"


def cert_path(gid: str) -> Path:
    return HERE / f"{gid}.cert.json"


TAG = "v0.5.1"


def check_checkout() -> str:
    """Record the kapi-oss checkout commit and refuse (ValueError) unless truth_gate/, kapi/ and protocol/ are
    identical to tag v0.5.1 and clean (no modified, staged or untracked file there, R2-12). These git calls run here,
    outside the guarded study run."""
    root = Path(cli.__file__).resolve().parent.parent
    head = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"], capture_output=True, text=True)
    if head.returncode != 0:
        raise ValueError(f"{root} is not a git checkout")
    diff = subprocess.run(
        ["git", "-C", str(root), "diff", "--quiet", TAG, "--", "truth_gate", "kapi", "protocol"],
        capture_output=True, text=True,
    )
    if diff.returncode != 0:
        raise ValueError(f"truth_gate/, kapi/ or protocol/ in {root} differ from tag {TAG} (or the tag is missing)")
    status = subprocess.run(
        ["git", "-C", str(root), "status", "--porcelain", "--untracked-files=all", "--", "truth_gate", "kapi", "protocol"],
        capture_output=True, text=True,
    )
    if status.returncode != 0 or status.stdout.strip():
        raise ValueError(f"truth_gate/, kapi/ or protocol/ in {root} have modified, staged or untracked files")
    return head.stdout.strip()


REPO = HERE.parent.parent


def file_hashes() -> dict:
    """SHA-256 of every file in audit/ and tesaron/ (not caches, quick certificates or GATE_TOOL.json itself). The
    definition is audit.prefreeze_check.gate_file_hashes, which the pre-freeze check uses to compare."""
    return gate_file_hashes(REPO)


def rewrite_lf(path: Path) -> bool:
    """Rewrite a file with LF line endings (bytes only; True if anything changed). truth_gate writes its certificates in
    text mode, which gives CRLF on Windows; the body hash is over the canonical body, not over these bytes (R3-1)."""
    if not path.is_file():
        return False
    data = path.read_bytes()
    fixed = data.replace(b"\r\n", b"\n")
    if fixed != data:
        path.write_bytes(fixed)
    return fixed != data


def write_gate_tool(commit: str, results: dict) -> Path:
    """audit/gate/GATE_TOOL.json: the kapi-oss commit, the tag check, every certificate's verdict and body hash, the
    exit code of its verification, and the SHA-256 of every file in audit/ and tesaron/ (PREREG section 6.3)."""
    certs = {}
    for gid in IDS:
        doc = json.loads(cert_path(gid).read_text(encoding="utf-8"))
        certs[gid] = {
            "verdict": doc["body"]["verdict"],
            "body_sha256": doc["body_sha256"],
            "flags": sorted({f for c in doc["body"]["components"] for f in c["flags"]}),
            "verify_exit": results.get(gid),
        }
    out = HERE / "GATE_TOOL.json"
    payload = {
        "tool": "truth_gate",
        "tool_version": cli.TOOL_VERSION,
        "kapi_oss_commit": commit,
        "tag": TAG,
        "tag_check": "truth_gate/, kapi/ and protocol/ identical to the tag and clean (no modified, staged or untracked file)",
        "python": sys.version,
        "certificates": certs,
        "files": file_hashes(),
    }
    with open(out, "w", encoding="utf-8", newline=chr(10)) as fh:  # LF on every machine (R3-1)
        fh.write(json.dumps(payload, indent=1, sort_keys=True) + chr(10))
    return out


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    quick = "--quick" in argv
    verify = "--verify" in argv
    ids = [a for a in argv if not a.startswith("--")]
    if ids:
        try:
            commit = check_checkout()
        except ValueError as exc:
            print(f"refusing: {exc}", file=sys.stderr)
            return 4
        print(f"kapi-oss checkout commit {commit}; truth_gate/, kapi/ and protocol/ identical to tag {TAG}")
    if not ids:
        print(__doc__)
        return 4
    if ids == ["all"]:
        ids = list(IDS)
    worst = 0
    exit_codes: dict = {}
    for gid in ids:
        if gid not in IDS:
            print(f"unknown study {gid!r}; known: {', '.join(IDS)}")
            return 4
        t0 = time.perf_counter()
        if verify:
            code = cli.main(["verify", str(cert_path(gid)), str(study_path(gid))])
        else:
            out = HERE / f"{gid}.cert.json" if not quick else HERE / f"{gid}.quick.cert.json"
            code = cli.main(["check", str(study_path(gid)), "--out", str(out)] + (["--quick"] if quick else []))
        if not verify:
            rewrite_lf(out)
        print(f"[{gid}] exit {code}, {time.perf_counter() - t0:.1f} s")
        exit_codes[gid] = code
        worst = max(worst, code)
    if verify and set(ids) == set(IDS) and not quick:
        print(f"wrote {write_gate_tool(commit, exit_codes)}")
    return worst


if __name__ == "__main__":
    sys.exit(main())
