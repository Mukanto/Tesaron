"""Freeze verifier and writer (PREREG section 9, R1-22), part of audit/ and frozen with it.

Same manifest format and core-hash algorithm as Truth_Gate's freeze.py (freeze_format 1, algorithm sha256, the
"files" table of relative POSIX paths to SHA-256 hashes, and core_sha256 = SHA-256 of the sorted "path:hash" lines
joined by newlines). Standard library only.

    py -m audit.freeze write FILE_OR_DIR... -o FREEZE.json [--no-readonly]
    py -m audit.freeze verify FREEZE.json [--require-readonly]

Exit codes: 0 all good, 1 verification failed, 2 usage or I/O error. The runner uses this module, not truth_gate.

Hashes are over the raw bytes. A tool that rewrites line endings (for example a git checkout with autocrlf) changes the
hash; freeze the files in the form in which they will be run. (Carried over from the Truth_Gate tool,
protocol/tools/freeze.py. This repository fixes the form with .gitattributes, `* text=auto eol=lf`, and audit/clone_verify.py
checks in a fresh clone that the frozen bytes are reproduced.)
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import stat
import sys

FORMAT = 1
CHUNK = 1 << 20


def sha256_file(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(CHUNK), b""):
            digest.update(block)
    return digest.hexdigest()


def core_hash(files: dict) -> str:
    """Hash of the sorted path:sha256 lines. Detects an edited manifest."""
    text = "\n".join(f"{path}:{files[path]}" for path in sorted(files))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _expand(paths):
    found = []
    for item in paths:
        if os.path.isdir(item):
            for folder, dirs, names in os.walk(item):
                dirs[:] = sorted(d for d in dirs if d != "__pycache__")
                for name in sorted(names):
                    if not name.endswith((".pyc", ".pyo")):
                        found.append(os.path.join(folder, name))
        elif os.path.isfile(item):
            found.append(item)
        else:
            raise FileNotFoundError(item)
    return found


def _make_readonly(path: str) -> bool:
    try:
        mode = os.stat(path).st_mode
        os.chmod(path, mode & ~(stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH))
        return True
    except OSError:
        return False


def _is_writable(path: str) -> bool:
    return bool(os.stat(path).st_mode & stat.S_IWUSR)


def write_manifest(paths, output: str, readonly: bool = True) -> dict:
    """Hash the files (directories are walked) and write the manifest. Never overwrites an existing manifest."""
    out = os.path.abspath(output)
    if os.path.exists(out):
        raise FileExistsError(f"refusing to overwrite {output}")
    base = os.path.dirname(out)
    files = {}
    for path in _expand(paths):
        absolute = os.path.abspath(path)
        if absolute == out:
            continue
        files[os.path.relpath(absolute, base).replace(os.sep, "/")] = sha256_file(absolute)
    if not files:
        raise ValueError("no files to freeze")
    manifest = {
        "freeze_format": FORMAT,
        "created_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "algorithm": "sha256",
        "files": dict(sorted(files.items())),
        "core_sha256": core_hash(files),
    }
    with open(out, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(manifest, handle, indent=2, sort_keys=False)
        handle.write("\n")
    if readonly:
        for rel in files:
            _make_readonly(os.path.join(base, *rel.split("/")))
        _make_readonly(out)
    return manifest


def load_manifest(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as handle:
        manifest = json.load(handle)
    if not isinstance(manifest, dict) or not isinstance(manifest.get("files"), dict) or not manifest["files"]:
        raise ValueError("manifest has no 'files' table")
    return manifest


def verify_manifest(path: str, require_readonly: bool = False):
    """(problems, warnings): lists of strings. No problems means the freeze holds."""
    problems, warnings = [], []
    manifest = load_manifest(path)
    files = manifest["files"]
    base = os.path.dirname(os.path.abspath(path))
    if core_hash(files) != manifest.get("core_sha256"):
        problems.append("MANIFEST EDITED: core_sha256 does not match the file table")
    for rel in sorted(files):
        target = os.path.join(base, *rel.split("/"))
        if not os.path.isfile(target):
            problems.append(f"MISSING: {rel}")
            continue
        if sha256_file(target) != files[rel]:
            problems.append(f"MODIFIED: {rel}")
        elif _is_writable(target):
            (problems if require_readonly else warnings).append(f"WRITABLE: {rel}")
    return problems, warnings


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="audit.freeze", description="Write and verify a SHA-256 freeze manifest.")
    sub = parser.add_subparsers(dest="command", required=True)
    w = sub.add_parser("write")
    w.add_argument("files", nargs="+")
    w.add_argument("-o", "--output", required=True)
    w.add_argument("--no-readonly", action="store_true")
    v = sub.add_parser("verify")
    v.add_argument("manifest")
    v.add_argument("--require-readonly", action="store_true")
    args = parser.parse_args(argv)
    if args.command == "write":
        try:
            manifest = write_manifest(args.files, args.output, readonly=not args.no_readonly)
        except (OSError, ValueError) as exc:
            print(f"cannot write the manifest: {exc}", file=sys.stderr)
            return 2
        print(f"froze {len(manifest['files'])} file(s) -> {args.output}")
        print(f"core_sha256 {manifest['core_sha256']}")
        return 0
    try:
        problems, warnings = verify_manifest(args.manifest, args.require_readonly)
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
