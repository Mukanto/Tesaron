"""Tesaron v0.3 design study S3, the all_true study (blind review 1, R1-7): which of the five degenerate baselines of SPEC §10
the criterion excludes on v0.3 worlds, and how many worlds have a reliable source.

    py -m audit.design.v03_all_true_study            # writes prereg/v03/ALL_TRUE_STUDY.json
    py -m audit.design.v03_all_true_study --quick    # 3 draws, 10 test worlds, prints only

Objective. PREREG v0.3 section 2 states that, under each of S2's 40 Q-40 draws, all_true was feasible and scored > 0 on 22 of
the 30 development test worlds (at alpha 0.95, 0.90 or 0.85), that echo, all_false, all_unknown and all_both never scored, and
that only 6 of the 30 worlds have a source at or above 0.95 and 20 at or above 0.90. The pre-registration prints these
numbers, so a study file reproduces them and the pre-freeze check reruns it (PREREG 6.3).

Method. The worlds are those of design study S2 (`audit.design.v03_tau_rule_study`): the first 30 valid final v0.3 worlds from
development seed 930000, encoder seed = world seed + 10000, fixed system. The 40 tau are the 40 Q-40 tau of
`prereg/v03/TAU_RULE_STUDY.json` (calibration draws of S2). For each world, each of the five baselines (all_true, echo,
all_false, all_unknown, all_both) and each alpha level of the grid, the exact metrics of the baseline are computed by the code
that G7a uses (`audit.v03.checks.baseline_exacts`); under each tau the baseline at alpha is feasible by `audit.exact.feasible`
and scores > 0 by `audit.checks._score_positive` (a single point scores (1 - new_false) * new_true, which is positive iff
new_true > 0 and new_false < 1), exactly as `audit.v03.checks.baseline_points` scores a G7a baseline. Per draw the study records,
for each baseline, the number of worlds on which it is feasible at some alpha, the worlds on which it scores > 0 and at which
alpha levels, and the number of worlds per alpha level. Per world it records the highest source reliability, and it counts the
worlds with a source at or above 0.95 and at or above 0.90 (exact decimal comparison).

Design quantities only: the study reads whether a single point scores > 0 (a G7a-type outcome, which the pre-registration
allows to be shown), and it computes new_true and new_false in memory for that; it stores no new_true or new_false value, no
T-1 or G8 quantity and no per-world outcome of either (PREREG 2, "No pilot"). The four feasibility metrics are used and dropped.
"""

from __future__ import annotations

import json
import platform
import sys
import time
from fractions import Fraction
from pathlib import Path

import numpy as np

from audit import checks as C
from audit.design.draw_study import _median
from audit.design.v03_tau_rule_study import ALPHAS, ENC_OFFSET, N_TEST, TEST_START, build_valid, four_metrics
from audit.exact import ExactTaus, feasible, str_frac
from audit.v03.checks import baseline_exacts

ROOT = Path(__file__).resolve().parent.parent.parent
OUT = ROOT / "prereg" / "v03" / "ALL_TRUE_STUDY.json"
TAU_STUDY = ROOT / "prereg" / "v03" / "TAU_RULE_STUDY.json"
TAU_RULE = "Q-40"
BASELINES = ("all_true", "echo", "all_false", "all_unknown", "all_both")
SOURCE_LEVELS = ("0.95", "0.90")
TAU_NAMES = ("tau_s", "tau_d", "tau_t", "tau_b")


def load_taus(path: Path = TAU_STUDY, rule: str = TAU_RULE) -> list:
    """The ExactTaus of every calibration draw of design study S2 under `rule` (the 40 Q-40 tau)."""
    doc = json.loads(path.read_text(encoding="utf-8"))
    return [ExactTaus(*(str_frac(d["tau"][n]) for n in TAU_NAMES)) for d in doc["draws"][rule]]


def reduce_world(world, context, encoding) -> dict:
    """What the study keeps of a world: per baseline and alpha the four feasibility metrics (with a placeholder new_true, which
    `audit.exact.feasible` only tests for being defined) and whether the single point scores > 0; and the source
    reliabilities. new_true and new_false themselves are not kept."""
    per = {}
    for name, exs in baseline_exacts(world, context, encoding, BASELINES).items():
        per[name] = [(dict(four_metrics(ex), new_true=Fraction(1)), C._score_positive(ex)) for ex in exs]
    return {"points": per, "reliabilities": [p.value for p in world.params.source_reliabilities]}


def at_least(reliabilities, level: str) -> bool:
    """Is some source at or above `level` ("0.95")? Exact comparison of the printed decimals."""
    lo = Fraction(level)
    return any(Fraction(repr(float(r))) >= lo for r in reliabilities)


def draw_record(taus: ExactTaus, worlds: list) -> dict:
    """The record of one calibration draw: per baseline, the number of worlds where it is feasible at some alpha, the worlds
    where it is feasible and scores > 0 with their alpha levels, and the number of worlds per alpha level."""
    out = {}
    for name in BASELINES:
        feas_worlds, scoring = 0, {}
        for w in worlds:
            pts = w["points"][name]
            feas_a = [a for a, (m, _) in zip(ALPHAS, pts) if feasible(m, taus)]
            feas_worlds += bool(feas_a)
            levels = [f"{a:.2f}" for a, (m, pos) in zip(ALPHAS, pts) if pos and feasible(m, taus)]
            if levels:
                scoring[str(w["seed"])] = levels
        by_alpha = {f"{a:.2f}": sum(f"{a:.2f}" in lv for lv in scoring.values()) for a in ALPHAS}
        out[name] = {"n_worlds_feasible": feas_worlds, "n_worlds_scoring": len(scoring),
                     "scoring_by_alpha": {a: n for a, n in by_alpha.items() if n}, "scoring_worlds": scoring}
    return out


def summarize(draws: list) -> dict:
    """Over the draws: per baseline the min, median and maximum number of worlds that score, the alpha levels at which it scored
    on some world in some draw; and whether all_true scored on the same worlds at the same levels in every draw."""
    out = {}
    for name in BASELINES:
        counts = [d["baselines"][name]["n_worlds_scoring"] for d in draws]
        levels = sorted({a for d in draws for a in d["baselines"][name]["scoring_by_alpha"]}, reverse=True)
        out[name] = {"n_worlds_scoring": {"min": min(counts), "median": _median(counts), "max": max(counts)},
                     "scoring_alpha_levels": levels}
    first = draws[0]["baselines"]["all_true"]["scoring_worlds"]
    out["all_true"]["same_worlds_and_levels_in_every_draw"] = all(
        d["baselines"]["all_true"]["scoring_worlds"] == first for d in draws)
    return out


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    quick = "--quick" in argv
    taus = load_taus()
    n_draws, n_test = (3, 10) if quick else (len(taus), N_TEST)
    t0 = time.perf_counter()
    worlds, rejected, seed = [], [], TEST_START
    while len(worlds) < n_test:
        built, reason = build_valid(seed)
        if built is None:
            rejected.append({"seed": seed, "reason": reason})
        else:
            world, ctx, enc = built
            worlds.append(dict(reduce_world(world, ctx, enc), seed=seed))
        seed += 1
    draws = [{"draw": i, "tau": {n: f"{getattr(t, n).numerator}/{getattr(t, n).denominator}" for n in TAU_NAMES},
              "baselines": draw_record(t, worlds)} for i, t in enumerate(taus[:n_draws])]
    summary = summarize(draws)
    n_source = {lv: sum(at_least(w["reliabilities"], lv) for w in worlds) for lv in SOURCE_LEVELS}
    runtime = time.perf_counter() - t0
    for name in BASELINES:
        s = summary[name]["n_worlds_scoring"]
        print(f"{name}: scoring worlds min {s['min']}, median {s['median']}, max {s['max']}; "
              f"alpha levels {', '.join(summary[name]['scoring_alpha_levels']) or '-'}")
    print(f"all_true: same worlds and levels in every draw: {summary['all_true']['same_worlds_and_levels_in_every_draw']}")
    print(f"worlds with a source >= 0.95: {n_source['0.95']} of {len(worlds)}; >= 0.90: {n_source['0.90']}")
    print(f"runtime {runtime:.0f} s")
    if quick:
        return 0
    doc = {
        "what": "Tesaron v0.3 design study S3, the all_true study (R1-7): design quantities only, no new_true/new_false value, "
                "no T-1 or G8 quantity",
        "python": sys.version, "numpy": np.__version__, "platform": platform.platform(), "runtime_seconds": runtime,
        "tau_source": f"prereg/v03/TAU_RULE_STUDY.json, rule {TAU_RULE}", "n_draws": n_draws,
        "alphas": [f"{a:.2f}" for a in ALPHAS], "baselines": list(BASELINES), "test_world_seeds": [w["seed"] for w in worlds],
        "test_rejected": rejected,
        "worlds_with_a_source_at_or_above": {lv: n_source[lv] for lv in SOURCE_LEVELS},
        "highest_reliability_per_world": {str(w["seed"]): max(w["reliabilities"]) for w in worlds},
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
