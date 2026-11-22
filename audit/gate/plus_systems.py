"""The gate's plus-world systems (PREREG section 6.3). The oracle (audit/oracle.py) is the plus system of G7a;
NoPropagation is the plus system of G8: abduction whose pass 2 adds the hypotheses, which are U atoms, and does not
deduce, so no encoded atom can change. They exist only in the gate studies (and the oracle as G7a's anchor)."""

from __future__ import annotations

from audit.oracle import Oracle  # noqa: F401
from audit.system import System
from audit.twins._decode_variant import decode_variant


class NoPropagation(System):
    name = "no-propagation"

    def decode(self, facts, rules, vocab, k):
        return decode_variant(facts, rules, vocab, k, propagate=False)
