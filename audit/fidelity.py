"""Fidelity controls F1, F2 and F4 on one world (PREREG section 6.1). F3 is done after the run by a fresh agent.

F1  decoder: pass-1 and pass-2 fact sets and their statuses against the brute-force closure of audit.indep at every grid
    configuration; the full ranked abduction candidate list with scores and the kept top-k against the independent
    enumeration (audit.indep.abduction); the pass-2 input is built from the independently enumerated hypotheses, not
    from the decoder's; naive against semi-naive evaluation.
F2  H against a brute-force closure.
F4  PCM centers and class-unit mu_pos to 1e-12; the PCM converged flag, iteration count and degenerate flag (recomputed
    from SPEC section 5 step 3), the class units' provenance and status, the relation units (degrees, with the support
    degrees taken from the world's source reliabilities, and provenance) and the interface facts of all units at
    every alpha, exactly.
"""

from __future__ import annotations

from audit.checks import ALPHAS, KS
from audit.indep import (
    closure_fact_keys,
    compare_class_units,
    compare_interface_facts,
    compare_relation_units,
    enumerate_candidates,
    independent_fit,
    independent_H,
    max_center_difference,
    max_mu_difference,
    top_k,
)
from audit.indep.h_closure import brute_force_closure
from audit.system import FIXED
from tesaron.criterion.metrics import compute_H
from tesaron.decoder import naive_eval_with_records, ranked_candidates, seminaive_eval_with_records

F4_TOLERANCE = 1e-12
MAX_PROBLEMS = 5


def _keys(fact_iter) -> set:
    return {(ch.name, atom.pred, tuple(atom.args)) for ch, atom in fact_iter}


def _status_map(out) -> dict:
    return {(ch.name, atom.pred, tuple(atom.args)): info.status.name for (ch, atom), info in out.facts.items()}


def f1_details(rec) -> dict:
    """The F1 comparison with counts: {"ok": bool, "detail": str, "n_configs": int, "n_candidate_lists": int,
    "n_candidates": int} (the counts are what was compared)."""
    ctx, world = rec.context, rec.world
    rules, vocab = tuple(ctx.rules), ctx.vocabulary
    entities = world.entities
    n_configs = n_lists = n_cands = 0

    def fail(msg):
        return {"ok": False, "detail": msg, "n_configs": n_configs, "n_candidate_lists": n_lists,
                "n_candidates": n_cands}

    for alpha in ALPHAS:
        facts = FIXED.interface_facts(rec.encoding.units, alpha)
        observed = _keys(facts)
        pass1 = closure_fact_keys(set(facts), rules, vocab, entities)
        ranked = enumerate_candidates(pass1, observed, rules, vocab, entities)

        # the decoder's full ranked list, computed over the decoder's own pass-1 fixpoint
        r1 = seminaive_eval_with_records(set(facts), rules, vocab)
        dec_ranked = [((c.fact[0].name, c.fact[1].pred, tuple(c.fact[1].args)), c.score)
                      for c in ranked_candidates(r1.facts, set(facts), rules, vocab)]
        indep_ranked = [(fact, score) for score, fact in ranked]
        n_lists += 1
        n_cands += len(indep_ranked)
        if dec_ranked != indep_ranked:
            return fail(f"alpha={alpha}: the ranked candidate list (with scores) differs from the independent "
                        f"enumeration ({len(dec_ranked)} against {len(indep_ranked)} candidates)")

        for k in KS:
            out = FIXED.decode(facts, rules, vocab, k)
            n_configs += 1
            kept = top_k(ranked, k)
            hyp = [((c.fact[0].name, c.fact[1].pred, tuple(c.fact[1].args)), c.score) for c in out.hypotheses]
            if hyp != [(fact, score) for score, fact in kept]:
                return fail(f"alpha={alpha} k={k}: the kept top-k candidates differ from the independent enumeration")
            # pass 2 from the INDEPENDENT hypotheses
            pass2 = brute_force_closure(pass1 | {fact for _, fact in kept}, rules, vocab, entities)
            if _keys(out.facts) != pass2:
                return fail(f"alpha={alpha} k={k}: the decoder's facts differ from the brute-force closure "
                            f"(pass 1 plus the independent hypotheses)")
            expected = {}
            for key in pass2:
                expected[key] = ("OBSERVED" if key in observed else "DERIVED" if key in pass1 else "HYPOTHESIS")
            if _status_map(out) != expected:
                return fail(f"alpha={alpha} k={k}: a fact status differs from the independent classification")
        # naive against semi-naive on the pass-1 input and on the pass-2 input at the largest k
        inputs = [("pass1", set(facts))]
        kept10 = top_k(ranked, KS[-1])
        if kept10:
            inputs.append(("pass2", set(r1.facts) | {c.fact for c in ranked_candidates(r1.facts, set(facts), rules,
                                                                                         vocab)[:KS[-1]]}))
        for name, start in inputs:
            a = naive_eval_with_records(start, rules, vocab)
            b = seminaive_eval_with_records(start, rules, vocab)
            if a.facts != b.facts or a.records != b.records:
                return fail(f"alpha={alpha} {name}: naive and semi-naive evaluation differ")
    return {"ok": True, "detail": "", "n_configs": n_configs, "n_candidate_lists": n_lists, "n_candidates": n_cands}


def f1_check(rec) -> tuple[bool, str]:
    d = f1_details(rec)
    return d["ok"], d["detail"]


def f2_check(rec) -> tuple[bool, str]:
    """H from tesaron.criterion.metrics.compute_H versus the separate brute-force closure (audit.indep)."""
    world, enc = rec.world, rec.encoding
    atoms = sorted(enc.units)
    ours = [(a.pred, tuple(a.args)) for a in compute_H(atoms, world.truth, world.rules, world.vocabulary)]
    theirs = independent_H(atoms, world.truth, world.rules, world.vocabulary, world.entities)
    if sorted(ours) != sorted(theirs):
        return False, f"H differs: {len(ours)} atoms against {len(theirs)}"
    return True, ""


def f4_values(rec) -> tuple[float, float]:
    """(largest center difference, largest class-unit mu_pos difference) against the independent loop."""
    enc = rec.encoding
    return (
        max_center_difference(rec.world, rec.context, enc.derive_ids, enc.fit.centers),
        max_mu_difference(rec.world, rec.context, enc.derive_ids, enc.fit.centers, enc.units),
    )


def f4_details(rec) -> dict:
    """Every F4 comparison of one world: the two largest differences, whether the relation units (degrees and provenance,
    D_derive and D_validate) are exactly equal, and whether the interface facts of all units at every alpha are exactly
    equal; with the problems found (at most a few)."""
    enc, ctx, world = rec.encoding, rec.context, rec.world
    centers, mu = f4_values(rec)
    problems = []
    _, iterations, converged, degenerate = independent_fit(world, ctx, enc.derive_ids)
    flags_equal = (iterations, converged, degenerate) == (enc.fit.n_iter, enc.fit.converged, enc.fit.degenerate)
    if not flags_equal:
        problems.append(f"PCM flags: iterations {enc.fit.n_iter}, converged {enc.fit.converged}, degenerate "
                        f"{enc.fit.degenerate} against {iterations}, {converged}, {degenerate}")
    usable = converged and not degenerate
    cls = compare_class_units(world, enc.derive_ids, world.params.n_classes, usable, enc.units)
    rel = compare_relation_units(world, enc.derive_ids, ctx.vocabulary, enc.units)
    rel_val = compare_relation_units(world, enc.validate_ids, ctx.vocabulary, enc.validation_units)
    iface = []
    for alpha in ALPHAS:
        iface += compare_interface_facts(enc.units, alpha, FIXED.interface_facts(enc.units, alpha))
    if not centers <= F4_TOLERANCE:
        problems.append(f"PCM centers differ by {centers}")
    if not mu <= F4_TOLERANCE:
        problems.append(f"class-unit mu_pos differs by {mu}")
    problems += [f"class units: {p}" for p in cls[:MAX_PROBLEMS]]
    problems += [f"relation units: {p}" for p in rel[:MAX_PROBLEMS]]
    problems += [f"validation relation units: {p}" for p in rel_val[:MAX_PROBLEMS]]
    problems += [f"interface facts: {p}" for p in iface[:MAX_PROBLEMS]]
    return {
        "max_center_difference": centers,
        "max_mu_pos_difference": mu,
        "pcm_flags_equal": flags_equal,
        "class_units_equal": not cls,
        "n_class_units": sum(1 for a in enc.units if a.pred.startswith("c")),
        "relation_units_equal": not rel and not rel_val,
        "n_relation_units": sum(1 for a in enc.units if not a.pred.startswith("c")),
        "interface_facts_equal": not iface,
        "n_interface_fact_sets": len(ALPHAS),
        "problems": problems,
        "ok": not problems,
    }


def f4_check(rec) -> tuple[bool, str]:
    """PCM centers and class-unit mu_pos of tesaron against the separate loop in audit.indep, to 1e-12; relation units
    and interface facts, exactly."""
    d = f4_details(rec)
    return d["ok"], "; ".join(d["problems"])


def run_controls(rec) -> dict:
    """{"F1": (ok, detail), "F2": ..., "F4": ...}"""
    return {"F1": f1_check(rec), "F2": f2_check(rec), "F4": f4_check(rec)}
