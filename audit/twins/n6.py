"""N6: hypotheses are inserted with status OBSERVED (G6)."""

from __future__ import annotations

from audit.system import System
from audit.twins._decode_variant import decode_variant
from tesaron.enums import EpistemicStatus


class N6(System):
    name = "N6"

    def decode(self, facts, rules, vocab, k):
        return decode_variant(facts, rules, vocab, k, hyp_status=EpistemicStatus.OBSERVED)
