"""D4 smoke test (PREREG section 8, step 3): the checks on twenty development worlds, development seeds only.

    py -m audit.smoke_d4 [--n 20] [--no-subprocess]

For each check it prints only: the number of defined worlds; reachable (yes/no: the fixed system HOLDS on some world and
each twin of the check FAILS on some world); covered (yes/no: the check returns every component it declares, gate
check K7, here: on every world its collected data hold every declared key and its judge answers HOLDS, FAILS or
UNDEFINED). No count of HOLDS and no verdict value is printed.
Exception: for the deterministic implementation tests G1-G6 a world on which the FIXED system FAILS is a bug to be
fixed before the freeze, so it is printed with its seed.
"""

from __future__ import annotations

import argparse
import sys

from audit import checks as C
from audit.cache import get_encoding
from audit.gate.common import gate_taus
from audit.per_world import OUTCOME, TWIN_TEST, evaluate_world
from audit.seeds import seeder
from audit.worldset import generate_valid

OUTCOMES = set(OUTCOME.values())


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--no-subprocess", action="store_true")
    args = ap.parse_args(argv)
    sd = seeder("dev")
    taus = gate_taus()
    records, rejected = generate_valid(args.n, sd, "world-test", "enc-test", "aux", build=get_encoding)
    evals = [evaluate_world(r, taus, sd, subprocess_checks=not args.no_subprocess, keep_data=True) for r in records]
    print(f"D4 smoke test: {len(records)} development worlds ({len(rejected)} draws rejected); no verdict values")
    for test in C.TEST_IDS:
        outcomes = [ev["fixed"][test]["outcome"] for ev in evals]
        defined = sum(o != "UNDEFINED" for o in outcomes)
        twins = [n for n, t in TWIN_TEST.items() if t == test]
        fixed_holds = any(o == "HOLDS" for o in outcomes)
        reachable = fixed_holds and all(any(ev["twins"][n]["outcome"] == "FAILS" for ev in evals) for n in twins)
        covered = all(
            set(C.DECLARED_KEYS[test]) <= set(ev["fixed"][test]["data"]) and ev["fixed"][test]["outcome"] in OUTCOMES
            for ev in evals
        )
        print(f"{test}: defined {defined}; reachable {'yes' if reachable else 'no'}; covered {'yes' if covered else 'no'}")
        if test in C.TEST_IDS[:6]:
            for rec, o in zip(records, outcomes):
                if o == "FAILS":
                    print(f"  BUG: the fixed system FAILS {test} on world {rec.world_seed} (encoder seed {rec.enc_seed})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
