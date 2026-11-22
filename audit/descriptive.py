"""Descriptive arms (PREREG sections 3.2, 5 and 6.2). None of them enters any verdict."""

from __future__ import annotations

from dataclasses import replace
from fractions import Fraction

import numpy as np

from audit import checks as C
from audit.exact import EPS_D, EPS_F, ExactTaus, feasible
from audit.system import FIXED
from tesaron.belnap import on_boundary, unit_value
from tesaron.criterion.wisdom import Point, hypervolume, pareto_front

WINDOW = (0.80, 0.75, 0.70, 0.65)  # the class-only window of T-1 (I-5)
BOUNDARY_LOW, BOUNDARY_HIGH = 0.60, 0.65  # the 0.60/0.65 boundary
UPPER_LOW, UPPER_HIGH = 0.80, 0.85  # the 0.80/0.85 boundary (the 0.80 source is excluded from 0.85 up)


def cross_seed_agreement(world, context, encoding, aux_seed: int, system=FIXED) -> dict:
    """D4a. Encoded values at alpha0 under the world's encoder seed and under the aux seed: the share of agreeing
    values among atoms present in both encodings and outside the boundary band in both, for class atoms and for
    all atoms. A share is None if no atom qualifies."""
    other = system.encode(world, replace(context, encoder_seed=aux_seed))
    eps = context.epsilon_band
    n_all = n_cls = agree_all = agree_cls = 0
    for atom in sorted(set(encoding.units) & set(other.units)):
        u1, u2 = encoding.units[atom], other.units[atom]
        if on_boundary(u1, C.ALPHA0, eps) or on_boundary(u2, C.ALPHA0, eps):
            continue
        same = unit_value(u1, C.ALPHA0) is unit_value(u2, C.ALPHA0)
        n_all += 1
        agree_all += same
        if atom.pred.startswith("c"):
            n_cls += 1
            agree_cls += same
    return {
        "aux_seed": aux_seed,
        "n_all": n_all,
        "agree_all": agree_all,
        "share_all": None if n_all == 0 else agree_all / n_all,
        "n_class": n_cls,
        "agree_class": agree_cls,
        "share_class": None if n_cls == 0 else agree_cls / n_cls,
    }


def g8_whole_grid(exacts: list, taus: ExactTaus) -> dict:
    """I-4: fidelity >= tau_s and deviation <= tau_d at every grid point, exactly (an undefined fidelity fails)."""
    ok = [ex["fidelity"] is not None and ex["fidelity"] >= taus.tau_s and ex["deviation"] <= taus.tau_d for ex in exacts]
    return {"all_points_ok": all(ok), "n_points_ok": sum(ok), "n_points": len(ok)}


def t1_all_points(exacts: list):
    """I-2: T-1 with every grid point counted as feasible. True / False / None."""
    return C.judge_t1(C.collect_t1_all_points(exacts))


def g7b(results, exacts: list, taus: ExactTaus) -> dict:
    """G7b (AQ2), descriptive: the system's hypervolume over the grid, and whether it is > 0. Feasibility is exact; the
    hypervolume of the front is computed on floats."""
    points = []
    for (a, k), ex, key in zip(C.GRID, exacts, C.GRID):
        m = results[key][1]
        feas = feasible(ex, taus) and m.new_true is not None
        points.append(Point(m.x, m.new_true, feas, (a, k)))
    hv = hypervolume(pareto_front(points))
    return {"hypervolume": hv, "positive": hv > 0.0}


def t1_structure(exacts: list, taus: ExactTaus) -> dict:
    """I-5, per world: the feasible alpha set; whether some alpha <= 0.60 is feasible; whether some alpha >= 0.85 is
    feasible; T-1 on the pairs that cross the 0.60/0.65 boundary, on the pairs that cross the 0.80/0.85 boundary, and
    inside the window alpha 0.65-0.80. Outcomes are True / False / None."""
    feas = [feasible(ex, taus) and ex["uncertainty"] is not None for ex in exacts]
    alphas = [a for a, _ in C.GRID]
    u = [ex["uncertainty"] for ex in exacts]
    nf = [ex["new_false"] for ex in exacts]
    low = lambda a: a <= BOUNDARY_LOW
    high = lambda a: a >= BOUNDARY_HIGH
    cross = lambda p, q: (low(alphas[p]) and high(alphas[q])) or (high(alphas[p]) and low(alphas[q]))
    upper_low = lambda a: a <= UPPER_LOW
    upper_high = lambda a: a >= UPPER_HIGH
    cross_upper = lambda p, q: (upper_low(alphas[p]) and upper_high(alphas[q])) or (
        upper_high(alphas[p]) and upper_low(alphas[q]))
    inside = lambda p, q: alphas[p] in WINDOW and alphas[q] in WINDOW
    safe_u = [x if x is not None else Fraction(0) for x in u]
    safe_nf = [x if x is not None else Fraction(0) for x in nf]
    return {
        "feasible_alphas": sorted({alphas[i] for i in range(len(alphas)) if feas[i]}, reverse=True),
        "some_alpha_le_060_feasible": any(feas[i] and low(alphas[i]) for i in range(len(alphas))),
        "alpha_ge_085_feasible": any(feas[i] and upper_high(alphas[i]) for i in range(len(alphas))),
        "t1_crossing_pairs": C.t1_pairs(feas, safe_u, safe_nf, cross),
        "t1_cross_080_085": C.t1_pairs(feas, safe_u, safe_nf, cross_upper),
        "t1_window_pairs": C.t1_pairs(feas, safe_u, safe_nf, inside),
    }


def g8_single_atom_only(data) -> bool | None:
    """I-6: True if the world FAILS G8 and every violated bound is violated by a change of at most one atom. The change
    in atoms is exact: the fidelity drop times |I| and the deviation rise times the number of decided encoded atoms are
    integers (both denominators depend on alpha only, not on k, and are stored raw per alpha: the stored fractions are
    in lowest terms and do not give the atom count). None if G8 is not FAILS for this world."""
    if C.judge_g8(data) is not False:
        return None
    comps = C.g8_comparisons(data)
    if comps is None:
        return None
    n_i = [int(x) for x in np.asarray(data["n_I"]).reshape(-1)]
    n_dec = [int(x) for x in np.asarray(data["n_decided"]).reshape(-1)]
    for i, j, drop, rise in comps:
        if drop > EPS_F and drop * n_i[i] > 1:
            return False
        if rise > EPS_D and rise * n_dec[i] > 1:
            return False
    return True


def default_feasibility(results, taus: ExactTaus) -> bool:
    """R1-13: whether the default configuration (alpha0, k0) is feasible on this world."""
    return feasible(results[(C.ALPHA0, C.K0)][2], taus)
