"""A small System abstraction: the pipeline steps that checks call, so that the same check runs on the fixed
system (tesaron as it is) or on a faulty twin (audit/twins) that overrides exactly one step.

Twins never change tesaron/; they subclass System and replace or wrap one method.
"""

from __future__ import annotations

from dataclasses import replace

from tesaron.belnap import interface_facts
from tesaron.criterion.metrics import compute_metrics_for_exact
from tesaron.decoder import decode
from tesaron.encoder import encode as tesaron_encode
from tesaron.encoder import encode_from_rows as tesaron_encode_from_rows


class System:
    """The fixed system: tesaron v0.1 with revisions S-1..S-7, unchanged."""

    name = "fixed"

    # ---- encoder -------------------------------------------------------------------------------------------
    def encode(self, world, context):
        return self._post_encoding(tesaron_encode(world, context), world, context)

    def encode_rows(self, world, context, derive_ids, validate_ids):
        """Re-encode with a given split (G3). Twins that change the encoder apply the same change here."""
        return self._post_encoding(
            tesaron_encode_from_rows(world, context, derive_ids, validate_ids), world, context
        )

    def _post_encoding(self, encoding, world, context):
        return encoding

    # ---- interface and decoder -----------------------------------------------------------------------------
    def interface_facts(self, units, alpha):
        return interface_facts(units, alpha)

    def decode(self, facts, rules, vocab, k):
        return decode(facts, rules, vocab, k)

    # ---- one configuration ---------------------------------------------------------------------------------
    def evaluate_exact(self, world, context, encoding, alpha, k):
        """(decoder output, metrics, exact metrics) of configuration (alpha, k); the exact metrics are the
        fractions.Fraction companions of tesaron.criterion.compute_metrics_exact."""
        ctx = replace(context, alpha=alpha, k_abduction=k)
        facts = self.interface_facts(encoding.units, alpha)
        out = self.decode(facts, ctx.rules, ctx.vocabulary, k)
        m, ex = compute_metrics_for_exact(world, ctx, encoding, out)
        return out, m, ex

    def evaluate(self, world, context, encoding, alpha, k):
        """(decoder output, metrics) of configuration (alpha, k)."""
        return self.evaluate_exact(world, context, encoding, alpha, k)[:2]

    def evaluate_grid(self, world, context, encoding, grid):
        """{(alpha, k): (output, metrics, exact metrics)} for every configuration of the grid."""
        return {(a, k): self.evaluate_exact(world, context, encoding, a, k) for a, k in grid}


FIXED = System()
