"""Canonical hashes of encodings and decoder outputs, and numeric encodings of hashes for check data."""

from __future__ import annotations

import numpy as np

from tesaron.serialize import canonical_hash


def encoding_payload(enc) -> dict:
    return {
        "selected": list(enc.selected_ids),
        "derive": list(enc.derive_ids),
        "validate": list(enc.validate_ids),
        "fit": enc.fit,
        "units": enc.units,
        "validation_units": enc.validation_units,
    }


def encoding_hash(enc) -> str:
    """Canonical hash (tesaron.serialize) of everything an Encoding holds."""
    return canonical_hash(encoding_payload(enc))


def output_payload(out) -> dict:
    facts = []
    for (ch, atom), info in out.facts.items():
        deriv = None
        if info.derivation is not None:
            rid, prem = info.derivation
            deriv = [rid, [[int(c), str(a)] for c, a in prem]]
        facts.append(
            [int(ch), str(atom), int(info.status), list(info.provenance), deriv, info.score]
        )
    hyps = [[int(c.fact[0]), str(c.fact[1]), c.score, [[rid, list(th)] for rid, th in c.instances]] for c in out.hypotheses]
    return {"facts": facts, "hypotheses": hyps, "rounds": list(out.rounds)}


def output_hash(out) -> str:
    """Canonical hash of a DecoderOutput: facts with status, provenance, derivation and score, hypotheses, rounds."""
    return canonical_hash(output_payload(out))


def hash_to_array(hex_digest: str) -> np.ndarray:
    """First 16 bytes of a hex SHA-256 as two uint64 values, so that equality can be tested on numeric arrays."""
    b = bytes.fromhex(hex_digest)[:16]
    return np.array([int.from_bytes(b[:8], "big"), int.from_bytes(b[8:], "big")], dtype=np.uint64)
