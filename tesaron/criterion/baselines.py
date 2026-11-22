"""Degenerate baselines (SPEC section 10), in the decoder's output format (full / verdict)."""

from __future__ import annotations

from typing import Mapping

from tesaron.atoms import Atom
from tesaron.belnap import enc
from tesaron.enums import Belnap
from tesaron.meaning import MeaningUnit


class ValueOutput:
    """An output whose full and verdict are the same table of Belnap values (U where absent)."""

    def __init__(self, values: Mapping[Atom, Belnap] | None = None, default: Belnap = Belnap.U) -> None:
        self._values = dict(values or {})
        self._default = default

    def full(self, atom: Atom) -> Belnap:
        return self._values.get(atom, self._default)

    def verdict(self, atom: Atom) -> Belnap:
        return self.full(atom)


BASELINE_NAMES = ("echo", "all_true", "all_false", "all_unknown", "all_both")


def echo(units: Mapping[Atom, MeaningUnit], alpha: float, vocab: frozenset[Atom]) -> ValueOutput:
    """enc(a) for every atom: no deduction, no abduction."""
    return ValueOutput({a: enc(units, a, alpha) for a in sorted(vocab)})


def all_true() -> ValueOutput:
    return ValueOutput(default=Belnap.T)


def all_false() -> ValueOutput:
    return ValueOutput(default=Belnap.F)


def all_unknown() -> ValueOutput:
    return ValueOutput(default=Belnap.U)


def all_both() -> ValueOutput:
    return ValueOutput(default=Belnap.B)


def make_baselines(
    units: Mapping[Atom, MeaningUnit], alpha: float, vocab: frozenset[Atom]
) -> dict[str, ValueOutput]:
    return {
        "echo": echo(units, alpha, vocab),
        "all_true": all_true(),
        "all_false": all_false(),
        "all_unknown": all_unknown(),
        "all_both": all_both(),
    }
