"""F3 independent recomputation for Tesaron v0.2.

Written from INSTRUCTIONS_F3.md, SPEC.md (sections 1, 5-10), PREREG_v0.2.md (sections 3-5) and OUTPUT_SCHEMA.json.
Standard library only. Usage:
    python -I f3.py <task_folder>
Reads <task_folder>/inputs/*.json, writes <task_folder>/out/<world_seed>.json and verdict_table.json, and writes
diagnostics to <task_folder>/scratch/diagnostics.json.
"""
import glob
import itertools
import json
import math
import os
import re
import sys
from fractions import Fraction

VALUES = ("T", "F", "B", "U")
ATOM_RE = re.compile(r"^([A-Za-z0-9_]+)\((.*)\)$")


def parse_atom(s):
    m = ATOM_RE.match(s)
    if not m:
        raise ValueError("bad atom " + s)
    pred = m.group(1)
    args = tuple(a.strip() for a in m.group(2).split(","))
    return pred, args


def atom_str(pred, args):
    return pred + "(" + ",".join(args) + ")"


def fstr(fr):
    if fr is None:
        return None
    assert isinstance(fr, Fraction)
    assert fr >= 0
    return "%d/%d" % (fr.numerator, fr.denominator)


def ratio(num, den, empty):
    """num/den as Fraction; `empty` is returned when den == 0."""
    if den == 0:
        return empty
    return Fraction(num, den)


def to_value(mu_pos, mu_neg, alpha):
    pos = mu_pos >= alpha
    neg = mu_neg >= alpha
    if pos and not neg:
        return "T"
    if neg and not pos:
        return "F"
    if pos and neg:
        return "B"
    return "U"


def build_vocab(d):
    ents = list(d["entities"])
    vocab = []
    for k in range(d["n_classes"]):
        for e in ents:
            vocab.append(atom_str("c%d" % k, (e,)))
    for a in range(d["n_relations"]):
        for x in ents:
            for y in ents:
                if x != y:
                    vocab.append(atom_str("r%d" % a, (x, y)))
    return vocab


def is_var(arg):
    return len(arg) > 0 and arg[0].isupper()


def closure(facts, rules, entities, vocab_set):
    """Brute-force least fixpoint of (channel, atom) facts under the rules.

    Every rule is grounded over every assignment of entities to its variables; a body literal with channel C requires
    the fact (C, atom); the head adds (C_head, atom_head). Atoms outside the vocabulary are discarded.
    """
    facts = set(facts)
    grounded = []
    for r in rules:
        vars_ = []
        for lit in [r["head"]] + list(r["body"]):
            for a in lit["args"]:
                if is_var(a) and a not in vars_:
                    vars_.append(a)
        grounded.append((r, vars_))
    while True:
        new = set()
        for r, vars_ in grounded:
            for combo in itertools.product(entities, repeat=len(vars_)):
                sub = dict(zip(vars_, combo))

                def ground(lit):
                    args = tuple(sub[a] if is_var(a) else a for a in lit["args"])
                    return (lit["channel"], atom_str(lit["pred"], args))

                ok = True
                for lit in r["body"]:
                    if ground(lit) not in facts:
                        ok = False
                        break
                if not ok:
                    continue
                h = ground(r["head"])
                if h[1] in vocab_set and h not in facts:
                    new.add(h)
        if not new:
            return facts
        facts |= new


def compute_metrics(full, verdict, enc, I, E, H, K, W, vocab, units, vunits, alpha, eps):
    """All SPEC section 8 metrics as Fractions (or None).

    full, verdict, enc: dict atom -> value, missing = U. I is the set for this alpha.
    """
    def fv(a):
        return full.get(a, "U")

    def vv(a):
        return verdict.get(a, "U")

    def ev(a):
        return enc.get(a, "U")

    # fidelity
    fid_num = sum(1 for a in I if fv(a) == W[a])
    fidelity = ratio(fid_num, len(I), None)
    # deviation
    dev_den_set = [a for a in I if ev(a) in ("T", "F")]
    dev_num = sum(1 for a in dev_den_set if fv(a) != ev(a))
    deviation = ratio(dev_num, len(dev_den_set), Fraction(0, 1))
    # consistency
    if len(K) == 0:
        consistency = None
    else:
        consistency = 1 - Fraction(sum(1 for a in K if fv(a) == "B"), len(K))
    # uncertainty
    uncertainty = ratio(sum(1 for a in K if vv(a) == "U"), len(K), None)
    # new_true
    new_true = ratio(sum(1 for a in H if vv(a) == W[a]), len(H), None)
    # new_false
    nf_den = [a for a in vocab if a not in I and vv(a) in ("T", "F")]
    nf_num = sum(1 for a in nf_den if vv(a) != W[a])
    new_false = ratio(nf_num, len(nf_den), Fraction(0, 1))
    # validation_agreement
    va_den = 0
    va_num = 0
    for a, u in vunits.items():
        if u[2] == "NOT_COMPUTED":
            val = "U"
        else:
            val = to_value(u[0], u[1], alpha)
        if val in ("T", "F") and vv(a) in ("T", "F"):
            va_den += 1
            if val == vv(a):
                va_num += 1
    validation_agreement = ratio(va_num, va_den, None)
    # boundary_share (float comparison of |mu - alpha| < epsilon_band)
    nb = 0
    for a, u in units.items():
        if abs(u[0] - alpha) < eps or abs(u[1] - alpha) < eps:
            nb += 1
    boundary_share = ratio(nb, len(units), None)
    return {
        "fidelity": fidelity,
        "deviation": deviation,
        "consistency": consistency,
        "uncertainty": uncertainty,
        "new_true": new_true,
        "new_false": new_false,
        "validation_agreement": validation_agreement,
        "boundary_share": boundary_share,
    }


def feasible(m, taus):
    for key in ("fidelity", "consistency", "uncertainty", "new_true"):
        if m[key] is None:
            return False
    return (m["fidelity"] >= taus["tau_s"] and m["deviation"] <= taus["tau_d"]
            and m["consistency"] >= taus["tau_t"] and m["uncertainty"] <= taus["tau_b"])


def single_score(m, taus):
    if not feasible(m, taus):
        return Fraction(0)
    return (1 - m["new_false"]) * m["new_true"]


def hypervolume(points):
    """Exact area of the union of [0,x]x[0,y]."""
    pts = sorted(points, key=lambda p: (-p[0], -p[1]))
    area = Fraction(0)
    ymax = Fraction(0)
    for x, y in pts:
        if y > ymax:
            area += x * (y - ymax)
            ymax = y
    return area


DELTA = Fraction(1, 20)


def t1_pairs(points, pair_filter):
    """points: list of (alpha_fraction, unc, nf). Returns None / False / True."""
    any_distinct = False
    violated = False
    for p in points:
        for q in points:
            if p is q:
                continue
            if not pair_filter(p[0], q[0]):
                continue
            if q[1] < p[1]:
                any_distinct = True
                if q[2] - p[2] > DELTA:
                    violated = True
    if not any_distinct:
        return None
    return not violated


def process_world(d, diag):
    seed = d["world_seed"]
    vocab = build_vocab(d)
    vocab_set = set(vocab)
    entities = list(d["entities"])
    true_set = set(d["true_atoms"])
    wd = {"world_seed": seed, "problems": []}
    for a in true_set:
        if a not in vocab_set:
            wd["problems"].append("true atom outside vocab: " + a)
    W = {a: ("T" if a in true_set else "F") for a in vocab}
    units = d["units"]
    vunits = d["validation_units"]
    for a in list(units) + list(vunits):
        if a not in vocab_set:
            wd["problems"].append("unit atom outside vocab: " + a)
    eps = d["epsilon_band"]
    taus = {k: Fraction(v) for k, v in d["taus"].items()}

    # configs: key -> (alpha_str, alpha_float, k)
    cfgs = {}
    for key in d["configs"]:
        astr, kstr = key.split("|")
        cfgs[key] = (astr, float(astr), int(kstr))
    alpha_strs = sorted({v[0] for v in cfgs.values()}, key=lambda s: -float(s))
    for a in d["alphas"]:
        if repr(float(a)) not in alpha_strs:
            wd["problems"].append("alpha %r not among config keys" % a)

    # Sets
    E = set(units.keys())
    enc_by_alpha = {}
    I_by_alpha = {}
    ties = []
    for astr in alpha_strs:
        alpha = float(astr)
        enc = {}
        for a, u in units.items():
            if u[2] == "NOT_COMPUTED":
                val = "U"
            else:
                val = to_value(u[0], u[1], alpha)
                if u[0] == alpha or u[1] == alpha:
                    ties.append((a, astr))
            if val != "U":
                enc[a] = val
        enc_by_alpha[astr] = enc
        I_by_alpha[astr] = set(enc.keys())
    wd["enc_ties"] = ties
    # boundary diagnostics: float vs exact-on-doubles vs exact-decimal
    bdiff = []
    for astr in alpha_strs:
        alpha = float(astr)
        for a, u in units.items():
            for mu in (u[0], u[1]):
                f1 = abs(mu - alpha) < eps
                f2 = abs(Fraction(mu) - Fraction(alpha)) < Fraction(eps)
                f3 = abs(Fraction(repr(mu)) - Fraction(astr)) < Fraction(repr(eps))
                if not (f1 == f2 == f3):
                    bdiff.append((a, astr, mu, f1, f2, f3))
    wd["boundary_method_differences"] = bdiff

    start = set()
    for a in E:
        start.add(("POS" if W[a] == "T" else "NEG", a))
    fix = closure(start, d["rules"], entities, vocab_set)
    H = set()
    hch = {}
    for ch, a in fix:
        if a not in E:
            H.add(a)
            hch.setdefault(a, set()).add(ch)
    for a, chs in hch.items():
        if len(chs) != 1:
            wd["problems"].append("H atom with both channels: " + a)
        ch = next(iter(chs))
        if (ch == "POS") != (W[a] == "T"):
            wd["problems"].append("H atom channel disagrees with W: " + a)
    K = E | H
    wd["counts"] = {"E": len(E), "H": len(H), "K": len(K),
                    "I": {s: len(I_by_alpha[s]) for s in alpha_strs}}

    # Metrics per config
    metrics = {}
    for key, c in d["configs"].items():
        astr, alpha, k = cfgs[key]
        for part in ("full", "verdict"):
            for a, v in c[part].items():
                if a not in vocab_set:
                    wd["problems"].append("%s atom outside vocab at %s: %s" % (part, key, a))
                if v not in VALUES:
                    wd["problems"].append("bad value %r" % v)
        metrics[key] = compute_metrics(c["full"], c["verdict"], enc_by_alpha[astr], I_by_alpha[astr], E, H, K, W,
                                       vocab, units, vunits, alpha, eps)

    # k-independence of verdict (descriptive check only)
    kdep = []
    for astr in alpha_strs:
        base = d["configs"].get(astr + "|0", {}).get("verdict")
        for kk in (5, 10):
            v = d["configs"].get("%s|%d" % (astr, kk), {}).get("verdict")
            if base is not None and v is not None and v != base:
                kdep.append("%s|%d" % (astr, kk))
    wd["verdict_k_dependent_configs"] = kdep

    # Feasible set
    feas = [key for key in d["configs"] if feasible(metrics[key], taus)]

    # Pareto front
    pts = {}
    for key in feas:
        m = metrics[key]
        if m["new_true"] is None:
            continue
        pts[key] = (1 - m["new_false"], m["new_true"])
    front = []
    for key, p in pts.items():
        dominated = False
        for key2, q in pts.items():
            if key2 == key:
                continue
            if q[0] >= p[0] and q[1] >= p[1] and (q[0] > p[0] or q[1] > p[1]):
                dominated = True
                break
        if not dominated:
            front.append(key)
    front.sort(key=lambda kk: (-pts[kk][0], -pts[kk][1], Fraction(cfgs[kk][0]), cfgs[kk][2]))
    hv = hypervolume(list(pts.values()))

    # G7a
    a0, k0 = d["default_configuration"]
    baseline_scores = {}
    oracle_feasible_any = False
    oracle_pos_any = False
    baseline_pos = []
    for astr in alpha_strs:
        alpha = float(astr)
        enc = enc_by_alpha[astr]
        I = I_by_alpha[astr]
        bl = {
            "echo": dict(enc),
            "all_true": {a: "T" for a in vocab},
            "all_false": {a: "F" for a in vocab},
            "all_unknown": {},
            "all_both": {a: "B" for a in vocab},
        }
        for name, out in bl.items():
            m = compute_metrics(out, out, enc, I, E, H, K, W, vocab, units, vunits, alpha, eps)
            s = single_score(m, taus)
            baseline_scores["%s@%s" % (name, astr)] = {"feasible": feasible(m, taus), "score": fstr(s)}
            if s > 0:
                baseline_pos.append("%s@%s" % (name, astr))
        oracle = {}
        for a in K:
            if a in I:
                oracle[a] = enc[a]
            else:
                oracle[a] = W[a]
        m = compute_metrics(oracle, oracle, enc, I, E, H, K, W, vocab, units, vunits, alpha, eps)
        of = feasible(m, taus)
        os_ = single_score(m, taus)
        baseline_scores["oracle@%s" % astr] = {"feasible": of, "score": fstr(os_),
                                               "metrics": {k_: fstr(v_) for k_, v_ in m.items()}}
        if of:
            oracle_feasible_any = True
            if os_ > 0:
                oracle_pos_any = True
    if not oracle_feasible_any:
        g7a = "UNDEFINED"
    elif not baseline_pos and oracle_pos_any:
        g7a = "HOLDS"
    else:
        g7a = "FAILS"
    wd["g7a_detail"] = {"baseline_positive": baseline_pos, "oracle_feasible_any": oracle_feasible_any,
                        "oracle_positive_any": oracle_pos_any, "scores": baseline_scores}

    # G8
    a0str = repr(float(a0))
    anchor_key = "%s|10" % a0str
    c_anchor = d["configs"][anchor_key]
    hyp_atoms = [a for a in vocab if c_anchor["full"].get(a, "U") != "U" and c_anchor["verdict"].get(a, "U") == "U"]
    hyp_tf = [a for a in hyp_atoms if c_anchor["full"][a] in ("T", "F")]
    wd["g8_hypotheses_at_anchor"] = {"full_not_U": len(hyp_atoms), "full_T_or_F": len(hyp_tf)}
    n_comp = 0
    viol = []
    for astr in alpha_strs:
        m0 = metrics["%s|0" % astr]
        for kk in (5, 10):
            mk = metrics["%s|%d" % (astr, kk)]
            if m0["fidelity"] is None or mk["fidelity"] is None:
                continue
            n_comp += 1
            if m0["fidelity"] - mk["fidelity"] > Fraction(1, 20) or mk["deviation"] - m0["deviation"] > Fraction(1, 50):
                viol.append("%s|%d" % (astr, kk))
    if len(hyp_atoms) == 0 or n_comp == 0:
        g8 = "UNDEFINED"
    elif viol:
        g8 = "FAILS"
    else:
        g8 = "HOLDS"
    wd["g8_detail"] = {"n_comparisons": n_comp, "violations": viol}

    # T-1
    fpts = [(Fraction(cfgs[key][0]), metrics[key]["uncertainty"], metrics[key]["new_false"]) for key in feas]
    distinct_unc = {p[1] for p in fpts}
    if len(distinct_unc) < 2:
        t1 = "UNDEFINED"
    else:
        r = t1_pairs(fpts, lambda ap, aq: True)
        t1 = "HOLDS" if r else "FAILS"

    lo60 = Fraction(60, 100)
    hi65 = Fraction(65, 100)
    lo80 = Fraction(80, 100)
    hi85 = Fraction(85, 100)
    window = {Fraction(80, 100), Fraction(75, 100), Fraction(70, 100), Fraction(65, 100)}

    def crossing(ap, aq, lo, hi):
        return (ap <= lo and aq >= hi) or (aq <= lo and ap >= hi)

    t1s = {
        "some_alpha_le_060_feasible": any(p[0] <= lo60 for p in fpts),
        "alpha_ge_085_feasible": any(p[0] >= hi85 for p in fpts),
        "t1_window_pairs": t1_pairs(fpts, lambda ap, aq: ap in window and aq in window),
        "t1_crossing_pairs": t1_pairs(fpts, lambda ap, aq: crossing(ap, aq, lo60, hi65)),
        "t1_cross_080_085": t1_pairs(fpts, lambda ap, aq: crossing(ap, aq, lo80, hi85)),
    }

    out = {
        "world_seed": seed,
        "metrics": {key: {mk: fstr(mv) for mk, mv in metrics[key].items()} for key in d["configs"]},
        "feasible": feas,
        "pareto_front": front,
        "hypervolume": fstr(hv),
        "outcomes": {"G7a": g7a, "G8": g8, "T-1": t1},
        "t1_structure": t1s,
    }
    diag.append(wd)
    return out


def wilson(n_holds, n):
    z = 1.6448536269514722
    p = n_holds / n
    z2 = z * z
    centre = p + z2 / (2 * n)
    spread = z * math.sqrt(p * (1 - p) / n + z2 / (4 * n * n))
    bound = (centre - spread) / (1 + z2 / n)
    return bound


def main(task):
    in_dir = os.path.join(task, "inputs")
    out_dir = os.path.join(task, "out")
    scratch = os.path.join(task, "scratch")
    os.makedirs(scratch, exist_ok=True)
    files = sorted(glob.glob(os.path.join(in_dir, "*.json")))
    diag = []
    worlds = []
    for f in files:
        with open(f, "r", encoding="utf-8") as fh:
            d = json.load(fh)
        expect = os.path.splitext(os.path.basename(f))[0]
        assert str(d["world_seed"]) == expect, (f, d["world_seed"])
        res = process_world(d, diag)
        with open(os.path.join(out_dir, "%d.json" % d["world_seed"]), "w", encoding="utf-8") as fh:
            json.dump(res, fh, indent=1, sort_keys=False)
            fh.write("\n")
        outc = dict(d["given_outcomes_g1_g6"])
        outc["G7"] = res["outcomes"]["G7a"]
        outc["G8"] = res["outcomes"]["G8"]
        outc["T-1"] = res["outcomes"]["T-1"]
        worlds.append((d["draw_index"], d["world_seed"], outc))
    worlds.sort()
    rows = []
    for test in ["G1", "G2", "G3", "G4", "G5", "G6", "G7", "G8", "T-1"]:
        oc = [(di, s, o[test]) for di, s, o in worlds]
        for _, _, v in oc:
            assert v in ("HOLDS", "FAILS", "UNDEFINED"), (test, v)
        nh = sum(1 for x in oc if x[2] == "HOLDS")
        nf = sum(1 for x in oc if x[2] == "FAILS")
        nu = sum(1 for x in oc if x[2] == "UNDEFINED")
        nd = nh + nf
        fails = [x for x in oc if x[2] == "FAILS"]
        ffw = min(fails)[1] if fails else None
        if test in ("G8", "T-1"):
            wl = None if nd == 0 else wilson(nh, nd)
            if nd < 16:
                verdict = "INSUFFICIENT"
            else:
                verdict = "HOLDS" if wl >= 0.80 else "FAILS"
            wls = None if wl is None else format(wl, ".3f")
        else:
            if nf > 0:
                verdict = "FAILS"
            elif nd >= 16:
                verdict = "HOLDS"
            else:
                verdict = "INSUFFICIENT"
            wls = None
        rows.append({"test": test, "verdict": verdict, "n_holds": nh, "n_fails": nf, "n_undefined": nu,
                     "n_defined": nd, "wilson_lower": wls, "first_failing_world": ffw})
    with open(os.path.join(out_dir, "verdict_table.json"), "w", encoding="utf-8") as fh:
        json.dump({"rows": rows}, fh, indent=1)
        fh.write("\n")
    with open(os.path.join(scratch, "diagnostics.json"), "w", encoding="utf-8") as fh:
        json.dump(diag, fh, indent=1, default=str)
        fh.write("\n")
    print(json.dumps(rows, indent=1))


if __name__ == "__main__":
    main(sys.argv[1])
