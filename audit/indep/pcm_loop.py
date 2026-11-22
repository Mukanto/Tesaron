"""F4: an independent PCM loop (PREREG section 6.1).

Written directly with explicit loops over points and clusters instead of the vectorized code in
tesaron.encoder.pcm. It reads only plain numbers and the world's feature rows; it does not import tesaron.encoder.
"""

from __future__ import annotations

import math


def pcm_centers(points, init_centers, eta, m, max_iter, tol):
    """Krishnapuram-Keller PCM with the SPEC section 5 update order: typicalities, then centers.

    Returns (centers as a list of lists, number of iterations, converged flag).
    """
    centers = [list(map(float, c)) for c in init_centers]
    dim = len(centers[0])
    power = 1.0 / (m - 1.0)
    converged = False
    iterations = 0
    for iterations in range(1, max_iter + 1):
        new_centers = []
        for k, c in enumerate(centers):
            num = [0.0] * dim
            den = 0.0
            for x in points:
                d2 = 0.0
                for j in range(dim):
                    d2 += (x[j] - c[j]) ** 2
                u = 1.0 / (1.0 + (d2 / eta[k]) ** power)
                w = u**m
                den += w
                for j in range(dim):
                    num[j] += w * x[j]
            new_centers.append([v / den for v in num])
        shift = max(
            math.sqrt(sum((a - b) ** 2 for a, b in zip(nc, oc))) for nc, oc in zip(new_centers, centers)
        )
        centers = new_centers
        if shift < tol:
            converged = True
            break
    return centers, iterations, converged


def max_center_difference(world, context, derive_ids, fitted_centers) -> float:
    """Largest absolute coordinate difference between fitted_centers and an independent fit on the feature rows of
    derive_ids (rows taken from the world, ordered by row id)."""
    derive = set(derive_ids)
    rows = sorted((r for r in world.feature_rows if r.row_id in derive), key=lambda r: r.row_id)
    points = [list(map(float, r.x)) for r in rows]
    centers, _, _ = pcm_centers(points, context.prototypes, context.eta, context.m, context.max_iter, context.tol)
    return max(abs(a - b) for c, f in zip(centers, fitted_centers) for a, b in zip(c, f))


def max_mu_difference(world, context, derive_ids, fitted_centers, units) -> float:
    """Largest absolute difference between the class units' mu_pos in `units` and an independent computation: the
    mean of an entity's D_derive feature rows (ordered by row id), then u_ek = 1 / (1 + (d2 / eta_k)^(1/(m-1)))
    against the fitted centers. Entities without D_derive rows have no class units."""
    derive = set(derive_ids)
    rows = {}
    for r in sorted(world.feature_rows, key=lambda r: r.row_id):
        if r.row_id in derive:
            rows.setdefault(r.entity, []).append(list(map(float, r.x)))
    power = 1.0 / (context.m - 1.0)
    worst = 0.0
    seen = set()
    for entity, pts in rows.items():
        dim = len(pts[0])
        mean = [sum(p[j] for p in pts) / len(pts) for j in range(dim)]
        for k, c in enumerate(fitted_centers):
            d2 = sum((mean[j] - c[j]) ** 2 for j in range(dim))
            u = 1.0 / (1.0 + (d2 / context.eta[k]) ** power)
            atom = next((a for a in units if a.pred == f"c{k}" and a.args == (entity,)), None)
            if atom is None:
                worst = max(worst, 1.0)  # a missing unit
                continue
            seen.add(atom)
            worst = max(worst, abs(units[atom].mu_pos.value - u))
    extra = [a for a in units if a.pred.startswith("c") and a not in seen]
    if extra:
        worst = max(worst, 1.0)  # a class unit for an entity without D_derive rows
    return worst


def min_pairwise_distance(points) -> float:
    """The smallest Euclidean distance between two different points of a list."""
    best = math.inf
    for i in range(len(points)):
        for j in range(i + 1, len(points)):
            best = min(best, math.sqrt(sum((a - b) ** 2 for a, b in zip(points[i], points[j]))))
    return best


def independent_fit(world, context, derive_ids):
    """The whole PCM fit of SPEC section 5 step 3 on the feature rows of derive_ids (ordered by row id), from the
    prototypes: (centers, number of iterations, converged flag, degenerate flag). The fit is degenerate if the smallest
    distance between two fitted centers is below 0.5 times the smallest distance between two prototypes (S-3)."""
    derive = set(derive_ids)
    rows = sorted((r for r in world.feature_rows if r.row_id in derive), key=lambda r: r.row_id)
    points = [list(map(float, r.x)) for r in rows]
    centers, iterations, converged = pcm_centers(points, context.prototypes, context.eta, context.m, context.max_iter,
                                                 context.tol)
    prototypes = [list(map(float, c)) for c in context.prototypes]
    degenerate = min_pairwise_distance(centers) < 0.5 * min_pairwise_distance(prototypes)
    return centers, iterations, converged, degenerate
