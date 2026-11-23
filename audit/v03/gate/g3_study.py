"""Layer-1 gate study for G3 (PREREG_v0.3 section 6.3).

plus : the fixed system on a v0.3 development world (seeds drawn by the study rng from 930000-930999).
minus: twin N3 (every relation atom with no report gets a default mu_pos = 0.8) on a v0.3 development world.
criterion: audit.checks.judge_g3, the judge that Layer 2 runs on the real test worlds.
control (K4): every ablated unit stays decided (the ablation changes nothing).

Run it with audit/v03/gate/certify.py (it imports the audit modules before the leak guard is armed).
"""

import numpy as np

from truth_gate import Budget, Control, Criterion, Study, Targets, World

from audit import checks as C
from audit.v03.gate import common as G
from audit.twins import N3


def _copy(d):
    return {k: np.array(v, copy=True) for k, v in d.items()}


def _control(d, rng):
    out = _copy(d)
    out["decided_after"] = out["decided_before"].copy()
    return out


def _twin(rng):
    return N3()


STUDY = Study(
    name="G3: a meaning unit needs its data (necessity)",
    criteria=[Criterion("G3", C.judge_g3)],
    worlds={
        "plus": World(G.plus_world("G3")),
        "minus": World(
            G.minus_world("G3", _twin),
            derived_from="plus",
            change="twin N3: every relation atom without a report gets a default prior mu_pos = 0.8",
        ),
    },
    controls=[Control("ablation_changes_nothing", ["G3"], transform=_control)],
    budget=Budget(samples=100),
    targets=Targets(),
)
