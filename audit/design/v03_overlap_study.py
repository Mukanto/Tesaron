"""Tesaron v0.3 design study S1b (writes prereg/v03/OVERLAP_STUDY.json).

    py -m audit.design.v03_overlap_study

The designer ran this first as a scratch run on 2026-11-23 with the same rule.

Context. S1 (prereg/v03/WORLD_STUDY.json) chose no radius: lowering prototype_radius makes PCM fits degenerate
(radius 1.5: 83 of 100 degenerate) before world-false T-encoded class atoms become common (radius 2.0: 8% of worlds at
alpha 0.50). S1b tests a different realisation of "weak typicality can point to the wrong class" for the author to
consider: radius stays 3.0, and only the overlap entities (2 of 20 per world) move closer to their partner prototype.

Criteria (written before this run; the same three as S1). Overlap fractions: 0.4 (v0.2), 0.6, 0.7, 0.8, 0.85, 0.9, 0.95.
Worlds: development seeds 930000..930099, encoder seed = world seed + 10000, v0.3 params (8 sources U(0.55, 0.97),
q_true 0.1875, q_false 0.0075, radius 3.0) with overlap_fraction replaced. The candidate is the SMALLEST fraction (least
change from v0.2) such that all three hold:
  (1) validity rate (D5) >= 0.90;
  (2) G1 parts (i) and (iii) hold on every valid world;
  (3) the share of valid worlds with at least one world-false T-encoded class atom at alpha = 0.50 is >= 0.50.
Reported besides (no criterion): the same share at alpha 0.60, 0.70 and 0.80 (is the wrong evidence weak?), and the
pooled wrong ratio. Design quantities only: no decoder run.
"""

from __future__ import annotations

import json
import platform
import sys
import time
from dataclasses import replace
from pathlib import Path

import numpy as np

from audit import checks as C
from audit.design.v03_world_study import (
    ALPHAS, ENC_OFFSET, SEEDS, SHARE_MIN, VALIDITY_MIN, alpha_counts, fmt, summarize,
)
from audit.v03.worlds import V03_RADIUS, check_valid_v03, v03_params
from tesaron.encoder import Context, encode
from tesaron.worlds import WorldGenerationError, generate_world

OUT = Path(__file__).resolve().parent.parent.parent / "prereg" / "v03" / "OVERLAP_STUDY.json"
FRACTIONS = (0.4, 0.6, 0.7, 0.8, 0.85, 0.9, 0.95)
SHOW = ("0.80", "0.70", "0.60", "0.50")


def world_record(seed: int, fraction: float) -> dict:
    """The S1 per-world record (audit.design.v03_world_study.world_record) at radius 3.0 with overlap_fraction replaced."""
    rec = {"seed": seed, "enc_seed": seed + ENC_OFFSET}
    try:
        world = generate_world(seed, replace(v03_params(seed, V03_RADIUS), overlap_fraction=fraction))
    except WorldGenerationError:
        return {**rec, "valid": False, "reason": "generator"}
    ctx = Context.from_world(world, seed + ENC_OFFSET)
    enc = encode(world, ctx)
    ok, reason, h = check_valid_v03(world, ctx, enc)
    rec.update({"valid": ok, "reason": reason, "pcm_converged": enc.fit.converged, "pcm_degenerate": enc.fit.degenerate,
                "pcm_iterations": enc.fit.n_iter, "n_H": h,
                "reliabilities": [p.value for p in world.params.source_reliabilities]})
    if not ok:
        return rec
    g1_i, _, g1_iii = C.g1_parts(C.collect_g1(None, world, ctx, enc))
    rec.update({"g1_i": g1_i, "g1_iii": g1_iii, "n_E": len(enc.units), "n_K": len(enc.units) + h,
                "alpha": {f"{a:.2f}": alpha_counts(world, enc.units, a) for a in ALPHAS}})
    return rec


def apply_criteria(summaries: list) -> dict:
    """Criteria (1)-(3) mechanically; candidate = the smallest fraction of the list passing all three (None if none)."""
    per, candidate = {}, None
    for s in summaries:
        share = s["per_alpha"]["0.50"]["share_worlds_with_false_T_class"]
        c1 = s["validity_rate"] is not None and s["validity_rate"] >= VALIDITY_MIN
        c2 = s["n_valid"] > 0 and s["share_g1_i"] == 1.0 and s["share_g1_iii"] == 1.0
        c3 = share is not None and share >= SHARE_MIN
        per[f"{s['overlap_fraction']}"] = {"c1_validity": c1, "c2_g1": c2, "c3_false_T_share": c3,
                                           "all": c1 and c2 and c3}
        if c1 and c2 and c3 and (candidate is None or s["overlap_fraction"] < candidate):
            candidate = s["overlap_fraction"]
    return {"candidate_overlap_fraction": candidate, "criteria": per}


def print_table(summaries: list, verdict: dict) -> None:
    print("frac | valid reasons | rate | G1i G1iii | share >=1 false T class @0.80/0.70/0.60/0.50 | pooled @same | criteria")
    for s in summaries:
        pa = s["per_alpha"]
        c = verdict["criteria"][f"{s['overlap_fraction']}"]
        print(f"{s['overlap_fraction']:<5} | {s['n_valid']}/{s['n_worlds']} {s['invalid_reasons']} | "
              f"{fmt(s['validity_rate'], 2)} | {fmt(s['share_g1_i'], 2)} {fmt(s['share_g1_iii'], 2)} | "
              + " / ".join(fmt(pa[a]["share_worlds_with_false_T_class"], 2) for a in SHOW) + " | "
              + " / ".join(fmt(pa[a]["pooled_false_T_class_ratio"]) for a in SHOW)
              + f" | {c['c1_validity']} {c['c2_g1']} {c['c3_false_T_share']}")
    print(f"candidate_overlap_fraction: {verdict['candidate_overlap_fraction']}")


def main(argv=None) -> int:
    t0 = time.perf_counter()
    records, summaries = {}, []
    for fraction in FRACTIONS:
        recs = [world_record(s, fraction) for s in SEEDS]
        records[f"{fraction}"] = recs
        s = summarize(fraction, recs)
        s["overlap_fraction"] = s.pop("radius")
        s["prototype_radius"] = V03_RADIUS
        summaries.append(s)
    verdict = apply_criteria(summaries)
    runtime = time.perf_counter() - t0
    print_table(summaries, verdict)
    print(f"runtime {runtime:.0f} s")
    doc = {
        "what": "Tesaron v0.3 design study S1b (overlap fraction at radius 3.0): design quantities only, no decoder run",
        "python": sys.version, "numpy": np.__version__, "platform": platform.platform(),
        "runtime_seconds": runtime, "prototype_radius": V03_RADIUS, "overlap_fractions": list(FRACTIONS),
        "seeds": [SEEDS[0], SEEDS[-1]], "alphas": list(ALPHAS),
        "candidate_overlap_fraction": verdict["candidate_overlap_fraction"], "criteria": verdict["criteria"],
        "summaries": summaries, "records": records,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(doc, fh, indent=1, sort_keys=True)
        fh.write("\n")
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
