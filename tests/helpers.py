"""Shared test helpers. Seeds used anywhere in the tests lie in 900000..900999 (SPEC section 11)."""

from __future__ import annotations

import itertools

import numpy as np

from tesaron.atoms import Atom
from tesaron.decoder.datalog import Literal, Rule, instantiate
from tesaron.enums import Channel


def rng_for(seed: int) -> np.random.Generator:
    assert 900000 <= seed <= 900999
    return np.random.Generator(np.random.PCG64(seed))


def A(pred: str, *args: str) -> Atom:
    return Atom(pred, tuple(args))


def pos(pred: str, *args: str):
    return (Channel.POS, A(pred, *args))


def neg(pred: str, *args: str):
    return (Channel.NEG, A(pred, *args))


def L(pred: str, *args: str, ch: Channel = Channel.POS) -> Literal:
    return Literal(pred, tuple(args), ch)


def brute_instances(rule: Rule, true_atoms, entities) -> list[dict[str, str]]:
    """Independent brute-force enumeration of ground instances with a true (POS) body."""
    vs = rule.variables()
    out = []
    for values in itertools.product(entities, repeat=len(vs)):
        theta = dict(zip(vs, values))
        if all(instantiate(lit, theta) in true_atoms for lit in rule.body):
            out.append(theta)
    return out


def brute_closure(start_atoms, positive_rules, entities, vocab) -> set[Atom]:
    """Independent least model by repeated brute-force instance enumeration."""
    true = set(start_atoms)
    while True:
        new = set()
        for rule in positive_rules:
            for theta in brute_instances(rule, true, entities):
                head = instantiate(rule.head, theta)
                if head in vocab and head not in true:
                    new.add(head)
        if not new:
            return true
        true |= new
