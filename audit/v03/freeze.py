"""Freeze writer and verifier of Tesaron v0.3 (PREREG_v0.3 sections 8 step 7 and 9), part of audit/ and frozen with it.

    py -m audit.v03.freeze write [--no-readonly]        # writes prereg/v03/FREEZE_v0.3.json (never overwrites)
    py -m audit.v03.freeze verify [--require-readonly] [--coverage]

The manifest uses the format and the algorithm of `audit.freeze` (v0.2's tool, imported, not copied): freeze_format 1, sha256, a
"files" table of POSIX paths relative to the manifest's folder (prereg/v03/) and core_sha256 over the sorted "path:hash" lines.

The files in the manifest (PREREG section 9): prereg/PREREG_v0.3.md, SPEC.md, SPEC_v0.3.md, tesaron/**, audit/**, the .json
files directly in prereg/v03/ except the manifest itself (the design studies S1, S1b and S2, the power study, the all_true study,
the n_q study and F4), pyproject.toml and tests/**. Not in it: README.md, LICENSE, .gitattributes, .gitignore, the freeze record, prereg/v03/reviews/, run/ and v0.2's
own records. `--coverage` additionally requires that the manifest lists exactly the files the walk finds (an added or a missing
file is reported).

Exit codes: 0 all good, 1 verification failed, 2 usage or I/O error.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

from audit import freeze as base

REPO = Path(__file__).resolve().parent.parent.parent
MANIFEST_REL = "prereg/v03/FREEZE_v0.3.json"
# PREREG section 9, in the order of the list there
FROZEN_PATHS = ("prereg/PREREG_v0.3.md", "SPEC.md", "SPEC_v0.3.md", "tesaron", "audit", "pyproject.toml", "tests")
STUDY_FOLDER = "prereg/v03"
STUDY_JSON = re.compile(r"prereg/v03/[^/]+\.json")  # "prereg/v03/*.json": the files directly in the folder


def is_study_json(rel: str, manifest_rel: str = MANIFEST_REL) -> bool:
    """A file of prereg/v03 that the manifest lists: a .json directly in the folder, not the manifest itself."""
    return bool(STUDY_JSON.fullmatch(rel)) and rel != manifest_rel


def manifest_files(repo: Path = REPO) -> list:
    """The repository-relative POSIX paths the freeze hashes: every file under the PREREG section 9 paths (the walk of
    `audit.freeze`: no __pycache__, no .pyc/.pyo) and the .json files directly in prereg/v03/ except the manifest. A missing
    path raises FileNotFoundError."""
    root = repo.resolve()
    rels = []
    for rel in FROZEN_PATHS:
        for found in base._expand([str(root / rel)]):
            rels.append(Path(found).resolve().relative_to(root).as_posix())
    folder = root / STUDY_FOLDER
    if folder.is_dir():
        for path in sorted(folder.glob("*.json")):
            rel = path.resolve().relative_to(root).as_posix()
            if is_study_json(rel):
                rels.append(rel)
    return sorted(set(rels))


def write(repo: Path = REPO, readonly: bool = True) -> dict:
    """Write prereg/v03/FREEZE_v0.3.json over `manifest_files`; refuses to overwrite an existing manifest. With readonly (the
    default, as in v0.2) every frozen file and the manifest are made read-only."""
    root = repo.resolve()
    return base.write_manifest([str(root / rel) for rel in manifest_files(root)], str(root / MANIFEST_REL), readonly=readonly)


def verify(repo: Path = REPO, require_readonly: bool = False, coverage: bool = False) -> tuple:
    """(problems, warnings) of the manifest of `repo`: the bytes of every listed file (`audit.freeze.verify_manifest`) and, with
    `coverage`, that the manifest lists exactly the files `manifest_files` finds."""
    path = repo / MANIFEST_REL
    problems, warnings = base.verify_manifest(str(path), require_readonly)
    if coverage:
        manifest = base.load_manifest(str(path))
        listed = {(path.parent / rel).resolve().relative_to(repo.resolve()).as_posix() for rel in manifest["files"]}
        walked = set(manifest_files(repo))
        problems += [f"NOT IN THE MANIFEST: {rel}" for rel in sorted(walked - listed)]
        problems += [f"IN THE MANIFEST BUT NOT FOUND BY THE WALK: {rel}" for rel in sorted(listed - walked)]
    return problems, warnings


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="py -m audit.v03.freeze", description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="command", required=True)
    w = sub.add_parser("write")
    w.add_argument("--no-readonly", action="store_true")
    w.add_argument("--repo", default=str(REPO), help="the repository (default: this one; for trial runs on a copy)")
    v = sub.add_parser("verify")
    v.add_argument("--require-readonly", action="store_true")
    v.add_argument("--coverage", action="store_true")
    v.add_argument("--repo", default=str(REPO))
    args = ap.parse_args(argv)
    repo = Path(args.repo)
    if args.command == "write":
        try:
            manifest = write(repo, readonly=not args.no_readonly)
        except (OSError, ValueError) as exc:
            print(f"cannot write the manifest: {exc}", file=sys.stderr)
            return 2
        print(f"froze {len(manifest['files'])} file(s) -> {repo / MANIFEST_REL}")
        print(f"core_sha256 {manifest['core_sha256']}")
        return 0
    try:
        problems, warnings = verify(repo, args.require_readonly, args.coverage)
    except (OSError, ValueError) as exc:
        print(f"cannot read manifest: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    for line in warnings:
        print("warning: " + line)
    for line in problems:
        print(line)
    if problems:
        print("FREEZE BROKEN")
        return 1
    print("FREEZE OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
