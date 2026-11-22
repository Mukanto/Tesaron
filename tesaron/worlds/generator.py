"""World generator (SPEC section 3).

RNG stream order, for a seed (explicit numpy Generator(PCG64(seed)), nothing global):
  1. base classes (round-robin, then a permutation),
  2. the special entities, stratified by base class (revision S-1): one permutation of the classes, then for each
     special slot (outliers first, then overlaps) in order, slot s takes the class perm[s % n_classes] and one
     rng.integers draw picks an entity among that class's not-yet-special entities (in entity order),
  3. acceptance loop, each attempt: rule indices (R1..R6 in order, see _draw_rules), then the base relation
     facts as one rng.random((n_relations, n_entities, n_entities)) array,
  4. after acceptance: outlier angles / overlap partner prototypes (entity order), then the feature noise,
  5. report rows: per source in order, one array draw for "considered" and one for "correct polarity".
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from functools import cached_property
from typing import Mapping

import numpy as np

from tesaron.atoms import Atom, build_vocabulary, class_pred, entity_names, relation_pred
from tesaron.decoder.datalog import Literal, Rule, ground_instances, seminaive_eval
from tesaron.degrees import Probability
from tesaron.enums import Channel

_X, _Y, _Z = "X", "Y", "Z"


@dataclass(frozen=True)
class WorldParams:
    n_entities: int = 20
    n_classes: int = 3
    n_relations: int = 3
    n_sources: int = 3
    feature_dim: int = 2
    prototype_radius: float = 3.0
    feature_sigma: float = 0.6
    rows_per_entity: int = 5
    n_outliers: int = 2
    n_overlaps: int = 2
    outlier_radius: float = 7.0
    overlap_fraction: float = 0.4
    base_density: float = 0.04
    source_reliabilities: tuple[Probability, ...] = (Probability(0.95), Probability(0.80), Probability(0.60))
    q_true: float = 0.5
    q_false: float = 0.02
    max_attempts: int = 1000

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_reliabilities", tuple(self.source_reliabilities))
        if any(not isinstance(p, Probability) for p in self.source_reliabilities):
            raise TypeError("source_reliabilities must be Probability objects")
        if len(self.source_reliabilities) != self.n_sources:
            raise ValueError("n_sources must equal len(source_reliabilities)")
        if self.feature_dim < 2:
            raise ValueError("feature_dim must be >= 2")
        if self.n_classes < 2 or self.n_relations < 2:
            raise ValueError("need at least 2 classes and 2 relations (rules need a != b, i != j)")
        if self.n_outliers + self.n_overlaps > self.n_entities:
            raise ValueError("more outliers and overlaps than entities")

    def prototypes(self) -> tuple[tuple[float, ...], ...]:
        """Class k at angle 2*pi*k/n_classes on a circle of radius prototype_radius (fixed, not random)."""
        out = []
        for k in range(self.n_classes):
            ang = 2.0 * math.pi * k / self.n_classes
            xy = (self.prototype_radius * math.cos(ang), self.prototype_radius * math.sin(ang))
            out.append(xy + (0.0,) * (self.feature_dim - 2))
        return tuple(out)


@dataclass(frozen=True)
class FeatureRow:
    row_id: str
    entity: str
    x: tuple[float, ...]


@dataclass(frozen=True)
class ReportRow:
    row_id: str
    source: str
    atom: Atom
    polarity: Channel  # POS = reports the atom as true, NEG = reports it as false


@dataclass(frozen=True)
class World:
    seed: int
    params: WorldParams
    entities: tuple[str, ...]
    base_classes: tuple[int, ...]  # aligned with entities
    outliers: tuple[str, ...]
    overlaps: tuple[str, ...]
    feature_rows: tuple[FeatureRow, ...]
    base_facts: tuple[Atom, ...]  # base relation facts (base class facts are in base_classes)
    rules: tuple[Rule, ...]
    true_atoms: frozenset[Atom]
    source_reliabilities: Mapping[str, Probability]
    report_rows: tuple[ReportRow, ...]
    attempts: int = 0  # number of draws (rules + base facts) needed for acceptance, including the accepted one

    @cached_property
    def vocabulary(self) -> frozenset[Atom]:
        return build_vocabulary(self.entities, self.params.n_classes, self.params.n_relations)

    def truth(self, atom: Atom) -> bool:
        """Classical world truth of a vocabulary atom."""
        if atom not in self.vocabulary:
            raise ValueError(f"{atom} is outside the vocabulary")
        return atom in self.true_atoms


def _draw_rules(rng: np.random.Generator, p: WorldParams) -> tuple[Rule, ...]:
    """Exactly 6 rules, one per template. Draw order per rule: R1 (a, i, j), R2 (a, b, i), R3 (a, b),
    R4 (a, b, c), R5 (a, b, i), R6 (i, j). a != b only for R2, R3, R5 and i != j only for R6 (where
    the template table states it); R4's a, b, c and R1's i, j are unconstrained."""
    nr, nc = p.n_relations, p.n_classes

    def draw(n: int) -> int:
        return int(rng.integers(0, n))

    def draw_other(a: int, n: int) -> int:
        return (a + 1 + int(rng.integers(0, n - 1))) % n

    def c(k: int, v: str) -> Literal:
        return Literal(class_pred(k), (v,))

    def r(a: int, u: str, v: str, ch: Channel = Channel.POS) -> Literal:
        return Literal(relation_pred(a), (u, v), ch)

    rules = []
    a, i, j = draw(nr), draw(nc), draw(nc)
    rules.append(Rule("R1", c(j, _Y), (r(a, _X, _Y), c(i, _X))))
    a = draw(nr); b = draw_other(a, nr); i = draw(nc)
    rules.append(Rule("R2", r(b, _X, _Y), (r(a, _X, _Y), c(i, _X))))
    a = draw(nr); b = draw_other(a, nr)
    rules.append(Rule("R3", r(b, _Y, _X), (r(a, _X, _Y),)))
    a, b, cc = draw(nr), draw(nr), draw(nr)
    rules.append(Rule("R4", r(cc, _X, _Z), (r(a, _X, _Y), r(b, _Y, _Z))))
    a = draw(nr); b = draw_other(a, nr); i = draw(nc)
    rules.append(Rule("R5", r(a, _X, _Y, Channel.NEG), (r(b, _X, _Y), c(i, _X))))
    i = draw(nc); j = draw_other(i, nc)
    rules.append(Rule("R6", Literal(class_pred(j), (_X,), Channel.NEG), (c(i, _X),)))
    return tuple(rules)


def _closure(
    class_facts: set[Atom], base_facts: set[Atom], rules: tuple[Rule, ...], vocab: frozenset[Atom]
) -> frozenset[Atom]:
    """Least model under the positive-head rules."""
    start = {(Channel.POS, a) for a in class_facts | base_facts}
    positive = [rule for rule in rules if rule.head.channel is Channel.POS]
    result = seminaive_eval(start, positive, vocab)
    return frozenset(atom for ch, atom in result if ch is Channel.POS)


def _accepted(rules: tuple[Rule, ...], true_atoms: frozenset[Atom]) -> bool:
    """SPEC section 3 acceptance: (1) consistency of R5 and R6, (2) every rule fires at least once.

    "Fires" for R1-R4: some ground instance has a true body (literal reading: this counts instances whose
    head is outside the vocabulary, e.g. R4 with X = Z). For R5 and R6: some ground instance has a true
    body and a false head atom.
    """
    true_facts = {(Channel.POS, a) for a in true_atoms}
    for rule in rules:
        insts = ground_instances(rule, true_facts)
        if rule.head.channel is Channel.NEG:
            heads = [Atom(rule.head.pred, tuple(t[a] if a in t else a for a in rule.head.args)) for t in insts]
            if any(h in true_atoms for h in heads):
                return False  # consistency violated
            if not any(h not in true_atoms for h in heads):
                return False  # never fires
        elif not insts:
            return False
    return True


def generate_world(seed: int, params: WorldParams = WorldParams()) -> World:
    """Deterministic world for a seed. Raises RuntimeError after params.max_attempts failed draws."""
    rng = np.random.Generator(np.random.PCG64(seed))
    p = params
    entities = entity_names(p.n_entities)
    vocab = build_vocabulary(entities, p.n_classes, p.n_relations)

    # 1. base classes: round-robin (balanced), then shuffled; every entity has exactly one.
    rr = np.array([i % p.n_classes for i in range(p.n_entities)])
    base_classes = tuple(int(x) for x in rr[rng.permutation(p.n_entities)])
    class_facts = {Atom(class_pred(k), (e,)) for e, k in zip(entities, base_classes)}

    # 2. which entities are outliers / overlaps: stratified by base class (revision S-1, SPEC section 15).
    class_order = [int(x) for x in rng.permutation(p.n_classes)]
    special: list[int] = []
    for slot in range(p.n_outliers + p.n_overlaps):
        cls = class_order[slot % p.n_classes]
        free = [i for i in range(p.n_entities) if base_classes[i] == cls and i not in special]
        if not free:
            raise ValueError(f"class {cls} has no entity left for special slot {slot}")
        special.append(free[int(rng.integers(0, len(free)))])
    outlier_idx = sorted(special[: p.n_outliers])
    overlap_idx = sorted(special[p.n_outliers :])

    # 3. acceptance loop.
    rules: tuple[Rule, ...] = ()
    base_facts: list[Atom] = []
    true_atoms: frozenset[Atom] = frozenset()
    attempts = 0
    for attempts in range(1, p.max_attempts + 1):
        rules = _draw_rules(rng, p)
        mask = rng.random((p.n_relations, p.n_entities, p.n_entities)) < p.base_density
        base_facts = [
            Atom(relation_pred(a), (entities[x], entities[y]))
            for a in range(p.n_relations)
            for x in range(p.n_entities)
            for y in range(p.n_entities)
            if x != y and mask[a, x, y]
        ]
        true_atoms = _closure(class_facts, set(base_facts), rules, vocab)
        if _accepted(rules, true_atoms):
            break
    else:
        raise RuntimeError(f"no acceptable world in {p.max_attempts} attempts (seed {seed})")

    # 4. feature rows (after acceptance).
    protos = np.array(p.prototypes())
    means = []
    for idx, e in enumerate(entities):
        base = base_classes[idx]
        if idx in outlier_idx:
            ang = float(rng.uniform(0.0, 2.0 * math.pi))
            m = np.zeros(p.feature_dim)
            m[0], m[1] = p.outlier_radius * math.cos(ang), p.outlier_radius * math.sin(ang)
        elif idx in overlap_idx:
            o = int(rng.integers(0, p.n_classes - 1))
            o = o if o < base else o + 1
            m = protos[base] + p.overlap_fraction * (protos[o] - protos[base])
        else:
            m = protos[base].copy()
        means.append(m)
    noise = rng.normal(0.0, p.feature_sigma, size=(p.n_entities * p.rows_per_entity, p.feature_dim))
    feature_rows = []
    for n in range(p.n_entities * p.rows_per_entity):
        idx = n // p.rows_per_entity
        x = means[idx] + noise[n]
        feature_rows.append(FeatureRow(f"f{n:04d}", entities[idx], tuple(float(v) for v in x)))

    # 5. sources and report rows.
    source_names = tuple(f"s{i}" for i in range(p.n_sources))
    base_set = set(base_facts)
    candidates: list[tuple[Atom, bool]] = []  # (atom, is_true); derived-but-not-base true atoms excluded
    for atom in sorted(vocab):
        if not atom.pred.startswith("r"):
            continue
        if atom in true_atoms:
            if atom in base_set:
                candidates.append((atom, True))
        else:
            candidates.append((atom, False))
    reports: list[ReportRow] = []
    for s_idx, source in enumerate(source_names):
        rel = p.source_reliabilities[s_idx].value
        q = np.array([p.q_true if t else p.q_false for _, t in candidates])
        considered = rng.random(len(candidates)) < q
        chosen = [candidates[i] for i in range(len(candidates)) if considered[i]]
        correct = rng.random(len(chosen)) < rel
        for (atom, is_true), ok in zip(chosen, correct):
            truth_pol = Channel.POS if is_true else Channel.NEG
            pol = truth_pol if ok else Channel.NEG if truth_pol is Channel.POS else Channel.POS
            reports.append(ReportRow(f"r{len(reports):04d}", source, atom, pol))

    return World(
        seed=seed,
        params=p,
        entities=entities,
        base_classes=base_classes,
        outliers=tuple(entities[i] for i in outlier_idx),
        overlaps=tuple(entities[i] for i in overlap_idx),
        feature_rows=tuple(feature_rows),
        base_facts=tuple(sorted(base_facts)),
        rules=rules,
        true_atoms=true_atoms,
        source_reliabilities={s: p.source_reliabilities[i] for i, s in enumerate(source_names)},
        report_rows=tuple(reports),
        attempts=attempts,
    )
