"""All checks, twins and descriptive outputs for one world (Layer 2 and the D4 smoke test)."""

from __future__ import annotations

import numpy as np

from audit import checks as C
from audit import descriptive as D
from audit.exact import frac_str
from audit.subproc import run_hash
from audit.system import FIXED
from audit.twins._source import PairSource, SetOrderSource
from audit.twins import N1a, N1b, N2, N3, N4, N5, N6, N7, N8, with_trade_off
from audit.exact import ExactTaus
from tesaron.enums import Belnap

OUTCOME = {True: "HOLDS", False: "FAILS", None: "UNDEFINED"}
G4_HASHSEEDS = ("0", "1", "4242")
G2_HASHSEEDS = ("0", "1")

TWIN_TEST = {"N1a": "G1", "N1b": "G1", "N2": "G2", "N3": "G3", "N4": "G4", "N5": "G5", "N6": "G6", "N7": "G7",
             "N8": "G8", "NT": "T-1"}
TWIN_CLASSES = {"N1a": N1a, "N1b": N1b, "N3": N3, "N5": N5, "N6": N6, "N7": N7, "N8": N8}


def make_twin(name: str, seeder, draw: int):
    """The twin of the real run. N2 gets the two derived seeds seed("n2", 2i) and seed("n2", 2i + 1) for test world i
    (dev mode: their dev mapping); N4 gets the iteration order of a set of strings. No system entropy anywhere."""
    if name == "N2":
        return N2(PairSource(seeder("n2", 2 * draw), seeder("n2", 2 * draw + 1)))
    if name == "N4":
        return N4(SetOrderSource())
    return TWIN_CLASSES[name]()


def perm_rngs(seeder, draw: int):
    """The three G4 permutation generators of a world: seed('perm', 3 * draw + p), p = 0, 1, 2."""
    return [np.random.Generator(np.random.PCG64(seeder("perm", 3 * draw + p))) for p in range(3)]


def _jsonable(arr) -> list:
    a = np.asarray(arr)
    if a.dtype.kind == "f":
        return [None if not np.isfinite(v) else float(v) for v in a.ravel()] if a.ndim == 1 else \
            [[None if not np.isfinite(v) else float(v) for v in row] for row in a.reshape(a.shape[0], -1)]
    return a.tolist()


def data_to_json(data: dict) -> dict:
    return {k: _jsonable(v) for k, v in data.items()}


def collect_for(test: str, system, rec, taus: ExactTaus, seeder, subprocess_checks: bool, results=None, encoding=None):
    """Collected data of one test on one world for `system` (fixed or twin)."""
    world, ctx = rec.world, rec.context
    enc = encoding if encoding is not None else system.encode(world, ctx)
    sysname = "fixed" if system is FIXED else system.name
    if test == "G1":
        return C.collect_g1(system, world, ctx, enc)
    if test == "G2":
        subs = None
        if subprocess_checks and sysname == "fixed":
            subs = [run_hash("encoding", rec.world_seed, rec.enc_seed, sysname, hs) for hs in G2_HASHSEEDS]
        return C.collect_g2(system, world, ctx, subs)
    if test == "G3":
        return C.collect_g3(system, world, ctx, enc)
    if test == "G4":
        subs = None
        if subprocess_checks and sysname in ("fixed", "N4"):
            subs = [run_hash("output", rec.world_seed, rec.enc_seed, sysname, hs) for hs in G4_HASHSEEDS]
        return C.collect_g4(system, world, ctx, enc, perm_rngs(seeder, rec.draw), subs)
    if test == "G5":
        return C.collect_g5(system, world, ctx, enc)
    if test == "G6":
        return C.collect_g6(system, world, ctx, enc)
    if test == "G7":
        return C.collect_g7a(system, world, ctx, enc, taus)
    res = results if results is not None else C.evaluate_grid(system, world, ctx, enc)
    if test == "G8":
        return C.collect_g8(system, world, ctx, enc, res)
    if test == "T-1":
        return C.collect_t1(C.exact_list(res), taus)
    raise ValueError(test)


def nt_exacts(exacts: list, taus: ExactTaus) -> list:
    """NT applied to a world's metric points: new_false rises by 1/5 across the uncertainty span of the feasible points."""
    from audit.exact import feasible

    mask = [feasible(ex, taus) for ex in exacts]
    nf = with_trade_off([ex["uncertainty"] or 0 for ex in exacts], [ex["new_false"] for ex in exacts], mask)
    return [dict(ex, new_false=v) for ex, v in zip(exacts, nf)]


def evaluate_world(rec, taus: ExactTaus, seeder, *, subprocess_checks=True, run_twins=True, keep_data=True) -> dict:
    """Fixed-system outcomes of G1-G7a, G8 and T-1, twin outcomes, and the descriptive arms, for one WorldRecord."""
    world, ctx, enc = rec.world, rec.context, rec.encoding
    results = C.evaluate_grid(FIXED, world, ctx, enc)
    exacts = C.exact_list(results)
    fixed, data_cache = {}, {}
    for test in C.TEST_IDS:
        data = collect_for(test, FIXED, rec, taus, seeder, subprocess_checks, results, enc)
        fixed[test] = {"outcome": OUTCOME[C.JUDGES[test](data)]}
        if test == "G1":
            fixed[test]["failed_parts"] = C.g1_failed_parts(data)  # R2-13: which parts of G1 failed
        if test == "G8":
            fixed[test]["n_hypotheses"] = int(np.max(np.asarray(data["n_hypotheses"])))
        data_cache[test] = data
        if keep_data:
            fixed[test]["data"] = data_to_json(data)
    twins = {}
    if run_twins:
        for name in TWIN_TEST:
            if name == "NT":
                continue
            test = TWIN_TEST[name]
            twin = make_twin(name, seeder, rec.draw)
            data = collect_for(test, twin, rec, taus, seeder, subprocess_checks)
            twins[name] = {"test": test, "outcome": OUTCOME[C.JUDGES[test](data)]}
        twins["NT"] = {"test": "T-1", "outcome": OUTCOME[C.judge_t1(C.collect_t1(nt_exacts(exacts, taus), taus))]}
    g8_single = D.g8_single_atom_only(data_cache["G8"])
    descriptive = {
        "cross_seed": D.cross_seed_agreement(world, ctx, enc, rec.aux_seed) if rec.aux_seed is not None else None,
        "g7b": D.g7b(results, exacts, taus),
        "g8_whole_grid": D.g8_whole_grid(exacts, taus),
        "g8_single_atom_only": g8_single,
        "t1_all_points": OUTCOME[D.t1_all_points(exacts)],
        "t1_structure": D.t1_structure(exacts, taus),
        "default_feasible": D.default_feasibility(results, taus),
    }
    return {"results": results, "exacts": exacts, "fixed": fixed, "twins": twins, "descriptive": descriptive}


def exact_json(ex: dict) -> dict:
    """An exact metric dict as strings p/q (None stays None)."""
    return {k: (None if v is None else frac_str(v)) for k, v in ex.items()}


def grid_listing(results) -> dict:
    """full and verdict of every configuration as lists of the atoms that are not U (for the outputs files)."""
    out = {}
    for (a, k), (output, _, _) in results.items():
        full, verdict = {}, {}
        atoms = set()
        if hasattr(output, "facts"):
            atoms = {atom for (_, atom) in output.facts}
        for atom in sorted(atoms):
            f, v = output.full(atom), output.verdict(atom)
            if f is not Belnap.U:
                full[str(atom)] = f.value
            if v is not Belnap.U:
                verdict[str(atom)] = v.value
        out[f"{a}|{k}"] = {"full": full, "verdict": verdict}
    return out
