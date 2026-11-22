"""tau calibration, rule D1 (PREREG section 7): run the fixed system at the default configuration (alpha0, k0) on the
calibration worlds; tau_s = min fidelity, tau_d = max deviation, tau_t = min consistency, tau_b = max uncertainty, all
as exact fractions (audit.exact)."""

from __future__ import annotations

from audit.checks import ALPHA0, K0
from audit.exact import ExactTaus, compute_taus  # noqa: F401
from audit.system import FIXED


def default_exact(rec) -> dict:
    """Exact metrics of the fixed system at (alpha0, k0) on a WorldRecord."""
    return FIXED.evaluate_exact(rec.world, rec.context, rec.encoding, ALPHA0, K0)[2]


def default_metrics(rec):
    """Float metrics at (alpha0, k0)."""
    return FIXED.evaluate(rec.world, rec.context, rec.encoding, ALPHA0, K0)[1]
