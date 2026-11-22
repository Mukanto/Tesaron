"""Two-channel Datalog (SPEC sections 7.1 and 7.2).

Body literals use strong negation: a POS literal means "a POS fact is present", a NEG literal means
"a NEG fact is present". There is no negation as failure. A POS and a NEG fact for the same atom may
coexist (value B); nothing else follows from that.

Determinism: rules are processed sorted by id; the substitutions of a rule are processed in sorted
order (variables sorted by name, bindings compared lexicographically). Derivations are searched in
rounds (all derivations of a round see the facts at the start of the round), so the first derivation
of a fact is: earliest round, then smallest rule id, then smallest substitution. Naive and
semi-naive evaluation therefore give identical results and identical derivation records.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Iterable, Mapping

from tesaron.atoms import Atom
from tesaron.enums import Channel

Fact = tuple[Channel, Atom]
Record = tuple[str, tuple[Fact, ...]]  # (rule_id, premise facts in body order)


def is_variable(arg: str) -> bool:
    """A variable is a string starting with an uppercase letter; anything else is an entity constant."""
    return bool(arg) and arg[0].isupper()


@dataclass(frozen=True)
class Literal:
    pred: str
    args: tuple[str, ...]
    channel: Channel = Channel.POS

    def __post_init__(self) -> None:
        object.__setattr__(self, "args", tuple(self.args))
        if any(not isinstance(a, str) or a == "" for a in self.args):
            raise ValueError("literal arguments must be non-empty strings")
        if not isinstance(self.channel, Channel):
            raise TypeError("channel must be a Channel")

    def variables(self) -> tuple[str, ...]:
        """Distinct variables in order of first occurrence."""
        seen: list[str] = []
        for a in self.args:
            if is_variable(a) and a not in seen:
                seen.append(a)
        return tuple(seen)


@dataclass(frozen=True)
class Rule:
    id: str
    head: Literal
    body: tuple[Literal, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "body", tuple(self.body))
        body_vars = {v for lit in self.body for v in lit.variables()}
        missing = [v for v in self.head.variables() if v not in body_vars]
        if missing:
            raise ValueError(
                f"unsafe rule {self.id}: head variables {missing} do not occur in the body"
            )

    def variables(self) -> tuple[str, ...]:
        """All variables of the rule, sorted by name."""
        vs = set(self.head.variables())
        for lit in self.body:
            vs.update(lit.variables())
        return tuple(sorted(vs))


def instantiate(lit: Literal, theta: Mapping[str, str]) -> Atom:
    """Atom of a literal under a substitution (all its variables must be bound)."""
    return Atom(lit.pred, tuple(theta[a] if is_variable(a) else a for a in lit.args))


def _match(lit: Literal, atom: Atom, theta: Mapping[str, str]) -> dict[str, str] | None:
    if atom.pred != lit.pred or len(atom.args) != len(lit.args):
        return None
    new = dict(theta)
    for pa, ca in zip(lit.args, atom.args):
        if is_variable(pa):
            bound = new.get(pa)
            if bound is None:
                new[pa] = ca
            elif bound != ca:
                return None
        elif pa != ca:
            return None
    return new


Index = dict[tuple[Channel, str], list[Atom]]


def build_index(facts: Iterable[Fact]) -> Index:
    """(channel, pred) -> sorted list of atoms."""
    idx: Index = defaultdict(list)
    for ch, atom in sorted(facts):
        idx[(ch, atom.pred)].append(atom)
    return idx


def match_literals(
    literals: tuple[Literal, ...],
    index_of,
    theta: Mapping[str, str],
) -> list[dict[str, str]]:
    """All substitutions extending theta that make every literal present.

    index_of(i) gives the Index the i-th literal is matched against.
    """
    results: list[dict[str, str]] = []

    def extend(i: int, th: Mapping[str, str]) -> None:
        if i == len(literals):
            results.append(dict(th))
            return
        lit = literals[i]
        for atom in index_of(i).get((lit.channel, lit.pred), ()):
            t = _match(lit, atom, th)
            if t is not None:
                extend(i + 1, t)

    extend(0, theta)
    return results


def _sorted_unique_substitutions(
    rule: Rule, thetas: list[dict[str, str]]
) -> list[tuple[str, ...]]:
    vs = rule.variables()
    return sorted({tuple(t[v] for v in vs) for t in thetas})


def ground_instances(rule: Rule, facts: Iterable[Fact]) -> list[dict[str, str]]:
    """All ground instances (substitutions) of the rule whose body is present in facts, sorted."""
    idx = build_index(facts)
    vs = rule.variables()
    subs = _sorted_unique_substitutions(rule, match_literals(rule.body, lambda i: idx, {}))
    return [dict(zip(vs, s)) for s in subs]


@dataclass(frozen=True)
class EvalResult:
    facts: frozenset[Fact]
    records: dict[Fact, Record]  # first derivation of each fact that was not in the input
    rounds: int


def _check_rules(rules: Iterable[Rule]) -> list[Rule]:
    rs = sorted(rules, key=lambda r: r.id)
    for a, b in zip(rs, rs[1:]):
        if a.id == b.id:
            raise ValueError(f"duplicate rule id {a.id!r}")
    return rs


def _fixpoint(
    facts: Iterable[Fact], rules: Iterable[Rule], vocab: Iterable[Atom] | frozenset[Atom], seminaive: bool
) -> EvalResult:
    vocab_set = vocab if isinstance(vocab, (set, frozenset)) else frozenset(vocab)
    rs = _check_rules(rules)
    current: set[Fact] = {f for f in facts if f[1] in vocab_set}
    records: dict[Fact, Record] = {}
    delta: set[Fact] = set(current)
    bound = 2 * len(vocab_set) + 1
    rounds = 0
    first = True
    while True:
        rounds += 1
        full_idx = build_index(current)
        delta_idx = build_index(delta) if seminaive else None
        new: dict[Fact, Record] = {}
        for rule in rs:
            vs = rule.variables()
            if seminaive:
                if not rule.body:
                    thetas = [{}] if first else []
                else:
                    thetas = []
                    for d in range(len(rule.body)):
                        thetas.extend(
                            match_literals(
                                rule.body,
                                lambda i, d=d: delta_idx if i == d else full_idx,
                                {},
                            )
                        )
            else:
                thetas = match_literals(rule.body, lambda i: full_idx, {})
            for sub in _sorted_unique_substitutions(rule, thetas):
                theta = dict(zip(vs, sub))
                head_atom = instantiate(rule.head, theta)
                fact = (rule.head.channel, head_atom)
                if head_atom not in vocab_set or fact in current or fact in new:
                    continue
                new[fact] = (
                    rule.id,
                    tuple((lit.channel, instantiate(lit, theta)) for lit in rule.body),
                )
        if not new:
            break
        current.update(new)
        records.update(new)
        delta = set(new)
        first = False
        if rounds > bound:
            raise AssertionError("fixpoint exceeded the termination bound 2*|vocab|+1")
    if rounds > bound:
        raise AssertionError("fixpoint exceeded the termination bound 2*|vocab|+1")
    return EvalResult(frozenset(current), records, rounds)


def naive_eval_with_records(facts, rules, vocab) -> EvalResult:
    return _fixpoint(facts, rules, vocab, seminaive=False)


def seminaive_eval_with_records(facts, rules, vocab) -> EvalResult:
    return _fixpoint(facts, rules, vocab, seminaive=True)


def naive_eval(facts, rules, vocab) -> set[Fact]:
    """Least fixpoint as a set of (channel, atom); derived atoms outside the vocabulary are discarded."""
    return set(naive_eval_with_records(facts, rules, vocab).facts)


def seminaive_eval(facts, rules, vocab) -> set[Fact]:
    """Same result as naive_eval, computed semi-naively."""
    return set(seminaive_eval_with_records(facts, rules, vocab).facts)
