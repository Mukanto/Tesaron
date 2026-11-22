"""F1: an independent enumeration of the abduction candidates (PREREG section 6.1, SPEC section 7.3).

A brute-force enumerator: every rule is grounded over EVERY assignment of entities to its variables, with no joins and
no index. It follows the text of SPEC section 7.3 literally and does not import tesaron.decoder, tesaron.encoder or
tesaron.belnap. Rules are read by attribute only (rule.id, rule.head, rule.body; a literal has .pred, .args and
.channel, whose name is "POS" or "NEG"); atoms by .pred and .args.

Facts are tuples (channel_name, pred, args). The candidates over the pass-1 fixpoint F1 are those instances (rule, theta)
for which
  - the head under theta is an OBSERVED fact of F1;
  - exactly one body literal is missing from F1 and all the others are present;
  - the missing literal is fully ground by the head and the present body literals: a variable that occurs only in the
    missing literal excludes the instance (no existential guessing);
  - the atom of the missing literal is in the vocabulary;
  - the atom of the missing literal has neither a POS nor a NEG fact in F1.
The candidate is the missing literal as a fact. Its score is the number of distinct (rule id, theta). The ranking is
score descending, then (channel, pred, args) ascending, with POS before NEG (SPEC section 1: Channel POS = 0, NEG = 1).
"""

from __future__ import annotations

import itertools

CHANNEL_RANK = {"POS": 0, "NEG": 1}


def _is_var(arg: str) -> bool:
    return arg[:1].isupper()


def _vars(literal) -> set:
    return {a for a in literal.args if _is_var(a)}


def _ground(literal, theta) -> tuple:
    args = tuple(theta[a] if _is_var(a) else a for a in literal.args)
    return (literal.channel.name, literal.pred, args)


def enumerate_candidates(f1, observed, rules, vocab_atoms, entities) -> list:
    """The ranked candidates over F1 as a list of (score, fact), fact = (channel_name, pred, args).

    f1: the pass-1 fixpoint as fact keys; observed: the OBSERVED facts as fact keys (a subset of f1); vocab_atoms:
    iterable of atoms; entities: the entity names that variables range over."""
    f1 = set(f1)
    observed = set(observed)
    vocab = {(a.pred, tuple(a.args)) for a in vocab_atoms}
    entities = list(entities)
    instances: dict = {}
    for rule in rules:
        variables = sorted({a for lit in (rule.head, *rule.body) for a in lit.args if _is_var(a)})
        head_vars = _vars(rule.head)
        for values in itertools.product(entities, repeat=len(variables)):
            theta = dict(zip(variables, values))
            if _ground(rule.head, theta) not in observed:
                continue
            body = [_ground(lit, theta) for lit in rule.body]
            missing = [i for i, fact in enumerate(body) if fact not in f1]
            if len(missing) != 1:
                continue
            j = missing[0]
            bound = set(head_vars)
            for i, lit in enumerate(rule.body):
                if i != j:
                    bound |= _vars(lit)
            if not _vars(rule.body[j]) <= bound:
                continue  # not fully ground: a variable occurs only in the missing literal
            fact = body[j]
            if (fact[1], fact[2]) not in vocab:
                continue
            if ("POS", fact[1], fact[2]) in f1 or ("NEG", fact[1], fact[2]) in f1:
                continue  # the atom's value is not U
            instances.setdefault(fact, set()).add((rule.id, tuple(theta[v] for v in variables)))
    ranked = [(len(inst), fact) for fact, inst in instances.items()]
    ranked.sort(key=lambda sf: (-sf[0], CHANNEL_RANK[sf[1][0]], sf[1][1], sf[1][2]))
    return ranked


def top_k(ranked, k: int) -> list:
    """The first k candidates; none for k = 0."""
    return list(ranked[:k]) if k > 0 else []
