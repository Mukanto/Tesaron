"""F1 and F4 on 20 v0.3 development worlds, before the freeze (PREREG_v0.3 section 6.1): writes prereg/v03/F4_PREFREEZE.json.

    py -m audit.v03.f4_prefreeze [--out PATH]

As v0.2's `audit.f4_prefreeze`, on the first 20 valid v0.3 development worlds (dev seed mapping, worlds from 930000 up, encoder
seed + 10000; `audit.v03.worldset`). F4, per world: the largest absolute difference between tesaron's fitted PCM centers and the
independent loop of audit/indep, and between the class units' mu_pos and their independent recomputation (tolerance 1e-12);
whether the relation units (degrees, from the world's source reliabilities, and provenance), the class units' provenance and status,
the PCM converged flag, iteration count and degenerate flag and the interface facts of all units at every alpha are exactly equal
to their independent recomputation. F1, per world: whether the decoder's pass-1 and pass-2 facts and statuses, its ranked
abduction candidate list with scores and its kept top-k equal the independent brute-force results at every grid configuration.
Nothing about any outcome is recorded (no new_false, new_true, T-1 or G8 quantity, PREREG section 2); the file says whether every
comparison was equal. The output is LF.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from audit.fidelity import F4_TOLERANCE, f1_details, f4_details
from audit.v03.seeds import DEV_CORE, seeder
from audit.v03.worldset import generate_valid_v03

OUT = Path(__file__).resolve().parent.parent.parent / "prereg" / "v03" / "F4_PREFREEZE.json"
N_WORLDS = 20
F4_KEYS = ("max_center_difference", "max_mu_pos_difference", "relation_units_equal", "pcm_flags_equal", "class_units_equal",
           "n_class_units", "n_relation_units", "interface_facts_equal", "n_interface_fact_sets", "problems")
F1_KEYS = ("ok", "detail", "n_configs", "n_candidate_lists", "n_candidates")


def build_document(n_worlds: int = N_WORLDS) -> dict:
    records, rejected = generate_valid_v03(n_worlds, seeder(DEV_CORE), "world-test", "enc-test")
    rows = []
    for rec in records:
        f4, f1 = f4_details(rec), f1_details(rec)
        rows.append({"world_seed": rec.world_seed, "enc_seed": rec.enc_seed,
                     "f4": {k: f4[k] for k in F4_KEYS}, "f1": {k: f1[k] for k in F1_KEYS}})
    doc = {
        "what": "F1 and F4 (PREREG_v0.3 6.1): tesaron against the independent implementations in audit/indep, on v0.3 "
                "development worlds",
        "tolerance": F4_TOLERANCE,
        "n_worlds": len(rows),
        "n_rejected_draws": len(rejected),
        "max_center_difference": max(r["f4"]["max_center_difference"] for r in rows),
        "max_mu_pos_difference": max(r["f4"]["max_mu_pos_difference"] for r in rows),
        "f4_floats_within_tolerance": all(
            r["f4"]["max_center_difference"] <= F4_TOLERANCE and r["f4"]["max_mu_pos_difference"] <= F4_TOLERANCE
            for r in rows),
        "f4_relation_units_all_equal": all(r["f4"]["relation_units_equal"] for r in rows),
        "f4_pcm_flags_all_equal": all(r["f4"]["pcm_flags_equal"] for r in rows),
        "f4_class_units_all_equal": all(r["f4"]["class_units_equal"] for r in rows),
        "f4_interface_facts_all_equal": all(r["f4"]["interface_facts_equal"] for r in rows),
        "f1_all_equal": all(r["f1"]["ok"] for r in rows),
        "n_candidates_compared": sum(r["f1"]["n_candidates"] for r in rows),
        "n_configurations_compared": sum(r["f1"]["n_configs"] for r in rows),
        "worlds": rows,
    }
    doc["every_comparison_equal"] = (
        doc["f4_floats_within_tolerance"] and doc["f4_relation_units_all_equal"] and doc["f4_pcm_flags_all_equal"]
        and doc["f4_class_units_all_equal"] and doc["f4_interface_facts_all_equal"] and doc["f1_all_equal"])
    return doc


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="py -m audit.v03.f4_prefreeze", description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", type=Path, default=OUT, help="output file (default: prereg/v03/F4_PREFREEZE.json)")
    ap.add_argument("--n-worlds", type=int, default=N_WORLDS)
    args = ap.parse_args(argv)
    doc = build_document(args.n_worlds)
    with open(args.out, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(doc, indent=1, sort_keys=True) + "\n")
    print(f"wrote {args.out}: max center difference {doc['max_center_difference']:.3e}, "
          f"max mu_pos difference {doc['max_mu_pos_difference']:.3e}; relation units equal "
          f"{doc['f4_relation_units_all_equal']}, interface facts equal {doc['f4_interface_facts_all_equal']}, "
          f"F1 equal {doc['f1_all_equal']}; every comparison equal {doc['every_comparison_equal']}")
    return 0 if doc["every_comparison_equal"] else 1


if __name__ == "__main__":
    sys.exit(main())
