"""Layer-1 gate study for G4 (PREREG_v0.3 section 6.3).

plus : the fixed system on a v0.3 development world (seeds drawn by the study rng from 930000-930999).
minus: twin N4 (abduction breaks score ties in an order drawn from the study rng on every call) on a development
       world.
criterion: audit.checks.judge_g4, the judge that Layer 2 runs on the real test worlds.
control (K4): the permuted-input output hashes differ from the original.

The gate forbids subprocesses, so the three PYTHONHASHSEED subprocess hashes of G4 are not exercised here (they run
in Layer 2 and in the unit tests).

Run it with audit/v03/gate/certify.py (it imports the audit modules before the leak guard is armed).
"""

import numpy as np

from truth_gate import Budget, Control, Criterion, Study, Targets, World

from audit import checks as C
from audit.v03.gate import common as G
from audit.twins import N4


def _copy(d):
    return {k: np.array(v, copy=True) for k, v in d.items()}


def _control(d, rng):
    out = _copy(d)
    out["h_perm"] = out["h_perm"] + np.uint64(1)
    return out


def _twin(rng):
    return N4(G.rng_source(rng))


STUDY = Study(
    name="G4: the decoder gives the same output for the same input (same machine, same NumPy build)",
    criteria=[Criterion("G4", C.judge_g4)],
    worlds={
        "plus": World(G.plus_world("G4")),
        "minus": World(
            G.minus_world("G4", _twin),
            derived_from="plus",
            change="twin N4: among abduction candidates with equal score the order is drawn from the study rng on "
                   "every call",
        ),
    },
    controls=[Control("permutation_changes_output", ["G4"], transform=_control)],
    budget=Budget(samples=100),
    targets=Targets(),
)
