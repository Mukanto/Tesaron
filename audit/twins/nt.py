"""NT: metric points with a built-in trade-off (T-1).

new_false rises by TRADE_OFF (0.2) across the uncertainty span as uncertainty falls. In the gate it is applied to the
plus world's metric points; in the detector diagnostic to the metric points of a real world. All arithmetic is exact
(fractions.Fraction).
"""

from __future__ import annotations

from fractions import Fraction

TRADE_OFF = Fraction(1, 5)


def with_trade_off(uncertainty, new_false, mask=None) -> list:
    """new_false + TRADE_OFF * (u_max - u) / (u_max - u_min): +1/5 at the lowest uncertainty, +0 at the highest.
    The span of u is taken over the points selected by mask (default: all); points outside the mask are unchanged.
    uncertainty and new_false are sequences of Fractions."""
    n = len(uncertainty)
    sel = [True] * n if mask is None else [bool(m) for m in mask]
    chosen = [uncertainty[i] for i in range(n) if sel[i]]
    if not chosen or max(chosen) == min(chosen):
        return list(new_false)
    lo, hi = min(chosen), max(chosen)
    out = []
    for i in range(n):
        if sel[i]:
            out.append(new_false[i] + TRADE_OFF * (hi - uncertainty[i]) / (hi - lo))
        else:
            out.append(new_false[i])
    return out
