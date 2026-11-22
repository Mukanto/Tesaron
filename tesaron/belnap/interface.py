"""Belnap interface (SPEC section 6)."""

from __future__ import annotations

from typing import Mapping

from tesaron.atoms import Atom
from tesaron.degrees import Membership
from tesaron.enums import Belnap, Channel, ComputationalStatus
from tesaron.meaning import MeaningUnit

Fact = tuple[Channel, Atom]


def _threshold(alpha) -> float:
    if isinstance(alpha, Membership):
        return alpha.value
    if isinstance(alpha, bool) or not isinstance(alpha, (int, float)):
        raise TypeError(f"alpha must be a plain number or Membership, got {type(alpha).__name__}")
    return float(alpha)


def to_value(mu_pos: Membership, mu_neg: Membership, alpha) -> Belnap:
    """pos = (mu_pos >= alpha), neg = (mu_neg >= alpha); equality counts as >=."""
    if not isinstance(mu_pos, Membership) or not isinstance(mu_neg, Membership):
        raise TypeError("to_value needs Membership degrees")
    a = _threshold(alpha)
    return Belnap.from_channels(mu_pos >= a, mu_neg >= a)


def unit_value(unit: MeaningUnit, alpha) -> Belnap:
    """Interface value of a unit. A NOT_COMPUTED unit produces no facts, so its value is U."""
    if unit.status is ComputationalStatus.NOT_COMPUTED:
        return Belnap.U
    return to_value(unit.mu_pos, unit.mu_neg, alpha)


def interface_facts(
    units: Mapping[Atom, MeaningUnit], alpha
) -> dict[Fact, tuple[str, ...]]:
    """Initial facts (status OBSERVED): (POS, atom) if pos, (NEG, atom) if neg, with the unit's provenance.

    Returns {fact: provenance} in sorted fact order. NOT_COMPUTED units produce no facts.
    """
    a = _threshold(alpha)
    out: dict[Fact, tuple[str, ...]] = {}
    for atom in sorted(units):
        unit = units[atom]
        if unit.status is ComputationalStatus.NOT_COMPUTED:
            continue
        if unit.mu_pos >= a:
            out[(Channel.POS, atom)] = unit.provenance
        if unit.mu_neg >= a:
            out[(Channel.NEG, atom)] = unit.provenance
    return {f: out[f] for f in sorted(out)}


def encoded_values(units: Mapping[Atom, MeaningUnit], alpha) -> dict[Atom, Belnap]:
    """enc(a) for every atom that has a unit (sorted by atom)."""
    return {atom: unit_value(units[atom], alpha) for atom in sorted(units)}


def enc(units: Mapping[Atom, MeaningUnit], atom: Atom, alpha) -> Belnap:
    """enc(a): the interface value of atom a, or U if a has no unit."""
    unit = units.get(atom)
    return Belnap.U if unit is None else unit_value(unit, alpha)


def on_boundary(unit: MeaningUnit, alpha, epsilon_band: float) -> bool:
    """|mu_pos - alpha| < epsilon_band or |mu_neg - alpha| < epsilon_band (descriptive only)."""
    a = _threshold(alpha)
    return abs(unit.mu_pos.value - a) < epsilon_band or abs(unit.mu_neg.value - a) < epsilon_band


def boundary_share(units: Mapping[Atom, MeaningUnit], alpha, epsilon_band: float) -> float | None:
    """Share of meaning units on the boundary band; None if there are no units."""
    if not units:
        return None
    n = sum(1 for atom in sorted(units) if on_boundary(units[atom], alpha, epsilon_band))
    return n / len(units)
