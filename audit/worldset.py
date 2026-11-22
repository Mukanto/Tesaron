"""Valid-world generation with replacement (PREREG section 7, D5).

A world is valid if the fixed system's PCM fit is usable (converged and not degenerate) and |H| >= 10. An invalid
world is replaced by the next derived seed; at most 200 draws per set, otherwise the run stops (WorldSetError).

Draw i of a set uses world seed seed(world_role, i), encoder seed seed(enc_role, i) and, for a test set, the
auxiliary encoder seed seed("aux", i). Valid worlds keep their draw index, which is also what the G4 permutation
seeds are derived from (seed("perm", 3 * i + p), p = 0, 1, 2).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from tesaron.criterion.metrics import compute_H
from tesaron.encoder import Context, encode
from tesaron.worlds import WorldGenerationError, generate_world

MIN_H = 10
MAX_DRAWS = 200


class WorldSetError(RuntimeError):
    """No complete set of valid worlds within the draw limit."""


@dataclass
class WorldRecord:
    draw: int
    world_seed: int
    enc_seed: int
    aux_seed: int | None
    world: object = field(repr=False)
    context: object = field(repr=False)
    encoding: object = field(repr=False)
    h_size: int = 0


def check_valid(world, context, encoding, calibration: bool = False) -> tuple[bool, str, int]:
    """(valid, reason, |H|) of a world under D5. A calibration world is also invalid if a default-configuration
    metric used by the tau rule (fidelity, deviation, consistency, uncertainty) is undefined."""
    if not encoding.fit.usable:
        return False, "pcm_unusable", 0
    h = compute_H(sorted(encoding.units), world.truth, world.rules, world.vocabulary)
    if len(h) < MIN_H:
        return False, "h_too_small", len(h)
    if calibration:
        from audit.checks import ALPHA0, K0
        from audit.exact import defined_default_metrics
        from audit.system import FIXED

        ex = FIXED.evaluate_exact(world, context, encoding, ALPHA0, K0)[2]
        if not defined_default_metrics(ex):
            return False, "undefined_default_metric", len(h)
    return True, "", len(h)


def generate_valid(
    n: int,
    seeder,
    world_role: str,
    enc_role: str,
    aux_role: str | None = None,
    max_draws: int = MAX_DRAWS,
    build=None,
    calibration: bool = False,
):
    """(valid records, rejected draws as dicts). `build(world_seed, enc_seed) -> (world, context, encoding)` can be
    given to share a cache; by default the world is generated and encoded here."""
    records: list[WorldRecord] = []
    rejected: list[dict] = []
    used_world_seeds: set[int] = set()
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
        if ws in used_world_seeds:  # only possible with the development mapping (seeds mod 1000)
            rejected.append({"draw": this, "world_seed": ws, "reason": "duplicate_seed"})
            continue
        try:
            if build is not None:
                world, ctx, enc = build(ws, es)
            else:
                world = generate_world(ws)
                ctx = Context.from_world(world, es)
                enc = encode(world, ctx)
        except WorldGenerationError:
            rejected.append({"draw": this, "world_seed": ws, "reason": "generator_failed"})
            continue
        ok, reason, h = (
            check_valid(world, ctx, enc, calibration=True) if calibration else check_valid(world, ctx, enc)
        )
        if not ok:
            rejected.append({"draw": this, "world_seed": ws, "reason": reason})
            continue
        used_world_seeds.add(ws)
        records.append(WorldRecord(this, ws, es, aux, world, ctx, enc, h))
    return records, rejected
