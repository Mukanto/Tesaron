"""A copy of tesaron.decoder.decode.decode with the places the decoder twins and the gate's plus systems change made
explicit: the candidates, the status of the hypotheses, and whether pass 2 deduces.

The fixed system never uses this function (it calls tesaron.decoder.decode directly).
"""

from __future__ import annotations

from tesaron.decoder.abduction import ranked_candidates
from tesaron.decoder.datalog import seminaive_eval_with_records
from tesaron.decoder.decode import DecoderOutput, FactInfo
from tesaron.enums import EpistemicStatus


def decode_variant(
    interface_facts,
    rules,
    vocab,
    k_abduction,
    *,
    candidates_fn=ranked_candidates,
    hyp_status=EpistemicStatus.HYPOTHESIS,
    propagate=True,
) -> DecoderOutput:
    """Pass 1 (deduction), candidates (top k of candidates_fn), pass 2. With propagate=False pass 2 only adds the
    hypotheses as facts and does not deduce, so no fact of pass 1 can be changed by them."""
    rules = tuple(rules)
    observed = {f: prov for f, prov in interface_facts.items() if f[1] in vocab}
    r1 = seminaive_eval_with_records(observed, rules, vocab)
    infos = {}
    for fact in r1.facts:
        if fact in observed:
            infos[fact] = FactInfo(EpistemicStatus.OBSERVED, provenance=tuple(observed[fact]))
        else:
            infos[fact] = FactInfo(EpistemicStatus.DERIVED, derivation=r1.records[fact])
    cands = [] if k_abduction == 0 else list(candidates_fn(r1.facts, observed, rules, vocab))[:k_abduction]
    if not cands:
        return DecoderOutput(infos, (), (r1.rounds, 0))
    hyp_facts = {c.fact: c for c in cands}
    if not propagate:
        for fact, c in hyp_facts.items():
            if fact not in infos:
                infos[fact] = FactInfo(hyp_status, score=c.score)
        return DecoderOutput(infos, tuple(cands), (r1.rounds, 0))
    r2 = seminaive_eval_with_records(set(r1.facts) | set(hyp_facts), rules, vocab)
    for fact in r2.facts:
        if fact in infos:
            continue
        if fact in hyp_facts:
            infos[fact] = FactInfo(hyp_status, score=hyp_facts[fact].score)
        else:
            infos[fact] = FactInfo(EpistemicStatus.HYPOTHESIS, derivation=r2.records[fact])
    return DecoderOutput(infos, tuple(cands), (r1.rounds, r2.rounds))
