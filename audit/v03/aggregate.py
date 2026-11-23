"""From worlds to a test verdict, and the fixed wording of PREREG_v0.3 sections 3.3 and 4.

Deterministic tests (G1-G7a): HOLDS if no defined world FAILS and at least 16 are defined; one FAILS world fails the test
(A-8) even with fewer than 16 defined; otherwise "insufficient worlds". T-1 (the only quantitative test): "insufficient
worlds" with fewer than 16 defined worlds, otherwise HOLDS iff the one-sided 95% Wilson lower bound of the HOLDS share among
the defined worlds is at least 0.80. G8 has no verdict in v0.3: its descriptive sentence is built by `g8_descriptive`.

The wording is PREREG section 4's, verbatim; the tests compare the constants below with the PREREG text.
"""

from __future__ import annotations

from audit.aggregate import (  # reused unchanged from v0.2
    CLAIMS as V02_CLAIMS, DETERMINISTIC_NOTE, LABEL, LIMITATION, MIN_DEFINED, WILSON_THRESHOLD, Z_95_ONE_SIDED, hypothesis_summary,
    wilson_lower,
)

DETERMINISTIC_TESTS = ("G1", "G2", "G3", "G4", "G5", "G6", "G7")  # G7 is G7a
QUANTITATIVE_TESTS = ("T-1",)
# G7a's claim is narrowed to four baselines (PREREG 1 and 3.2, author decision 2026-11-23); every other claim is v0.2's
# T-1's claim states the one-atom floor (PREREG 1 and 3.2, R1-1, R2-1): it is the claim column of 3.2 without its trailing
# parenthesis
CLAIMS = {**V02_CLAIMS,
          "G7": "None of four degenerate baselines of SPEC §10 (echo, all_false, all_unknown, all_both) gets "
                "a positive score under the wisdom criterion",
          "T-1": "Within the reasonable bounds, admitting weaker evidence does not increase the share of new false "
                 "conclusions by more than δ or by one wrong conclusion, whichever is larger"}
EXPECTED_PARAGRAPH = (
    "Expected verdict: none. No pilot was run on v0.3 worlds before the freeze (PREREG v0.3 §2). Known factors point "
    "both ways (PREREG v0.3 §2). v0.2's T-1, on worlds with three discrete sources, failed. v0.3 changes the worlds, the "
    "τ rule, the configuration of calibration and feasibility, and T-1's tolerance together, so an outcome that differs "
    "from v0.2's cannot be attributed to the new worlds alone; the I-8 arm applies v0.2's full rule to the v0.3 worlds."
)
# PREREG section 4 (R1-3): printed with every G7a verdict; "(at α <levels>)" is omitted when no world scored
G7A_TEMPLATE = (
    "all_true, not judged, was feasible and scored > 0 on <n> of <N> test worlds (at α <levels>); echo, all_unknown and "
    "all_both score 0 by the definition of new_true, so among the four judged baselines only all_false can be excluded by the "
    "constraints."
)
G7A_PAREN = " (at α <levels>)"
NO_TAU = "NO_TAU"  # the per-world outcome under a draw-sensitivity set that has no tau (PREREG 7, R1-14)
T1_HOLDS_SENTENCE = (
    "A HOLDS on worlds whose feasible range spans few sources compares few steps; see the structure counts."
)
MEAN_NOTE = "(the mean of the two middle values)"
N_SOURCES = 8


def median_of(values: list) -> tuple[str, bool]:
    """(median as text, even count). The median of an even count is the mean of the two middle values, a whole or a
    half number, printed as a decimal."""
    vals = sorted(int(v) for v in values)
    mid = len(vals) // 2
    twice = 2 * vals[mid] if len(vals) % 2 else vals[mid - 1] + vals[mid]
    return (f"{twice // 2}" if twice % 2 == 0 else f"{twice // 2}.5"), len(vals) % 2 == 0


def structure_counts(outcomes: list, structure: list) -> dict:
    """Counts of the structure arm over the worlds whose T-1 outcome is defined. structure[i] is the structure dict
    (`audit.v03.checks.t1_structure`) of the world of outcomes[i]."""
    if len(structure) != len(outcomes):
        raise ValueError("structure and outcomes must describe the same worlds")
    rows = [s for (_, o), s in zip(outcomes, structure) if o != "UNDEFINED"]
    if any(not s["defined"] for s in rows):
        raise ValueError("a world with a defined T-1 outcome must have a defined structure")
    spans = [s["sources_spanned"] for s in rows]
    out = {"n": len(rows), "median": None, "even": None, "min": None, "max": None,
           "n_with_wrong_class_atom": sum(s["wrong_class_atoms_spanned"] >= 1 for s in rows),
           "sources_spanned": spans}
    if rows:
        out["median"], out["even"] = median_of(spans)
        out["min"], out["max"] = min(spans), max(spans)
    return out


def structure_sentence(c: dict) -> str:
    head = "In these worlds T-1 compares graded steps of evidence admission at k = 0: "
    if not c["n"]:
        return head + "there is no defined world, so no feasible α range was spanned."
    note = f" {MEAN_NOTE}" if c["even"] else ""
    return (
        head + f"over the {c['n']} defined worlds, the feasible α range spanned a median of {c['median']}{note} of the "
        f"{N_SOURCES} source reliabilities (minimum {c['min']}, maximum {c['max']}), and on "
        f"{c['n_with_wrong_class_atom']} of them it admitted at least one world-false class atom."
    )


def t1_verdict_of(outcomes: list) -> str:
    """The T-1 verdict (HOLDS, FAILS, INSUFFICIENT) of a list of per-world outcome strings."""
    holds = sum(o == "HOLDS" for o in outcomes)
    defined = holds + sum(o == "FAILS" for o in outcomes)
    if defined < MIN_DEFINED:
        return "INSUFFICIENT"
    return "HOLDS" if wilson_lower(holds, defined) >= WILSON_THRESHOLD else "FAILS"


def draw_sensitivity_counts(per_draw_outcomes: list) -> dict:
    """T-1's verdict under each alternative tau: per_draw_outcomes[b] is the list of the 50 per-world outcomes under tau b.
    Counts HOLDS, FAILS and "insufficient worlds" over the draws and the range of the number of defined worlds. A draw whose
    calibration set had no tau (its outcomes are NO_TAU, R1-14) counts as "insufficient worlds" and has no number of defined
    worlds: it is left out of the range and counted in "n_no_tau"."""
    no_tau = [any(x == NO_TAU for x in o) for o in per_draw_outcomes]
    verdicts = ["INSUFFICIENT" if nt else t1_verdict_of(o) for nt, o in zip(no_tau, per_draw_outcomes)]
    defined = [None if nt else sum(x != "UNDEFINED" for x in o) for nt, o in zip(no_tau, per_draw_outcomes)]
    counted = [d for d in defined if d is not None]
    return {
        "n_draws": len(per_draw_outcomes),
        "holds": verdicts.count("HOLDS"), "fails": verdicts.count("FAILS"),
        "insufficient": verdicts.count("INSUFFICIENT"), "n_no_tau": sum(no_tau),
        "defined_min": min(counted) if counted else None, "defined_max": max(counted) if counted else None,
        "verdicts": verdicts, "defined": defined,
    }


def draw_sensitivity_sentence(d: dict) -> str:
    return (
        f"Under {d['n_draws']} further calibration draws, T-1's verdict was HOLDS {d['holds']} times, FAILS "
        f"{d['fails']} times and 'insufficient worlds' {d['insufficient']} times (descriptive)."
    )


def g7a_sentence(summary: dict) -> str:
    """The fixed G7a sentence (PREREG 4, R1-3) from `all_true_summary`: the number n of test worlds on which all_true was
    feasible and scored > 0, the number N of test worlds, and the alpha levels at which it scored on some world, in
    decreasing order (two decimals); with n = 0 the parenthesis is omitted."""
    n, total = summary["n_worlds_scoring"], summary["n_worlds"]
    levels = ", ".join(f"{float(a):.2f}" for a in sorted(summary["scoring_by_alpha"], key=float, reverse=True))
    text = G7A_TEMPLATE if n else G7A_TEMPLATE.replace(G7A_PAREN, "")
    return text.replace("<n>", str(n)).replace("<N>", str(total)).replace("<levels>", levels)


def aggregate_test(test_id: str, outcomes: list, detector_both: int | None = None, failed_parts: dict | None = None,
                   structure: list | None = None, draw_sensitivity: dict | None = None,
                   all_true: dict | None = None) -> dict:
    """Verdict of one test from [(world_seed, "HOLDS" | "FAILS" | "UNDEFINED"), ...] in draw order (G1-G7a and T-1).
    structure and draw_sensitivity are required for T-1 (PREREG 4: their sentences go with every T-1 verdict), and
    all_true (`all_true_summary`) for G7a (R1-3: its sentence goes with every G7a verdict)."""
    if test_id not in DETERMINISTIC_TESTS + QUANTITATIVE_TESTS:
        raise ValueError(f"no verdict for test {test_id!r}")
    for _, o in outcomes:
        if o not in ("HOLDS", "FAILS", "UNDEFINED"):
            raise ValueError(f"bad outcome {o!r}")
    if test_id == "T-1" and (structure is None or draw_sensitivity is None):
        raise ValueError("T-1 needs the per-world structure and the draw-sensitivity counts")
    if test_id == "G7" and all_true is None:
        raise ValueError("G7a needs the all_true summary")
    ident = LABEL.get(test_id, test_id)
    n_holds = sum(o == "HOLDS" for _, o in outcomes)
    n_fails = sum(o == "FAILS" for _, o in outcomes)
    n_undefined = sum(o == "UNDEFINED" for _, o in outcomes)
    n_defined = n_holds + n_fails
    first_fail = next((s for s, o in outcomes if o == "FAILS"), None)  # outcomes are in draw order
    lower = wilson_lower(n_holds, n_defined) if test_id in QUANTITATIVE_TESTS and n_defined else None
    if test_id in DETERMINISTIC_TESTS:
        verdict = "FAILS" if n_fails > 0 else ("HOLDS" if n_defined >= MIN_DEFINED else "INSUFFICIENT")
    elif n_defined < MIN_DEFINED:
        verdict = "INSUFFICIENT"
    else:
        verdict = "HOLDS" if lower >= WILSON_THRESHOLD else "FAILS"

    claim = CLAIMS[test_id]
    if verdict == "INSUFFICIENT":
        text = f"{ident}: insufficient worlds ({n_defined} defined, {MIN_DEFINED} required); no verdict."
    elif test_id in DETERMINISTIC_TESTS:
        if verdict == "HOLDS":
            text = (f"{ident} holds: {claim}, in all {n_defined} defined test worlds ({n_undefined} undefined). "
                    f"{DETERMINISTIC_NOTE}")
        else:
            text = (f"{ident} does not hold: {n_fails} of {n_defined} defined test worlds fail; the first failing "
                    f"world is {first_fail}.")
            if test_id == "G1" and failed_parts and failed_parts.get(first_fail):
                text += f" Failed parts in the first failing world: {', '.join(failed_parts[first_fail])}."
    else:
        b = f"{lower:.3f}"
        if verdict == "HOLDS":
            text = (f"{ident} holds on at least 80% of worlds (one-sided Wilson bound, approximately 95%): {claim}. "
                    f"{n_holds} of {n_defined} defined worlds hold (Wilson lower bound {b}, threshold 0.80); "
                    f"{n_undefined} undefined.")
        else:
            text = (f"{ident} is not demonstrated: {n_holds} of {n_defined} defined worlds hold (Wilson lower bound {b}, "
                    f"threshold 0.80); this does not show that the per-world rate is below 0.80; {n_undefined} "
                    f"undefined; the first failing world is {first_fail}.")
    counts = struct_text = ds_text = g7a_text = None
    if test_id == "G7":  # the all_true sentence goes with every G7a verdict, "insufficient worlds" included
        g7a_text = g7a_sentence(all_true)
        text += " " + g7a_text
    if test_id == "T-1":  # the additional sentences go with every T-1 verdict, "insufficient worlds" included
        counts = structure_counts(outcomes, structure)
        struct_text = structure_sentence(counts)
        ds_text = draw_sensitivity_sentence(draw_sensitivity)
        text += " " + struct_text + " " + ds_text
        if verdict == "HOLDS":
            text += " " + T1_HOLDS_SENTENCE
    qualifier = None
    if verdict == "HOLDS" and detector_both:
        qualifier = f"the detector did not separate on {detector_both} worlds"
        text += f" ({qualifier})"
    return {
        "test": test_id, "id": ident, "verdict": verdict, "n_holds": n_holds, "n_fails": n_fails,
        "n_undefined": n_undefined, "n_defined": n_defined, "wilson_lower": lower, "first_failing_world": first_fail,
        "text": text, "expected_paragraph": EXPECTED_PARAGRAPH if test_id in QUANTITATIVE_TESTS else None,
        "detector_qualifier": qualifier, "structure": counts, "structure_text": struct_text,
        "draw_sensitivity": draw_sensitivity if test_id == "T-1" else None, "draw_sensitivity_text": ds_text,
        "all_true": all_true if test_id == "G7" else None, "all_true_text": g7a_text,
        "limitation": LIMITATION,
    }


def g8_descriptive(outcomes: list, hyp_counts: list, single_atom_only: list) -> dict:
    """G8, in the descriptive section only (no verdict): the HOLDS share among the defined worlds with its Wilson lower
    bound, the number of worlds that fail only through single-atom changes (v0.2 I-6), and the minimum, median and maximum
    of SPEC section 8's hyp_count at (alpha0, k = 10) over the defined worlds."""
    n_holds = sum(o == "HOLDS" for _, o in outcomes)
    n_fails = sum(o == "FAILS" for _, o in outcomes)
    n_undefined = sum(o == "UNDEFINED" for _, o in outcomes)
    n_defined = n_holds + n_fails
    lower = wilson_lower(n_holds, n_defined) if n_defined else None
    text = (f"G8 (descriptive, no verdict): {n_holds} of {n_defined} defined worlds hold (Wilson lower bound "
            f"{'n/a' if lower is None else f'{lower:.3f}'}); {n_undefined} undefined.")
    hyp = hypothesis_summary(outcomes, hyp_counts)
    return {"n_holds": n_holds, "n_fails": n_fails, "n_undefined": n_undefined, "n_defined": n_defined,
            "wilson_lower": lower, "text": text, "hyp_count": hyp,
            "failing_only_through_single_atom_changes": sum(x is True for x in single_atom_only)}


def all_true_summary(arms: list) -> dict:
    """The all_true descriptive arm over the worlds (PREREG 3.2): arms[i] is `audit.v03.checks.all_true_arm` of world i.
    The number of worlds where all_true is feasible and scores > 0 at some alpha, and for each alpha level the number of
    worlds where it does so at that level. Never part of a verdict."""
    levels = sorted({a for arm in arms for a in arm["scoring_alphas"]}, reverse=True)
    return {"n_worlds": len(arms), "n_worlds_scoring": sum(bool(arm["scores"]) for arm in arms),
            "n_worlds_feasible": sum(bool(arm["feasible_alphas"]) for arm in arms),
            "scoring_by_alpha": {str(a): sum(a in arm["scoring_alphas"] for arm in arms) for a in levels}}


def undefined_as_fails(outcomes: list) -> dict:
    """Descriptive: the Wilson share with UNDEFINED worlds counted as FAILS."""
    n = len(outcomes)
    holds = sum(o == "HOLDS" for _, o in outcomes)
    return {"n_holds": holds, "n": n, "wilson_lower": wilson_lower(holds, n) if n else None}


def verdict_table(per_test: dict, detector_both: dict | None = None, failed_parts: dict | None = None,
                  structure: list | None = None, draw_sensitivity: dict | None = None,
                  all_true: dict | None = None) -> dict:
    """PREREG 4's table: one row per test with a verdict (G1-G7a and T-1), no combined verdict, the limitation sentence
    next to every verdict. G8 is not a row (it is descriptive)."""
    detector_both = detector_both or {}
    rows = [
        aggregate_test(t, per_test[t], detector_both.get(t), failed_parts if t == "G1" else None,
                       structure if t == "T-1" else None, draw_sensitivity if t == "T-1" else None,
                       all_true if t == "G7" else None)
        for t in (*DETERMINISTIC_TESTS, *QUANTITATIVE_TESTS)
    ]
    return {"rows": rows, "limitation": LIMITATION}


__all__ = ["CLAIMS", "DETERMINISTIC_TESTS", "EXPECTED_PARAGRAPH", "G7A_TEMPLATE", "LIMITATION", "MIN_DEFINED", "NO_TAU",
           "QUANTITATIVE_TESTS",
           "T1_HOLDS_SENTENCE", "Z_95_ONE_SIDED", "aggregate_test", "all_true_summary", "draw_sensitivity_counts",
           "draw_sensitivity_sentence", "g7a_sentence", "g8_descriptive", "structure_counts", "structure_sentence", "t1_verdict_of",
           "undefined_as_fails", "verdict_table", "wilson_lower"]
