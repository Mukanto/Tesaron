"""v0.3 variants of the checks of PREREG_v0.3 section 3.2: G7a over four baselines (author decision, 2026-11-23) and the
all_true descriptive arm, T-1 at k = 0 (A1), its structure arm (I-5), the draw-sensitivity reading, and the v0.3 form of the
G4 twin N4. Everything else (G1-G6, G8 and their judges) is `audit.checks`, unchanged.

G7a judges echo, all_false, all_unknown and all_both only. all_true is a descriptive arm (PREREG 1, 2, 3.2): it is scored by
the same code as a G7a baseline (`baseline_points`) but never enters the judge.

T-1 is read on the 10 configurations with k = 0 only, with the tolerance max(delta, 1/n_q) of PREREG 3.2 (R1-1: n_q is the number
of decided atoms outside I at the later point q, the denominator of new_false; each exact metric dict handed to T-1 carries it
as "n_q", `k_exacts`). `k_exacts(results, k)` lists the exact metric dicts of the 10 alpha
levels at one k, in the order of `ALPHAS` (0.95 .. 0.50); a point is feasible under `audit.exact.feasible` (an undefined
fidelity or new_true makes it infeasible). T-1 is UNDEFINED when fewer than two feasible points have distinct uncertainty.
"""

from __future__ import annotations

from dataclasses import replace
from fractions import Fraction
from typing import Callable, Sequence

import numpy as np

from audit import checks as C
from audit.exact import DELTA, ExactTaus, decode_pairs, feasible, frac_str
from audit.hashing import hash_to_array
from audit.oracle import Oracle
from audit.system import FIXED
from audit.twins import N4
from audit.twins._source import SetOrderSource
from audit.v03.aggregate import NO_TAU  # noqa: F401  (the outcome of a draw-sensitivity arm without a tau, R1-14)
from audit.v03.subproc import run_hash as run_hash_v03
from tesaron.belnap import unit_value
from tesaron.criterion.baselines import make_baselines
from tesaron.criterion.metrics import compute_metrics_for_exact
from tesaron.enums import Belnap

ALPHAS = C.ALPHAS
K_CAL = 0  # calibration and T-1 configuration (A1)
OUTCOME = {True: "HOLDS", False: "FAILS", None: "UNDEFINED"}
G2_HASHSEEDS = ("0", "1")
G4_HASHSEEDS = ("0", "1", "4242")  # PYTHONHASHSEED of the subprocesses of G4 and of the twin N4, always set explicitly (A11)
N_SOURCES = 8
G7A_BASELINES = ("echo", "all_false", "all_unknown", "all_both")  # the four baselines G7a judges (PREREG 1, 3.2)
ALL_TRUE = "all_true"  # the descriptive arm (PREREG 3.2); not judged


NT_TRADE_OFF = Fraction(1, 2)  # the twin NT of v0.3: new_false rises by 1/2 across the uncertainty span (PREREG 6.2, R1-1)
# the data keys T-1 declares in v0.3: those of v0.2 and the denominators n_q of new_false (R1-1)
DECLARED_KEYS = {**C.DECLARED_KEYS, "T-1": (*C.DECLARED_KEYS["T-1"], "n_q")}


def decided_outside_count(units, vocabulary, output, alpha: float) -> int:
    """n_q, the denominator of new_false (SPEC section 8): the number of decided (T or F) atoms of the vocabulary outside I
    in the verdict view of `output` at `alpha`, where I is the set of encoded atoms whose value at alpha is not U. A design
    quantity (PREREG 2, "Resolution"); it is counted exactly as `compute_metrics_exact` counts `decided_out`."""
    inside = {a for a, u in units.items() if unit_value(u, alpha) is not Belnap.U}
    return sum(1 for a in vocabulary if a not in inside and output.verdict(a) in (Belnap.T, Belnap.F))


def n_q_grid(context, encoding, results: dict) -> dict:
    """{(alpha, k): n_q} for every configuration of `results` ({(alpha, k): (output, metrics, exact)})."""
    return {(a, k): decided_outside_count(encoding.units, context.vocabulary, res[0], a) for (a, k), res in results.items()}


def k_exacts(results: dict, k: int, n_q: dict) -> list:
    """The exact metric dicts of the 10 alpha levels at k, in ALPHAS order, each with its "n_q" (`n_q[(alpha, k)]`, an int).
    The key "n_q" is what T-1's judge reads for the one-atom floor; the metrics themselves are untouched."""
    return [dict(results[(a, k)][2], n_q=int(n_q[(a, k)])) for a in ALPHAS]


# ---------------------------------------------------------------------------------------------------------- G7a
def baseline_exacts(world, context, encoding, names) -> dict:
    """{name: [exact metric dict at each alpha of ALPHAS]} of single-point baselines (SPEC section 10), the metrics of
    `compute_metrics_for_exact` of the baseline's output at alpha (k-independent: a baseline is a single point)."""
    out = {}
    for name in names:
        out[name] = []
        for a in ALPHAS:
            output = make_baselines(encoding.units, a, context.vocabulary)[name]
            out[name].append(compute_metrics_for_exact(world, replace(context, alpha=a), encoding, output)[1])
    return out


def baseline_points(system, world, context, encoding, taus: ExactTaus, names) -> tuple:
    """(feasible, positive) boolean arrays of shape (len(names), 10) for single-point baselines at every alpha. A single
    point scores x * y = (1 - new_false) * new_true if it is feasible under taus and 0 otherwise, so it scores > 0 iff it is
    feasible and new_true > 0 and new_false < 1 (`audit.checks._score_positive`). A system with ignore_feasibility (the twin
    N7, the unconstrained criterion) has every point scored whatever its feasibility."""
    ignore = bool(getattr(system, "ignore_feasibility", False))
    exacts = baseline_exacts(world, context, encoding, names)
    feas = [[True if ignore else feasible(ex, taus) for ex in exacts[name]] for name in names]
    pos = [[C._score_positive(ex) for ex in exacts[name]] for name in names]
    return np.asarray(feas, dtype=bool), np.asarray(pos, dtype=bool)


def collect_g7a(system, world, context, encoding, taus: ExactTaus) -> dict:
    """G7a data of v0.3: feasibility and positivity of the four baselines `G7A_BASELINES` at every alpha, and of the oracle
    (PREREG 6.3). Same keys as `audit.checks.collect_g7a`; all_true is not in the data (see `all_true_arm`)."""
    base_f, base_p = baseline_points(system, world, context, encoding, taus, G7A_BASELINES)
    oracle_f, oracle_p = [], []
    for a in ALPHAS:
        _, _, ex = Oracle().evaluate_exact(world, context, encoding, a, 0)
        oracle_f.append(feasible(ex, taus))
        oracle_p.append(C._score_positive(ex))
    return {
        "base_feasible": base_f, "base_positive": base_p,
        "oracle_feasible": np.asarray(oracle_f, dtype=bool), "oracle_positive": np.asarray(oracle_p, dtype=bool),
        "no_oracle": C._flag(not any(oracle_f)),
    }


def judge_g7a(d):
    """HOLDS iff each of the four baselines at every alpha is infeasible or scores 0, and the oracle scores > 0 at some
    alpha; UNDEFINED iff the oracle has no feasible point. Data that do not have one row per G7a baseline and one column per
    alpha level (a v0.2 five-baseline array, for instance) are not judged: FAILS."""
    if C._is_undefined(d, "no_oracle"):
        return None
    shape = (len(G7A_BASELINES), len(ALPHAS))
    if np.asarray(d["base_feasible"]).shape != shape or np.asarray(d["base_positive"]).shape != shape:
        return False
    return C.judge_g7a(d)


def all_true_arm(system, world, context, encoding, taus: ExactTaus) -> dict:
    """The all_true descriptive arm of one world (PREREG 3.2): the alpha levels (descending) at which all_true is feasible,
    those at which it is feasible and scores > 0, and whether there is any. Scored exactly as G7a scores a baseline."""
    feas, pos = baseline_points(system, world, context, encoding, taus, (ALL_TRUE,))
    return {
        "feasible_alphas": [a for a, f in zip(ALPHAS, feas[0]) if f],
        "scoring_alphas": [a for a, f, p in zip(ALPHAS, feas[0], pos[0]) if f and p],
        "scores": bool((feas[0] & pos[0]).any()),
    }


# ---------------------------------------------------------------------------------------------------------- T-1
def _with_n_q(data: dict, exacts_k: list) -> dict:
    """`data` (the collected arrays of `audit.checks`) plus "n_q": the denominators of new_false of the 10 points. A point
    without an "n_q" is a bug of the caller (KeyError), never a silent tolerance of delta."""
    data["n_q"] = np.asarray([ex["n_q"] for ex in exacts_k], dtype=np.int64)
    return data


def t1_data(exacts_k: list, taus: ExactTaus) -> dict:
    """T-1 data of v0.3 from exact metric dicts that carry "n_q" (`k_exacts`): `audit.checks.collect_t1` and the n_q array."""
    return _with_n_q(C.collect_t1(exacts_k, taus), exacts_k)


def t1_all_points_data(exacts_k: list) -> dict:
    return _with_n_q(C.collect_t1_all_points(exacts_k), exacts_k)


def t1_tolerance(n_q: int, floor: bool = True) -> Fraction:
    """T-1's tolerance at a point q (PREREG 3.2, R1-1): max(delta, 1/n_q) with delta = 1/20 and n_q the number of decided
    atoms outside I at q; delta when n_q = 0 (and always without the floor, as in I-8 and I-9)."""
    return max(DELTA, Fraction(1, n_q)) if floor and n_q > 0 else DELTA


def t1_pairs_floor(feas, u, nf, n_q, floor: bool = True):
    """True, False or None for T-1 on exact values, like `audit.checks.t1_pairs` with the tolerance of `t1_tolerance` at q.
    feas: booleans; u, nf: Fractions; n_q: ints (one per point)."""
    idx = [i for i in range(len(feas)) if feas[i]]
    defined = False
    for p in idx:
        for q in idx:
            if u[q] < u[p]:
                defined = True
                if nf[q] - nf[p] > t1_tolerance(n_q[q], floor):
                    return False
    return True if defined else None


def _decode_n_q(d, n: int):
    """The n_q ints of T-1 data, or None if the array is not n finite non-negative whole numbers."""
    if "n_q" not in d:
        return None
    arr = np.asarray(d["n_q"], dtype=float)
    if arr.shape != (n,) or not np.all(np.isfinite(arr)) or np.any(arr < 0) or np.any(arr != np.floor(arr)):
        return None
    return [int(x) for x in arr]


def judge_t1(d):
    """T-1 of v0.3 (PREREG 3.2): for every pair of feasible points p, q with uncertainty(q) < uncertainty(p),
    new_false(q) - new_false(p) <= max(delta, 1/n_q) with n_q at q. UNDEFINED iff fewer than two feasible points have
    distinct uncertainty. Data that are malformed (no n_q array, a feasible point without exact values) are not judged: FAILS."""
    if C._is_undefined(d, "undefined"):
        return None
    feas = np.asarray(d["feasible"], dtype=bool)
    u, nf = decode_pairs(d["uncertainty"]), decode_pairs(d["new_false"])
    if len(u) != len(feas) or len(nf) != len(feas):
        return False
    n_q = _decode_n_q(d, len(feas))
    if n_q is None:
        return False
    idx = [i for i in range(len(feas)) if feas[i]]
    if any(not isinstance(u[i], Fraction) or not isinstance(nf[i], Fraction) for i in idx):
        return False  # a feasible point must have exact uncertainty and new_false
    result = t1_pairs_floor(list(feas), u, nf, n_q)
    return bool(result) if result is not None else False


JUDGES = {**C.JUDGES, "G7": judge_g7a, "T-1": judge_t1}  # the judges of v0.3: G7a over four baselines, T-1 with the floor


def t1_outcome(exacts_k: list, taus: ExactTaus, floor: bool = True) -> str:
    """HOLDS / FAILS / UNDEFINED of T-1 on the 10 points of one k under taus; `exacts_k` carry "n_q" (`k_exacts`). With
    floor=False the tolerance is delta only (I-9): the judge of `audit.checks`, as in v0.2."""
    data = t1_data(exacts_k, taus)
    return OUTCOME[judge_t1(data) if floor else C.judge_t1(data)]


def t1_all_points_outcome(exacts_k: list) -> str:
    """I-2: T-1 with every point of the k = 0 line counted as feasible (and the floor)."""
    return OUTCOME[judge_t1(t1_all_points_data(exacts_k))]


def t1_i8_outcome(results: dict, taus: ExactTaus) -> str:
    """I-8 (PREREG 3.2, R1-8): T-1 under v0.2's full rule on the 10 alpha levels. `taus` is the D1 tau of the first 10
    calibration worlds at (alpha0, k0); an alpha level is feasible when (alpha, k) is feasible for some k in {0, 5, 10};
    uncertainty and new_false are those of (alpha, 0) (they do not depend on k, PREREG 3.1); the tolerance is delta only."""
    ex0 = [results[(a, 0)][2] for a in ALPHAS]
    feas = [any(feasible(results[(a, k)][2], taus) for k in C.KS) for a in ALPHAS]
    data = C._t1_data(feas, [ex["uncertainty"] for ex in ex0], [ex["new_false"] for ex in ex0])
    return OUTCOME[C.judge_t1(data)]


def with_trade_off(uncertainty, new_false, mask=None, trade_off: Fraction = NT_TRADE_OFF) -> list:
    """The twin NT of v0.3: new_false + trade_off * (u_max - u) / (u_max - u_min), +trade_off at the lowest uncertainty and
    +0 at the highest, the span taken over the points selected by mask (default: all); the other points are unchanged. Exact
    arithmetic. It is `audit.twins.nt.with_trade_off` (v0.2, 1/5, frozen) with the trade-off of v0.3."""
    n = len(uncertainty)
    sel = [True] * n if mask is None else [bool(m) for m in mask]
    chosen = [uncertainty[i] for i in range(n) if sel[i]]
    if not chosen or max(chosen) == min(chosen):
        return list(new_false)
    lo, hi = min(chosen), max(chosen)
    return [new_false[i] + trade_off * (hi - uncertainty[i]) / (hi - lo) if sel[i] else new_false[i] for i in range(n)]


def nt_exacts(exacts: list, taus: ExactTaus) -> list:
    """NT applied to a world's metric points: new_false rises by 1/2 across the uncertainty span of the feasible points
    (R1-1); the other keys, "n_q" included, are untouched."""
    mask = [feasible(ex, taus) for ex in exacts]
    nf = with_trade_off([ex["uncertainty"] or 0 for ex in exacts], [ex["new_false"] for ex in exacts], mask)
    return [dict(ex, new_false=v) for ex, v in zip(exacts, nf)]


# ------------------------------------------------------------------------------------------------ structure (I-5)
def sources_spanned(reliabilities: Sequence[float], alpha_min: float, alpha_max: float) -> int:
    """#{rho of the world's reliabilities : alpha_min <= rho < alpha_max}, compared exactly as decimals."""
    lo, hi = Fraction(repr(float(alpha_min))), Fraction(repr(float(alpha_max)))
    return sum(1 for rho in reliabilities if lo <= Fraction(repr(float(rho))) < hi)


def t1_structure(exacts_k0: list, taus: ExactTaus, reliabilities: Sequence[float],
                 wrong_class_atoms: Callable[[float, float], int]) -> dict:
    """The structure arm of one world (PREREG 3.2). `wrong_class_atoms(alpha_min, alpha_max)` returns the number of class
    atoms that are T-encoded at alpha_min, not T-encoded at alpha_max and world-false.

    "defined" is T-1's own definedness (two feasible points with distinct uncertainty). Only a defined world has the other
    fields; `feasible_alphas` is listed for every world. `largest_increase` is the largest new_false(q) - new_false(p)
    over the pairs of T-1's definition (feasible p, q with uncertainty(q) < uncertainty(p)), an exact Fraction."""
    feas = [feasible(ex, taus) for ex in exacts_k0]
    levels = [a for a, f in zip(ALPHAS, feas) if f]
    idx = [i for i, f in enumerate(feas) if f]
    pairs = [(p, q) for p in idx for q in idx if exacts_k0[q]["uncertainty"] < exacts_k0[p]["uncertainty"]]
    out = {"feasible_alphas": levels, "defined": bool(pairs), "alpha_min": None, "alpha_max": None,
           "sources_spanned": None, "wrong_class_atoms_spanned": None, "largest_increase": None}
    if not pairs:
        return out
    a_min, a_max = min(levels), max(levels)
    out.update(
        alpha_min=a_min, alpha_max=a_max,
        sources_spanned=sources_spanned(reliabilities, a_min, a_max),
        wrong_class_atoms_spanned=int(wrong_class_atoms(a_min, a_max)),
        largest_increase=max(exacts_k0[q]["new_false"] - exacts_k0[p]["new_false"] for p, q in pairs),
    )
    return out


def wrong_class_atoms_fn(world, units) -> Callable[[float, float], int]:
    """The `wrong_class_atoms` callable of a real world: class atoms T-encoded at alpha_min and not at alpha_max that
    the world makes false."""
    from tesaron.belnap import unit_value
    from tesaron.enums import Belnap

    class_atoms = [a for a in sorted(units) if a.pred.startswith("c")]

    def count(alpha_min: float, alpha_max: float) -> int:
        return sum(
            1 for a in class_atoms
            if unit_value(units[a], alpha_min) is Belnap.T and unit_value(units[a], alpha_max) is not Belnap.T
            and not world.truth(a)
        )

    return count


def structure_json(s: dict) -> dict:
    """A structure dict with Fractions as "p/q" strings."""
    return {k: (frac_str(v) if isinstance(v, Fraction) else v) for k, v in s.items()}


def f3_structure_json(s: dict) -> dict:
    """The structure dict as the F3 comparison reads it (INSTRUCTIONS_F3.md step 8): fractions as "p/q" strings and alpha
    levels as strings spelled as in the configuration keys ("0.95", "0.9", ..., "0.5"), so that no float is compared."""
    out = structure_json(s)
    out["feasible_alphas"] = [str(a) for a in s["feasible_alphas"]]
    for key in ("alpha_min", "alpha_max"):
        out[key] = None if s[key] is None else str(s[key])
    return out


# ------------------------------------------------------------------------------------------------ the G4 twin N4
def make_n4() -> N4:
    return N4(SetOrderSource())


def collect_g4_n4(rec, subprocess_checks: bool, perm_rngs=None) -> dict:
    """G4 data of the twin N4 (PREREG 6.2, A11). With subprocesses: the hash of the output at (alpha0, k0) is taken from
    three fresh interpreters with PYTHONHASHSEED 0, 1 and 4242 (set explicitly), and the first one plays the part of the
    original order, so the data (and the outcome) are a function of the world alone, not of the parent's hash seed. The
    fixpoint comparison and the fact count are the fixed system's (they do not depend on the twin). Without subprocesses
    (development shortcut) the in-process N4 is used."""
    world, ctx, enc = rec.world, rec.context, rec.encoding
    if not subprocess_checks:
        return C.collect_g4(make_n4(), world, ctx, make_n4().encode(world, ctx), perm_rngs or [], None)
    subs = [run_hash_v03("output", rec.world_seed, rec.enc_seed, "N4", hs) for hs in G4_HASHSEEDS]
    data = C.collect_g4(FIXED, world, ctx, enc, [], None)
    data["h0"] = hash_to_array(subs[0])
    data["h_sub"] = np.stack([hash_to_array(h) for h in subs])
    return data
