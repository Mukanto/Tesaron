"""Valid-world sets of Tesaron v0.3 (PREREG_v0.3 section 7, D5 with A1).

A world is valid if the fixed system's PCM fit is usable (converged and not degenerate) and |H| >= 10. A calibration world
is also invalid if one of its four tau metrics at the calibration configuration (alpha0, k = 0) is undefined. A world whose
generator fails after max_attempts (`WorldGenerationError`) is invalid. An invalid world is replaced by the next draw
index; at most 200 draws per set, otherwise `WorldSetError` (the run stops with no verdict).

`WorldRecord` is v0.2's. Draw i of a set uses world seed seed(world_role, i), encoder seed seed(enc_role, i) and, for a
test set, the auxiliary seed seed("aux", i).
"""

from __future__ import annotations

from audit.checks import ALPHA0
from audit.exact import defined_default_metrics
from audit.system import FIXED
from audit.v03.worlds import build_v03_final
from audit.worldset import MAX_DRAWS, WorldRecord, WorldSetError, check_valid
from tesaron.worlds import WorldGenerationError

__all__ = ["MAX_DRAWS", "WorldRecord", "WorldSetError", "build_cached", "check_valid_v03_run", "clear_cache",
           "generate_valid_v03"]

_BUILT: dict = {}
MAX_CACHED = 128


def build_cached(world_seed: int, enc_seed: int):
    """(world, context, fixed-system encoding) of the final v0.3 world. A pure function of its arguments, memoised in
    process (a development run builds the same world for several purposes). May raise WorldGenerationError."""
    key = (world_seed, enc_seed)
    hit = _BUILT.get(key)
    if hit is None:
        if len(_BUILT) >= MAX_CACHED:  # bounded: the 20 alternative sets alone are 800 worlds
            _BUILT.pop(next(iter(_BUILT)))
        hit = _BUILT[key] = build_v03_final(world_seed, enc_seed)
    return hit


def clear_cache() -> None:
    _BUILT.clear()


def check_valid_v03_run(world, context, encoding, calibration: bool = False) -> tuple[bool, str, int]:
    """(valid, reason, |H|) of a world under D5. For a calibration world, fidelity, deviation, consistency and
    uncertainty at (alpha0, k = 0) must all be defined."""
    ok, reason, h = check_valid(world, context, encoding, calibration=False)
    if not ok or not calibration:
        return ok, reason, h
    ex = FIXED.evaluate_exact(world, context, encoding, ALPHA0, 0)[2]
    if not defined_default_metrics(ex):
        return False, "undefined_default_metric", h
    return True, "", h


def generate_valid_v03(n: int, seeder, world_role: str, enc_role: str, aux_role: str | None = None,
                       max_draws: int = MAX_DRAWS, build=build_cached, calibration: bool = False):
    """(valid records, rejected draws as dicts) of one set of n worlds, with replacement and the cap of `max_draws`."""
    records: list[WorldRecord] = []
    rejected: list[dict] = []
    used: set[int] = set()
    draw = 0
    while len(records) < n:
        if draw >= max_draws:
            raise WorldSetError(
                f"only {len(records)} valid worlds of {n} within {max_draws} draws ({len(rejected)} rejected)"
            )
        ws, es = seeder(world_role, draw), seeder(enc_role, draw)
        aux = seeder(aux_role, draw) if aux_role else None
        this = draw
        draw += 1
        if ws in used:
            rejected.append({"draw": this, "world_seed": ws, "reason": "duplicate_seed"})
            continue
        try:
            world, ctx, enc = build(ws, es)
        except WorldGenerationError:
            rejected.append({"draw": this, "world_seed": ws, "reason": "generator_failed"})
            continue
        ok, reason, h = check_valid_v03_run(world, ctx, enc, calibration=calibration)
        if not ok:
            rejected.append({"draw": this, "world_seed": ws, "reason": reason})
            continue
        used.add(ws)
        records.append(WorldRecord(this, ws, es, aux, world, ctx, enc, h))
    return records, rejected
