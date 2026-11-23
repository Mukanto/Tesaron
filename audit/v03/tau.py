"""tau calibration of Tesaron v0.3 (PREREG_v0.3 sections 3.2 and 7; author decisions A1 and A3).

    main tau       Q-40 at (alpha0, k = 0) on the 40 calibration worlds: tau_s is the 4th smallest fidelity, tau_t the 4th
                   smallest consistency, tau_d the 4th largest deviation and tau_b the 4th largest uncertainty, duplicates
                   included, all exact fractions.
    I-6            Q-40 at (alpha0, k0 = 5) on the same 40 worlds (feasibility at (alpha, k0)).
    I-7            D1 (minimum and maximum, v0.2's rule) on the first 10 of the 40 worlds, at k = 0.
    I-8            D1 on the first 10 of the 40 worlds at (alpha0, k0 = 5) (R1-8: v0.2's full rule; computed in calibrate,
                   committed in TAU.json, recomputed in test).
    draw sensitivity   Q-40 at (alpha0, k = 0) on each of the 20 alternative calibration sets.

Only the four feasibility metrics of a calibration world leave this module (`four_metrics` drops everything else), and
every comparison is on exact fractions. The order-statistic code is that of design study S2 (`audit.design.
v03_tau_rule_study.rule_taus`).
"""

from __future__ import annotations

from audit.checks import ALPHA0, K0
from audit.design.v03_tau_rule_study import FOUR, four_metrics, rule_taus
from audit.exact import ExactTaus, frac_str
from audit.system import FIXED

Q_INDEX = 3  # the 4th smallest / 4th largest (0-based index 3)
Q_RULE = "Q-40"
I7_WORLDS = 10  # D1 on the first 10 calibration worlds (in draw order)
TAU_NAMES = ("tau_s", "tau_d", "tau_t", "tau_b")


def calibration_four(rec, k: int) -> dict:
    """The four feasibility metrics (exact) of a calibration world at (alpha0, k); nothing else is kept."""
    return four_metrics(FIXED.evaluate_exact(rec.world, rec.context, rec.encoding, ALPHA0, k)[2])


def q40(metrics: list) -> ExactTaus:
    """Q-40 on a list of four-metric dicts (any length of at least 4; the frozen run has 40)."""
    if len(metrics) < Q_INDEX + 1:
        raise ValueError("Q-40 needs at least 4 calibration worlds")
    return rule_taus(metrics, len(metrics), Q_INDEX)


def d1_first(metrics: list, n: int = I7_WORLDS) -> ExactTaus:
    """D1 (minimum fidelity and consistency, maximum deviation and uncertainty) on the first n worlds in draw order."""
    if not metrics:
        raise ValueError("D1 needs at least one calibration world")
    return rule_taus(metrics, min(n, len(metrics)), 0)


def taus_to_json(taus: ExactTaus) -> dict:
    """tau as "p/q" strings (the floats are for reading only)."""
    return {**{n: frac_str(getattr(taus, n)) for n in TAU_NAMES}, "floats": {n: float(getattr(taus, n)) for n in TAU_NAMES}}


def taus_from_json(doc: dict) -> ExactTaus:
    from audit.exact import str_frac

    return ExactTaus(*(str_frac(doc[n]) for n in TAU_NAMES))


def metrics_to_json(m: dict) -> dict:
    return {k: (None if m[k] is None else frac_str(m[k])) for k in FOUR}


__all__ = ["ALPHA0", "FOUR", "I7_WORLDS", "K0", "Q_INDEX", "Q_RULE", "TAU_NAMES", "calibration_four", "d1_first",
           "four_metrics", "metrics_to_json", "q40", "taus_from_json", "taus_to_json"]
