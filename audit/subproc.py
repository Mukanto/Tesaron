"""Subprocess hashes for G2 and G4 (runs under another PYTHONHASHSEED).

    python -m audit.subproc --kind encoding|output --world-seed S --enc-seed E --system fixed|N4

Prints one hex hash. Used by audit.checks callers in Layer 2 and by the unit tests; never by the gate (the gate forbids
subprocesses).
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _system(name: str):
    from audit.system import FIXED
    from audit.twins import N4
    from audit.twins._source import SetOrderSource

    return {"fixed": FIXED, "N4": N4(SetOrderSource())}[name]  # N4: iteration order of a set of strings


def compute(kind: str, world_seed: int, enc_seed: int, system_name: str) -> str:
    from audit.cache import get_encoding
    from audit.checks import ALPHA0, K0
    from audit.hashing import encoding_hash, output_hash

    world, ctx, _ = get_encoding(world_seed, enc_seed)
    system = _system(system_name)
    enc = system.encode(world, ctx)
    if kind == "encoding":
        return encoding_hash(enc)
    facts = system.interface_facts(enc.units, ALPHA0)
    return output_hash(system.decode(facts, ctx.rules, ctx.vocabulary, K0))


def run_hash(kind: str, world_seed: int, enc_seed: int, system_name: str, hashseed: str) -> str:
    """Run `compute` in a fresh interpreter with PYTHONHASHSEED=hashseed and return its hash."""
    env = dict(os.environ)
    env["PYTHONHASHSEED"] = str(hashseed)
    res = subprocess.run(
        [sys.executable, "-B", "-m", "audit.subproc", "--kind", kind, "--world-seed", str(world_seed),
         "--enc-seed", str(enc_seed), "--system", system_name],
        cwd=ROOT, env=env, capture_output=True, text=True, timeout=600,
    )
    if res.returncode != 0:
        raise RuntimeError(f"subprocess failed ({res.returncode}): {res.stderr.strip()[-300:]}")
    return res.stdout.strip()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--kind", choices=("encoding", "output"), required=True)
    ap.add_argument("--world-seed", type=int, required=True)
    ap.add_argument("--enc-seed", type=int, required=True)
    ap.add_argument("--system", choices=("fixed", "N4"), default="fixed")
    a = ap.parse_args(argv)
    print(compute(a.kind, a.world_seed, a.enc_seed, a.system))
    return 0


if __name__ == "__main__":
    sys.exit(main())
