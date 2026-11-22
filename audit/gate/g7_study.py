"""Layer-1 gate study for G7a (PREREG section 6.3, draft 5).

plus : the actual criterion (audit.checks.collect_g7a) applied to the baselines and to the oracle on a development world
       (seeds drawn by the study rng from 900000-900999).
minus: twin N7, the unconstrained criterion: feasibility is ignored, so every baseline point is scored.
criterion: audit.checks.judge_g7a, the judge that Layer 2 runs on the real test worlds.
control (K4): every baseline point is feasible and has a positive score.

tau of the gate: the D1 rule (exact) on ten development calibration worlds (audit.gate.common.gate_taus).

Run it with audit/gate/certify.py (it imports the audit modules before the leak guard is armed).
"""

import numpy as np

from truth_gate import Budget, Control, Criterion, Study, Targets, World

from audit import checks as C
from audit.gate import common as G
from audit.twins import N7


def _control(d, rng):
    out = {k: np.array(v, copy=True) for k, v in d.items()}
    out["base_feasible"] = np.ones_like(out["base_feasible"], dtype=bool)
    out["base_positive"] = np.ones_like(out["base_positive"], dtype=bool)
    return out


def _twin(rng):
    return N7()


STUDY = Study(
    name="G7a: none of the five degenerate baselines of SPEC §10 (echo, all_true, all_false, all_unknown, all_both) gets a positive score under the wisdom criterion",
    criteria=[Criterion("G7", C.judge_g7a)],
    worlds={
        "plus": World(G.plus_world("G7")),
        "minus": World(
            G.minus_world("G7", _twin),
            derived_from="plus",
            change="twin N7: the unconstrained criterion; feasibility is ignored, so every baseline point is scored",
        ),
    },
    controls=[Control("baselines_feasible_and_positive", ["G7"], transform=_control)],
    budget=Budget(samples=100),
    targets=Targets(),
)
