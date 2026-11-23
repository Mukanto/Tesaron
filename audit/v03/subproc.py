"""Subprocess hashes for G2 and G4 on v0.3 worlds (a fresh interpreter under an explicit PYTHONHASHSEED).

    python -m audit.v03.subproc --kind encoding|output --world-seed S --enc-seed E --system fixed|N4

`audit.subproc` rebuilds the world with the v0.2 parameters, so it cannot be used on v0.3 worlds; this module is its
v0.3 counterpart (the world comes from `audit.v03.worlds.build_v03_final`). It prints one hex hash.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys

from audit.subproc import ROOT


def compute(kind: str, world_seed: int, enc_seed: int, system_name: str) -> str:
    from audit.checks import ALPHA0, K0
    from audit.hashing import encoding_hash, output_hash
    from audit.subproc import _system
    from audit.v03.worldset import build_cached

    world, ctx, _ = build_cached(world_seed, enc_seed)
    system = _system(system_name)
    enc = system.encode(world, ctx)
    if kind == "encoding":
        return encoding_hash(enc)
    facts = system.interface_facts(enc.units, ALPHA0)
    return output_hash(system.decode(facts, ctx.rules, ctx.vocabulary, K0))


def run_hash(kind: str, world_seed: int, enc_seed: int, system_name: str, hashseed: str) -> str:
    """Run `compute` in a fresh interpreter with PYTHONHASHSEED=hashseed (always set explicitly) and return its hash."""
    env = dict(os.environ)
    env["PYTHONHASHSEED"] = str(hashseed)
    res = subprocess.run(
        [sys.executable, "-B", "-m", "audit.v03.subproc", "--kind", kind, "--world-seed", str(world_seed),
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
