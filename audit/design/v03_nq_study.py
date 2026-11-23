"""Tesaron v0.3 n_q study (PREREG_v0.3 section 2, "Resolution (R1-1)", and section 7, T-1's tolerance; blind review 2, R2-3):
the denominators of new_false that the one-atom floor of T-1 rests on.

    py -m audit.design.v03_nq_study            # writes prereg/v03/NQ_STUDY.json
    py -m audit.design.v03_nq_study --quick    # 3 draws, 10 test worlds, prints only

Objective: give the numbers that PREREG section 2 prints for n_q (the median at alpha 0.80, 0.70 and 0.60) and the pair figure of
section 7 (the number of T-1 pairs of the power study's development worlds, and how many of them have a smaller denominator at
q than at p) a committed study that the pre-freeze check reproduces.

Method. Worlds: the 50 development test worlds of the power study, the seeds of `test_world_seeds` in
`prereg/v03/POWER_STUDY.json` (final v0.3 worlds: 8 sources U(0.55, 0.97), q_true 0.1875, q_false 0.0075, radius 3.0, overlap
fraction 0.8; encoder seed = world seed + 10000), fixed system, k = 0 (A1). A world that is not valid (D5) stops the study.
  1. n_q at every alpha of the grid (0.95 ... 0.50): the number of decided (T or F) atoms of the vocabulary outside I in the
     verdict view of the output at (alpha, 0), where I is the set of encoded atoms whose value at alpha is not U. It is counted
     by `audit.v03.checks.decided_outside_count`, the function that gives the T-1 judge its n_q (`n_q_grid`), and it is the
     denominator of new_false (SPEC section 8). Per alpha, over the worlds: the median, the minimum and the maximum, and the
     number of worlds with n_q < 20 (the number below which one wrong atom is more than delta = 0.05).
  2. T-1 pairs: for each of the 40 Q-40 tau of the power study (`draws[i]["tau"]`), on the same worlds, the feasible points
     at k = 0 (fidelity >= tau_s, deviation <= tau_d, consistency >= tau_t, uncertainty <= tau_b, exactly), and the ordered pairs
     (p, q) of feasible points with uncertainty(q) < uncertainty(p). Summed over the worlds and the draws: the number of such
     pairs, and the number of them with n_q(q) < n_q(p) (the denominator falls from p to q).

Design quantities only: no new_true, no new_false, no T-1, G8 or G7 judgment and no per-world outcome is computed or written.
Fidelity, deviation, consistency and uncertainty are computed only because feasibility needs them; the exact metric dict of
the metric code, which also holds new_true and new_false in memory, is reduced to those four at once (`S2.four_metrics`).
"""

from __future__ import annotations

import json
import platform
import sys
import time
from fractions import Fraction
from pathlib import Path

import numpy as np

from audit.design import v03_tau_rule_study as S2
from audit.exact import ExactTaus, str_frac
from audit.system import FIXED
from audit.v03.checks import decided_outside_count

REPO = Path(__file__).resolve().parent.parent.parent
OUT = REPO / "prereg" / "v03" / "NQ_STUDY.json"
POWER = REPO / "prereg" / "v03" / "POWER_STUDY.json"
ALPHAS = S2.ALPHAS
K = S2.K  # A1: k = 0
FLOOR_ATOMS = 20  # below this many decided atoms outside I, one wrong atom is more than delta = 0.05
N_DRAWS_QUICK, N_TEST_QUICK = 3, 10


def exact_median(values: list):
    """The median of a list of ints as an int when it is whole, else as a float (a half number)."""
    vals = sorted(values)
    mid = len(vals) // 2
    twice = 2 * vals[mid] if len(vals) % 2 else vals[mid - 1] + vals[mid]
    return twice // 2 if twice % 2 == 0 else twice / 2


def world_data(seed: int) -> dict:
    """{seed, four: {alpha: the four feasibility metrics}, n_q: {alpha: int}} of a valid development test world at k = 0."""
    built, reason = S2.build_valid(seed)
    if built is None:
        raise ValueError(f"world {seed} of the power study is not valid ({reason})")
    world, ctx, enc = built
    four, n_q = {}, {}
    for a in ALPHAS:
        output, _, exact = FIXED.evaluate_exact(world, ctx, enc, a, K)
        four[a] = S2.four_metrics(exact)  # drops new_true and new_false
        n_q[a] = decided_outside_count(enc.units, ctx.vocabulary, output, a)
    return {"seed": seed, "four": four, "n_q": n_q}


def nq_summary(worlds: list) -> dict:
    """Per alpha over the worlds: median, min, max of n_q and the number of worlds with n_q < FLOOR_ATOMS."""
    out = {}
    for a in ALPHAS:
        vals = [w["n_q"][a] for w in worlds]
        out[f"{a:.2f}"] = {"median": exact_median(vals), "min": min(vals), "max": max(vals),
                           "n_below_20": sum(v < FLOOR_ATOMS for v in vals), "n_worlds": len(vals)}
    return out


def pair_counts(worlds: list, taus: ExactTaus) -> dict:
    """T-1 pairs of one tau over the worlds: the pairs (p, q) of feasible k = 0 points with uncertainty(q) < uncertainty(p),
    and those among them with n_q(q) < n_q(p)."""
    pairs = falling = 0
    for w in worlds:
        feas = [a for a in ALPHAS if S2.feasible4(w["four"][a], taus)]
        for p in feas:
            for q in feas:
                if w["four"][q]["uncertainty"] < w["four"][p]["uncertainty"]:
                    pairs += 1
                    falling += w["n_q"][q] < w["n_q"][p]
    return {"n_pairs": pairs, "n_falling": falling}


def read_power() -> dict:
    with open(POWER, encoding="utf-8") as fh:
        return json.load(fh)


def taus_of(draw: dict) -> ExactTaus:
    t = draw["tau"]
    return ExactTaus(tau_s=str_frac(t["tau_s"]), tau_d=str_frac(t["tau_d"]), tau_t=str_frac(t["tau_t"]),
                     tau_b=str_frac(t["tau_b"]))


def print_report(summary: dict, totals: dict) -> None:
    for alpha, s in summary.items():
        print(f"  alpha {alpha}: n_q median {s['median']}, min {s['min']}, max {s['max']}, "
              f"worlds with n_q < {FLOOR_ATOMS}: {s['n_below_20']} of {s['n_worlds']}")
    print(f"  T-1 pairs over {totals['n_draws']} draws: {totals['n_pairs']}; with n_q(q) < n_q(p): {totals['n_falling']}")


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    quick = "--quick" in argv
    t0 = time.perf_counter()
    power = read_power()
    seeds = [int(s) for s in power["test_world_seeds"]]
    draws_in = power["draws"]
    if quick:
        seeds, draws_in = seeds[:N_TEST_QUICK], draws_in[:N_DRAWS_QUICK]
    worlds = [world_data(s) for s in seeds]
    summary = nq_summary(worlds)
    per_draw = []
    for i, d in enumerate(draws_in):
        per_draw.append({"draw": i, "tau": d["tau"], **pair_counts(worlds, taus_of(d))})
    totals = {"n_draws": len(per_draw), "n_pairs": sum(d["n_pairs"] for d in per_draw),
              "n_falling": sum(d["n_falling"] for d in per_draw)}
    runtime = time.perf_counter() - t0
    print_report(summary, totals)
    print(f"runtime {runtime:.0f} s")
    if quick:
        return 0
    doc = {
        "what": "Tesaron v0.3 n_q study: the denominators of new_false at k = 0 and the T-1 pairs of the power study's "
                "development worlds; design quantities only, no new_true/new_false, no outcomes",
        "python": sys.version, "numpy": np.__version__, "platform": platform.platform(), "runtime_seconds": runtime,
        "source": "prereg/v03/POWER_STUDY.json (test_world_seeds and the 40 Q-40 tau of draws[i].tau)",
        "k": K, "alphas": list(ALPHAS), "floor_atoms": FLOOR_ATOMS, "n_test_worlds": len(worlds),
        "test_world_seeds": seeds,
        "n_q_by_alpha": summary,
        "n_q_per_world": {str(w["seed"]): {f"{a:.2f}": w["n_q"][a] for a in ALPHAS} for w in worlds},
        "t1_pairs": {"definition": "ordered pairs (p, q) of feasible k = 0 points with uncertainty(q) < uncertainty(p), "
                                   "over the 40 Q-40 tau and the test worlds",
                     **totals, "draws": per_draw},
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(doc, fh, indent=1, sort_keys=True)
        fh.write("\n")
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
