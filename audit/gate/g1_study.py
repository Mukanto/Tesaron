"""Layer-1 gate study for G1 (PREREG section 6.3).

plus : the fixed system on a development world (seeds drawn by the study rng from 900000-900999).
minus: twin N1a (typicalities normalized to sum 1 per entity) or N1b (mu_neg = 1 - mu_pos for class atoms), chosen
       by the study rng, on a development world.
criterion: audit.checks.judge_g1, the judge that Layer 2 runs on the real test worlds.
control (K4): add 0.5 to every outlier typicality (the sums of the outlier entities then exceed 0.5).

Run it with audit/gate/certify.py (it imports the audit modules before the leak guard is armed).
"""

import numpy as np

from truth_gate import Budget, Control, Criterion, Study, Targets, World

from audit import checks as C
from audit.gate import common as G
from audit.twins import N1a, N1b


def _copy(d):
    return {k: np.array(v, copy=True) for k, v in d.items()}


def _control(d, rng):
    out = _copy(d)
    out["outlier_pos"] = out["outlier_pos"] + 0.5
    return out


def _twin(rng):
    return N1a() if rng.random() < 0.5 else N1b()


STUDY = Study(
    name="G1: membership degrees are not turned into probabilities",
    criteria=[Criterion("G1", C.judge_g1)],
    worlds={
        "plus": World(G.plus_world("G1")),
        "minus": World(
            G.minus_world("G1", _twin),
            derived_from="plus",
            change="twin N1a (typicalities normalized to sum 1 per entity, FCM-like) or N1b (mu_neg = 1 - mu_pos "
                   "for class atoms), drawn per sample",
        ),
    },
    controls=[Control("inflate_outlier_typicality", ["G1"], transform=_control)],
    budget=Budget(samples=100),
    targets=Targets(),
)
