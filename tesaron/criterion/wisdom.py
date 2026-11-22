"""Wisdom criterion: constrained Pareto and hypervolume (SPEC section 9)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable, Sequence

from tesaron.criterion.metrics import Metrics

# Creativity grid in v0.1; the final grid is fixed in the v0.2 pre-registration.
ALPHAS = (0.9, 0.8, 0.7, 0.6, 0.5)
KS = (0, 5, 10)
DEFAULT_GRID: tuple[tuple[float, int], ...] = tuple((a, k) for a in ALPHAS for k in KS)


@dataclass(frozen=True)
class Taus:
    """Constraint thresholds. Parameters in v0.1; the calibration rule is fixed in v0.2."""

    tau_s: float  # fidelity >= tau_s
    tau_d: float  # deviation <= tau_d
    tau_t: float  # consistency >= tau_t
    tau_b: float  # uncertainty <= tau_b


PLACEHOLDER_TAUS = Taus(tau_s=0.8, tau_d=0.05, tau_t=0.9, tau_b=0.5)  # placeholder, not frozen


def is_feasible(m: Metrics, taus: Taus) -> bool:
    """fidelity >= tau_s, deviation <= tau_d, consistency >= tau_t, uncertainty <= tau_b.
    A None in fidelity or new_true makes the point infeasible (a None consistency or uncertainty, which
    arises only when K is empty, does too)."""
    if m.fidelity is None or m.new_true is None or m.consistency is None or m.uncertainty is None:
        return False
    return (
        m.fidelity >= taus.tau_s
        and m.deviation <= taus.tau_d
        and m.consistency >= taus.tau_t
        and m.uncertainty <= taus.tau_b
    )


@dataclass(frozen=True)
class Point:
    """One configuration on one world: (x, y) = (1 - new_false, new_true)."""

    x: float
    y: float | None
    feasible: bool = True
    config: tuple[float, int] | None = None  # (alpha, k_abduction)
    uncertainty: float | None = None
    new_false: float | None = None


def make_point(config: tuple[float, int], m: Metrics, taus: Taus) -> Point:
    return Point(
        x=m.x,
        y=m.new_true,
        feasible=is_feasible(m, taus),
        config=config,
        uncertainty=m.uncertainty,
        new_false=m.new_false,
    )


def _dominates(p: Point, q: Point) -> bool:
    return p.x >= q.x and p.y >= q.y and (p.x > q.x or p.y > q.y)


def pareto_front(points: Iterable[Point]) -> list[Point]:
    """Non-dominated feasible points, ordered x descending, then y descending (then config, for ties)."""
    feas = [p for p in points if p.feasible and p.y is not None]
    front = [p for p in feas if not any(_dominates(q, p) for q in feas)]
    return sorted(front, key=lambda p: (-p.x, -p.y, p.config if p.config is not None else (0.0, 0)))


def hypervolume(front: Iterable, ref: tuple[float, float] = (0.0, 0.0)) -> float:
    """Area of the union of the rectangles [ref_x, x] x [ref_y, y]; infeasible points count 0.
    Elements are Points or (x, y) tuples."""
    xy = []
    for p in front:
        if isinstance(p, Point):
            if not p.feasible or p.y is None:
                continue
            xy.append((p.x, p.y))
        else:
            xy.append((float(p[0]), float(p[1])))
    xy = [(x, y) for x, y in xy if x > ref[0] and y > ref[1]]
    xs = sorted({x for x, _ in xy})
    area, prev = 0.0, ref[0]
    for x in xs:
        height = max(y for px, y in xy if px >= x) - ref[1]
        area += (x - prev) * height
        prev = x
    return area


def point_score(p: Point) -> float:
    """Score of one point: its rectangle area x*y if feasible, else 0."""
    return hypervolume([p])


class T1Result(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    UNDEFINED = "undefined"


def t1_world(points: Sequence[Point], delta: float = 0.05) -> T1Result:
    """Over the feasible points of one world: for every pair (p, q) with uncertainty(q) < uncertainty(p),
    new_false(q) - new_false(p) <= delta must hold. Undefined if fewer than two feasible points have
    distinct uncertainty values. Compared exactly, with no extra float tolerance."""
    feas = [p for p in points if p.feasible]
    if len({p.uncertainty for p in feas}) < 2:
        return T1Result.UNDEFINED
    for p in feas:
        for q in feas:
            if q.uncertainty < p.uncertainty and q.new_false - p.new_false > delta:
                return T1Result.FAIL
    return T1Result.PASS
