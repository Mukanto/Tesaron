"""N7: the unconstrained criterion (G7a): feasibility is ignored, so every baseline point is scored."""

from __future__ import annotations

from audit.system import System


class N7(System):
    """N7 is the fixed system with a marker that audit.checks.collect_g7a reads: the criterion is applied without
    its feasibility constraint (all_true then scores > 0)."""

    name = "N7"
    ignore_feasibility = True
