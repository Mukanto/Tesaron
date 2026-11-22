"""Layer-1 gate study for G6 (PREREG section 6.3).

plus : the fixed system on a development world (seeds drawn by the study rng from 900000-900999).
minus: twin N6 (hypotheses inserted with status OBSERVED) on a development world.
criterion: audit.checks.judge_g6, the judge that Layer 2 runs on the real test worlds.
control (K4): relabel every HYPOTHESIS fact as OBSERVED while it is still outside the pass-1 fixpoint.

Run it with audit/gate/certify.py (it imports the audit modules before the leak guard is armed).
"""

import numpy as np

from truth_gate import Budget, Control, Criterion, Study, Targets, World

from audit import checks as C
from audit.gate import common as G
from audit.twins import N6


def _copy(d):
    return {k: np.array(v, copy=True) for k, v in d.items()}


def _control(d, rng):
    out = _copy(d)
    status = out["status"]
    out["status"] = np.where(status == 1, 3, status)
    return out


def _twin(rng):
    return N6()


STUDY = Study(
    name="G6: expansion makes no unevidenced claims",
    criteria=[Criterion("G6", C.judge_g6)],
    worlds={
        "plus": World(G.plus_world("G6")),
        "minus": World(
            G.minus_world("G6", _twin),
            derived_from="plus",
            change="twin N6: abduced hypotheses are inserted with status OBSERVED",
        ),
    },
    controls=[Control("hypotheses_labelled_observed", ["G6"], transform=_control)],
    budget=Budget(samples=100),
    targets=Targets(),
)
