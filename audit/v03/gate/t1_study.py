"""Layer-1 gate study for T-1 (PREREG_v0.3 section 6.3).

plus : the k = 0 grid metrics (the 10 alpha levels) of the fixed system on a v0.3 development world on which T-1 is defined at
       the gate tau (the study rng draws seeds from 930000-930999 until it finds one; the skipped draws are counted, definedness
       only), with new_false replaced by a constant, as T-1 data under the gate tau
       (audit.v03.gate.common.gate_taus). The real new_false values are replaced where they are read and are never stored,
       printed or put into the certificate (PREREG section 2, no pilot); T-1 holds on this plus world by construction.
       The real denominators n_q of new_false are kept (design quantities): the one-atom floor needs them.
minus: twin NT applied to that plus: new_false rises by 1/2 across the uncertainty span of the feasible points (R1-1).
criterion: audit.v03.checks.judge_t1 (exact, with the one-atom floor max(delta, 1/n_q)), the judge that Layer 2 runs on the
           real test worlds. T-1 is read at k = 0 only (A1); the data are the 10 points of the k = 0 line.
control (K4): add the same trade-off (1/2) to the plus data.

Run it with audit/v03/gate/certify.py (it imports the audit modules before the leak guard is armed).
"""

from truth_gate import Budget, Control, Criterion, Study, Targets, World

from audit.v03 import checks as V
from audit.v03.aggregate import CLAIMS
from audit.v03.gate import common as G

STUDY = Study(
    name="T-1: " + CLAIMS["T-1"],  # the claim of PREREG 3.2 (R2-1): it states the one-atom floor
    criteria=[Criterion("T-1", V.judge_t1)],
    worlds={
        "plus": World(G.t1_plus),
        "minus": World(
            G.t1_minus,
            derived_from="plus",
            change="twin NT applied to the plus metric points: new_false rises by 1/2 across the uncertainty span "
                   "as uncertainty falls",
        ),
    },
    controls=[Control("add_trade_off", ["T-1"], transform=lambda d, rng: G.t1_add_trade_off(d))],
    budget=Budget(samples=100),
    targets=Targets(),
)
