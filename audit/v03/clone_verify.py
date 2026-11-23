"""Clone verification of Tesaron v0.3 (PREREG_v0.3 sections 6.3 and 8 step 7): does a fresh clone reproduce the frozen bytes?

    py -m audit.v03.clone_verify [--repo PATH]

A thin wrapper of `audit.clone_verify` (v0.2's, imported): it clones the local repository at HEAD into a fresh temporary folder (so
that a line-ending conversion by git would show) and runs the clone's own freeze verifier there, for v0.3's manifest
prereg/v03/FREEZE_v0.3.json and then for v0.2's prereg/FREEZE_v0.2.json (which must still verify after v0.3's freeze). Run after the
freeze commit and before the push. It never writes into the repository, never fetches and never uses the network.

Exit codes: 0 both manifests verify in the clone, 1 one does not, 2 the clone or a verifier could not run.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from audit import clone_verify as base

REPO = Path(__file__).resolve().parent.parent.parent
V03_MANIFEST_REL = "prereg/v03/FREEZE_v0.3.json"
V02_MANIFEST_REL = base.MANIFEST_REL  # prereg/FREEZE_v0.2.json
CLONE_RELS = (V03_MANIFEST_REL, V02_MANIFEST_REL)


def verify_both(repo: Path = REPO, tmp_root=None, rels=CLONE_RELS) -> list:
    """[(manifest, result of `audit.clone_verify.clone_and_verify`)] for each manifest; the v0.3 verifier of the clone is not
    used: the clone's `audit.freeze verify` (the algorithm of both manifests) is."""
    return [(rel, base.clone_and_verify(repo, rel, tmp_root)) for rel in rels]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="py -m audit.v03.clone_verify", description=__doc__.split("\n\n")[0])
    ap.add_argument("--repo", default=str(REPO), help="the repository to clone (default: this one)")
    ap.add_argument("--tmp-root", default=None, help="folder for the temporary clone (default: the system's)")
    args = ap.parse_args(argv)
    try:
        results = verify_both(Path(args.repo), args.tmp_root)
    except (OSError, subprocess.SubprocessError) as exc:
        print(f"cannot clone or verify: {exc}", file=sys.stderr)
        return 2
    code = 0
    for rel, res in results:
        if res.get("error"):
            print(f"{rel}: cannot clone or verify: {res['output']}", file=sys.stderr)
            return 2
        print(f"{rel}:")
        print(res["output"])
        print(f"clone HEAD {res['head']}")
        if not res["ok"]:
            code = max(code, 1 if res["returncode"] == 1 else 2)
    print("CLONE VERIFIES" if code == 0 else "CLONE DOES NOT VERIFY")
    return code


if __name__ == "__main__":
    sys.exit(main())
