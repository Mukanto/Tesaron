"""F2: an independent computation of H (PREREG section 6.1).

A brute-force closure: every rule is applied to every assignment of entities to its variables until nothing changes.
This file does not import tesaron.decoder. Rules are read by attribute only (rule.id, rule.head, rule.body; a literal
has .pred, .args and .channel, whose name is "POS" or "NEG"), so it works on the world's own rule objects.

Facts are tuples (channel_name, pred, args).
"""

from __future__ import annotations

import itertools


def _is_var(arg: str) -> bool:
    return arg[:1].isupper()


def _ground(literal, theta) -> tuple:
    args = tuple(theta[a] if _is_var(a) else a for a in literal.args)
    return (literal.channel.name, literal.pred, args)


def brute_force_closure(seed_facts, rules, vocab_atoms, entities) -> set:
    """Least fixpoint of the rules over seed_facts. vocab_atoms: iterable of (pred, args); entities: names."""
    vocab = {(a.pred, tuple(a.args)) for a in vocab_atoms}
    facts = {(ch, pred, tuple(args)) for ch, pred, args in seed_facts if (pred, tuple(args)) in vocab}
    entities = list(entities)
    changed = True
    while changed:
        changed = False
        for rule in rules:
            variables = sorted({a for lit in (rule.head, *rule.body) for a in lit.args if _is_var(a)})
            for values in itertools.product(entities, repeat=len(variables)):
                theta = dict(zip(variables, values))
                if all(_ground(lit, theta) in facts for lit in rule.body):
                    head = _ground(rule.head, theta)
                    if (head[1], head[2]) in vocab and head not in facts:
                        facts.add(head)
                        changed = True
    return facts


def independent_H(E_atoms, truth, rules, vocab_atoms, entities) -> list[tuple]:
    """H as a sorted list of (pred, args): atoms outside E that appear, in either channel, in the closure seeded
    with POS a for every a in E with W(a) = T and NEG a for every a in E with W(a) = F."""
    e_keys = {(a.pred, tuple(a.args)) for a in E_atoms}
    seeds = {("POS" if truth(a) else "NEG", a.pred, tuple(a.args)) for a in E_atoms}
    closure = brute_force_closure(seeds, rules, vocab_atoms, entities)
    return sorted({(pred, args) for _, pred, args in closure if (pred, args) not in e_keys})


def closure_fact_keys(facts, rules, vocab_atoms, entities) -> set:
    """Brute-force closure of facts given as (channel, atom) tuples (channel an enum with a .name, atom with .pred and
    .args), returned as (channel name, pred, args) keys."""
    seeds = {(ch.name, a.pred, tuple(a.args)) for ch, a in facts}
    return brute_force_closure(seeds, rules, vocab_atoms, entities)
