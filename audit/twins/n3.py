"""N3: every relation atom with no report gets a default mu_pos = 0.8 (a prior; G3)."""

from __future__ import annotations

from dataclasses import replace

from audit.system import System
from tesaron.degrees import Membership
from tesaron.enums import EpistemicStatus
from tesaron.meaning import MeaningUnit

DEFAULT_PRIOR = 0.8


class N3(System):
    name = "N3"

    def _post_encoding(self, encoding, world, context):
        units = dict(encoding.units)
        for atom in sorted(context.vocabulary):
            if atom.pred.startswith("r") and atom not in units:
                units[atom] = MeaningUnit(
                    atom, Membership(DEFAULT_PRIOR), Membership(0.0), (), EpistemicStatus.OBSERVED
                )
        return replace(encoding, units={a: units[a] for a in sorted(units)})
