"""Exact comparisons (PREREG section 3.1, R1-8).

Every metric is a ratio of integer counts. tesaron exposes the counts as fractions.Fraction companions
(tesaron.criterion.compute_metrics_exact); everything in audit/ that compares a metric with tau, epsilon_f,
epsilon_d or delta, or subtracts two metrics, does it here on Fractions. Tau values are exact fractions.

Fractions travel through the gate's numeric data arrays as (numerator, denominator) pairs of integers; (0, 0) marks an
undefined value. decode_pairs() turns such an array back into Fractions, None (undefined) or INVALID (a pair that no
well-formed collect() produces; it appears only when the gate's probes replace the data by zeros or noise).
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction

import numpy as np

EPS_F = Fraction(5, 100)  # G8 tolerances (D4b, Q-eps_d (a)): 0.05 and 0.02 exactly
EPS_D = Fraction(2, 100)
DELTA = Fraction(5, 100)  # T-1 (D2)
INVALID = "invalid"
MAX_RATIO = 3  # a well-formed value is at most 1.2 (new_false plus the NT trade-off)


@dataclass(frozen=True)
class ExactTaus:
    tau_s: Fraction  # fidelity >= tau_s
    tau_d: Fraction  # deviation <= tau_d
    tau_t: Fraction  # consistency >= tau_t
    tau_b: Fraction  # uncertainty <= tau_b

    def floats(self):
        """tesaron's float Taus, for the descriptive uses of tesaron.criterion.wisdom only."""
        from tesaron.criterion.wisdom import Taus

        return Taus(float(self.tau_s), float(self.tau_d), float(self.tau_t), float(self.tau_b))

    def to_json(self) -> dict:
        d = {}
        for name in ("tau_s", "tau_d", "tau_t", "tau_b"):
            v = getattr(self, name)
            d[name] = float(v)
            d[name + "_exact"] = frac_str(v)
        return d

    @staticmethod
    def from_json(doc: dict) -> "ExactTaus":
        return ExactTaus(*(str_frac(doc[n + "_exact"]) for n in ("tau_s", "tau_d", "tau_t", "tau_b")))


def frac_str(f: Fraction) -> str:
    return f"{f.numerator}/{f.denominator}"


def str_frac(s: str) -> Fraction:
    n, d = s.split("/")
    return Fraction(int(n), int(d))


def feasible(ex: dict, taus: ExactTaus) -> bool:
    """fidelity >= tau_s, deviation <= tau_d, consistency >= tau_t and uncertainty <= tau_b, exactly. An undefined
    fidelity or new_true (and, only for an empty K, consistency or uncertainty) makes the point infeasible."""
    f, d, c, u, nt = ex["fidelity"], ex["deviation"], ex["consistency"], ex["uncertainty"], ex["new_true"]
    if f is None or nt is None or c is None or u is None:
        return False
    return f >= taus.tau_s and d <= taus.tau_d and c >= taus.tau_t and u <= taus.tau_b


def compute_taus(exact_list) -> tuple[ExactTaus, dict]:
    """D1: tau_s = min fidelity, tau_d = max deviation, tau_t = min consistency, tau_b = max uncertainty over the
    calibration worlds' default-configuration metrics, as exact fractions. Raises ValueError on an undefined metric
    (a calibration world with an undefined metric is invalid and must have been replaced)."""
    for ex in exact_list:
        if any(ex[k] is None for k in ("fidelity", "deviation", "consistency", "uncertainty")):
            raise ValueError("a calibration world has an undefined default-configuration metric")
    taus = ExactTaus(
        tau_s=min(ex["fidelity"] for ex in exact_list),
        tau_d=max(ex["deviation"] for ex in exact_list),
        tau_t=min(ex["consistency"] for ex in exact_list),
        tau_b=max(ex["uncertainty"] for ex in exact_list),
    )
    return taus, {"n_worlds": len(exact_list)}


def defined_default_metrics(ex: dict) -> bool:
    """A calibration world is valid only if its default-configuration metrics used by D1 are all defined."""
    return all(ex[k] is not None for k in ("fidelity", "deviation", "consistency", "uncertainty"))


def encode_pairs(fracs) -> np.ndarray:
    """Fractions (or None for undefined) -> int64 array of (numerator, denominator) pairs, shape (len, 2)."""
    out = np.zeros((len(fracs), 2), dtype=np.int64)
    for i, f in enumerate(fracs):
        if f is not None:
            out[i] = (f.numerator, f.denominator)
    return out


def decode_pairs(arr) -> list:
    """Inverse of encode_pairs for an array of any leading shape; entries are Fraction, None or INVALID."""
    a = np.asarray(arr, dtype=float).reshape(-1, 2)
    out = []
    for n, d in a:
        if not (np.isfinite(n) and np.isfinite(d)):
            out.append(INVALID)
            continue
        n, d = int(n), int(d)
        if n == 0 and d == 0:
            out.append(None)
        elif d > 0 and 0 <= n <= MAX_RATIO * d:
            out.append(Fraction(n, d))
        else:
            out.append(INVALID)
    return out


# ---- constrained Pareto front and hypervolume, exactly (SPEC section 9; the F3 comparison fields) -------------------
def pareto_points(exacts_by_config: dict, taus: ExactTaus) -> list:
    """[(config, x, y)] for the feasible points with a defined new_true, x = 1 - new_false and y = new_true, as
    Fractions. exacts_by_config: {(alpha, k): exact metric dict}."""
    out = []
    for config in sorted(exacts_by_config):
        ex = exacts_by_config[config]
        if feasible(ex, taus) and ex["new_true"] is not None:
            out.append((config, 1 - ex["new_false"], ex["new_true"]))
    return out


def pareto_front_exact(points) -> list:
    """The non-dominated points among [(config, x, y)], ordered x descending, y descending, then config ascending."""
    dominated = lambda p, q: q[1] >= p[1] and q[2] >= p[2] and (q[1] > p[1] or q[2] > p[2])
    front = [p for p in points if not any(dominated(p, q) for q in points)]
    return sorted(front, key=lambda p: (-p[1], -p[2], p[0]))


def hypervolume_exact(points, ref=(Fraction(0), Fraction(0))) -> Fraction:
    """Area of the union of the rectangles [ref_x, x] x [ref_y, y] over [(config, x, y)], exactly."""
    xy = [(x, y) for _, x, y in points if x > ref[0] and y > ref[1]]
    area, prev = Fraction(0), ref[0]
    for x in sorted({x for x, _ in xy}):
        area += (x - prev) * (max(y for px, y in xy if px >= x) - ref[1])
        prev = x
    return area
