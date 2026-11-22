"""Layer-1 gate study for G8 (PREREG section 6.3, draft 5).

plus : abduction without propagation (audit.gate.plus_systems.NoPropagation: pass 2 adds the hypotheses, which are U
       atoms, and does not deduce, so no encoded atom can change) on a development world (seeds drawn by the study rng
       from 900000-900999). Layer 2 judges the fixed system; this system exists only here.
minus: twin N8 applied to that plus (at every k > 0 the first min(k, n) observed facts of decided encoded atoms are
       replaced by the opposite-channel fact with status HYPOTHESIS).
criterion: audit.checks.judge_g8 (exact comparisons), the judge that Layer 2 runs on the real test worlds.
control (K4): lower the fidelity of every k > 0 column by about 0.2 (abduction destroys meaning).

Run it with audit/gate/certify.py (it imports the audit modules before the leak guard is armed).
"""

import numpy as np

from truth_gate import Budget, Control, Criterion, Study, Targets, World

from audit import checks as C
from audit.gate import common as G
from audit.twins import N8


def _control(d, rng):
    out = {k: np.array(v, copy=True) for k, v in d.items()}
    fid = out["fidelity"]  # shape (alphas, ks, 2): numerator, denominator
    fid[:, 1:, 0] = np.maximum(fid[:, 1:, 0] - fid[:, 1:, 1] // 5 - 1, 0)
    out["fidelity"] = fid
    return out


def _twin(rng):
    return N8(propagate=False)


STUDY = Study(
    name="G8: creativity (abduction) preserves meaning",
    criteria=[Criterion("G8", C.judge_g8)],
    worlds={
        "plus": World(G.plus_world("G8")),
        "minus": World(
            G.minus_world("G8", _twin),
            derived_from="plus",
            change="twin N8 applied to the no-propagation plus: abduction overwrites observations (the first min(k, n) "
                   "observed facts of decided encoded atoms get the opposite channel, status HYPOTHESIS)",
        ),
    },
    controls=[Control("abduction_lowers_fidelity", ["G8"], transform=_control)],
    budget=Budget(samples=100),
    targets=Targets(),
)
