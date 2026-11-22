"""Enums of SPEC section 1."""

from __future__ import annotations

from enum import Enum, IntEnum


class Channel(IntEnum):
    """POS = evidence for, NEG = evidence against. IntEnum so that sorting is deterministic."""

    POS = 0
    NEG = 1


class Belnap(Enum):
    """Belnap values. They describe only the system's epistemic state, never the world."""

    T = "T"
    F = "F"
    B = "B"
    U = "U"

    @property
    def pos(self) -> bool:
        return self in (Belnap.T, Belnap.B)

    @property
    def neg(self) -> bool:
        return self in (Belnap.F, Belnap.B)

    @staticmethod
    def from_channels(pos: bool, neg: bool) -> "Belnap":
        if pos and neg:
            return Belnap.B
        if pos:
            return Belnap.T
        if neg:
            return Belnap.F
        return Belnap.U


class EpistemicStatus(IntEnum):
    """OBSERVED > DERIVED > HYPOTHESIS (strongest to weakest)."""

    HYPOTHESIS = 1
    DERIVED = 2
    OBSERVED = 3


class ComputationalStatus(Enum):
    """Kept separate from the epistemic statuses; used only when the encoder does not converge."""

    NOT_COMPUTED = "NOT_COMPUTED"
