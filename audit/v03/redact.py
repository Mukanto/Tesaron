"""The redaction boundary of the development runner (PREREG_v0.3 section 2, "no pilot").

On v0.3 worlds, development worlds included, nothing may be printed, written or returned to anyone that reveals
  - new_false or new_true values,
  - a T-1 outcome or a G8 outcome (per world or aggregated), T-1's structure arm (including its "largest increase"),
  - a verdict-table row for T-1,
  - draw-sensitivity verdicts, or the I-2, I-6, I-7, I-8 and I-9 outcomes.
(G7b's hypervolume is a function of 1 - new_false and is withheld too. G1-G7a outcomes, their twins, the all_true arm,
definedness counts, tau values (the I-8 tau included), the denominators n_q of new_false and the four feasibility metrics of
calibration worlds may be shown.)

`redact(doc)` is the ONLY path from the in-memory results of a development run to the console or to a file: it returns a
deep copy in which every forbidden field is the string "REDACTED". It works on the key names of the runner's documents
(`is_forbidden_key`) and replaces whole verdict-table rows of T-1 and G8. `find_violations` is the independent scan that the
runner and the tests use on the result.
"""

from __future__ import annotations

import re

REDACTED = "REDACTED"
FORBIDDEN_KEY_EXACT = {"T-1", "G8", "NT", "N8", "new_false", "new_true"}
# a key whose lower-case form starts with one of these (t1_all_points, g8_whole_grid, draw_sensitivity, ...) or contains one
FORBIDDEN_KEY_PREFIX = ("t1", "g8", "draw_sens", "structure", "largest", "i2", "i6", "i7", "i8", "i9", "g7b", "hyp",
                        "expected", "undefined_as_fails", "n_hypotheses")
FORBIDDEN_KEY_PART = ("new_false", "new_true", "wrong_class", "sources_spanned", "increase")
VERDICT_ROW_TESTS = ("T-1", "G8")
# the one phrase of the fixed G7a sentence (PREREG 4, R1-3) that names new_true as a definition, not as a value; it is removed
# from a string before the scan looks for the word
ALLOWED_PHRASES = ("by the definition of new_true",)
_FRAC = re.compile(r"-?\d+/\d+")


def is_forbidden_key(key) -> bool:
    k = str(key)
    if k in FORBIDDEN_KEY_EXACT:
        return True
    low = k.lower()
    return low.startswith(FORBIDDEN_KEY_PREFIX) or any(p in low for p in FORBIDDEN_KEY_PART)


def redact(obj):
    """A deep copy of obj (dicts, lists, tuples, scalars) with every forbidden field replaced by "REDACTED"."""
    if isinstance(obj, dict):
        if obj.get("test") in VERDICT_ROW_TESTS and "verdict" in obj:  # a verdict-table row of T-1 or G8
            return {"test": obj["test"], "verdict_row": REDACTED}
        return {str(k): (REDACTED if is_forbidden_key(k) else redact(v)) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [redact(v) for v in obj]
    return obj


def find_violations(obj, path: str = "") -> list:
    """Paths in obj that a redacted document must not have: a forbidden key whose value is not "REDACTED", a verdict-table
    row of T-1 or G8 that is not collapsed, or a string that names new_false or new_true."""
    bad = []
    if isinstance(obj, dict):
        if obj.get("test") in VERDICT_ROW_TESTS and "verdict" in obj:
            bad.append(f"{path}: an un-redacted verdict row of {obj['test']}")
        for k, v in obj.items():
            here = f"{path}/{k}"
            if is_forbidden_key(k):
                if v != REDACTED:
                    bad.append(here)
            else:
                bad += find_violations(v, here)
    elif isinstance(obj, (list, tuple)):
        for i, v in enumerate(obj):
            bad += find_violations(v, f"{path}[{i}]")
    elif isinstance(obj, str):
        text = obj
        for phrase in ALLOWED_PHRASES:
            text = text.replace(phrase, "")
        if "new_false" in text or "new_true" in text or "T-1 holds" in text or "T-1 does not hold" in text \
                or "T-1 is not demonstrated" in text or "G8 (descriptive" in text:
            bad.append(f"{path}: a string that states a forbidden quantity")
    return bad


def redact_checked(doc):
    """redact(doc), then the scan; raises if anything slipped through (which would be a bug in this module)."""
    out = redact(doc)
    bad = find_violations(out)
    if bad:
        raise AssertionError("redaction boundary leaks: " + "; ".join(bad[:5]))
    return out
