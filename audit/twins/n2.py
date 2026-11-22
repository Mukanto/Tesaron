"""N2: the encoder's permutation does not come from the context seed (G2)."""

from __future__ import annotations

from dataclasses import replace

from audit.system import System
from tesaron.encoder import encode as tesaron_encode


class N2(System):
    """N2: selection and split use a seed that is not the context's (real run: two derived seeds, seed("n2", 2i)
    and seed("n2", 2i + 1); gate: rng-drawn, a different seed on every call)."""

    name = "N2"

    def __init__(self, source) -> None:
        self.source = source

    def encode(self, world, context):
        return self._post_encoding(
            tesaron_encode(world, replace(context, encoder_seed=self.source.draw_seed())), world, context
        )
