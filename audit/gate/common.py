"""Shared pieces of the Layer-1 gate studies (PREREG section 6.3, draft 5).

A gate study file is a single file that the Truth_Gate loads with its leak guard armed: no file may be opened while
the study runs, and a module that is not yet imported cannot be imported then (its source file would be opened).
Everything the studies use is therefore imported before the guard is armed, by audit.gate.certify. Nothing in this
module reads a file, starts a process or uses the network; the only state is an in-process memo of pure functions.
"""

from __future__ import annotations

from fractions import Fraction

import numpy as np

from audit import checks as C
from audit.cache import get_encoding
from audit.exact import ExactTaus, compute_taus, decode_pairs, encode_pairs, feasible
from audit.gate.plus_systems import NoPropagation
from audit.seeds import seeder
from audit.system import FIXED
from audit.tau import default_exact
from audit.twins._source import RngSource
from audit.twins.nt import with_trade_off
from audit.worldset import check_valid, generate_valid
from tesaron.worlds import WorldGenerationError

DEV_LOW, DEV_HIGH = 900000, 901000  # numpy integers(low, high): seeds 900000..900999
T1_WINDOW = (0.80, 0.75, 0.70, 0.65)  # PREREG 6.3: the plus world of T-1 is restricted to alpha 0.65-0.80

_VALID: dict = {}
_TAUS: list = []


def gate_taus() -> ExactTaus:
    """tau for the gate's development worlds: the D1 rule (exact) on ten development calibration worlds (dev seed
    mapping). Computed once and memoized; it is a pure function."""
    if not _TAUS:
        sd = seeder("dev")
        recs, _ = generate_valid(10, sd, "world-cal", "enc-cal", build=get_encoding, calibration=True)
        taus, _ = compute_taus([default_exact(r) for r in recs])
        _TAUS.append(taus)
    return _TAUS[0]


def _valid(ws: int, es: int):
    key = (ws, es)
    if key not in _VALID:
        world, ctx, enc = get_encoding(ws, es)
        _VALID[key] = check_valid(world, ctx, enc)[0]
    return _VALID[key]


def draw_valid_world(rng: np.random.Generator, max_tries: int = 200):
    """(world, context, world_seed, encoder_seed): a valid development world whose seeds the study rng draws from
    900000-900999. A world that is invalid under D5 is skipped (the rng draws the next pair)."""
    for _ in range(max_tries):
        ws = int(rng.integers(DEV_LOW, DEV_HIGH))
        es = int(rng.integers(DEV_LOW, DEV_HIGH))
        try:
            if _valid(ws, es):
                world, ctx, _ = get_encoding(ws, es)
                return world, ctx, ws, es
        except WorldGenerationError:  # world generator exhausted its attempts
            continue
    raise RuntimeError("no valid development world found")


def collect_test(test: str, system, world, ctx, rng: np.random.Generator, taus: ExactTaus | None = None):
    """Data of one test for `system` on a world. Randomness other than the system's own (the G4 permutations) is
    drawn from rng, so equal rng states give equal data."""
    enc = system.encode(world, ctx)
    if test == "G1":
        return C.collect_g1(system, world, ctx, enc)
    if test == "G2":
        return C.collect_g2(system, world, ctx)  # the subprocess part runs only in Layer 2
    if test == "G3":
        return C.collect_g3(system, world, ctx, enc)
    if test == "G4":
        perms = [np.random.Generator(np.random.PCG64(int(rng.integers(DEV_LOW, DEV_HIGH)))) for _ in range(3)]
        return C.collect_g4(system, world, ctx, enc, perms)  # the subprocess part runs only in Layer 2
    if test == "G5":
        return C.collect_g5(system, world, ctx, enc)
    if test == "G6":
        return C.collect_g6(system, world, ctx, enc)
    if test == "G7":
        return C.collect_g7a(system, world, ctx, enc, taus or gate_taus())
    results = C.evaluate_grid(system, world, ctx, enc)
    if test == "G8":
        return C.collect_g8(system, world, ctx, enc, results)
    raise ValueError(test)


PLUS_SYSTEMS = {"G8": NoPropagation}  # PREREG 6.3: for G8 the claim holds by construction (no propagation)


def plus_world(test: str):
    """generate() of the plus world on a development world: the fixed system for G1-G6 and G7a (the actual criterion
    applied to the baselines and the oracle); for G8 abduction without propagation."""

    def generate(rng):
        world, ctx, _, _ = draw_valid_world(rng)
        system = PLUS_SYSTEMS[test]() if test in PLUS_SYSTEMS else FIXED
        return collect_test(test, system, world, ctx, rng)

    return generate


def minus_world(test: str, twin_factory):
    """generate() of the minus world: a faulty twin on a development world. twin_factory(rng) builds the twin (a twin
    with non-canonical behaviour gets an RngSource on the same rng)."""

    def generate(rng):
        world, ctx, _, _ = draw_valid_world(rng)
        return collect_test(test, twin_factory(rng), world, ctx, rng)

    return generate


def rng_source(rng):
    return RngSource(rng)


# ---- T-1: real-shaped metric arrays ------------------------------------------------------------------------------
def window_exacts(rng: np.random.Generator) -> list:
    """The exact grid metrics of the fixed system on a development world drawn by the rng, restricted to alpha
    0.65-0.80 (all three k)."""
    world, ctx, _, _ = draw_valid_world(rng)
    enc = FIXED.encode(world, ctx)
    results = C.evaluate_grid(FIXED, world, ctx, enc, [(a, k) for a in T1_WINDOW for k in C.KS])
    return [results[(a, k)][2] for a in T1_WINDOW for k in C.KS]


def t1_plus(rng):
    return C.collect_t1(window_exacts(rng), gate_taus())


def t1_minus(rng):
    """NT applied to T-1's plus: new_false rises by 1/5 across the uncertainty span of the feasible points."""
    exacts = window_exacts(rng)
    taus = gate_taus()
    mask = [feasible(ex, taus) for ex in exacts]
    nf = with_trade_off([ex["uncertainty"] or 0 for ex in exacts], [ex["new_false"] for ex in exacts], mask)
    return C.collect_t1([dict(ex, new_false=v) for ex, v in zip(exacts, nf)], taus)


def t1_add_trade_off(d: dict) -> dict:
    """K4 control of T-1: add the trade-off to plus data (exact arithmetic on the pair arrays)."""
    out = {k: np.array(v, copy=True) for k, v in d.items()}
    feas = np.asarray(out["feasible"], dtype=bool)
    u, nf = decode_pairs(out["uncertainty"]), decode_pairs(out["new_false"])
    ok = [isinstance(x, Fraction) and isinstance(y, Fraction) for x, y in zip(u, nf)]
    uu = [x if isinstance(x, Fraction) else Fraction(0) for x in u]
    nn = [y if isinstance(y, Fraction) else Fraction(0) for y in nf]
    mask = [bool(f) and o for f, o in zip(feas, ok)]
    new = with_trade_off(uu, nn, mask)
    out["new_false"] = encode_pairs([v if o else None for v, o in zip(new, ok)])
    return out
