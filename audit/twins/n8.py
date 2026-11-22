"""N8: abduction overwrites observations (G8)."""

from __future__ import annotations

from audit.system import System
from audit.twins._decode_variant import decode_variant
from tesaron.decoder.abduction import Candidate
from tesaron.enums import Channel


def overwrite_candidates(facts, k: int) -> tuple[list[Candidate], list]:
    """The first min(k, n) observed facts of decided encoded atoms (canonical order of the facts; n = their number)
    and, for each, the opposite-channel fact. A decided atom has exactly one observed channel (T or F)."""
    channels: dict = {}
    for ch, atom in facts:
        channels.setdefault(atom, set()).add(ch)
    decided = sorted(f for f in facts if len(channels[f[1]]) == 1)
    chosen = decided[:k]
    return [Candidate(fact=(Channel.NEG if ch is Channel.POS else Channel.POS, atom), score=1, instances=())
            for ch, atom in chosen], chosen


class N8(System):
    """N8: at every k > 0 the first min(k, n) observed facts of decided encoded atoms are removed from the
    observations and the opposite-channel fact is added with status HYPOTHESIS; deduction then runs as usual
    (propagate=True), or not at all in the gate's plus-world variant (propagate=False). With k = 0 nothing happens.
    It acts on every world that has decided encoded atoms."""

    name = "N8"

    def __init__(self, propagate: bool = True) -> None:
        self.propagate = propagate

    def decode(self, facts, rules, vocab, k):
        if k == 0:
            return decode_variant(facts, rules, vocab, 0, propagate=self.propagate)
        cands, chosen = overwrite_candidates(facts, k)
        kept = {f: p for f, p in facts.items() if f not in set(chosen)}
        return decode_variant(kept, rules, vocab, k, candidates_fn=lambda *a: cands, propagate=self.propagate)
