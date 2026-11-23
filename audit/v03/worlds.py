"""v0.3 reference worlds: 8 sources with per-world reliabilities U(0.55, 0.97) and a configurable prototype radius.

The generator, encoder, decoder and Context are the unchanged v0.2 code; a v0.3 world is `generate_world` called with
different `WorldParams`. The reliabilities come from their own random stream (seed and REL_STREAM_TAG), so the world
draw itself (classes, rules, base facts, features) is not shifted by them.
"""

from __future__ import annotations

from dataclasses import replace

import numpy as np

from audit.worldset import check_valid
from tesaron.degrees import Probability
from tesaron.encoder import Context, encode
from tesaron.worlds import World, WorldParams, generate_world

N_SOURCES = 8
REL_LOW = 0.55
REL_HIGH = 0.97
# v0.2 expected number of reports per atom is kept: 3 * 0.5 = 8 * 0.1875 and 3 * 0.02 = 8 * 0.0075.
Q_TRUE = 0.1875
Q_FALSE = 0.0075
REL_STREAM_TAG = 0x7E5A03
# Final v0.3 worlds (author decision A4): classes stay far apart, the overlap entities move close to their partner class.
V03_RADIUS = 3.0
V03_OVERLAP_FRACTION = 0.8


def v03_reliabilities(seed: int) -> tuple[Probability, ...]:
    """The 8 source reliabilities of the world with this seed, rounded to 3 decimals, in draw order."""
    rng = np.random.Generator(np.random.PCG64(np.random.SeedSequence([seed, REL_STREAM_TAG])))
    xs = rng.uniform(REL_LOW, REL_HIGH, size=N_SOURCES)
    return tuple(Probability(round(float(x), 3)) for x in xs)


def v03_params(seed: int, prototype_radius: float) -> WorldParams:
    """Default WorldParams except the five v0.3 fields."""
    return WorldParams(
        n_sources=N_SOURCES,
        source_reliabilities=v03_reliabilities(seed),
        q_true=Q_TRUE,
        q_false=Q_FALSE,
        prototype_radius=prototype_radius,
    )


def generate_world_v03(seed: int, prototype_radius: float) -> World:
    return generate_world(seed, v03_params(seed, prototype_radius))


def build_v03(world_seed: int, enc_seed: int, prototype_radius: float):
    """(world, default context, fixed-system encoding) of a v0.3 world. May raise WorldGenerationError."""
    world = generate_world_v03(world_seed, prototype_radius)
    ctx = Context.from_world(world, enc_seed)
    return world, ctx, encode(world, ctx)


def check_valid_v03(world, context, encoding) -> tuple[bool, str, int]:
    """D5 validity (the unchanged `audit.worldset.check_valid`) with the reason split into
    "pcm_not_converged", "pcm_degenerate", "H_lt_10"; (valid, reason, |H|)."""
    ok, reason, h = check_valid(world, context, encoding)
    if ok:
        return True, "", h
    if reason == "pcm_unusable":
        return False, ("pcm_not_converged" if not encoding.fit.converged else "pcm_degenerate"), 0
    if reason == "h_too_small":
        return False, "H_lt_10", h
    return False, reason, h


def v03_world_params(seed: int) -> WorldParams:
    """Parameters of the final v0.3 world: the S1 parameters at radius V03_RADIUS with overlap_fraction
    V03_OVERLAP_FRACTION. Differs from WorldParams() only in six fields."""
    return replace(v03_params(seed, V03_RADIUS), overlap_fraction=V03_OVERLAP_FRACTION)


def generate_world_v03_final(seed: int) -> World:
    return generate_world(seed, v03_world_params(seed))


def build_v03_final(world_seed: int, enc_seed: int):
    """(world, default context, fixed-system encoding) of a final v0.3 world. May raise WorldGenerationError."""
    world = generate_world_v03_final(world_seed)
    ctx = Context.from_world(world, enc_seed)
    return world, ctx, encode(world, ctx)
