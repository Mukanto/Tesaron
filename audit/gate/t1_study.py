"""Layer-1 gate study for T-1 (PREREG section 6.3, draft 5).

plus : the exact grid metrics of the fixed system on a development world (seeds drawn by the study rng from 900000-900999),
       restricted to alpha 0.65-0.80 (real-shaped data), as T-1 data under the gate tau (audit.gate.common.gate_taus).
minus: twin NT applied to that plus: new_false rises by 1/5 across the uncertainty span of the feasible points.
criterion: audit.checks.judge_t1 (exact), the judge that Layer 2 runs on the real test worlds.
control (K4): add the same trade-off to the plus data.

Run it with audit/gate/certify.py (it imports the audit modules before the leak guard is armed).
"""

from truth_gate import Budget, Control, Criterion, Study, Targets, World

from audit import checks as C
from audit.gate import common as G

STUDY = Study(
    name="T-1: within the reasonable bounds, admitting weaker evidence does not increase new false conclusions by more than δ",
    criteria=[Criterion("T-1", C.judge_t1)],
    worlds={
        "plus": World(G.t1_plus),
        "minus": World(
            G.t1_minus,
            derived_from="plus",
            change="twin NT applied to the plus metric points: new_false rises by 1/5 across the uncertainty span "
                   "as uncertainty falls",
        ),
    },
    controls=[Control("add_trade_off", ["T-1"], transform=lambda d, rng: G.t1_add_trade_off(d))],
    budget=Budget(samples=100),
    targets=Targets(),
)
