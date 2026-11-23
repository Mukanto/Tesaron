"""Shared pieces of the v0.3 Layer-1 gate studies (PREREG_v0.3 section 6.3).

A gate study file is a single file that the Truth_Gate loads with its leak guard armed: no file may be opened while the study
runs, and a module that is not yet imported cannot be imported then (its source file would be opened). Everything the studies
use is therefore imported before the guard is armed, by `audit.v03.gate.certify`. Nothing in this module reads a file, starts a
process or uses the network; the only state is an in-process memo of pure functions.

The studies run on v0.3 development worlds: the study rng draws the world seed and the encoder seed from 930000..930999
(`audit.v03.worlds.build_v03_final`, the world of the real run). "No pilot" (PREREG section 2): the T-1 `plus` world uses a
development world's k = 0 metrics with new_false replaced by a constant before anything is judged; the real new_false (and
new_true) values are never stored, printed or put into a certificate (`t1_plus_exacts`). The denominators n_q of new_false,
which T-1's one-atom floor needs, are design quantities and are kept as they are (PREREG 6.3).
"""

from __future__ import annotations

from fractions import Fraction

import numpy as np

from audit import checks as C
from audit.exact import ExactTaus, feasible
from audit.exact import decode_pairs, encode_pairs
from audit.gate.common import rng_source  # noqa: F401  (v0.2's, frozen)
from audit.system import FIXED
from audit.v03 import checks as V
from audit.v03.seeds import DEV_CORE, seeder
from audit.v03.tau import calibration_four, q40
from audit.v03.worldset import build_cached, check_valid_v03_run, generate_valid_v03
from tesaron.worlds import WorldGenerationError

DEV_LOW, DEV_HIGH = 930000, 931000  # numpy integers(low, high): seeds 930000..930999
N_GATE_CAL = 40  # the gate's tau is Q-40 on 40 development calibration worlds, as in the real run
CONST_NEW_FALSE = Fraction(1, 10)  # the constant that replaces new_false in T-1's plus world

_VALID: dict = {}
_TAUS: list = []


def gate_taus() -> ExactTaus:
    """tau for the gate's development worlds: the Q-40 rule (exact) on the first 40 valid development calibration worlds
    (dev seed mapping, calibration configuration (alpha0, k = 0)). Only the four feasibility metrics of those worlds are
    read. Computed once and memoized; it is a pure function."""
    if not _TAUS:
        recs, _ = generate_valid_v03(N_GATE_CAL, seeder(DEV_CORE), "world-cal", "enc-cal", calibration=True)
        _TAUS.append(q40([calibration_four(r, V.K_CAL) for r in recs]))
    return _TAUS[0]


def _valid(ws: int, es: int) -> bool:
    key = (ws, es)
    if key not in _VALID:
        world, ctx, enc = build_cached(ws, es)
        _VALID[key] = check_valid_v03_run(world, ctx, enc)[0]
    return _VALID[key]


def draw_valid_world(rng: np.random.Generator, max_tries: int = 200):
    """(world, context, world_seed, encoder_seed): a valid v0.3 development world whose seeds the study rng draws from
    930000-930999. A world that is invalid under D5 is skipped (the rng draws the next pair)."""
    for _ in range(max_tries):
        ws = int(rng.integers(DEV_LOW, DEV_HIGH))
        es = int(rng.integers(DEV_LOW, DEV_HIGH))
        try:
            if _valid(ws, es):
                world, ctx, _ = build_cached(ws, es)
                return world, ctx, ws, es
        except WorldGenerationError:  # world generator exhausted its attempts
            continue
    raise RuntimeError("no valid development world found")


def collect_test(test: str, system, world, ctx, rng: np.random.Generator, taus: ExactTaus | None = None):
    """Data of one test (G1-G7a) for `system` on a world. Randomness other than the system's own (the G4 permutations) is
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
        return V.collect_g7a(system, world, ctx, enc, taus or gate_taus())  # four baselines and the oracle
    raise ValueError(test)


def plus_world(test: str):
    """generate() of the plus world on a development world: the fixed system for G1-G6; for G7a the actual criterion applied
    to the four baselines and to the oracle."""

    def generate(rng):
        world, ctx, _, _ = draw_valid_world(rng)
        return collect_test(test, FIXED, world, ctx, rng)

    return generate


def minus_world(test: str, twin_factory):
    """generate() of the minus world: a faulty twin on a development world. twin_factory(rng) builds the twin (a twin with
    non-canonical behaviour gets an RngSource on the same rng)."""

    def generate(rng):
        world, ctx, _, _ = draw_valid_world(rng)
        return collect_test(test, twin_factory(rng), world, ctx, rng)

    return generate


# ---- T-1: real-shaped metric arrays with a constant new_false ----------------------------------------------------
T1_COUNTS = {"accepted": 0, "skipped_undefined": 0}  # definedness only: worlds the T-1 plus world took, and draws it skipped
T1_MAX_SKIPS = 500


def reset_t1_counts() -> None:
    T1_COUNTS.update(accepted=0, skipped_undefined=0)


def t1_plus_exacts(rng: np.random.Generator) -> list:
    """The k = 0 grid metrics (10 alpha levels) of the fixed system on a development world drawn by the rng, with new_false
    replaced by the constant CONST_NEW_FALSE. The study draws development worlds until it finds one on which T-1 is defined at the
    gate tau (two feasible k = 0 points with distinct uncertainty): an undefined world would make the gate abstain, and
    definedness is not what the gate tests (PREREG section 6.3). The number of skipped draws is kept in `T1_COUNTS`
    (definedness only; the driver prints it). The real new_false is replaced in the same expression that reads it: it is not
    kept, returned, printed or recorded (PREREG section 2, no pilot). The other metrics only decide feasibility and the
    uncertainty values; new_true is replaced too, by a positive constant: only its definedness counts. The denominator n_q
    of new_false at each point (a design quantity, PREREG 2) is kept: T-1's one-atom floor needs the real one."""
    taus = gate_taus()
    for _ in range(T1_MAX_SKIPS + 1):
        world, ctx, _, _ = draw_valid_world(rng)
        enc = FIXED.encode(world, ctx)
        out = []
        for a in C.ALPHAS:
            output, _, ex = FIXED.evaluate_exact(world, ctx, enc, a, V.K_CAL)
            out.append({
                "fidelity": ex["fidelity"], "deviation": ex["deviation"], "consistency": ex["consistency"],
                "uncertainty": ex["uncertainty"],
                "new_true": None if ex["new_true"] is None else Fraction(1, 2),
                "new_false": CONST_NEW_FALSE,
                "n_q": V.decided_outside_count(enc.units, ctx.vocabulary, output, a),
            })
        if len({ex["uncertainty"] for ex in out if feasible(ex, taus)}) >= 2:
            T1_COUNTS["accepted"] += 1
            return out
        T1_COUNTS["skipped_undefined"] += 1
    raise RuntimeError("no development world with a defined T-1 found")


def t1_plus(rng):
    return V.t1_data(t1_plus_exacts(rng), gate_taus())


def t1_minus(rng):
    """NT applied to T-1's plus: new_false rises by 1/2 across the uncertainty span of the feasible points (R1-1)."""
    return V.t1_data(V.nt_exacts(t1_plus_exacts(rng), gate_taus()), gate_taus())


def t1_add_trade_off(d: dict) -> dict:
    """K4 control of T-1 (v0.3): add NT's trade-off (1/2, `V.NT_TRADE_OFF`) to plus data, exact arithmetic on the pair arrays;
    every other key, n_q included, is copied."""
    out = {k: np.array(v, copy=True) for k, v in d.items()}
    feas = np.asarray(out["feasible"], dtype=bool)
    u, nf = decode_pairs(out["uncertainty"]), decode_pairs(out["new_false"])
    ok = [isinstance(x, Fraction) and isinstance(y, Fraction) for x, y in zip(u, nf)]
    uu = [x if isinstance(x, Fraction) else Fraction(0) for x in u]
    nn = [y if isinstance(y, Fraction) else Fraction(0) for y in nf]
    mask = [bool(f) and o for f, o in zip(feas, ok)]
    new = V.with_trade_off(uu, nn, mask)
    out["new_false"] = encode_pairs([v if o else None for v, o in zip(new, ok)])
    return out
