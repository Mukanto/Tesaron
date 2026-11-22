"""F1 and F4 on 20 development worlds, before the freeze (PREREG section 6.1): writes prereg/F4_PREFREEZE.json.

    py -m audit.f4_prefreeze

F4, per world: the largest absolute difference between tesaron's fitted PCM centers and the independent loop of
audit/indep, and between the class units' mu_pos and their independent recomputation (tolerance 1e-12); whether the
relation units (degrees, from the world's source reliabilities, and provenance), the class units' provenance and status, the
PCM converged flag, iteration count and degenerate flag (recomputed from SPEC section 5 step 3) and the interface facts of
all units at every alpha are exactly equal to their independent recomputation.
F1, per world: whether the decoder's pass-1 and pass-2 facts and statuses, its full ranked abduction candidate list with
scores and its kept top-k all equal the independent brute-force results at every grid configuration, with the numbers
of configurations and candidates compared.
Nothing about any test outcome is recorded; the file also says whether every comparison was equal.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from audit.cache import get_encoding
from audit.fidelity import F4_TOLERANCE, f1_details, f4_details
from audit.seeds import seeder
from audit.worldset import generate_valid

OUT = Path(__file__).resolve().parent.parent / "prereg" / "F4_PREFREEZE.json"
N_WORLDS = 20


def main(argv=None) -> int:
    records, _ = generate_valid(N_WORLDS, seeder("dev"), "world-test", "enc-test", build=get_encoding)
    rows = []
    for rec in records:
        f4 = f4_details(rec)
        f1 = f1_details(rec)
        rows.append({
            "world_seed": rec.world_seed,
            "enc_seed": rec.enc_seed,
            "f4": {k: f4[k] for k in ("max_center_difference", "max_mu_pos_difference", "relation_units_equal",
                                       "pcm_flags_equal", "class_units_equal", "n_class_units", "n_relation_units", "interface_facts_equal", "n_interface_fact_sets",
                                       "problems")},
            "f1": {k: f1[k] for k in ("ok", "detail", "n_configs", "n_candidate_lists", "n_candidates")},
        })
    doc = {
        "what": "F1 and F4 (PREREG 6.1): tesaron against the independent implementations in audit/indep, on "
                "development worlds",
        "tolerance": F4_TOLERANCE,
        "n_worlds": len(rows),
        "max_center_difference": max(r["f4"]["max_center_difference"] for r in rows),
        "max_mu_pos_difference": max(r["f4"]["max_mu_pos_difference"] for r in rows),
        "f4_floats_within_tolerance": all(
            r["f4"]["max_center_difference"] <= F4_TOLERANCE and r["f4"]["max_mu_pos_difference"] <= F4_TOLERANCE
            for r in rows
        ),
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
        and doc["f4_class_units_all_equal"]
        and doc["f4_interface_facts_all_equal"] and doc["f1_all_equal"]
    )
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:  # LF on every machine (R3-1)
        fh.write(json.dumps(doc, indent=1, sort_keys=True) + "\n")
    print(f"wrote {OUT}: max center difference {doc['max_center_difference']:.3e}, "
          f"max mu_pos difference {doc['max_mu_pos_difference']:.3e}; relation units equal "
          f"{doc['f4_relation_units_all_equal']}, interface facts equal {doc['f4_interface_facts_all_equal']}, "
          f"F1 equal {doc['f1_all_equal']}; every comparison equal {doc['every_comparison_equal']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
