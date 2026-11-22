"""Sources of the non-canonical behaviour of the twins N2 and N4.

No source uses system entropy. N2 (real run): PairSource, two derived seeds that do not come from the context
(seed("n2", 2i) and seed("n2", 2i + 1) for test world i). N4 (real run): SetOrderSource, the iteration order of a Python
set of strings, which depends on PYTHONHASHSEED and so differs between processes. Gate: RngSource, drawn from the
study's own rng on every call, so that two evaluations with the same rng give identical data (gate check K6) while
repeated runs inside one data sample still differ.
"""

from __future__ import annotations

import numpy as np


class PairSource:
    """Real run, N2: alternates between two fixed seeds that are not the context's seed."""

    def __init__(self, seed_a: int, seed_b: int) -> None:
        self.seeds = (seed_a, seed_b)
        self.calls = 0

    def draw_seed(self) -> int:
        s = self.seeds[self.calls % 2]
        self.calls += 1
        return s


class SetOrderSource:
    """Real run, N4: positions of keys in the iteration order of a Python set of strings."""

    def order(self, keys: list[str]) -> list[int]:
        iteration = list(set(keys))
        position = {k: i for i, k in enumerate(iteration)}
        return [position[k] for k in keys]


class RngSource:
    """Gate: every call draws fresh values from the study's rng."""

    def __init__(self, rng: np.random.Generator) -> None:
        self.rng = rng

    def draw_seed(self) -> int:
        return int(self.rng.integers(0, 2**31 - 1))

    def order(self, keys: list[str]) -> list[int]:
        return [int(i) for i in self.rng.permutation(len(keys))]
