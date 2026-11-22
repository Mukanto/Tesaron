"""N5: PCM is fitted on D_derive union D_validate (G5)."""

from __future__ import annotations

from dataclasses import replace

import numpy as np

from audit.system import System
from tesaron.encoder import encode as tesaron_encode
from tesaron.encoder import encode_from_rows as tesaron_encode_from_rows
from tesaron.encoder.core import _build_units
from tesaron.encoder.pcm import pcm_fit


def _refit_on_union(world, context, encoding):
    union = frozenset(encoding.derive_ids) | frozenset(encoding.validate_ids)
    feats = [r for r in sorted(world.feature_rows, key=lambda r: r.row_id) if r.row_id in union]
    fit = pcm_fit(
        np.array([r.x for r in feats], dtype=float),
        np.array(context.prototypes, dtype=float),
        np.array(context.eta, dtype=float),
        context.m,
        context.max_iter,
        context.tol,
    )
    units = _build_units(world, context, frozenset(encoding.derive_ids), fit)
    vunits = _build_units(world, context, frozenset(encoding.validate_ids), fit)
    return replace(encoding, fit=fit, units=units, validation_units=vunits)


class N5(System):
    name = "N5"

    def encode(self, world, context):
        return _refit_on_union(world, context, tesaron_encode(world, context))

    def encode_rows(self, world, context, derive_ids, validate_ids):
        return _refit_on_union(world, context, tesaron_encode_from_rows(world, context, derive_ids, validate_ids))
