"""Meaning units (SPEC section 5, step 5)."""

from __future__ import annotations

from dataclasses import dataclass

from tesaron.atoms import Atom
from tesaron.degrees import Membership
from tesaron.enums import ComputationalStatus, EpistemicStatus


@dataclass(frozen=True)
class MeaningUnit:
    """An atom with a degree of support mu_pos and a degree of refutation mu_neg."""

    atom: Atom
    mu_pos: Membership
    mu_neg: Membership
    provenance: tuple[str, ...]
    status: EpistemicStatus | ComputationalStatus

    def __post_init__(self) -> None:
        for name in ("mu_pos", "mu_neg"):
            if not isinstance(getattr(self, name), Membership):
                raise TypeError(f"{name} must be a Membership, got {type(getattr(self, name)).__name__}")
        if not isinstance(self.status, (EpistemicStatus, ComputationalStatus)):
            raise TypeError("status must be an EpistemicStatus or ComputationalStatus")
        object.__setattr__(self, "provenance", tuple(self.provenance))
