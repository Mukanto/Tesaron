"""Atoms and the vocabulary (SPEC section 1)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, order=True)
class Atom:
    """Atom(pred, args), ordered by (pred, args)."""

    pred: str
    args: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "args", tuple(self.args))

    def __str__(self) -> str:
        return f"{self.pred}({','.join(self.args)})"


def atom_str(atom: Atom) -> str:
    return str(atom)


def entity_names(n_entities: int) -> tuple[str, ...]:
    """e00, e01, ..."""
    return tuple(f"e{i:02d}" for i in range(n_entities))


def class_pred(k: int) -> str:
    return f"c{k}"


def relation_pred(a: int) -> str:
    return f"r{a}"


def build_vocabulary(
    entities: tuple[str, ...], n_classes: int, n_relations: int
) -> frozenset[Atom]:
    """All class atoms c_k(e) plus all relation atoms r_a(x, y) with x != y (60 + 1140 by default)."""
    atoms: set[Atom] = set()
    for k in range(n_classes):
        for e in entities:
            atoms.add(Atom(class_pred(k), (e,)))
    for a in range(n_relations):
        for x in entities:
            for y in entities:
                if x != y:
                    atoms.add(Atom(relation_pred(a), (x, y)))
    return frozenset(atoms)
