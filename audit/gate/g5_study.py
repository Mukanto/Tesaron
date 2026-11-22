"""Layer-1 gate study for G5 (PREREG section 6.3).

plus : the fixed system on a development world (seeds drawn by the study rng from 900000-900999).
minus: twin N5 (PCM fitted on D_derive union D_validate) on a development world.
criterion: audit.checks.judge_g5, the judge that Layer 2 runs on the real test worlds.
control (K4): the centers after corrupting D_validate differ from the original (a leak).

Run it with audit/gate/certify.py (it imports the audit modules before the leak guard is armed).
"""

import numpy as np

from truth_gate import Budget, Control, Criterion, Study, Targets, World

from audit import checks as C
from audit.gate import common as G
from audit.twins import N5


def _copy(d):
    return {k: np.array(v, copy=True) for k, v in d.items()}


def _control(d, rng):
    out = _copy(d)
    out["centers_val_corrupt"] = out["centers"] + 0.1
    return out


def _twin(rng):
    return N5()


STUDY = Study(
    name="G5: validation data do not leak into pattern computation",
    criteria=[Criterion("G5", C.judge_g5)],
    worlds={
        "plus": World(G.plus_world("G5")),
        "minus": World(
            G.minus_world("G5", _twin),
            derived_from="plus",
            change="twin N5: PCM is fitted on D_derive union D_validate",
        ),
    },
    controls=[Control("validation_leaks", ["G5"], transform=_control)],
    budget=Budget(samples=100),
    targets=Targets(),
)
