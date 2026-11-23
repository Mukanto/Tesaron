"""Fidelity controls F1, F2 and F4 of Tesaron v0.3 (PREREG_v0.3 section 6.1) on test worlds and on calibration worlds.

On a test world all three controls are v0.2's (`audit.fidelity`), over the whole grid. On a calibration world F2 and F4 are
the same, and F1 is restricted to the two configurations the calibration reads, (alpha0, 0) and (alpha0, k0): the same
comparison as `audit.fidelity.f1_details`, over those configurations only.
"""

from __future__ import annotations

from audit.checks import ALPHA0, K0
from audit.fidelity import _keys, _status_map, f2_check, f4_check, run_controls
from audit.indep import closure_fact_keys, enumerate_candidates, top_k
from audit.indep.h_closure import brute_force_closure
from audit.system import FIXED
from tesaron.decoder import naive_eval_with_records, ranked_candidates, seminaive_eval_with_records

CAL_ALPHAS = (ALPHA0,)
CAL_KS = (0, K0)


def f1_restricted(rec, alphas=CAL_ALPHAS, ks=CAL_KS) -> tuple[bool, str]:
    """F1 over the configurations alphas x ks: the decoder's pass-1 and pass-2 fact sets, statuses and abduction candidate
    lists against the independent closure and enumerator, and naive against semi-naive evaluation."""
    ctx, world = rec.context, rec.world
    rules, vocab, entities = tuple(ctx.rules), ctx.vocabulary, world.entities
    for alpha in alphas:
        facts = FIXED.interface_facts(rec.encoding.units, alpha)
        observed = _keys(facts)
        pass1 = closure_fact_keys(set(facts), rules, vocab, entities)
        ranked = enumerate_candidates(pass1, observed, rules, vocab, entities)
        r1 = seminaive_eval_with_records(set(facts), rules, vocab)
        dec_ranked = [((c.fact[0].name, c.fact[1].pred, tuple(c.fact[1].args)), c.score)
                      for c in ranked_candidates(r1.facts, set(facts), rules, vocab)]
        if dec_ranked != [(fact, score) for score, fact in ranked]:
            return False, f"alpha={alpha}: the ranked candidate list (with scores) differs from the independent enumeration"
        for k in ks:
            out = FIXED.decode(facts, rules, vocab, k)
            kept = top_k(ranked, k)
            hyp = [((c.fact[0].name, c.fact[1].pred, tuple(c.fact[1].args)), c.score) for c in out.hypotheses]
            if hyp != [(fact, score) for score, fact in kept]:
                return False, f"alpha={alpha} k={k}: the kept top-k candidates differ from the independent enumeration"
            pass2 = brute_force_closure(pass1 | {fact for _, fact in kept}, rules, vocab, entities)
            if _keys(out.facts) != pass2:
                return False, f"alpha={alpha} k={k}: the decoder's facts differ from the brute-force closure"
            expected = {key: ("OBSERVED" if key in observed else "DERIVED" if key in pass1 else "HYPOTHESIS")
                        for key in pass2}
            if _status_map(out) != expected:
                return False, f"alpha={alpha} k={k}: a fact status differs from the independent classification"
        inputs = [("pass1", set(facts))]
        if top_k(ranked, ks[-1]):
            inputs.append(("pass2", set(r1.facts) | {c.fact for c in
                                                     ranked_candidates(r1.facts, set(facts), rules, vocab)[:ks[-1]]}))
        for name, start in inputs:
            a, b = naive_eval_with_records(start, rules, vocab), seminaive_eval_with_records(start, rules, vocab)
            if a.facts != b.facts or a.records != b.records:
                return False, f"alpha={alpha} {name}: naive and semi-naive evaluation differ"
    return True, ""


def run_controls_test_world(rec) -> dict:
    """{"F1": (ok, detail), "F2": ..., "F4": ...}, F1 over the whole grid."""
    return run_controls(rec)


def run_controls_calibration_world(rec) -> dict:
    """Same keys; F1 only at (alpha0, 0) and (alpha0, k0)."""
    return {"F1": f1_restricted(rec), "F2": f2_check(rec), "F4": f4_check(rec)}
