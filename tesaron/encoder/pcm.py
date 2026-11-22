"""Possibilistic c-means, Krishnapuram and Keller 1993 (SPEC section 5, step 3)."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class PCMFit:
    centers: tuple[tuple[float, ...], ...]
    n_iter: int
    converged: bool
    degenerate: bool = False  # smallest center distance < 0.5 x smallest prototype distance (revision S-3)

    @property
    def usable(self) -> bool:
        """Non-converged and degenerate fits are treated alike: class units are NOT_COMPUTED."""
        return self.converged and not self.degenerate


def typicality(points: np.ndarray, centers: np.ndarray, eta: np.ndarray, m: float) -> np.ndarray:
    """u_ik = 1 / (1 + (d2_ik / eta_k)^(1/(m-1))). Not normalized over k. Shape (n_points, n_centers)."""
    pts = np.atleast_2d(np.asarray(points, dtype=float))
    d2 = ((pts[:, None, :] - centers[None, :, :]) ** 2).sum(axis=2)
    return 1.0 / (1.0 + (d2 / eta[None, :]) ** (1.0 / (m - 1.0)))


def _min_pairwise(c: np.ndarray) -> float:
    """Smallest Euclidean distance between two rows (inf if there are fewer than two)."""
    best = float("inf")
    for i in range(len(c)):
        for j in range(i + 1, len(c)):
            best = min(best, float(np.linalg.norm(c[i] - c[j])))
    return best


def pcm_fit(
    points: np.ndarray,
    init_centers: np.ndarray,
    eta: np.ndarray,
    m: float,
    max_iter: int,
    tol: float,
) -> PCMFit:
    """Each iteration updates the typicalities, then the centers. Stops when the largest center shift
    falls below tol; if that has not happened after max_iter iterations, converged is False.
    The fit is degenerate if the smallest distance between two fitted centers is below 0.5 x the smallest
    distance between two initial centers (the prototypes); coincident centers must never pass silently."""
    pts = np.asarray(points, dtype=float)
    centers = np.array(init_centers, dtype=float)
    eta = np.asarray(eta, dtype=float)
    converged = False
    n_iter = 0
    for n_iter in range(1, max_iter + 1):
        u = typicality(pts, centers, eta, m)
        w = u**m
        new_centers = (w.T @ pts) / w.sum(axis=0)[:, None]
        shift = float(np.max(np.linalg.norm(new_centers - centers, axis=1)))
        centers = new_centers
        if shift < tol:
            converged = True
            break
    degenerate = _min_pairwise(centers) < 0.5 * _min_pairwise(np.array(init_centers, dtype=float))
    return PCMFit(
        tuple(tuple(float(v) for v in row) for row in centers), n_iter, converged, bool(degenerate)
    )
