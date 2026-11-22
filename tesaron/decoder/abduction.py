"""Single-step abduction (SPEC section 7.3, step 2; author decision A-4)."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Iterable

from tesaron.atoms import Atom
from tesaron.decoder.datalog import (
    Fact,
    Rule,
    _match,
    build_index,
    instantiate,
    is_variable,
    match_literals,
)
from tesaron.enums import Channel


@dataclass(frozen=True)
class Candidate:
    fact: Fact  # the missing literal as (channel, atom)
    score: int  # number of distinct (rule_id, theta) instances it completes
    instances: tuple[tuple[str, tuple[str, ...]], ...]  # (rule_id, theta values in sorted-variable order)


def ranked_candidates(
    f1: Iterable[Fact],
    observed: Iterable[Fact],
    rules: Iterable[Rule],
    vocab: frozenset[Atom],
) -> list[Candidate]:
    """All abduction candidates over the pass-1 fixpoint F1, ranked.

    For every rule and every ground substitution theta such that
      - the head under theta is an OBSERVED fact of F1,
      - exactly one body literal (by position) is missing from F1 and all the others are present,
      - the missing literal is fully ground (bound by the head or by the present body literals),
      - its atom is in the vocabulary,
      - its atom has neither a POS nor a NEG fact in F1 (value U),
    the candidate is the missing literal as (channel, atom). No existential guessing.
    Score = number of distinct (rule_id, theta) instances; ranking = score descending, then
    (channel, pred, args) ascending.
    """
    f1_set = set(f1)
    observed_set = set(observed)
    idx = build_index(f1_set)
    obs_idx = build_index(observed_set)
    instances: dict[Fact, set[tuple[str, tuple[str, ...]]]] = defaultdict(set)

    for rule in sorted(rules, key=lambda r: r.id):
        vs = rule.variables()
        head = rule.head
        for head_atom in obs_idx.get((head.channel, head.pred), ()):
            theta0 = _match(head, head_atom, {})
            if theta0 is None:
                continue
            for j, missing in enumerate(rule.body):
                others = rule.body[:j] + rule.body[j + 1 :]
                for theta in match_literals(others, lambda i: idx, theta0):
                    if any(is_variable(a) and a not in theta for a in missing.args):
                        continue  # not fully ground
                    atom = instantiate(missing, theta)
                    if atom not in vocab:
                        continue
                    if (missing.channel, atom) in f1_set:
                        continue  # not missing
                    if (Channel.POS, atom) in f1_set or (Channel.NEG, atom) in f1_set:
                        continue  # value is not U
                    if any(v not in theta for v in vs):
                        continue
                    instances[(missing.channel, atom)].add((rule.id, tuple(theta[v] for v in vs)))

    cands = [
        Candidate(fact=fact, score=len(inst), instances=tuple(sorted(inst)))
        for fact, inst in instances.items()
    ]
    cands.sort(key=lambda c: (-c.score, int(c.fact[0]), c.fact[1].pred, c.fact[1].args))
    return cands


def abduce(
    f1: Iterable[Fact],
    observed: Iterable[Fact],
    rules: Iterable[Rule],
    vocab: frozenset[Atom],
    k: int,
) -> list[Candidate]:
    """The top-k candidates. With k = 0 there is no abduction."""
    if k < 0:
        raise ValueError("k_abduction must be >= 0")
    if k == 0:
        return []
    return ranked_candidates(f1, observed, rules, vocab)[:k]
