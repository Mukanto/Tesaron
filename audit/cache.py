"""In-process memo of pure, deterministic computations (world generation, encoding).

Every cached function is a pure function of its arguments, so caching cannot change any result; it only saves time
when the gate evaluates the same development world many times. No file is read or written.
"""

from __future__ import annotations

from tesaron.encoder import Context, encode
from tesaron.worlds import generate_world

_WORLDS: dict = {}
_ENCODINGS: dict = {}


def get_world(world_seed: int):
    w = _WORLDS.get(world_seed)
    if w is None:
        w = _WORLDS[world_seed] = generate_world(world_seed)
    return w


def get_encoding(world_seed: int, enc_seed: int):
    """(world, context, fixed-system encoding) for a world seed and an encoder seed."""
    key = (world_seed, enc_seed)
    hit = _ENCODINGS.get(key)
    if hit is None:
        world = get_world(world_seed)
        ctx = Context.from_world(world, enc_seed)
        hit = _ENCODINGS[key] = (world, ctx, encode(world, ctx))
    return hit


def clear() -> None:
    _WORLDS.clear()
    _ENCODINGS.clear()
