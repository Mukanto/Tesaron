"""Metrics (SPEC section 8).

W(a) in {T, F} is the world truth. Sets:
  E: atoms with a meaning unit from D_derive (any degrees)
  I: atoms in E with enc(a) != U           (depends on alpha)
  H: atoms not in E entailed by the world rules from the W-values of E
  K: E union H
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Callable, Iterable, Mapping, Protocol

from tesaron.atoms import Atom
from tesaron.belnap import boundary_share, on_boundary, unit_value
from tesaron.decoder.datalog import Rule, seminaive_eval
from tesaron.enums import Belnap, Channel
from tesaron.meaning import MeaningUnit


class Output(Protocol):
    def full(self, atom: Atom) -> Belnap: ...
    def verdict(self, atom: Atom) -> Belnap: ...


@dataclass(frozen=True)
class Metrics:
    fidelity: float | None
    deviation: float
    consistency: float | None
    uncertainty: float | None
    new_true: float | None
    new_false: float
    hyp_count: int
    hyp_correct: int
    validation_agreement: float | None
    boundary_share: float | None
    size_E: int
    size_I: int
    size_H: int
    size_K: int

    @property
    def x(self) -> float:
        """Pareto axis x = 1 - new_false."""
        return 1.0 - self.new_false

    @property
    def y(self) -> float | None:
        """Pareto axis y = new_true."""
        return self.new_true


def _w(truth: Callable[[Atom], bool], atom: Atom) -> Belnap:
    return Belnap.T if truth(atom) else Belnap.F


def compute_H(
    E: Iterable[Atom],
    truth: Callable[[Atom], bool],
    world_rules: Iterable[Rule],
    vocab: frozenset[Atom],
) -> list[Atom]:
    """Atoms outside E that appear (in either channel) in the fixpoint seeded with POS a for W(a)=T and
    NEG a for W(a)=F, a in E. Asserts that the derived channel of each H atom agrees with W and that no
    H atom has both channels."""
    e_set = set(E)
    seeds = {(Channel.POS if truth(a) else Channel.NEG, a) for a in e_set}
    fix = seminaive_eval(seeds, world_rules, vocab)
    channels: dict[Atom, set[Channel]] = {}
    for ch, atom in fix:
        if atom not in e_set:
            channels.setdefault(atom, set()).add(ch)
    for atom in sorted(channels):
        chs = channels[atom]
        if len(chs) != 1:
            raise AssertionError(f"H atom {atom} has both channels")
        (ch,) = chs
        if (ch is Channel.POS) != truth(atom):
            raise AssertionError(f"H atom {atom}: derived channel {ch.name} disagrees with world truth")
    return sorted(channels)


def _share(num: int, den: int, empty: float | None) -> float | None:
    return empty if den == 0 else num / den


def compute_metrics_exact(
    *,
    truth: Callable[[Atom], bool],
    vocab: frozenset[Atom],
    world_rules: Iterable[Rule],
    units: Mapping[Atom, MeaningUnit],
    validation_units: Mapping[Atom, MeaningUnit],
    alpha: float,
    epsilon_band: float,
    output: Output,
) -> tuple[Metrics, dict]:
    """All metrics of SPEC section 8 for one configuration, and exact companions (SPEC S-7): a dict with the keys
    fidelity, deviation, consistency, uncertainty, new_true, new_false, validation_agreement, boundary_share whose
    values are fractions.Fraction of the integer counts (None where the metric is undefined, as for the floats).
    The float values are exactly those of compute_metrics. In the formulas B and U never equal W."""
    world_rules = tuple(world_rules)
    vocab_sorted = sorted(vocab)
    E = sorted(units)
    enc = {a: unit_value(units[a], alpha) for a in E}
    I = [a for a in E if enc[a] is not Belnap.U]
    I_set = set(I)
    H = compute_H(E, truth, world_rules, vocab)  # H always uses the WORLD's rules (S-5)
    K = sorted(set(E) | set(H))

    n_fid = sum(1 for a in I if output.full(a) is _w(truth, a))
    fidelity = _share(n_fid, len(I), None)

    decided_enc = [a for a in I if enc[a] in (Belnap.T, Belnap.F)]
    n_dev = sum(1 for a in decided_enc if output.full(a) is not enc[a])
    deviation = _share(n_dev, len(decided_enc), 0.0)

    n_both = sum(1 for a in K if output.full(a) is Belnap.B)
    consistency = _share(n_both, len(K), None)
    consistency = None if consistency is None else 1.0 - consistency
    n_unc = sum(1 for a in K if output.verdict(a) is Belnap.U)
    uncertainty = _share(n_unc, len(K), None)

    n_nt = sum(1 for a in H if output.verdict(a) is _w(truth, a))
    new_true = _share(n_nt, len(H), None)

    outside = [a for a in vocab_sorted if a not in I_set]
    decided_out = [a for a in outside if output.verdict(a) in (Belnap.T, Belnap.F)]
    n_nf = sum(1 for a in decided_out if output.verdict(a) is not _w(truth, a))
    new_false = _share(n_nf, len(decided_out), 0.0)

    hyp_atoms = [
        a for a in vocab_sorted
        if output.full(a) in (Belnap.T, Belnap.F) and output.verdict(a) is Belnap.U
    ]
    hyp_correct = sum(1 for a in hyp_atoms if output.full(a) is _w(truth, a))

    agree = total = 0
    for a in sorted(validation_units):
        v = unit_value(validation_units[a], alpha)
        d = output.verdict(a)
        if v in (Belnap.T, Belnap.F) and d in (Belnap.T, Belnap.F):
            total += 1
            agree += v is d
    validation_agreement = _share(agree, total, None)

    n_units = len(units)
    n_boundary = sum(1 for a in sorted(units) if on_boundary(units[a], alpha, epsilon_band))
    exact = {
        "fidelity": Fraction(n_fid, len(I)) if I else None,
        "deviation": Fraction(n_dev, len(decided_enc)) if decided_enc else Fraction(0),
        "consistency": Fraction(len(K) - n_both, len(K)) if K else None,
        "uncertainty": Fraction(n_unc, len(K)) if K else None,
        "new_true": Fraction(n_nt, len(H)) if H else None,
        "new_false": Fraction(n_nf, len(decided_out)) if decided_out else Fraction(0),
        "validation_agreement": Fraction(agree, total) if total else None,
        "boundary_share": Fraction(n_boundary, n_units) if n_units else None,
    }
    metrics = Metrics(
        fidelity=fidelity,
        deviation=deviation,  # type: ignore[arg-type]
        consistency=consistency,
        uncertainty=uncertainty,
        new_true=new_true,
        new_false=new_false,  # type: ignore[arg-type]
        hyp_count=len(hyp_atoms),
        hyp_correct=hyp_correct,
        validation_agreement=validation_agreement,
        boundary_share=boundary_share(units, alpha, epsilon_band),
        size_E=len(E),
        size_I=len(I),
        size_H=len(H),
        size_K=len(K),
    )
    return metrics, exact


def compute_metrics(**kwargs) -> Metrics:
    """All metrics of SPEC section 8 for one configuration (see compute_metrics_exact for the arguments)."""
    return compute_metrics_exact(**kwargs)[0]


def compute_metrics_for(world, context, encoding, output: Output) -> Metrics:
    """Convenience wrapper: world truth, context (alpha, epsilon_band, vocabulary); H uses world.rules and encoding."""
    return compute_metrics(
        truth=world.truth,
        vocab=context.vocabulary,
        world_rules=world.rules,  # never context.rules: H must not move with the decoder's rules (S-5)
        units=encoding.units,
        validation_units=encoding.validation_units,
        alpha=context.alpha,
        epsilon_band=context.epsilon_band,
        output=output,
    )


def compute_metrics_for_exact(world, context, encoding, output: Output) -> tuple[Metrics, dict]:
    """compute_metrics_for with the exact companions of compute_metrics_exact (SPEC S-7)."""
    return compute_metrics_exact(
        truth=world.truth,
        vocab=context.vocabulary,
        world_rules=world.rules,
        units=encoding.units,
        validation_units=encoding.validation_units,
        alpha=context.alpha,
        epsilon_band=context.epsilon_band,
        output=output,
    )
