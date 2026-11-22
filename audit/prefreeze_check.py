"""Pre-freeze check (PREREG sections 6.3 and 8 step 6): refuses unless the tree that is about to be frozen is the tree
that the gate certified and that git tracks.

    py -m audit.prefreeze_check [--gate-tool] [--tracked] [PATH ...]

1. GATE_TOOL.json: audit/gate/GATE_TOOL.json["files"] equals the current SHA-256 of every file in audit/ and tesaron/
   (the same file set and the same hashes). Any file added, removed or changed since `certify all --verify` is listed.
2. Tracked files: the file set that audit/freeze.py would hash for the manifest paths equals the set that git tracks
   there (`git ls-files`). A file that is untracked or ignored (a quick certificate, a scratch file) and would enter
   the manifest is listed, and so is a tracked file that the walk would not hash. And for every walked file the SHA-256
   of its working bytes equals the SHA-256 of its staged blob (`git cat-file blob :<path>`): the bytes that the freeze
   hashes are the bytes that git stores, so a fresh clone reproduces them. A line-ending conversion or an uncommitted
   edit makes the two differ (R3-1); `git status` and `git diff` hide the former.
The default manifest paths are those of PREREG section 9. Standard library only; it never writes, commits or fetches.
Exit codes: 0 both hold, 1 something differs, 2 usage or I/O error.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

from audit import freeze as freeze_tool

REPO = Path(__file__).resolve().parent.parent
GATE_TOOL_REL = "audit/gate/GATE_TOOL.json"
GATE_DIRS = ("audit", "tesaron")
MANIFEST_PATHS = (
    "prereg/PREREG_v0.2.md", "SPEC.md", "tesaron", "audit", "prereg/F4_PREFREEZE.json", "prereg/DRAW_STUDY.json",
    "pyproject.toml", "tests",
)


def gate_file_hashes(repo: Path = REPO) -> dict:
    """SHA-256 of every file in audit/ and tesaron/ (not caches, quick certificates or GATE_TOOL.json itself). This is
    the table that certify.py writes into GATE_TOOL.json."""
    out = {}
    for sub in GATE_DIRS:
        for path in sorted((repo / sub).rglob("*")):
            if not path.is_file() or "__pycache__" in path.parts or path.suffix in (".pyc", ".pyo"):
                continue
            if path.name == "GATE_TOOL.json" or path.name.endswith(".quick.cert.json"):
                continue
            out[path.relative_to(repo).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return out


def check_gate_tool(repo: Path = REPO) -> list:
    """Problems of GATE_TOOL.json against the current files, as strings (empty if it holds)."""
    path = repo / GATE_TOOL_REL
    try:
        recorded = json.loads(path.read_text(encoding="utf-8")).get("files")
    except (OSError, ValueError) as exc:
        return [f"cannot read {GATE_TOOL_REL}: {type(exc).__name__}"]
    if not isinstance(recorded, dict):
        return [f"{GATE_TOOL_REL} has no file table"]
    current = gate_file_hashes(repo)
    problems = []
    for rel in sorted(set(recorded) | set(current)):
        if rel not in current:
            problems.append(f"GATE_TOOL lists a file that is gone: {rel}")
        elif rel not in recorded:
            problems.append(f"file not in GATE_TOOL: {rel}")
        elif recorded[rel] != current[rel]:
            problems.append(f"changed since the gate ran: {rel}")
    return problems


def _git_lines(repo: Path, *args: str) -> list:
    res = subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True)
    if res.returncode != 0:
        raise OSError(f"git {' '.join(args[:2])} failed: {res.stderr.strip()}")
    return [line for line in res.stdout.splitlines() if line]


def staged_blobs(repo: Path, rels) -> dict:
    """{path: bytes of its staged blob (`git cat-file blob :<path>`), or None if there is none}."""
    rels = list(rels)
    res = subprocess.run(["git", "cat-file", "--batch"], cwd=repo, capture_output=True,
                         input="".join(f":{r}\n" for r in rels).encode("utf-8"))
    if res.returncode != 0:
        raise OSError(f"git cat-file --batch failed: {res.stderr.decode('utf-8', 'replace').strip()}")
    data, pos, out = res.stdout, 0, {}
    for rel in rels:
        end = data.index(b"\n", pos)
        header = data[pos:end].decode("utf-8", "replace").split()
        pos = end + 1
        if header[-1] == "missing":
            out[rel] = None
            continue
        size = int(header[2])
        out[rel] = data[pos:pos + size]
        pos += size + 1  # the blob is followed by a newline
    return out


def check_tracked_set(repo: Path = REPO, paths=MANIFEST_PATHS) -> list:
    """Problems of the frozen file set against git's tracked files, as strings (empty if they are equal)."""
    problems = []
    existing = []
    for rel in paths:
        if (repo / rel).exists():
            existing.append(rel)
        else:
            problems.append(f"listed path does not exist: {rel}")
    walked = set()
    for rel in existing:
        for found in freeze_tool._expand([str(repo / rel)]):
            walked.add(Path(found).resolve().relative_to(repo.resolve()).as_posix())
    tracked = set()
    batch = []

    def flush():
        if batch:
            tracked.update(_git_lines(repo, "ls-files", "--", *batch))
            batch.clear()

    size = 0
    for rel in existing:
        if batch and size + len(rel) > 6000:
            flush()
            size = 0
        batch.append(rel)
        size += len(rel) + 1
    flush()
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


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="py -m audit.prefreeze_check", description=__doc__.split("\n\n")[0])
    ap.add_argument("--gate-tool", action="store_true", help="run only the GATE_TOOL.json check")
    ap.add_argument("--tracked", action="store_true", help="run only the tracked-file-set check")
    ap.add_argument("paths", nargs="*", help="manifest paths (default: those of PREREG section 9)")
    args = ap.parse_args(argv)
    both = not args.gate_tool and not args.tracked
    problems = []
    try:
        if both or args.gate_tool:
            problems += check_gate_tool()
        if both or args.tracked:
            problems += check_tracked_set(REPO, tuple(args.paths) or MANIFEST_PATHS)
    except OSError as exc:
        print(f"cannot check: {exc}", file=sys.stderr)
        return 2
    for p in problems:
        print(p)
    print("PRE-FREEZE CHECK FAILED" if problems else "PRE-FREEZE CHECK OK")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
