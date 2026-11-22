"""Layer-1 gate study for G2 (PREREG section 6.3).

plus : the fixed system on a development world (seeds drawn by the study rng from 900000-900999).
minus: twin N2 (the encoder's selection seed is drawn from the study rng on every call instead of the context seed)
       on a development world.
criterion: audit.checks.judge_g2, the judge that Layer 2 runs on the real test worlds.
control (K4): make the second in-process hash differ from the first.

The gate forbids subprocesses, so the PYTHONHASHSEED subprocess part of G2 is not exercised here (it runs in Layer 2
and in the unit tests).

Run it with audit/gate/certify.py (it imports the audit modules before the leak guard is armed).
"""

import numpy as np

from truth_gate import Budget, Control, Criterion, Study, Targets, World

from audit import checks as C
from audit.gate import common as G
from audit.twins import N2


def _copy(d):
    return {k: np.array(v, copy=True) for k, v in d.items()}


def _control(d, rng):
    out = _copy(d)
    out["h2"] = out["h1"] + np.uint64(1)
    return out


def _twin(rng):
    return N2(G.rng_source(rng))


STUDY = Study(
    name="G2: encoding is reproducible in the same context (same machine, same NumPy build)",
    criteria=[Criterion("G2", C.judge_g2)],
    worlds={
        "plus": World(G.plus_world("G2")),
        "minus": World(
            G.minus_world("G2", _twin),
            derived_from="plus",
            change="twin N2: the encoder's selection seed is drawn from the study rng on every call instead of the "
                   "context seed",
        ),
    },
    controls=[Control("second_run_differs", ["G2"], transform=_control)],
    budget=Budget(samples=100),
    targets=Targets(),
)
