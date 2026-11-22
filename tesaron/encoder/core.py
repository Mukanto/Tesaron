"""Encoder (SPEC section 5): sampling, split, PCM, entity typicality, meaning units."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from tesaron.atoms import Atom, class_pred
from tesaron.degrees import Membership, tconorm_max
from tesaron.encoder.context import Context
from tesaron.encoder.pcm import PCMFit, pcm_fit, typicality
from tesaron.enums import Channel, ComputationalStatus, EpistemicStatus
from tesaron.meaning import MeaningUnit


@dataclass(frozen=True)
class Encoding:
    selected_ids: tuple[str, ...]
    derive_ids: tuple[str, ...]
    validate_ids: tuple[str, ...]
    fit: PCMFit
    units: dict[Atom, MeaningUnit]  # keyed by atom, sorted
    validation_units: dict[Atom, MeaningUnit]  # from D_validate, same fitted centers; descriptive only


def _check_degrees(context: Context) -> None:
    for source in sorted(context.support):
        if not isinstance(context.support[source], Membership):
            raise TypeError(
                f"support degree of {source!r} must be a Membership, got {type(context.support[source]).__name__}"
            )


def _build_units(world, context: Context, row_ids: frozenset[str], fit: PCMFit) -> dict[Atom, MeaningUnit]:
    centers = np.array(fit.centers, dtype=float)
    eta = np.array(context.eta, dtype=float)
    class_status = EpistemicStatus.OBSERVED if fit.usable else ComputationalStatus.NOT_COMPUTED
    units: dict[Atom, MeaningUnit] = {}

    # Class atoms: an entity with no feature row in the set gets no class units.
    rows_by_entity: dict[str, list] = {}
    for fr in sorted(world.feature_rows, key=lambda r: r.row_id):
        if fr.row_id in row_ids:
            rows_by_entity.setdefault(fr.entity, []).append(fr)
    for entity in sorted(rows_by_entity):
        rows = rows_by_entity[entity]
        xbar = np.mean(np.array([r.x for r in rows], dtype=float), axis=0)
        u = typicality(xbar[None, :], centers, eta, context.m)[0]  # not normalized
        for k in range(len(centers)):
            atom = Atom(class_pred(k), (entity,))
            units[atom] = MeaningUnit(
                atom=atom,
                mu_pos=Membership(float(u[k])),
                # FORBIDDEN: computing mu_neg from mu_pos (e.g. 1 - mu_pos). Low typicality is absence of
                # evidence, not refutation. A class unit's mu_neg is a fixed 0 whatever mu_pos is.
                mu_neg=Membership(0.0),
                provenance=tuple(r.row_id for r in rows),
                status=class_status,
            )

    # Relation atoms: only if the atom has at least one report in the set.
    pos: dict[Atom, list] = {}
    neg: dict[Atom, list] = {}
    ids: dict[Atom, list[str]] = {}
    for rr in sorted(world.report_rows, key=lambda r: r.row_id):
        if rr.row_id not in row_ids or rr.atom not in context.vocabulary:
            continue
        ids.setdefault(rr.atom, []).append(rr.row_id)
        target = pos if rr.polarity is Channel.POS else neg
        target.setdefault(rr.atom, []).append(context.support[rr.source])
    for atom in sorted(ids):
        units[atom] = MeaningUnit(
            atom=atom,
            mu_pos=tconorm_max(*pos.get(atom, [])),
            mu_neg=tconorm_max(*neg.get(atom, [])),
            provenance=tuple(ids[atom]),
            status=EpistemicStatus.OBSERVED,
        )
    return {a: units[a] for a in sorted(units)}


def encode(world, context: Context) -> Encoding:
    """Sampling, split, PCM on D_derive only, entity typicality, meaning units, validation units."""
    _check_degrees(context)
    rng = np.random.Generator(np.random.PCG64(context.encoder_seed))

    # 1. Selection.
    all_ids = sorted([r.row_id for r in world.feature_rows] + [r.row_id for r in world.report_rows])
    n_total = len(all_ids)
    n_sel = round(context.sampling_ratio * n_total)
    perm = rng.permutation(n_total)
    selected = sorted(all_ids[int(i)] for i in perm[:n_sel])

    # 2. Split.
    n = len(selected)
    perm2 = rng.permutation(n)
    n_der = round(context.derive_fraction * n)
    derive = sorted(selected[int(i)] for i in perm2[:n_der])
    validate = sorted(selected[int(i)] for i in perm2[n_der:])
    derive_set, validate_set = frozenset(derive), frozenset(validate)

    # 3. PCM on the feature rows of D_derive only.
    feats = [r for r in sorted(world.feature_rows, key=lambda r: r.row_id) if r.row_id in derive_set]
    if not feats:
        raise ValueError("no feature rows in D_derive")
    x = np.array([r.x for r in feats], dtype=float)
    fit = pcm_fit(
        x,
        np.array(context.prototypes, dtype=float),
        np.array(context.eta, dtype=float),
        context.m,
        context.max_iter,
        context.tol,
    )

    # 4-6. Units from D_derive; validation units from D_validate with the same fitted centers (no refit).
    units = _build_units(world, context, derive_set, fit)
    validation_units = _build_units(world, context, validate_set, fit)
    return Encoding(tuple(selected), tuple(derive), tuple(validate), fit, units, validation_units)
