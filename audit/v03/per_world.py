"""All checks, twins and descriptive arms for one v0.3 world (PREREG_v0.3 sections 3.2 and 6.2).

G7a is the four-baseline G7a of `audit.v03.checks` (echo, all_false, all_unknown, all_both); all_true is the descriptive arm
`descriptive["all_true"]`.

`evaluate_world_v03` returns EVERYTHING, including new_false-based outcomes (T-1, G8, the structure arm, I-2, I-6, I-7, I-8,
I-9 and the draw-sensitivity outcomes). That is right for the real run and wrong for development (PREREG section 2, no
pilot): the development runner never prints or writes this dictionary; it passes it through `audit.v03.redact` first. The
denominators n_q of new_false (`ev["n_q"]`) are design quantities and may be shown.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from audit import checks as C
from audit import descriptive as D
from audit.exact import ExactTaus, feasible
from audit.per_world import (
    TWIN_CLASSES, data_to_json, perm_rngs,
)
from audit.system import FIXED
from audit.twins import N2
from audit.twins._source import PairSource
from audit.v03 import checks as V
from audit.v03.subproc import run_hash as run_hash_v03

OUTCOME = V.OUTCOME
# test id -> the twins of that test in v0.3 (no N8: G8 has no verdict)
TWIN_TEST = {"N1a": "G1", "N1b": "G1", "N2": "G2", "N3": "G3", "N4": "G4", "N5": "G5", "N6": "G6", "N7": "G7",
             "NT": "T-1"}
VERDICT_TESTS = ("G1", "G2", "G3", "G4", "G5", "G6", "G7", "T-1")  # G7 is G7a
ALL_TESTS = ("G1", "G2", "G3", "G4", "G5", "G6", "G7", "G8", "T-1")


@dataclass(frozen=True)
class TauSet:
    """Every tau a test world is read under: the main tau (Q-40 at (alpha0, 0)), the I-6 tau (Q-40 at (alpha0, k0)), the
    I-7 tau (D1 on the first 10 calibration worlds, k = 0), the I-8 tau (D1 on the first 10 calibration worlds at
    (alpha0, k0)) and the draw-sensitivity taus (Q-40 on the alternative sets; None for a set that did not reach 40 valid
    worlds, R1-14)."""

    main: ExactTaus
    i6: ExactTaus
    i7: ExactTaus
    i8: ExactTaus
    alt: tuple = field(default_factory=tuple)


def make_twin(name: str, seeder, draw: int):
    """The twin of the real run. N2 gets seed("n2", 2i) and seed("n2", 2i + 1) for test world i; N4 is special-cased in
    `collect_for` (v0.3 pins its hash seeds)."""
    if name == "N2":
        return N2(PairSource(seeder("n2", 2 * draw), seeder("n2", 2 * draw + 1)))
    if name == "N4":
        return V.make_n4()
    return TWIN_CLASSES[name]()


def collect_for(test: str, system, rec, taus: ExactTaus, seeder, subprocess_checks: bool, results=None, encoding=None,
                n_q=None):
    """Collected data of one test on one world for `system` (the fixed system or a twin). Like `audit.per_world.collect_for`
    but with v0.3 subprocesses (they rebuild the v0.3 world), T-1 at k = 0 with its n_q (`n_q` is `V.n_q_grid` of `results`;
    computed here if not given) and the v0.3 N4."""
    world, ctx = rec.world, rec.context
    enc = encoding if encoding is not None else system.encode(world, ctx)
    sysname = "fixed" if system is FIXED else system.name
    if test == "G1":
        return C.collect_g1(system, world, ctx, enc)
    if test == "G2":
        subs = None
        if subprocess_checks and sysname == "fixed":
            subs = [run_hash_v03("encoding", rec.world_seed, rec.enc_seed, sysname, hs) for hs in V.G2_HASHSEEDS]
        return C.collect_g2(system, world, ctx, subs)
    if test == "G3":
        return C.collect_g3(system, world, ctx, enc)
    if test == "G4":
        if sysname == "N4":
            return V.collect_g4_n4(rec, subprocess_checks, perm_rngs(seeder, rec.draw))
        subs = None
        if subprocess_checks and sysname == "fixed":
            subs = [run_hash_v03("output", rec.world_seed, rec.enc_seed, sysname, hs) for hs in V.G4_HASHSEEDS]
        return C.collect_g4(system, world, ctx, enc, perm_rngs(seeder, rec.draw), subs)
    if test == "G5":
        return C.collect_g5(system, world, ctx, enc)
    if test == "G6":
        return C.collect_g6(system, world, ctx, enc)
    if test == "G7":
        return V.collect_g7a(system, world, ctx, enc, taus)
    res = results if results is not None else C.evaluate_grid(system, world, ctx, enc)
    if test == "G8":
        return C.collect_g8(system, world, ctx, enc, res)
    if test == "T-1":
        return V.t1_data(V.k_exacts(res, V.K_CAL, n_q if n_q is not None else V.n_q_grid(ctx, enc, res)), taus)
    raise ValueError(test)


def evaluate_world_v03(rec, taus: TauSet, seeder, *, subprocess_checks=True, run_twins=True, keep_data=True) -> dict:
    """Fixed-system outcomes of G1-G7a, G8 and T-1, twin outcomes and the descriptive arms for one WorldRecord."""
    world, ctx, enc = rec.world, rec.context, rec.encoding
    main = taus.main
    results = C.evaluate_grid(FIXED, world, ctx, enc)
    exacts = C.exact_list(results)
    n_q = V.n_q_grid(ctx, enc, results)  # the denominators of new_false: design quantities (PREREG 2, R1-1)
    exacts_k0 = V.k_exacts(results, V.K_CAL, n_q)
    exacts_k5 = V.k_exacts(results, C.K0, n_q)
    fixed, data_cache = {}, {}
    for test in ALL_TESTS:
        data = collect_for(test, FIXED, rec, main, seeder, subprocess_checks, results, enc, n_q)
        fixed[test] = {"outcome": OUTCOME[V.JUDGES[test](data)]}
        if test == "G1":
            fixed[test]["failed_parts"] = C.g1_failed_parts(data)
        if test == "G8":
            fixed[test]["n_hypotheses"] = int(np.max(np.asarray(data["n_hypotheses"])))
        data_cache[test] = data
        if keep_data:
            fixed[test]["data"] = data_to_json(data)
    twins = {}
    if run_twins:
        for name, test in TWIN_TEST.items():
            if name == "NT":
                continue
            data = collect_for(test, make_twin(name, seeder, rec.draw), rec, main, seeder, subprocess_checks)
            twins[name] = {"test": test, "outcome": OUTCOME[V.JUDGES[test](data)]}
        nt = V.nt_exacts(exacts_k0, main)
        twins["NT"] = {"test": "T-1", "outcome": OUTCOME[V.judge_t1(V.t1_data(nt, main))]}
    structure = V.t1_structure(
        exacts_k0, main, [p.value for p in world.params.source_reliabilities], V.wrong_class_atoms_fn(world, enc.units)
    )
    descriptive = {
        "cross_seed": D.cross_seed_agreement(world, ctx, enc, rec.aux_seed) if rec.aux_seed is not None else None,
        "g7b": D.g7b(results, exacts, main),
        "g8_whole_grid": D.g8_whole_grid(exacts, main),
        "g8_single_atom_only": D.g8_single_atom_only(data_cache["G8"]),
        "g8_hyp_count": int(results[(C.ALPHA0, 10)][1].hyp_count),
        "all_true": V.all_true_arm(FIXED, world, ctx, enc, main),
        "t1_all_points": V.t1_all_points_outcome(exacts_k0),
        "t1_i6": V.t1_outcome(exacts_k5, taus.i6),
        "t1_i7": V.t1_outcome(exacts_k0, taus.i7),
        "t1_i8": V.t1_i8_outcome(results, taus.i8),
        "t1_i9": V.t1_outcome(exacts_k0, main, floor=False),
        "t1_draw_sensitivity": [V.NO_TAU if t is None else V.t1_outcome(exacts_k0, t) for t in taus.alt],
        "t1_structure": structure,
        "default_feasible": bool(feasible(results[(C.ALPHA0, V.K_CAL)][2], main)),
    }
    return {"results": results, "exacts": exacts, "exacts_k0": exacts_k0, "n_q": n_q, "fixed": fixed, "twins": twins,
            "descriptive": descriptive}
