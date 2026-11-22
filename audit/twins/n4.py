"""N4: abduction breaks ties by an order that is not canonical (G4)."""

from __future__ import annotations

from audit.system import System
from audit.twins._decode_variant import decode_variant
from audit.twins._source import SetOrderSource
from tesaron.decoder.abduction import ranked_candidates


class N4(System):
    """N4: among candidates with equal score the order is taken from a non-canonical source (real run: the
    iteration order of a Python set of strings; gate: a fresh rng-drawn order on every call). The score order
    itself is kept, so only ties, and therefore the cut at k_abduction, are affected."""

    name = "N4"

    def __init__(self, source=None) -> None:
        self.source = source if source is not None else SetOrderSource()

    def _candidates(self, f1, observed, rules, vocab):
        cands = ranked_candidates(f1, observed, rules, vocab)
        out = []
        i = 0
        while i < len(cands):
            j = i
            while j < len(cands) and cands[j].score == cands[i].score:
                j += 1
            group = cands[i:j]
            keys = [f"{int(c.fact[0])}|{c.fact[1]}" for c in group]
            order = self.source.order(keys)
            out.extend(c for _, c in sorted(zip(order, group), key=lambda t: t[0]))
            i = j
        return out

    def decode(self, facts, rules, vocab, k):
        return decode_variant(facts, rules, vocab, k, candidates_fn=self._candidates)
