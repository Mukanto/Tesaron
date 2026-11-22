"""Per-world checks G1-G8 and T-1 (PREREG section 3.2), each split into collecting data and judging it.

    collect_gN(system, world, context, ...) -> dict[str, numpy.ndarray]   (numeric or bool arrays only)
    judge_gN(data)                         -> True (HOLDS) | False (FAILS) | None (UNDEFINED)

The same judge runs in Layer 1 (the Truth_Gate study) and in Layer 2 (the real run). Anchors (parts that all-zero
data and noise cannot satisfy, gate check K5) are marked "anchor" below.

Definedness sentinel. The gate's probes replace every numeric array by zeros or by N(0, 1) noise. If a judge returned
UNDEFINED whenever a data array is zero or small, every probe would be UNDEFINED and the gate would call the probe
inconclusive. So a check that can be UNDEFINED (G6, G7a, G8, T-1) has collect() store its definedness condition as a
float flag that is exactly 10.0 when the check is undefined and 0.0 otherwise, and the judge returns None only when
that flag exceeds 5.0. N(0, 1) noise never reaches 5.0, and zeros mean "defined"; the judge's anchor then makes
such data FAIL.
"""

from __future__ import annotations

from dataclasses import replace
from fractions import Fraction

import numpy as np

from audit.exact import (
    DELTA, EPS_D, EPS_F, INVALID, ExactTaus, decode_pairs, encode_pairs, feasible,
)
from audit.hashing import encoding_hash, hash_to_array, output_hash
from audit.indep import closure_fact_keys
from audit.oracle import Oracle
from tesaron.atoms import Atom
from tesaron.belnap import unit_value
from tesaron.criterion.baselines import BASELINE_NAMES, make_baselines
from tesaron.criterion.metrics import compute_metrics_for_exact
from tesaron.decoder import naive_eval, seminaive_eval
from tesaron.enums import Belnap, Channel

ALPHA0 = 0.7
K0 = 5
ALPHAS = tuple(round(0.95 - 0.05 * i, 2) for i in range(10))  # 0.95 .. 0.50
KS = (0, 5, 10)
GRID = tuple((a, k) for a in ALPHAS for k in KS)  # 30 configurations (D3)
UNDEFINED_FLAG = 10.0
SENTINEL_THRESHOLD = 5.0

TEST_IDS = ("G1", "G2", "G3", "G4", "G5", "G6", "G7", "G8", "T-1")

# The data keys each check declares (gate check K7: a check returns every component it declares). Layer 1 and the
# D4 smoke test verify that collect_gN returns at least these keys, and that the judge answers True, False or None.
DECLARED_KEYS = {
    "G1": ("outlier_pos", "outlier_neg", "class_pos", "class_neg", "own_typicality"),
    "G2": ("h1", "h2", "h_alt"),
    "G3": ("decided_before", "decided_after"),
    "G4": ("h0", "h_perm", "fixpoints_equal", "n_facts"),
    "G5": ("centers", "centers_val_corrupt", "centers_der_corrupt", "unit_map", "unit_map_val_corrupt"),
    "G6": ("status", "in_pass1", "no_candidate"),
    "G7": ("base_feasible", "base_positive", "oracle_feasible", "oracle_positive", "no_oracle"),
    "G8": ("fidelity", "deviation", "n_hypotheses", "undefined", "n_I", "n_decided"),
    "T-1": ("feasible", "uncertainty", "new_false", "undefined"),
}


def _arr(values, dtype=float):
    return np.asarray(values, dtype=dtype)


def _flag(undefined: bool) -> np.ndarray:
    return _arr([UNDEFINED_FLAG if undefined else 0.0])


def _is_undefined(d, key: str) -> bool:
    return bool(np.max(np.asarray(d[key], dtype=float)) > SENTINEL_THRESHOLD)


# ======================================================================================================== G1
def collect_g1(system, world, context, encoding):
    """Class-unit degrees of the outlier entities, of all class units, and own-class typicality of the normal entities."""
    units = encoding.units
    n_classes = world.params.n_classes
    class_atoms = [a for a in sorted(units) if a.pred.startswith("c")]
    pos_rows, neg_rows = [], []
    for e in world.outliers:
        atoms = [Atom(f"c{k}", (e,)) for k in range(n_classes)]
        if atoms[0] in units:
            pos_rows.append([units[a].mu_pos.value for a in atoms])
            neg_rows.append([units[a].mu_neg.value for a in atoms])
    special = set(world.outliers) | set(world.overlaps)
    own = []
    for e, k in zip(world.entities, world.base_classes):
        a = Atom(f"c{k}", (e,))
        if e not in special and a in units:
            own.append(units[a].mu_pos.value)
    return {
        "outlier_pos": _arr(pos_rows).reshape(-1, n_classes),
        "outlier_neg": _arr(neg_rows).reshape(-1, n_classes),
        "class_pos": _arr([units[a].mu_pos.value for a in class_atoms]),
        "class_neg": _arr([units[a].mu_neg.value for a in class_atoms]),
        "own_typicality": _arr(own),
    }


G1_PARTS = ("(i)", "(ii)", "(iii)")


def g1_parts(d) -> tuple:
    """(ok_i, ok_ii, ok_iii) of G1 on collected data."""
    pos = np.asarray(d["outlier_pos"], dtype=float)
    all_neg = np.asarray(d["class_neg"], dtype=float)
    own = np.asarray(d["own_typicality"], dtype=float)
    # (i) the typicalities of an outlier entity sum to less than 0.5 (they are not normalized)
    ok_i = bool(np.all(pos.sum(axis=1) < 0.5))
    # (ii) every class unit of every entity has mu_neg exactly 0.0 (a class unit's mu_neg is a fixed 0; it is never
    # computed from mu_pos, SPEC section 5)
    ok_ii = bool(np.all(all_neg == 0.0))
    # (iii) anchor: the median own-class typicality of the normal entities is at least 0.5
    ok_iii = bool(own.size > 0 and np.median(own) >= 0.5)
    return ok_i, ok_ii, ok_iii


def g1_failed_parts(d) -> list:
    """The parts of G1 that fail on collected data, e.g. ["(ii)"]; empty if G1 holds."""
    return [name for name, ok in zip(G1_PARTS, g1_parts(d)) if not ok]


def judge_g1(d):
    return all(g1_parts(d))


# ======================================================================================================== G2
def collect_g2(system, world, context, subprocess_hashes=None):
    """Hashes of two in-process encodings, of one encoding with encoder seed + 1 and, if given, of subprocess
    encodings (Layer 2: PYTHONHASHSEED 0 and 1, set explicitly)."""
    h1 = encoding_hash(system.encode(world, context))
    h2 = encoding_hash(system.encode(world, context))
    h_alt = encoding_hash(system.encode(world, replace(context, encoder_seed=context.encoder_seed + 1)))
    data = {"h1": hash_to_array(h1), "h2": hash_to_array(h2), "h_alt": hash_to_array(h_alt)}
    if subprocess_hashes is not None:
        data["h_sub"] = np.stack([hash_to_array(h) for h in subprocess_hashes])
    return data


def judge_g2(d):
    h1 = np.asarray(d["h1"])
    same = np.array_equal(h1, np.asarray(d["h2"]))
    if "h_sub" in d:
        sub = np.asarray(d["h_sub"])
        same = same and np.array_equal(sub, np.broadcast_to(h1, sub.shape))
    # anchor: another encoder seed gives a different hash
    differs = not np.array_equal(h1, np.asarray(d["h_alt"]))
    return bool(same and differs)


# ======================================================================================================== G3
def collect_g3(system, world, context, encoding):
    """For every meaning unit: decided at alpha0 before, and decided after its provenance rows are removed from
    D_derive and the data re-encoded. One re-encoding per distinct provenance."""
    units = encoding.units
    atoms = sorted(units)
    before = [unit_value(units[a], ALPHA0) is not Belnap.U for a in atoms]
    by_prov: dict = {}
    for i, a in enumerate(atoms):
        by_prov.setdefault(tuple(units[a].provenance), []).append(i)
    after = [False] * len(atoms)
    for prov in sorted(by_prov):
        removed = set(prov)
        derive = [r for r in encoding.derive_ids if r not in removed]
        enc2 = system.encode_rows(world, context, derive, encoding.validate_ids)
        for i in by_prov[prov]:
            u = enc2.units.get(atoms[i])
            after[i] = u is not None and unit_value(u, ALPHA0) is not Belnap.U
    return {"decided_before": _arr(before, bool), "decided_after": _arr(after, bool)}


def judge_g3(d):
    before = np.asarray(d["decided_before"], dtype=bool)
    after = np.asarray(d["decided_after"], dtype=bool)
    # anchor: at least one ablated unit was decided before; none stays decided after its rows are removed
    return bool(before.any() and not after.any())


# ======================================================================================================== G4
def collect_g4(system, world, context, encoding, perm_rngs, subprocess_hashes=None):
    """Output hash at (alpha0, k0) in the original order and under permutations of facts and rules (one numpy
    Generator per permutation); optional subprocess hashes; naive versus semi-naive fixpoint."""
    facts = system.interface_facts(encoding.units, ALPHA0)
    rules, vocab = tuple(context.rules), context.vocabulary
    out0 = system.decode(facts, rules, vocab, K0)
    h_perm = []
    for rng in perm_rngs:
        items = list(facts.items())
        fact_order = rng.permutation(len(items))
        rule_order = rng.permutation(len(rules))
        shuffled = {items[int(i)][0]: items[int(i)][1] for i in fact_order}
        shuffled_rules = [rules[int(i)] for i in rule_order]
        h_perm.append(hash_to_array(output_hash(system.decode(shuffled, shuffled_rules, vocab, K0))))
    pass1_equal = naive_eval(facts, rules, vocab) == seminaive_eval(facts, rules, vocab)
    hyp_facts = {c.fact for c in out0.hypotheses}
    f1 = naive_eval(facts, rules, vocab)
    pass2_in = f1 | hyp_facts
    pass2_equal = naive_eval(pass2_in, rules, vocab) == seminaive_eval(pass2_in, rules, vocab)
    data = {
        "h0": hash_to_array(output_hash(out0)),
        "h_perm": np.stack(h_perm) if h_perm else np.zeros((0, 2), dtype=np.uint64),
        "fixpoints_equal": _arr([pass1_equal and pass2_equal], bool),
        "n_facts": _arr([len(out0.facts)], np.int64),
    }
    if subprocess_hashes is not None:
        data["h_sub"] = np.stack([hash_to_array(h) for h in subprocess_hashes])
    return data


def judge_g4(d):
    h0 = np.asarray(d["h0"])
    same = np.array_equal(np.asarray(d["h_perm"]), np.broadcast_to(h0, np.asarray(d["h_perm"]).shape))
    if "h_sub" in d:
        sub = np.asarray(d["h_sub"])
        same = same and np.array_equal(sub, np.broadcast_to(h0, sub.shape))
    fix = bool(np.all(np.asarray(d["fixpoints_equal"], dtype=bool)))
    anchor = bool(np.max(np.asarray(d["n_facts"], dtype=float)) >= 1)  # the output has at least one fact
    return bool(same and fix and anchor)


# ======================================================================================================== G5
def _garbage(row_id: str) -> tuple:
    n = int(row_id[1:])
    return (((n * 7919) % 2000) / 100.0 - 10.0, ((n * 104729 + 13) % 2000) / 100.0 - 10.0)


def corrupt_world(world, row_ids):
    """A World copy in which the feature values of row_ids are replaced by garbage (deterministic arithmetic on the
    row number, uniform-looking in [-10, 10)) and the polarities of the report rows among row_ids are flipped.
    Row ids are unchanged, so a seeded selection and split are unchanged."""
    ids = set(row_ids)
    feats = tuple(
        replace(f, x=_garbage(f.row_id) + tuple(f.x[2:])) if f.row_id in ids else f for f in world.feature_rows
    )
    reports = tuple(
        replace(r, polarity=Channel.NEG if r.polarity is Channel.POS else Channel.POS) if r.row_id in ids else r
        for r in world.report_rows
    )
    return replace(world, feature_rows=feats, report_rows=reports)


def unit_map_digest(units) -> np.ndarray:
    """Two uint64 of a hash of the full map atom -> (mu_pos, mu_neg, status, provenance), floats as exact hex."""
    import hashlib
    import json

    payload = [
        [str(a), units[a].mu_pos.value.hex(), units[a].mu_neg.value.hex(), units[a].status.name,
         list(units[a].provenance)]
        for a in sorted(units)
    ]
    return hash_to_array(hashlib.sha256(json.dumps(payload, separators=(",", ":")).encode("ascii")).hexdigest())


def collect_g5(system, world, context, encoding):
    """Fitted centers and D_derive units before and after corrupting D_validate; centers after corrupting D_derive."""
    enc_v = system.encode(corrupt_world(world, encoding.validate_ids), context)
    enc_d = system.encode(corrupt_world(world, encoding.derive_ids), context)
    for e in (enc_v, enc_d):  # the selection is a function of the row ids only, so it must be unchanged
        if (e.selected_ids, e.derive_ids, e.validate_ids) != (
            encoding.selected_ids, encoding.derive_ids, encoding.validate_ids
        ):
            raise AssertionError("selection changed when row values were corrupted")
    return {
        "centers": _arr(encoding.fit.centers),
        "centers_val_corrupt": _arr(enc_v.fit.centers),
        "centers_der_corrupt": _arr(enc_d.fit.centers),
        "unit_map": unit_map_digest(encoding.units),
        "unit_map_val_corrupt": unit_map_digest(enc_v.units),
    }


def judge_g5(d):
    same_centers = np.array_equal(np.asarray(d["centers"]), np.asarray(d["centers_val_corrupt"]))
    same_units = np.array_equal(np.asarray(d["unit_map"]), np.asarray(d["unit_map_val_corrupt"]))
    # anchor: corrupting D_derive the same way changes the centers
    anchor = not np.array_equal(np.asarray(d["centers"]), np.asarray(d["centers_der_corrupt"]))
    return bool(same_centers and same_units and anchor)


# ======================================================================================================== G6
def collect_g6(system, world, context, encoding):
    """Status of every fact of the output at (alpha0, k = 10), and whether it is in the pass-1 fixpoint recomputed
    from the observed facts alone (brute-force closure, no tesaron.decoder)."""
    facts = system.interface_facts(encoding.units, ALPHA0)
    rules, vocab = tuple(context.rules), context.vocabulary
    out = system.decode(facts, rules, vocab, 10)
    # the pass-1 fixpoint recomputed from the observed facts alone by the brute-force closure of audit.indep
    f1 = closure_fact_keys(facts, rules, vocab, world.entities)
    status = [int(info.status) for info in out.facts.values()]
    in_f1 = [(ch.name, atom.pred, tuple(atom.args)) in f1 for ch, atom in out.facts]
    return {
        "status": _arr(status, np.int64),
        "in_pass1": _arr(in_f1, bool),
        "no_candidate": _flag(len(out.hypotheses) == 0),
    }


def judge_g6(d):
    if _is_undefined(d, "no_candidate"):
        return None
    status = np.asarray(d["status"], dtype=float)
    in_f1 = np.asarray(d["in_pass1"], dtype=bool)
    solid = status > 1.5  # OBSERVED or DERIVED
    hypothesis = (status > 0.5) & (status <= 1.5)
    ok = bool(np.all(in_f1[solid])) and bool(np.all(hypothesis[~in_f1]))
    anchor = bool(solid.any() and hypothesis.any())  # there are solid facts and there are hypotheses
    return ok and anchor




# ======================================================================================================== grid
def evaluate_grid(system, world, context, encoding, grid=GRID):
    """{(alpha, k): (output, metrics, exact metrics)}"""
    return system.evaluate_grid(world, context, encoding, grid)


def exact_list(results, grid=GRID) -> list:
    """The exact metric dicts of the grid configurations, in grid order."""
    return [results[(a, k)][2] for a, k in grid]


# ======================================================================================================== G7a
def _score_positive(ex: dict) -> bool:
    """A single point (x, y) = (1 - new_false, new_true) scores x * y, which is > 0 iff new_true > 0 and new_false < 1."""
    return ex["new_true"] is not None and ex["new_false"] is not None and ex["new_true"] > 0 and ex["new_false"] < 1


def collect_g7a(system, world, context, encoding, taus: ExactTaus):
    """Feasibility and positivity of the score of every baseline at every alpha (single points; k-independent), and of
    the oracle at every alpha. A system with ignore_feasibility (the twin N7, the unconstrained criterion) has every
    baseline point scored whatever its feasibility."""
    ignore = bool(getattr(system, "ignore_feasibility", False))
    base_f, base_p = [], []
    for name in BASELINE_NAMES:
        row_f, row_p = [], []
        for a in ALPHAS:
            out = make_baselines(encoding.units, a, context.vocabulary)[name]
            _, ex = compute_metrics_for_exact(world, replace(context, alpha=a), encoding, out)
            row_f.append(True if ignore else feasible(ex, taus))
            row_p.append(_score_positive(ex))
        base_f.append(row_f)
        base_p.append(row_p)
    oracle_f, oracle_p = [], []
    for a in ALPHAS:
        _, _, ex = Oracle().evaluate_exact(world, context, encoding, a, 0)
        oracle_f.append(feasible(ex, taus))
        oracle_p.append(_score_positive(ex))
    return {
        "base_feasible": _arr(base_f, bool),
        "base_positive": _arr(base_p, bool),
        "oracle_feasible": _arr(oracle_f, bool),
        "oracle_positive": _arr(oracle_p, bool),
        "no_oracle": _flag(not any(oracle_f)),
    }


def judge_g7a(d):
    if _is_undefined(d, "no_oracle"):
        return None
    scored = np.asarray(d["base_feasible"], dtype=bool) & np.asarray(d["base_positive"], dtype=bool)
    ok = not bool(scored.any())  # every baseline at every alpha is infeasible or scores 0
    anchor = bool((np.asarray(d["oracle_feasible"], dtype=bool) & np.asarray(d["oracle_positive"], dtype=bool)).any())
    return ok and anchor


# ======================================================================================================== G8
def collect_g8(system, world, context, encoding, results=None):
    """Exact fidelity and deviation over the grid as (numerator, denominator) pairs, shape (alphas, ks, 2); the number
    of hypotheses at (alpha0, k = 10); UNDEFINED if there is none or every (alpha, k) comparison is skipped."""
    results = results if results is not None else evaluate_grid(system, world, context, encoding)
    ex = [[results[(a, k)][2] for k in KS] for a in ALPHAS]
    fid = encode_pairs([ex[i][j]["fidelity"] for i in range(len(ALPHAS)) for j in range(len(KS))])
    dev = encode_pairs([ex[i][j]["deviation"] for i in range(len(ALPHAS)) for j in range(len(KS))])
    n_hyp = len(getattr(results[(ALPHA0, 10)][0], "hypotheses", ()))
    # raw integer denominators per alpha, for the descriptive single-atom arm (I-6). The stored fractions are in lowest
    # terms, so they do not give the number of atoms. |I| (the fidelity denominator) and the number of decided encoded
    # atoms (the deviation denominator) depend on the encoding and alpha only, not on k (SPEC section 8).
    n_I = [results[(a, 0)][1].size_I for a in ALPHAS]
    n_decided = [
        sum(1 for u in encoding.units.values() if unit_value(u, a) in (Belnap.T, Belnap.F)) for a in ALPHAS
    ]
    compared = sum(
        1 for i in range(len(ALPHAS)) for j in (1, 2)
        if ex[i][0]["fidelity"] is not None and ex[i][j]["fidelity"] is not None
    )
    return {
        "fidelity": fid.reshape(len(ALPHAS), len(KS), 2),
        "deviation": dev.reshape(len(ALPHAS), len(KS), 2),
        "n_hypotheses": _arr([n_hyp], np.int64),
        "undefined": _flag(n_hyp == 0 or compared == 0),
        "n_I": _arr(n_I, np.int64),
        "n_decided": _arr(n_decided, np.int64),
    }


def g8_comparisons(d):
    """[(alpha index, k index, fidelity drop, deviation rise)] over the compared (alpha, k) as exact Fractions, or None
    if the data are malformed. A comparison with an undefined fidelity is skipped."""
    fid = decode_pairs(d["fidelity"])
    dev = decode_pairs(d["deviation"])
    n_k = len(KS)
    if len(fid) != len(ALPHAS) * n_k or len(dev) != len(fid) or any(v is INVALID or v is None for v in dev):
        return None
    if any(v is INVALID for v in fid):
        return None
    out = []
    for i in range(len(ALPHAS)):
        f0, d0 = fid[i * n_k], dev[i * n_k]
        for j in (1, 2):
            fk, dk = fid[i * n_k + j], dev[i * n_k + j]
            if f0 is None or fk is None:
                continue
            out.append((i, j, f0 - fk, dk - d0))
    return out


def judge_g8(d):
    if _is_undefined(d, "undefined"):
        return None
    comps = g8_comparisons(d)
    if comps is None:
        return False
    ok = all(drop <= EPS_F and rise <= EPS_D for _, _, drop, rise in comps)
    anchor = bool(np.max(np.asarray(d["n_hypotheses"], dtype=float)) >= 1) and len(comps) >= 1
    return ok and anchor


# ======================================================================================================== T-1
def collect_t1(exacts: list, taus: ExactTaus):
    """T-1 data from exact metric dicts (one per point): feasibility under taus, uncertainty and new_false as exact
    (numerator, denominator) pairs."""
    feas = [feasible(ex, taus) for ex in exacts]
    return _t1_data(feas, [ex["uncertainty"] for ex in exacts], [ex["new_false"] for ex in exacts])


def collect_t1_all_points(exacts: list):
    """Descriptive reading I-2: every point with defined uncertainty and new_false counts as feasible."""
    feas = [ex["uncertainty"] is not None and ex["new_false"] is not None for ex in exacts]
    return _t1_data(feas, [ex["uncertainty"] for ex in exacts], [ex["new_false"] for ex in exacts])


def _t1_data(feas, unc, nf):
    distinct = len({u for u, f in zip(unc, feas) if f})
    return {
        "feasible": _arr(feas, bool),
        "uncertainty": encode_pairs(unc),
        "new_false": encode_pairs(nf),
        "undefined": _flag(distinct < 2),
    }


def t1_pairs(feas, u, nf, pair_filter=None):
    """True, False or None for T-1 on exact values. feas: booleans; u, nf: Fractions. pair_filter(i, j) restricts the
    pairs (p = i, q = j) considered. None if no considered pair has distinct uncertainty."""
    idx = [i for i in range(len(feas)) if feas[i]]
    defined = False
    for p in idx:
        for q in idx:
            if u[q] < u[p] and (pair_filter is None or pair_filter(p, q)):
                defined = True
                if nf[q] - nf[p] > DELTA:
                    return False
    return True if defined else None


def judge_t1(d):
    if _is_undefined(d, "undefined"):
        return None
    feas = np.asarray(d["feasible"], dtype=bool)
    u, nf = decode_pairs(d["uncertainty"]), decode_pairs(d["new_false"])
    if len(u) != len(feas) or len(nf) != len(feas):
        return False
    idx = [i for i in range(len(feas)) if feas[i]]
    if any(not isinstance(u[i], Fraction) or not isinstance(nf[i], Fraction) for i in idx):
        return False  # a feasible point must have exact uncertainty and new_false
    # anchor: at least two feasible points with distinct uncertainty (the check's own definedness condition)
    result = t1_pairs(list(feas), u, nf)
    return bool(result) if result is not None else False


JUDGES = {
    "G1": judge_g1, "G2": judge_g2, "G3": judge_g3, "G4": judge_g4, "G5": judge_g5, "G6": judge_g6,
    "G7": judge_g7a, "G8": judge_g8, "T-1": judge_t1,
}
