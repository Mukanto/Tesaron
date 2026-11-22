"""Calibration-draw study (PREREG section 7, R2-4): how much the definedness of T-1 and the other design quantities
depend on the calibration draw. A replication of the blind reviewer's study with its own draw seed.

    py -m audit.design.draw_study            # writes prereg/DRAW_STUDY.json

Test worlds: the 30 development test worlds that `run_v02 --dev` uses (core "dev" mapping, roles world-test, enc-test and
aux). Calibration: 40 draws, each of 10 valid worlds (D5 validity and the calibration rule of R1-17: no undefined
default-configuration metric used by D1), drawn with numpy PCG64(1729) from the development seeds 900000-900999,
disjoint from the test worlds' seeds, with the same replacement rule as the runner (a draw of an invalid world is
replaced by the next one; at most 200 draws per set). For each draw tau is computed by the real D1 code
(audit.exact.compute_taus) and the real feasibility rule (audit.exact.feasible), exactly, on the fixed system's grid
metrics of the 30 test worlds. The grid metrics of a world do not depend on tau and are computed once.

Per draw it records only: tau as "p/q" strings, the number of test worlds on which T-1 is defined (at least two feasible
points with distinct uncertainty), with no feasible point, with a feasible default configuration, with some feasible
alpha >= 0.85, and on which G7a is defined (the oracle is feasible at some alpha). No new_false, no T-1 or G8 judgment, no
feasibility of the low-alpha regime (the one that T-1 compares with) and no per-world outcome is computed or written.
The summary adds min/median/max of each count and of each tau, the share of draws with fewer than 16 defined T-1 worlds,
and, for per-world HOLDS rates r in {0.95, 0.90, 0.85, 0.80}, the mean over draws of P(Binomial(n, r) >= need(n)), where n
is the draw's number of defined T-1 worlds and need(n) the least HOLDS count that the Wilson rule of section 3.3 accepts
(a draw with n < 16 contributes 0), with the table of need(n) and P(HOLDS | r) for n = 16..30.
"""

from __future__ import annotations

import json
import math
import sys
import time
from fractions import Fraction
from pathlib import Path

import numpy as np

from audit import checks as C
from audit.aggregate import MIN_DEFINED, WILSON_THRESHOLD, wilson_lower
from audit.cache import get_encoding
from audit.exact import compute_taus, feasible, frac_str
from audit.oracle import Oracle
from audit.seeds import seeder
from audit.system import FIXED
from audit.worldset import MAX_DRAWS, WorldSetError, check_valid, generate_valid
from tesaron.worlds import WorldGenerationError

OUT = Path(__file__).resolve().parent.parent.parent / "prereg" / "DRAW_STUDY.json"
RNG_SEED = 1729
N_DRAWS, N_CAL, N_TEST = 40, 10, 30
DEV_LOW, DEV_HIGH = 900000, 901000  # numpy integers(low, high): seeds 900000..900999
RATES = (0.95, 0.90, 0.85, 0.80)
UPPER_ALPHA = 0.85


def need(n: int):
    """The least HOLDS count h in 0..n with Wilson lower bound >= 0.80 of h / n, or None if there is none (n < 16 also
    gives None: fewer than 16 defined worlds is no verdict)."""
    if n < MIN_DEFINED:
        return None
    for h in range(n + 1):
        if wilson_lower(h, n) >= WILSON_THRESHOLD:
            return h
    return None


def p_holds(n: int, rate: float) -> float:
    """P(Binomial(n, rate) >= need(n)); 0 if there is no verdict possible."""
    h = need(n)
    if h is None:
        return 0.0
    return sum(math.comb(n, j) * rate**j * (1 - rate) ** (n - j) for j in range(h, n + 1))


def test_world_metrics(seed_fn):
    """Per test world: the exact grid metrics of the fixed system {(alpha, k): ex} and the oracle's {alpha: ex}."""
    records, _ = generate_valid(N_TEST, seed_fn, "world-test", "enc-test", "aux", build=get_encoding)
    worlds = []
    for rec in records:
        results = C.evaluate_grid(FIXED, rec.world, rec.context, rec.encoding)
        fixed = {key: res[2] for key, res in results.items()}
        oracle = {a: Oracle().evaluate_exact(rec.world, rec.context, rec.encoding, a, 0)[2] for a in C.ALPHAS}
        worlds.append({"seed": rec.world_seed, "fixed": fixed, "oracle": oracle})
    return worlds


def calibration_draw(rng, forbidden: set, cache: dict) -> list:
    """The default-configuration exact metrics of one calibration draw: 10 valid worlds with distinct seeds, none of
    them a test world."""
    exacts, used, draws = [], set(), 0
    while len(exacts) < N_CAL:
        if draws >= MAX_DRAWS:
            raise WorldSetError(f"only {len(exacts)} valid calibration worlds within {MAX_DRAWS} draws")
        ws, es = int(rng.integers(DEV_LOW, DEV_HIGH)), int(rng.integers(DEV_LOW, DEV_HIGH))
        draws += 1
        if ws in forbidden or ws in used:
            continue
        key = (ws, es)
        if key not in cache:
            try:
                world, ctx, enc = get_encoding(ws, es)
                ok = check_valid(world, ctx, enc, calibration=True)[0]
                cache[key] = FIXED.evaluate_exact(world, ctx, enc, C.ALPHA0, C.K0)[2] if ok else None
            except WorldGenerationError:
                cache[key] = None
        if cache[key] is None:
            continue
        used.add(ws)
        exacts.append(cache[key])
    return exacts


def draw_counts(taus, worlds) -> dict:
    """The design quantities of one calibration draw over the test worlds."""
    t1_defined = no_feasible = default_feasible = upper = g7a_defined = 0
    for w in worlds:
        feas = {key: feasible(ex, taus) and ex["uncertainty"] is not None for key, ex in w["fixed"].items()}
        unc = {w["fixed"][key]["uncertainty"] for key, f in feas.items() if f}
        t1_defined += len(unc) >= 2
        no_feasible += not any(feas.values())
        default_feasible += bool(feasible(w["fixed"][(C.ALPHA0, C.K0)], taus))
        upper += any(f and key[0] >= UPPER_ALPHA for key, f in feas.items())
        g7a_defined += any(feasible(ex, taus) for ex in w["oracle"].values())
    return {"n_t1_defined": t1_defined, "n_no_feasible": no_feasible, "n_default_feasible": default_feasible,
            "n_alpha_ge_085": upper, "n_g7a_defined": g7a_defined}


def _median(values):
    v = sorted(values)
    mid = len(v) // 2
    return v[mid] if len(v) % 2 else (v[mid - 1] + v[mid]) / 2


def summarize(draws: list) -> dict:
    counts = ("n_t1_defined", "n_no_feasible", "n_default_feasible", "n_alpha_ge_085", "n_g7a_defined")
    out = {"counts": {}, "tau": {}}
    for name in counts:
        vals = [d[name] for d in draws]
        out["counts"][name] = {"min": min(vals), "median": _median(vals), "max": max(vals)}
    for name in ("tau_s", "tau_d", "tau_t", "tau_b"):
        vals = [Fraction(d["tau"][name]) for d in draws]
        out["tau"][name] = {k: {"exact": frac_str(Fraction(v)), "float": float(v)} for k, v in
                            (("min", min(vals)), ("median", _median(vals)), ("max", max(vals)))}
    n_defined = [d["n_t1_defined"] for d in draws]
    out["p_insufficient"] = sum(n < MIN_DEFINED for n in n_defined) / len(draws)
    out["p_holds_given_rate"] = {
        f"{r:.2f}": sum(p_holds(n, r) for n in n_defined) / len(draws) for r in RATES
    }
    out["need_table"] = [
        {"n": n, "need": need(n), **{f"p_holds_{r:.2f}": p_holds(n, r) for r in RATES}} for n in range(16, 31)
    ]
    return out


def main(argv=None) -> int:
    t0 = time.perf_counter()
    seed_fn = seeder("dev")
    worlds = test_world_metrics(seed_fn)
    forbidden = {w["seed"] for w in worlds}
    rng = np.random.Generator(np.random.PCG64(RNG_SEED))
    cache: dict = {}
    draws = []
    for i in range(N_DRAWS):
        taus, _ = compute_taus(calibration_draw(rng, forbidden, cache))
        draws.append({"draw": i, "tau": {n: frac_str(getattr(taus, n)) for n in ("tau_s", "tau_d", "tau_t", "tau_b")},
                      **draw_counts(taus, worlds)})
    doc = {
        "what": "calibration-draw study (PREREG section 7, R2-4): design quantities only, no G8 or T-1 outcome",
        "rng": f"numpy PCG64({RNG_SEED})",
        "n_draws": N_DRAWS,
        "n_calibration_worlds_per_draw": N_CAL,
        "test_world_seeds": sorted(w["seed"] for w in worlds),
        "draws": draws,
        "summary": summarize(draws),
    }
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:  # LF on every machine (R3-1)
        fh.write(json.dumps(doc, indent=1, sort_keys=True) + "\n")
    s = doc["summary"]
    print(f"wrote {OUT} in {time.perf_counter() - t0:.0f} s")
    for name, v in s["counts"].items():
        print(f"{name}: min {v['min']}, median {v['median']}, max {v['max']}")
    for name, v in s["tau"].items():
        print(f"{name}: min {v['min']['float']:.4f}, median {v['median']['float']:.4f}, max {v['max']['float']:.4f}")
    print(f"P_insufficient {s['p_insufficient']:.3f}")
    for r, p in s["p_holds_given_rate"].items():
        print(f"mean P(HOLDS | rate {r}) {p:.4f}")
    print("need(n), P(HOLDS|r) for n = 16..30:")
    for row in s["need_table"]:
        print(f"  n={row['n']} need={row['need']} " + " ".join(f"{k[-4:]}={v:.4f}" for k, v in row.items()
                                                              if k.startswith("p_holds")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
