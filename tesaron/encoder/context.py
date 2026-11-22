"""Context: the encoder's and decoder's parameters, "the awareness" (SPEC section 4)."""

from __future__ import annotations

from dataclasses import dataclass

from tesaron.atoms import Atom
from tesaron.decoder.datalog import Rule
from tesaron.degrees import Membership, support_degrees_from_world

__all__ = ["Context", "support_degrees_from_world"]


@dataclass(frozen=True)
class Context:
    entities: tuple[str, ...]
    vocabulary: frozenset[Atom]
    prototypes: tuple[tuple[float, ...], ...]  # PCM initial centers
    eta: tuple[float, ...]  # one per class, fixed (2 * sigma^2, revision S-2)
    m: float  # fuzzifier
    max_iter: int
    tol: float
    support: dict[str, Membership]  # source -> support degree
    rules: tuple[Rule, ...]  # in v0.1 the decoder is given the true rules
    alpha: float  # one threshold (author decision A-3)
    k_abduction: int
    sampling_ratio: float
    derive_fraction: float
    encoder_seed: int
    epsilon_band: float

    @staticmethod
    def from_world(
        world,
        encoder_seed: int,
        *,
        eta: float | None = None,
        m: float = 2.0,
        max_iter: int = 1000,
        tol: float = 1e-6,
        alpha: float = 0.7,
        k_abduction: int = 5,
        sampling_ratio: float = 0.8,
        derive_fraction: float = 0.7,
        epsilon_band: float = 0.05,
    ) -> "Context":
        """Default context for a world (SPEC section 4 defaults).

        eta defaults to 2 * sigma**2 per class (revision S-2), sigma being the world's feature noise.
        """
        p = world.params
        if eta is None:
            eta = 2.0 * p.feature_sigma**2
        return Context(
            entities=world.entities,
            vocabulary=world.vocabulary,
            prototypes=p.prototypes(),
            eta=tuple(float(eta) for _ in range(p.n_classes)),
            m=m,
            max_iter=max_iter,
            tol=tol,
            support=support_degrees_from_world(world),
            rules=world.rules,
            alpha=alpha,
            k_abduction=k_abduction,
            sampling_ratio=sampling_ratio,
            derive_fraction=derive_fraction,
            encoder_seed=encoder_seed,
            epsilon_band=epsilon_band,
        )
