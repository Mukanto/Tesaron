"""Clone verification (PREREG section 8 step 7, R3-1): does a fresh clone reproduce the frozen bytes?

    py -m audit.clone_verify [--repo PATH]

Clones the local repository at HEAD into a fresh temporary folder (`git clone`, with the machine's git configuration as
it is, so a line-ending conversion would show), runs the clone's own freeze verifier (`py -m audit.freeze verify
prereg/FREEZE_v0.2.json`, with the clone as the working directory) there, prints its result and the clone's HEAD, and
removes the temporary folder. It is run after the freeze commit and before the push. It never writes into the repository,
never fetches and never touches the network (the clone source is a local path).

Exit codes: 0 the clone verifies, 1 it does not, 2 the clone or the verifier could not run.
"""

from __future__ import annotations

import argparse
import os
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
MANIFEST_REL = "prereg/FREEZE_v0.2.json"


def _force_remove(func, path, _exc):
    """shutil.rmtree error handler: git writes read-only object files."""
    os.chmod(path, stat.S_IWRITE)
    func(path)


def clone_and_verify(repo: Path = REPO, manifest_rel: str = MANIFEST_REL, tmp_root: str | None = None) -> dict:
    """{"ok": bool, "head": clone HEAD, "output": the verifier's output, "returncode": int}. The temporary folder is
    removed before returning, also on an error."""
    folder = Path(tempfile.mkdtemp(prefix="clone_verify_", dir=tmp_root))
    try:
        clone = folder / "clone"
        res = subprocess.run(["git", "clone", "--quiet", str(repo), str(clone)], capture_output=True, text=True)
        if res.returncode != 0:
            return {"ok": False, "head": None, "output": res.stderr.strip(), "returncode": 2, "error": "clone failed"}
        head = subprocess.run(["git", "-C", str(clone), "rev-parse", "HEAD"], capture_output=True, text=True)
        verify = subprocess.run(
            [sys.executable, "-B", "-m", "audit.freeze", "verify", manifest_rel],
            cwd=clone, capture_output=True, text=True,
            env={**os.environ, "PYTHONPATH": str(clone), "PYTHONDONTWRITEBYTECODE": "1"},
        )
        output = (verify.stdout + verify.stderr).strip()
        return {"ok": verify.returncode == 0, "head": head.stdout.strip(), "output": output,
                "returncode": verify.returncode}
    finally:
        shutil.rmtree(folder, onerror=_force_remove)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="py -m audit.clone_verify", description=__doc__.split("\n\n")[0])
    ap.add_argument("--repo", default=str(REPO), help="the repository to clone (default: this one)")
    ap.add_argument("--tmp-root", default=None, help="folder for the temporary clone (default: the system's)")
    args = ap.parse_args(argv)
    try:
        result = clone_and_verify(Path(args.repo), tmp_root=args.tmp_root)
    except OSError as exc:
        print(f"cannot clone or verify: {exc}", file=sys.stderr)
        return 2
    if result.get("error"):
        print(f"cannot clone or verify: {result['output']}", file=sys.stderr)
        return 2
    print(result["output"])
    print(f"clone HEAD {result['head']}")
    print("CLONE VERIFIES" if result["ok"] else "CLONE DOES NOT VERIFY")
    return 0 if result["ok"] else (1 if result["returncode"] == 1 else 2)


if __name__ == "__main__":
    sys.exit(main())
