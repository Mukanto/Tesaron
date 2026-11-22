"""Decoder: two passes and output (SPEC sections 7.3 and 7.4)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping

from tesaron.atoms import Atom
from tesaron.decoder.abduction import Candidate, abduce
from tesaron.decoder.datalog import Fact, Record, Rule, seminaive_eval_with_records
from tesaron.enums import Belnap, Channel, EpistemicStatus


@dataclass(frozen=True)
class FactInfo:
    status: EpistemicStatus
    provenance: tuple[str, ...] = ()  # row ids, for OBSERVED facts
    derivation: Record | None = None  # (rule_id, premises), for DERIVED and pass-2 HYPOTHESIS facts
    score: int | None = None  # abduction score, for abduced hypotheses


_EPISTEMIC_FOR_VERDICT = (EpistemicStatus.OBSERVED, EpistemicStatus.DERIVED)


class DecoderOutput:
    """For every vocabulary atom: facts per channel (with status and provenance or derivation),
    full(a) from all facts, verdict(a) from OBSERVED and DERIVED facts only."""

    def __init__(
        self,
        facts: Mapping[Fact, FactInfo],
        hypotheses: tuple[Candidate, ...] = (),
        rounds: tuple[int, int] = (0, 0),
    ) -> None:
        self.facts: dict[Fact, FactInfo] = {f: facts[f] for f in sorted(facts)}
        self.hypotheses = tuple(hypotheses)
        self.rounds = rounds
        full: dict[Atom, list[bool]] = {}
        verdict: dict[Atom, list[bool]] = {}
        for (ch, atom), info in self.facts.items():
            full.setdefault(atom, [False, False])[int(ch)] = True
            if info.status in _EPISTEMIC_FOR_VERDICT:
                verdict.setdefault(atom, [False, False])[int(ch)] = True
        self._full = {a: Belnap.from_channels(*v) for a, v in full.items()}
        self._verdict = {a: Belnap.from_channels(*v) for a, v in verdict.items()}

    def full(self, atom: Atom) -> Belnap:
        return self._full.get(atom, Belnap.U)

    def verdict(self, atom: Atom) -> Belnap:
        return self._verdict.get(atom, Belnap.U)

    def facts_of(self, atom: Atom) -> dict[Channel, FactInfo]:
        return {ch: self.facts[(ch, atom)] for ch in Channel if (ch, atom) in self.facts}

    def status_of(self, channel: Channel, atom: Atom) -> EpistemicStatus | None:
        info = self.facts.get((channel, atom))
        return None if info is None else info.status


def decode(
    interface_facts: Mapping[Fact, tuple[str, ...]],
    rules: Iterable[Rule],
    vocab: frozenset[Atom],
    k_abduction: int,
) -> DecoderOutput:
    """Pass 1 (deduction), single-step abduction (cap k_abduction), pass 2 (deduction with hypotheses)."""
    rules = tuple(rules)
    observed = {f: prov for f, prov in interface_facts.items() if f[1] in vocab}

    # Pass 1: new facts DERIVED; a fact both observed and derived keeps OBSERVED.
    r1 = seminaive_eval_with_records(observed, rules, vocab)
    infos: dict[Fact, FactInfo] = {}
    for fact in r1.facts:
        if fact in observed:
            infos[fact] = FactInfo(EpistemicStatus.OBSERVED, provenance=tuple(observed[fact]))
        else:
            infos[fact] = FactInfo(EpistemicStatus.DERIVED, derivation=r1.records[fact])

    # Abduction over F1.
    cands = abduce(r1.facts, observed, rules, vocab, k_abduction)
    if not cands:
        return DecoderOutput(infos, (), (r1.rounds, 0))

    # Pass 2: deduce again from F1 plus the hypotheses; facts new in pass 2 are HYPOTHESIS.
    hyp_facts = {c.fact: c for c in cands}
    r2 = seminaive_eval_with_records(set(r1.facts) | set(hyp_facts), rules, vocab)
    for fact in r2.facts:
        if fact in infos:
            continue
        if fact in hyp_facts:
            infos[fact] = FactInfo(EpistemicStatus.HYPOTHESIS, score=hyp_facts[fact].score)
        else:
            infos[fact] = FactInfo(EpistemicStatus.HYPOTHESIS, derivation=r2.records[fact])
    return DecoderOutput(infos, tuple(cands), (r1.rounds, r2.rounds))
