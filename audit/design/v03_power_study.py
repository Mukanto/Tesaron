"""Tesaron v0.3 power study (PREREG_v0.3 section 7, "Power of T-1"; protocol rule 16): how many test worlds T-1 is defined
on under the Q-40 rule, and what the Wilson rule then needs.

    py -m audit.design.v03_power_study            # writes prereg/v03/POWER_STUDY.json
    py -m audit.design.v03_power_study --quick    # 3 draws, 10 test worlds, prints only

Objective: replace the approximation of PREREG section 7 (taken from design study S2, 30 test worlds) by the figures of the
final design: Q-40 at k = 0 on 50 test worlds.

Method. Worlds: final v0.3 worlds (8 sources U(0.55, 0.97), q_true 0.1875, q_false 0.0075, radius 3.0, overlap fraction 0.8),
fixed system. Test worlds: the same 50 development test worlds that a development run uses, i.e. the first 50 valid worlds
(D5) among development seeds 930000, 930001, ...; encoder seed = world seed + 10000. Calibration: 40 draws with numpy
PCG64(3141); per draw, a permutation of the development seeds 930100..930999 is drawn and its first 40 valid calibration
worlds are kept (D5 plus: none of the four tau metrics at (0.7, k = 0) is undefined), the runner's replacement rule, at most
200 draws per draw. The code is that of design study S2 (`audit.design.v03_tau_rule_study`), with another rng seed and 50
test worlds. Each draw's tau is Q-40 at (alpha0, k = 0) (A1, A3): the 4th smallest fidelity and consistency, the 4th largest
deviation and uncertainty, exact fractions. Feasibility at (alpha, 0) is read exactly.

Per draw it records: tau as "p/q"; the number of test worlds on which T-1 is defined (at least two feasible alpha levels with
distinct uncertainty), with no feasible alpha, with the default (0.7, 0) feasible, and on which G7a is defined (the oracle is
feasible at some alpha); and per test world the feasible alpha set. Summary: min/median/max of each tau and each count; the
share of draws with fewer than 16 defined T-1 worlds; the mean over draws of P(HOLDS | r) for r in {0.95, 0.90, 0.85, 0.80}
as in DRAW_STUDY and S2 (P(Binomial(n, r) >= need(n)), n the draw's number of defined worlds, need(n) the least HOLDS count that
the Wilson rule of section 3.3 accepts; a draw with n < 16 contributes 0); and the table of need(n) and P(HOLDS | r) for
n = 16..50.

Design quantities only: no new_true, no new_false, no T-1, G8 or G7 judgment and no per-world outcome is computed or written.
Fidelity, deviation, consistency and uncertainty are computed only because feasibility needs them.
"""

from __future__ import annotations

import json
import platform
import sys
import time
from pathlib import Path

import numpy as np

from audit.design import v03_tau_rule_study as S2
from audit.design.draw_study import RATES, _median, need, p_holds
from audit.exact import frac_str, str_frac
from audit.aggregate import MIN_DEFINED

OUT = Path(__file__).resolve().parent.parent.parent / "prereg" / "v03" / "POWER_STUDY.json"
RNG_SEED = 3141
N_DRAWS, N_TEST = 40, 50
NEED_TABLE_RANGE = range(16, 51)
COUNTS = ("n_t1_defined", "n_no_feasible", "n_default_feasible", "n_g7a_defined")


def summarize(draws: list) -> dict:
    n_defined = [d["n_t1_defined"] for d in draws]
    return {
        "tau": {name: S2._three([str_frac(d["tau"][name]) for d in draws], True)
                for name in ("tau_s", "tau_d", "tau_t", "tau_b")},
        "counts": {name: S2._three([d[name] for d in draws], False) for name in COUNTS},
        "share_insufficient": sum(n < MIN_DEFINED for n in n_defined) / len(draws),
        "p_holds_given_rate": {f"{r:.2f}": sum(p_holds(n, r) for n in n_defined) / len(draws) for r in RATES},
        "median_defined": _median(n_defined),
        "need_at_median_defined": need(int(_median(n_defined))) if float(_median(n_defined)).is_integer() else
        {"floor": need(int(_median(n_defined))), "ceil": need(int(_median(n_defined)) + 1)},
        "need_table": [{"n": n, "need": need(n), **{f"p_holds_{r:.2f}": p_holds(n, r) for r in RATES}}
                       for n in NEED_TABLE_RANGE],
    }


def print_report(s: dict) -> None:
    for name, v in s["tau"].items():
        print(f"  {name}: " + "  ".join(f"{k} {x['exact']} ({x['float']:.4f})" for k, x in v.items()))
    for name, v in s["counts"].items():
        print(f"  {name}: min {v['min']}, median {v['median']}, max {v['max']}")
    print(f"  share of draws with fewer than {MIN_DEFINED} defined T-1 worlds: {s['share_insufficient']:.3f}")
    print("  mean P(HOLDS|r): " + " ".join(f"{r}={p:.4f}" for r, p in s["p_holds_given_rate"].items()))
    print(f"  median defined {s['median_defined']}; need at the median {s['need_at_median_defined']}")


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    quick = "--quick" in argv
    n_draws, n_test = (3, 10) if quick else (N_DRAWS, N_TEST)
    t0 = time.perf_counter()
    worlds, test_rejected = S2.test_worlds(n_test)
    rng = np.random.Generator(np.random.PCG64(RNG_SEED))
    cache: dict = {}
    draws = []
    for i in range(n_draws):
        kept, rejected = S2.calibration_draw(rng, cache)
        taus = S2.rule_taus([m for _, m in kept], S2.N_CAL, 3)  # Q-40
        counts, sets = S2.draw_counts(taus, worlds)
        draws.append({"draw": i, "cal_seeds": [s for s, _ in kept], "n_rejected": len(rejected),
                      "tau": {name: frac_str(getattr(taus, name)) for name in ("tau_s", "tau_d", "tau_t", "tau_b")},
                      **counts, "feasible_alphas": sets})
    summary = summarize(draws)
    runtime = time.perf_counter() - t0
    print_report(summary)
    print(f"runtime {runtime:.0f} s")
    if quick:
        return 0
    doc = {
        "what": "Tesaron v0.3 power study (Q-40, k = 0): design quantities only, no new_true/new_false, no outcomes",
        "python": sys.version, "numpy": np.__version__, "platform": platform.platform(), "runtime_seconds": runtime,
        "rng": f"numpy PCG64({RNG_SEED})", "n_draws": n_draws, "n_calibration_worlds_per_draw": S2.N_CAL,
        "alphas": list(S2.ALPHAS), "rule": "Q-40: 4th smallest fidelity and consistency, 4th largest deviation and uncertainty",
        "test_world_seeds": [w["seed"] for w in worlds], "test_rejected": test_rejected,
        "summary": summary, "draws": draws,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(doc, fh, indent=1, sort_keys=True)
        fh.write("\n")
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
