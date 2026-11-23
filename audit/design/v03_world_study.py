"""Tesaron v0.3 design study S1: the prototype radius that realises author decision A4 ("classes overlap").

    py -m audit.design.v03_world_study            # writes prereg/v03/WORLD_STUDY.json
    py -m audit.design.v03_world_study --quick    # 2 radii x 10 worlds, prints only

Objective. Choose prototype_radius (feature sigma fixed at 0.6) for the v0.3 worlds (8 sources, reliabilities
U(0.55, 0.97) per world, q_true 0.1875, q_false 0.0075) so that weak class evidence can be wrong, while the worlds stay
valid and the G1 anchors stay satisfiable.

Hypothesis. Lowering the radius raises the share of T-encoded class atoms that are world-false, mostly at low alpha, and
at some point raises the rate of degenerate PCM fits.

Criteria (written before the full run). Radii: 3.0, 2.0, 1.5, 1.25, 1.0, 0.875, 0.75. Worlds: development seeds
930000..930099, encoder seed = world seed + 10000, default Context otherwise. The chosen radius is the LARGEST radius in
the list such that all three hold:
  (1) validity rate (D5: generator succeeds, PCM converged and not degenerate, |H| >= 10) >= 0.90;
  (2) G1 parts (i) and (iii) hold on every valid world;
  (3) the share of valid worlds with at least one world-false T-encoded class atom at alpha = 0.50 is >= 0.50.
If no radius meets all three, no radius is chosen; the study reports this and the designer takes it to the author.

Design quantities only: no decoder run, no fidelity, deviation, consistency, uncertainty, new_true, new_false,
feasibility, T-1 or G8 quantity is computed or written.
"""

from __future__ import annotations

import json
import platform
import sys
import time
from pathlib import Path

import numpy as np

from audit import checks as C
from audit.v03.worlds import build_v03, check_valid_v03
from tesaron.belnap import unit_value
from tesaron.enums import Belnap
from tesaron.worlds import WorldGenerationError

OUT = Path(__file__).resolve().parent.parent.parent / "prereg" / "v03" / "WORLD_STUDY.json"
RADII = (3.0, 2.0, 1.5, 1.25, 1.0, 0.875, 0.75)
SEEDS = tuple(range(930000, 930100))
ENC_OFFSET = 10000
ALPHAS = tuple(round(0.95 - 0.05 * i, 2) for i in range(10))  # 0.95 .. 0.50
VALIDITY_MIN = 0.90
SHARE_MIN = 0.50
SUMMARY_ALPHAS = (0.95, 0.80, 0.70, 0.60, 0.50)


def alpha_counts(world, units, alpha: float) -> dict:
    """Class atoms with enc = T and how many are world-false; relation atoms in I, how many of them have enc in {T, F}
    and differ from W, how many are B."""
    n_t = n_t_false = 0
    n_rel_i = n_rel_tf = n_rel_wrong = n_rel_b = 0
    for atom in sorted(units):
        v = unit_value(units[atom], alpha)
        if atom.pred.startswith("c"):
            if v is Belnap.T:
                n_t += 1
                n_t_false += not world.truth(atom)
        elif v is not Belnap.U:
            n_rel_i += 1
            if v is Belnap.B:
                n_rel_b += 1
            else:
                n_rel_tf += 1
                n_rel_wrong += (v is Belnap.T) != world.truth(atom)
    return {"n_class_T": n_t, "n_class_T_false": n_t_false, "n_rel_I": n_rel_i, "n_rel_TF": n_rel_tf,
            "n_rel_wrong": n_rel_wrong, "n_rel_B": n_rel_b}


def world_record(seed: int, radius: float) -> dict:
    rec = {"seed": seed, "enc_seed": seed + ENC_OFFSET}
    try:
        world, ctx, enc = build_v03(seed, seed + ENC_OFFSET, radius)
    except WorldGenerationError:
        return {**rec, "valid": False, "reason": "generator"}
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


def _median(values):
    v = sorted(values)
    if not v:
        return None
    mid = len(v) // 2
    return v[mid] if len(v) % 2 else (v[mid - 1] + v[mid]) / 2


def _ratio(num: int, den: int):
    return num / den if den else None


def summarize(radius: float, recs: list) -> dict:
    valid = [r for r in recs if r["valid"]]
    n, nv = len(recs), len(valid)
    reasons: dict = {}
    for r in recs:
        if not r["valid"]:
            reasons[r["reason"]] = reasons.get(r["reason"], 0) + 1
    out = {"radius": radius, "n_worlds": n, "n_valid": nv, "invalid_reasons": reasons,
           "validity_rate": nv / n if n else None,
           "share_g1_i": _ratio(sum(r["g1_i"] for r in valid), nv),
           "share_g1_iii": _ratio(sum(r["g1_iii"] for r in valid), nv),
           "median_E": _median([r["n_E"] for r in valid]), "median_H": _median([r["n_H"] for r in valid]),
           "median_K": _median([r["n_K"] for r in valid]), "per_alpha": {}}
    for a in ALPHAS:
        k = f"{a:.2f}"
        rows = [r["alpha"][k] for r in valid]
        out["per_alpha"][k] = {
            "share_worlds_with_false_T_class": _ratio(sum(x["n_class_T_false"] >= 1 for x in rows), nv),
            "pooled_false_T_class_ratio": _ratio(sum(x["n_class_T_false"] for x in rows),
                                                 sum(x["n_class_T"] for x in rows)),
            "median_n_class_T": _median([x["n_class_T"] for x in rows]),
            "median_n_rel_I": _median([x["n_rel_I"] for x in rows]),
            "pooled_wrong_rel_over_TF": _ratio(sum(x["n_rel_wrong"] for x in rows), sum(x["n_rel_TF"] for x in rows)),
            "pooled_wrong_rel_over_I": _ratio(sum(x["n_rel_wrong"] for x in rows), sum(x["n_rel_I"] for x in rows)),
            "pooled_B_rel_over_I": _ratio(sum(x["n_rel_B"] for x in rows), sum(x["n_rel_I"] for x in rows)),
        }
    return out


def apply_criteria(summaries: list) -> dict:
    """Criteria (1)-(3) mechanically; chosen = the largest radius of the list passing all three (None if none)."""
    per, chosen = {}, None
    for s in summaries:
        share = s["per_alpha"]["0.50"]["share_worlds_with_false_T_class"]
        c1 = s["validity_rate"] is not None and s["validity_rate"] >= VALIDITY_MIN
        c2 = s["n_valid"] > 0 and s["share_g1_i"] == 1.0 and s["share_g1_iii"] == 1.0
        c3 = share is not None and share >= SHARE_MIN
        per[f"{s['radius']}"] = {"c1_validity": c1, "c2_g1": c2, "c3_false_T_share": c3, "all": c1 and c2 and c3}
        if c1 and c2 and c3 and (chosen is None or s["radius"] > chosen):
            chosen = s["radius"]
    return {"chosen_radius": chosen, "criteria": per}


def fmt(x, nd=3):
    return "-" if x is None else (f"{x:.{nd}f}" if isinstance(x, float) else str(x))


def print_table(summaries: list, verdict: dict) -> None:
    ks = [f"{a:.2f}" for a in SUMMARY_ALPHAS]
    print("radius | valid reasons | rate | G1i G1iii | share with >=1 false T class (a.50 a.70) | medians E H K")
    for s in summaries:
        pa = s["per_alpha"]
        print(f"{s['radius']:<6} | {s['n_valid']}/{s['n_worlds']} {s['invalid_reasons']} | {fmt(s['validity_rate'], 2)} | "
              f"{fmt(s['share_g1_i'], 2)} {fmt(s['share_g1_iii'], 2)} | "
              f"{fmt(pa['0.50']['share_worlds_with_false_T_class'], 2)} {fmt(pa['0.70']['share_worlds_with_false_T_class'], 2)} | "
              f"{fmt(s['median_E'], 1)} {fmt(s['median_H'], 1)} {fmt(s['median_K'], 1)}")
    print(f"per alpha {ks}: pooled false-T-class ratio | median relation atoms in I | wrong-rel/TF | wrong-rel/I | B-rel/I")
    for s in summaries:
        pa = s["per_alpha"]
        print(f"{s['radius']:<6} | " + " ".join(fmt(pa[k]["pooled_false_T_class_ratio"]) for k in ks) + " | "
              + " ".join(fmt(pa[k]["median_n_rel_I"], 1) for k in ks) + " | "
              + " ".join(fmt(pa[k]["pooled_wrong_rel_over_TF"]) for k in ks) + " | "
              + " ".join(fmt(pa[k]["pooled_wrong_rel_over_I"]) for k in ks) + " | "
              + " ".join(fmt(pa[k]["pooled_B_rel_over_I"]) for k in ks))
    for r, c in verdict["criteria"].items():
        print(f"radius {r}: c1 {c['c1_validity']} c2 {c['c2_g1']} c3 {c['c3_false_T_share']} -> {c['all']}")
    print(f"chosen_radius: {verdict['chosen_radius']}")


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    quick = "--quick" in argv
    radii, seeds = ((3.0, 1.0), SEEDS[:10]) if quick else (RADII, SEEDS)
    t0 = time.perf_counter()
    records, summaries = {}, []
    for radius in radii:
        recs = [world_record(s, radius) for s in seeds]
        records[f"{radius}"] = recs
        summaries.append(summarize(radius, recs))
    verdict = apply_criteria(summaries)
    runtime = time.perf_counter() - t0
    print_table(summaries, verdict)
    print(f"runtime {runtime:.0f} s")
    if quick:
        return 0
    doc = {
        "what": "Tesaron v0.3 design study S1 (prototype radius): design quantities only, no decoder run",
        "python": sys.version, "numpy": np.__version__, "platform": platform.platform(),
        "runtime_seconds": runtime, "radii": list(radii), "seeds": [seeds[0], seeds[-1]],
        "alphas": list(ALPHAS), "chosen_radius": verdict["chosen_radius"], "criteria": verdict["criteria"],
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
