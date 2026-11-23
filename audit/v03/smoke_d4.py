"""D4 smoke test of Tesaron v0.3 (PREREG_v0.3 section 8, step 3): the checks on development worlds only.

    py -m audit.v03.smoke_d4 [--n 20] [--n-cal 40] [--no-subprocess]

Development worlds: the first --n valid v0.3 worlds from development seed 930000 up (`audit.v03.seeds` dev mapping), with tau
from the Q-40 rule on the development calibration worlds (930100 up). For each check it prints only
  - the number of defined worlds;
  - reachable (yes/no): the fixed system HOLDS on some world and each twin of the check FAILS on some world;
  - covered (yes/no): the check returns every component it declares (gate check K7): on every world its collected data hold
    every declared key and its judge answers HOLDS, FAILS or UNDEFINED.
Same definitions as `audit.smoke_d4`. For T-1 and G8 only the number of defined worlds is printed (PREREG section 2, no
pilot): no reachable, no covered, no count of HOLDS, no verdict value, nothing about new_false. For G1-G6, a world on which the
FIXED system FAILS is a bug to be fixed before the freeze, so it is printed with its seed (that is an implementation test, not
a T-1 or G8 value).
"""

from __future__ import annotations

import argparse
import sys

from audit import checks as C
from audit.v03 import redact
from audit.v03.per_world import ALL_TESTS, OUTCOME, TWIN_TEST, evaluate_world_v03
from audit.v03.run_v03 import build_calibration
from audit.v03.seeds import DEV_CORE, seeder
from audit.v03.worldset import generate_valid_v03

OUTCOMES = set(OUTCOME.values())
DEFINEDNESS_ONLY = ("T-1", "G8")


def smoke(n: int, n_cal: int, subprocess_checks: bool) -> dict:
    sd = seeder(DEV_CORE)
    cal = build_calibration(DEV_CORE, None, n_cal, 0)
    records, rejected = generate_valid_v03(n, sd, "world-test", "enc-test", "aux")
    evals = [evaluate_world_v03(r, cal.taus, sd, subprocess_checks=subprocess_checks, keep_data=True) for r in records]
    rows, bugs = [], []
    for test in ALL_TESTS:
        outcomes = [ev["fixed"][test]["outcome"] for ev in evals]
        row = {"test": test, "n_defined": sum(o != "UNDEFINED" for o in outcomes), "reachable": None, "covered": None}
        if test not in DEFINEDNESS_ONLY:
            twins = [nm for nm, t in TWIN_TEST.items() if t == test]
            row["reachable"] = any(o == "HOLDS" for o in outcomes) and all(
                any(ev["twins"][nm]["outcome"] == "FAILS" for ev in evals) for nm in twins)
            row["covered"] = all(set(C.DECLARED_KEYS[test]) <= set(ev["fixed"][test]["data"])
                                 and ev["fixed"][test]["outcome"] in OUTCOMES for ev in evals)
        if test in C.TEST_IDS[:6]:
            bugs += [{"test": test, "world_seed": r.world_seed, "enc_seed": r.enc_seed}
                     for r, o in zip(records, outcomes) if o == "FAILS"]
        rows.append(row)
    return {"n_worlds": len(records), "n_rejected": len(rejected), "rows": rows, "bugs": bugs}


def lines_of(doc: dict) -> list:
    yn = lambda v: "yes" if v else "no"
    out = [f"D4 smoke test (v0.3): {doc['n_worlds']} development worlds ({doc['n_rejected']} draws rejected); "
           f"no verdict values"]
    for row in doc["rows"]:
        if row["reachable"] is None:
            out.append(f"{row['test']}: defined {row['n_defined']}")
        else:
            out.append(f"{row['test']}: defined {row['n_defined']}; reachable {yn(row['reachable'])}; "
                       f"covered {yn(row['covered'])}")
    for b in doc["bugs"]:
        out.append(f"  BUG: the fixed system FAILS {b['test']} on world {b['world_seed']} (encoder seed {b['enc_seed']})")
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--n-cal", type=int, default=40)
    ap.add_argument("--no-subprocess", action="store_true")
    args = ap.parse_args(argv)
    doc = redact.redact_checked(smoke(args.n, args.n_cal, not args.no_subprocess))
    for line in lines_of(doc):
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
