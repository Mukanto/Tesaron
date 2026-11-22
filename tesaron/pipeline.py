"""Glue: world -> encoder -> Belnap interface -> decoder -> metrics (SPEC section 0)."""

from __future__ import annotations

from dataclasses import replace

from tesaron.belnap import interface_facts
from tesaron.criterion.metrics import Metrics, compute_metrics_for
from tesaron.criterion.wisdom import DEFAULT_GRID, Point, Taus, make_point
from tesaron.decoder import DecoderOutput, decode
from tesaron.encoder import Context, Encoding, encode


def decode_encoding(context: Context, encoding: Encoding) -> DecoderOutput:
    """Interface facts at context.alpha, then the two-pass decoder with context.k_abduction."""
    facts = interface_facts(encoding.units, context.alpha)
    return decode(facts, context.rules, context.vocabulary, context.k_abduction)


def evaluate(world, context: Context, encoding: Encoding) -> tuple[DecoderOutput, Metrics]:
    output = decode_encoding(context, encoding)
    return output, compute_metrics_for(world, context, encoding, output)


def evaluate_grid(
    world,
    context: Context,
    encoding: Encoding,
    taus: Taus,
    grid: tuple[tuple[float, int], ...] = DEFAULT_GRID,
) -> list[tuple[Point, Metrics]]:
    """One (point, metrics) per (alpha, k_abduction) configuration; the encoding is shared."""
    out = []
    for alpha, k in grid:
        ctx = replace(context, alpha=alpha, k_abduction=k)
        _, metrics = evaluate(world, ctx, encoding)
        out.append((make_point((alpha, k), metrics, taus), metrics))
    return out


def run(world, context: Context) -> tuple[Encoding, DecoderOutput, Metrics]:
    encoding = encode(world, context)
    output, metrics = evaluate(world, context, encoding)
    return encoding, output, metrics
