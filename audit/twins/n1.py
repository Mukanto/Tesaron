"""N1a and N1b: the encoder turns membership into probability (G1)."""

from __future__ import annotations

from dataclasses import replace

from audit.system import System
from tesaron.degrees import Membership
from tesaron.enums import ComputationalStatus


def _class_units_by_entity(units) -> dict:
    by_entity: dict = {}
    for atom in sorted(units):
        if atom.pred.startswith("c"):
            by_entity.setdefault(atom.args[0], []).append(atom)
    return by_entity


class N1a(System):
    """N1a: typicalities are normalized to sum 1 per entity (FCM-like)."""

    name = "N1a"

    def _post_encoding(self, encoding, world, context):
        def fix(units):
            out = dict(units)
            for entity, atoms in _class_units_by_entity(units).items():
                total = sum(units[a].mu_pos.value for a in atoms)
                if total <= 0:
                    continue
                for a in atoms:
                    u = units[a]
                    out[a] = replace(u, mu_pos=Membership(min(1.0, u.mu_pos.value / total)))
            return out

        return replace(encoding, units=fix(encoding.units), validation_units=fix(encoding.validation_units))


class N1b(System):
    """N1b: mu_neg = 1 - mu_pos for class atoms (low typicality is read as refutation)."""

    name = "N1b"

    def _post_encoding(self, encoding, world, context):
        def fix(units):
            out = dict(units)
            for atom, u in units.items():
                if atom.pred.startswith("c") and u.status is not ComputationalStatus.NOT_COMPUTED:
                    out[atom] = replace(u, mu_neg=Membership(1.0 - u.mu_pos.value))
            return out

        return replace(encoding, units=fix(encoding.units), validation_units=fix(encoding.validation_units))
