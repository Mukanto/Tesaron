"""The oracle of PREREG section 6.3: every atom of I keeps its encoded value, every other atom of K gets its world
value, and all other atoms are U. It is the anchor of G7a (it must score > 0 at some alpha) and the plus system of the
gate's G7a study."""

from __future__ import annotations

from dataclasses import replace

from audit.system import System
from tesaron.belnap import unit_value
from tesaron.criterion.baselines import ValueOutput
from tesaron.criterion.metrics import compute_H, compute_metrics_for_exact
from tesaron.enums import Belnap


class Oracle(System):
    name = "oracle"

    def evaluate_exact(self, world, context, encoding, alpha, k):
        ctx = replace(context, alpha=alpha, k_abduction=k)
        units = encoding.units
        values = {}
        for atom in sorted(units):
            enc = unit_value(units[atom], alpha)
            if enc is not Belnap.U:  # I: keeps its encoded value
                values[atom] = enc
        for atom in sorted(set(units) | set(compute_H(sorted(units), world.truth, world.rules, ctx.vocabulary))):
            if atom not in values:  # the other atoms of K get their world value
                values[atom] = Belnap.T if world.truth(atom) else Belnap.F
        out = ValueOutput(values)
        m, ex = compute_metrics_for_exact(world, ctx, encoding, out)
        return out, m, ex
