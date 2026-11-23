"""Tesaron v0.3 design study S2: how much each candidate tau rule depends on the calibration draw (author decision A3).

    py -m audit.design.v03_tau_rule_study            # writes prereg/v03/TAU_RULE_STUDY.json
    py -m audit.design.v03_tau_rule_study --quick    # 3 draws, 10 test worlds, prints only

Worlds: final v0.3 worlds (8 sources U(0.55, 0.97), q_true 0.1875, q_false 0.0075, radius 3.0, overlap fraction 0.8),
fixed system. Test worlds: the first 30 valid worlds (D5) among development seeds 930000, 930001, ...; encoder seed =
world seed + 10000. Calibration: 40 draws with numpy PCG64(2718) from development seeds 930100..930999; per draw, a
sequence of seeds is drawn without replacement and its first 40 valid calibration worlds are kept (D5 plus: none of the
four tau metrics at (0.7, k = 0) is undefined), the runner's replacement rule, at most 200 draws per draw. Rules (A1:
everything at k = 0), applied to nested prefixes of the same 40 worlds, so that the rules are compared on paired draws:
  D1-10: tau_s = min fidelity, tau_t = min consistency, tau_d = max deviation, tau_b = max uncertainty over the first 10;
  Q-20:  the 2nd smallest fidelity and consistency, the 2nd largest deviation and uncertainty, over the first 20;
  Q-40:  the 4th smallest / 4th largest over all 40;
  D1-40: min / max over all 40 (a contrast: more worlds with extremes, more lenient; not a candidate).
D1-10, Q-20 and Q-40 have nearly the same expected leniency (order statistic m of n at m/(n+1) = 0.091, 0.095, 0.098).
Feasibility at (alpha, 0): fidelity >= tau_s, deviation <= tau_d, consistency >= tau_t, uncertainty <= tau_b, exactly.
T-1 is defined on a world when at least two feasible alpha levels have distinct uncertainty.

Per rule and draw it records: tau as "p/q"; the number of test worlds with T-1 defined, with no feasible alpha, with the
default (0.7, 0) feasible, and with G7a defined (the oracle feasible at some alpha); and per test world the feasible
alpha set. Summary per rule: min/median/max of each tau and each count; the share of draws with fewer than 16 defined
T-1 worlds; the mean over draws of P(HOLDS | r) for r in {0.95, 0.90, 0.85, 0.80} as in DRAW_STUDY; feasible-set
stability = for each test world the mean over draw pairs of the Jaccard similarity of its feasible alpha sets (two empty
sets: 1), then the median and the minimum over the 30 worlds.

Recommendation rule (written before the full run): among the candidates D1-10, Q-20 and Q-40, those whose share of draws
with fewer than 16 defined T-1 worlds is <= 0.05 are eligible; the designer recommends the eligible rule with the highest
median feasible-set stability (ties: fewer calibration worlds). If none is eligible, the designer reports that to the
author without a recommendation. The author decides A3.

Design quantities only: no new_true, no new_false, no T-1, G8 or G7 judgment and no per-world outcome is computed or
written. Fidelity, deviation, consistency and uncertainty are computed only because feasibility needs them.
"""

from __future__ import annotations

import json
import platform
import sys
import time
from fractions import Fraction
from itertools import combinations
from pathlib import Path

import numpy as np

from audit.aggregate import MIN_DEFINED
from audit.design.draw_study import RATES, _median, p_holds
from audit.exact import ExactTaus, frac_str, str_frac
from audit.oracle import Oracle
from audit.system import FIXED
from audit.v03.worlds import build_v03_final, check_valid_v03
from audit.worldset import MAX_DRAWS, WorldSetError
from tesaron.worlds import WorldGenerationError

OUT = Path(__file__).resolve().parent.parent.parent / "prereg" / "v03" / "TAU_RULE_STUDY.json"
RNG_SEED = 2718
N_DRAWS, N_CAL, N_TEST = 40, 40, 30
TEST_START = 930000
CAL_LOW, CAL_HIGH = 930100, 931000  # numpy integers: seeds 930100..930999
ENC_OFFSET = 10000
ALPHA0 = 0.7
K = 0  # author decision A1: tau is calibrated and feasibility is read at k = 0 only
ALPHAS = tuple(round(0.95 - 0.05 * i, 2) for i in range(10))  # 0.95 .. 0.50
FOUR = ("fidelity", "deviation", "consistency", "uncertainty")
# rule -> (number of calibration worlds used, 0-based index in the sorted list: smallest-first for fidelity and
# consistency, largest-first for deviation and uncertainty)
RULES = {"D1-10": (10, 0), "Q-20": (20, 1), "Q-40": (40, 3), "D1-40": (40, 0)}
CANDIDATES = ("D1-10", "Q-20", "Q-40")
MAX_SHARE_INSUFFICIENT = 0.05


def four_metrics(ex: dict) -> dict:
    """The four feasibility metrics of an exact metric dict; everything else (new_true, new_false, ...) is dropped here.
    On a valid world |H| >= 10 (D5), so new_true is defined, which is the only way it enters `audit.exact.feasible`; the
    assertion checks that and the value is discarded."""
    assert ex["new_true"] is not None, "new_true undefined on a valid world"
    return {k: ex[k] for k in FOUR}


def feasible4(m: dict, taus: ExactTaus) -> bool:
    """`audit.exact.feasible` on the four metrics (an undefined metric makes the point infeasible)."""
    f, d, c, u = (m[k] for k in FOUR)
    if f is None or c is None or u is None:
        return False
    return f >= taus.tau_s and d <= taus.tau_d and c >= taus.tau_t and u <= taus.tau_b


def build_valid(seed: int):
    """(world, ctx, enc) of a valid final v0.3 world, or the reason it is not."""
    try:
        world, ctx, enc = build_v03_final(seed, seed + ENC_OFFSET)
    except WorldGenerationError:
        return None, "generator"
    ok, reason, _ = check_valid_v03(world, ctx, enc)
    return ((world, ctx, enc), "") if ok else (None, reason)


def test_worlds(n: int):
    """The first n valid worlds from seed TEST_START up: [{seed, fixed: {alpha: 4 metrics}, oracle: {...}}], rejected."""
    out, rejected, seed = [], [], TEST_START
    while len(out) < n:
        built, reason = build_valid(seed)
        if built is None:
            rejected.append({"seed": seed, "reason": reason})
        else:
            world, ctx, enc = built
            fixed = {a: four_metrics(FIXED.evaluate_exact(world, ctx, enc, a, K)[2]) for a in ALPHAS}
            oracle = {a: four_metrics(Oracle().evaluate_exact(world, ctx, enc, a, K)[2]) for a in ALPHAS}
            out.append({"seed": seed, "fixed": fixed, "oracle": oracle})
        seed += 1
    return out, rejected


def calibration_metrics(seed: int, cache: dict):
    """(4 metrics at (0.7, 0) | None, reason); cached per seed (a pure function of the seed)."""
    if seed not in cache:
        built, reason = build_valid(seed)
        if built is None:
            cache[seed] = (None, reason)
        else:
            world, ctx, enc = built
            m = four_metrics(FIXED.evaluate_exact(world, ctx, enc, ALPHA0, K)[2])
            cache[seed] = (m, "") if all(m[k] is not None for k in FOUR) else (None, "undefined_tau_metric")
    return cache[seed]


def calibration_draw(rng, cache: dict):
    """([(seed, 4 metrics)] of the first N_CAL valid calibration worlds, rejected [{seed, reason}])."""
    seeds = rng.permutation(np.arange(CAL_LOW, CAL_HIGH))[:MAX_DRAWS]  # without replacement
    kept, rejected = [], []
    for s in seeds:
        s = int(s)
        m, reason = calibration_metrics(s, cache)
        if m is None:
            rejected.append({"seed": s, "reason": reason})
            continue
        kept.append((s, m))
        if len(kept) == N_CAL:
            return kept, rejected
    raise WorldSetError(f"only {len(kept)} valid calibration worlds of {N_CAL} within {MAX_DRAWS} draws")


def rule_taus(metrics: list, n: int, idx: int) -> ExactTaus:
    """The tau of one rule on the first n calibration worlds: the idx-th smallest fidelity and consistency, the idx-th
    largest deviation and uncertainty (duplicates count: sorted list index idx)."""
    sub = metrics[:n]
    asc = lambda key: sorted(m[key] for m in sub)
    desc = lambda key: sorted((m[key] for m in sub), reverse=True)
    return ExactTaus(tau_s=asc("fidelity")[idx], tau_d=desc("deviation")[idx],
                     tau_t=asc("consistency")[idx], tau_b=desc("uncertainty")[idx])


def draw_counts(taus: ExactTaus, worlds: list):
    """Counts over the test worlds and the feasible alpha set of each world (as a list of alpha strings)."""
    t1 = none = default = g7a = 0
    sets = []
    for w in worlds:
        feas = [a for a in ALPHAS if feasible4(w["fixed"][a], taus)]
        t1 += len({w["fixed"][a]["uncertainty"] for a in feas}) >= 2
        none += not feas
        default += ALPHA0 in feas
        g7a += any(feasible4(w["oracle"][a], taus) for a in ALPHAS)
        sets.append([f"{a:.2f}" for a in feas])
    return {"n_t1_defined": t1, "n_no_feasible": none, "n_default_feasible": default, "n_g7a_defined": g7a}, sets


def jaccard_stability(all_sets: list) -> list:
    """Per test world: the mean over draw pairs of the Jaccard similarity of the feasible alpha sets (exact);
    all_sets[draw][world] is a list of alpha strings."""
    n_worlds = len(all_sets[0])
    masks = [[sum(1 << ALPHAS.index(float(a)) for a in sets[j]) for j in range(n_worlds)] for sets in all_sets]
    out = []
    for j in range(n_worlds):
        total, pairs = Fraction(0), 0
        for x, y in combinations(range(len(all_sets)), 2):
            a, b = masks[x][j], masks[y][j]
            union = (a | b).bit_count()
            total += Fraction((a & b).bit_count(), union) if union else Fraction(1)
            pairs += 1
        out.append(total / pairs)
    return out


def _three(vals, as_fraction: bool) -> dict:
    lo, mid, hi = min(vals), _median(vals), max(vals)
    if as_fraction:
        return {k: {"exact": frac_str(Fraction(v)), "float": float(v)} for k, v in (("min", lo), ("median", mid),
                                                                                    ("max", hi))}
    return {"min": lo, "median": mid, "max": hi}


def summarize_rule(rule: str, draws: list) -> dict:
    n_defined = [d["n_t1_defined"] for d in draws]
    stab = jaccard_stability([d["feasible_alphas"] for d in draws])
    return {
        "rule": rule, "n_cal_worlds": RULES[rule][0],
        "tau": {name: _three([str_frac(d["tau"][name]) for d in draws], True)
                for name in ("tau_s", "tau_d", "tau_t", "tau_b")},
        "counts": {name: _three([d[name] for d in draws], False)
                   for name in ("n_t1_defined", "n_no_feasible", "n_default_feasible", "n_g7a_defined")},
        "share_insufficient": sum(n < MIN_DEFINED for n in n_defined) / len(draws),
        "p_holds_given_rate": {f"{r:.2f}": sum(p_holds(n, r) for n in n_defined) / len(draws) for r in RATES},
        "stability_per_world": [float(s) for s in stab],
        "stability_median": {"exact": frac_str(_median(stab)), "float": float(_median(stab))},
        "stability_min": {"exact": frac_str(min(stab)), "float": float(min(stab))},
    }


def recommend(summaries: dict) -> dict:
    """The recommendation rule: eligible = share_insufficient <= 0.05; highest median stability, ties fewer worlds."""
    eligible = [r for r in CANDIDATES if summaries[r]["share_insufficient"] <= MAX_SHARE_INSUFFICIENT]
    pick = None
    if eligible:
        key = lambda r: (-str_frac(summaries[r]["stability_median"]["exact"]), summaries[r]["n_cal_worlds"])
        pick = min(eligible, key=key)
    return {"eligible": eligible, "recommended": pick}


def print_report(summaries: dict, rec: dict) -> None:
    for rule, s in summaries.items():
        print(f"== {rule} (calibration worlds {s['n_cal_worlds']})")
        for name, v in s["tau"].items():
            print(f"  {name}: " + "  ".join(f"{k} {x['exact']} ({x['float']:.4f})" for k, x in v.items()))
        for name, v in s["counts"].items():
            print(f"  {name}: min {v['min']}, median {v['median']}, max {v['max']}")
        print(f"  share_insufficient {s['share_insufficient']:.3f}")
        print("  mean P(HOLDS|r): " + " ".join(f"{r}={p:.4f}" for r, p in s["p_holds_given_rate"].items()))
        print(f"  stability median {s['stability_median']['exact']} ({s['stability_median']['float']:.4f}), "
              f"min {s['stability_min']['exact']} ({s['stability_min']['float']:.4f})")
    print(f"eligible: {rec['eligible']}; recommended: {rec['recommended']}")


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    quick = "--quick" in argv
    n_draws, n_test = (3, 10) if quick else (N_DRAWS, N_TEST)
    t0 = time.perf_counter()
    worlds, test_rejected = test_worlds(n_test)
    rng = np.random.Generator(np.random.PCG64(RNG_SEED))
    cache: dict = {}
    per_rule = {r: [] for r in RULES}
    for i in range(n_draws):
        kept, rejected = calibration_draw(rng, cache)
        metrics = [m for _, m in kept]
        for rule, (n, idx) in RULES.items():
            taus = rule_taus(metrics, n, idx)
            counts, sets = draw_counts(taus, worlds)
            per_rule[rule].append({"draw": i, "cal_seeds": [s for s, _ in kept], "n_rejected": len(rejected),
                                   "tau": {name: frac_str(getattr(taus, name))
                                           for name in ("tau_s", "tau_d", "tau_t", "tau_b")},
                                   **counts, "feasible_alphas": sets})
    summaries = {rule: summarize_rule(rule, draws) for rule, draws in per_rule.items()}
    rec = recommend(summaries)
    runtime = time.perf_counter() - t0
    print_report(summaries, rec)
    print(f"runtime {runtime:.0f} s")
    if quick:
        return 0
    doc = {
        "what": "Tesaron v0.3 design study S2 (tau rule): design quantities only, no new_true/new_false, no verdicts",
        "python": sys.version, "numpy": np.__version__, "platform": platform.platform(), "runtime_seconds": runtime,
        "rng": f"numpy PCG64({RNG_SEED})", "n_draws": n_draws, "n_calibration_worlds_per_draw": N_CAL,
        "alphas": list(ALPHAS), "rules": {r: {"n_cal_worlds": n, "index": i} for r, (n, i) in RULES.items()},
        "test_world_seeds": [w["seed"] for w in worlds], "test_rejected": test_rejected,
        "eligible": rec["eligible"], "recommended": rec["recommended"],
        "summaries": summaries, "draws": per_rule,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(doc, fh, indent=1, sort_keys=True)
        fh.write("\n")
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
