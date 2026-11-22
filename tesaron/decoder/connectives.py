"""Belnap-Dunn connectives (SPEC section 7.1), for compound queries.

         pos            neg
  not a  a.neg          a.pos
  a & b  a.pos & b.pos  a.neg | b.neg
  a | b  a.pos | b.pos  a.neg & b.neg
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Union

from tesaron.atoms import Atom
from tesaron.enums import Belnap


def b_not(a: Belnap) -> Belnap:
    return Belnap.from_channels(a.neg, a.pos)


def b_and(a: Belnap, b: Belnap) -> Belnap:
    return Belnap.from_channels(a.pos and b.pos, a.neg or b.neg)


def b_or(a: Belnap, b: Belnap) -> Belnap:
    return Belnap.from_channels(a.pos or b.pos, a.neg and b.neg)


@dataclass(frozen=True)
class Not:
    arg: "Query"


@dataclass(frozen=True)
class And:
    left: "Query"
    right: "Query"


@dataclass(frozen=True)
class Or:
    left: "Query"
    right: "Query"


Query = Union[Atom, Not, And, Or]


def evaluate_query(query: Query, value_of: Callable[[Atom], Belnap]) -> Belnap:
    """Evaluate a compound query; value_of gives the Belnap value of an atom (e.g. output.full or .verdict)."""
    if isinstance(query, Atom):
        return value_of(query)
    if isinstance(query, Not):
        return b_not(evaluate_query(query.arg, value_of))
    if isinstance(query, And):
        return b_and(evaluate_query(query.left, value_of), evaluate_query(query.right, value_of))
    if isinstance(query, Or):
        return b_or(evaluate_query(query.left, value_of), evaluate_query(query.right, value_of))
    raise TypeError(f"not a query: {type(query).__name__}")
