"""F3 recomputation for Tesaron v0.3 (INSTRUCTIONS_F3.md).

Written from scratch from SPEC.md, SPEC_v0.3.md, PREREG_v0.3.md and INSTRUCTIONS_F3.md.
Standard library only. Exact values are fractions.Fraction; floats are used only for the
encoded values (step 1), the boundary band (step 3) and the Wilson bound, as instructed.

Usage: python f3.py <task_folder>
"""
import glob
import json
import math
import os
import sys
from decimal import Decimal
from fractions import Fraction

TASK = sys.argv[1] if len(sys.argv) > 1 else r"E:\Independent\tasks\tesaron_v03_f3"
INP = os.path.join(TASK, "inputs")
OUT = os.path.join(TASK, "out")

NOTES = []  # unclear points / anomalies found while computing


def note(msg):
    NOTES.append(msg)
    print("NOTE:", msg)


# --------------------------------------------------------------------------- basics

def fstr(x):
    if x is None:
        return None
    assert isinstance(x, Fraction), x
    return f"{x.numerator}/{x.denominator}"


def parse_atom(s):
    i = s.index("(")
    assert s.endswith(")"), s
    return s[:i], tuple(s[i + 1:-1].split(","))


def atom_str(pred, args):
    return f"{pred}({','.join(args)})"


def is_var(t):
    return t[:1].isupper()


def vocabulary(w):
    ents = w["entities"]
    vocab = []
    for k in range(w["n_classes"]):
        for e in ents:
            vocab.append(f"c{k}({e})")
    for a in range(w["n_relations"]):
        for x in ents:
            for y in ents:
                if x != y:
                    vocab.append(f"r{a}({x},{y})")
    return vocab


def is_class_atom(a):
    return a.startswith("c")


def to_value(mp, mn, alpha):
    # SPEC section 6: pos = mu_pos >= alpha, neg = mu_neg >= alpha (equality counts); IEEE doubles.
    pos = mp >= alpha
    neg = mn >= alpha
    if pos and not neg:
        return "T"
    if neg and not pos:
        return "F"
    if pos and neg:
        return "B"
    return "U"


def num_ok(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def enc_map(units, alpha):
    out = {}
    for a, u in units.items():
        mp, mn, status = u[0], u[1], u[2]
        if status == "NOT_COMPUTED":
            out[a] = "U"
        else:
            assert num_ok(mp) and num_ok(mn), (a, u)
            out[a] = to_value(mp, mn, alpha)
    return out


def on_boundary(u, alpha, eps):
    # Float comparison, as IEEE doubles (INSTRUCTIONS step 3).
    mp, mn = u[0], u[1]
    return abs(mp - alpha) < eps or abs(mn - alpha) < eps


# --------------------------------------------------------------------------- closure (H)

def check_safety(rules):
    for r in rules:
        bvars = {t for lit in r["body"] for t in lit["args"] if is_var(t)}
        for t in r["head"]["args"]:
            if is_var(t):
                assert t in bvars, ("unsafe rule", r)


def match_body(body, idx, theta):
    if not body:
        yield dict(theta)
        return
    lit = body[0]
    for args in idx.get((lit["channel"], lit["pred"]), ()):
        if len(args) != len(lit["args"]):
            continue
        t2 = dict(theta)
        ok = True
        for t, v in zip(lit["args"], args):
            if is_var(t):
                if t in t2:
                    if t2[t] != v:
                        ok = False
                        break
                else:
                    t2[t] = v
            elif t != v:
                ok = False
                break
        if ok:
            yield from match_body(body[1:], idx, t2)


def closure_join(facts, rules, vocab_set):
    """Naive least fixpoint (strong negation: NEG body literal needs a NEG fact, NEG head adds a NEG fact)."""
    F = set(facts)
    rounds = 0
    while True:
        rounds += 1
        idx = {}
        for ch, a in F:
            p, args = parse_atom(a)
            idx.setdefault((ch, p), []).append(args)
        new = set()
        for r in sorted(rules, key=lambda r: r["id"]):
            h = r["head"]
            for theta in match_body(r["body"], idx, {}):
                args = tuple(theta[t] if is_var(t) else t for t in h["args"])
                a = atom_str(h["pred"], args)
                if a not in vocab_set:
                    continue  # out-of-vocabulary atoms are discarded
                f = (h["channel"], a)
                if f not in F:
                    new.add(f)
        if not new:
            break
        F |= new
    assert rounds <= 2 * len(vocab_set) + 1, rounds
    return F


def closure_bruteforce(facts, rules, vocab_set, entities):
    """Brute force: every assignment of entities to the rule's variables, every round, until no change."""
    from itertools import product
    F = set(facts)
    prepared = []
    for r in rules:
        vars_ = sorted({t for lit in r["body"] for t in lit["args"] if is_var(t)})
        prepared.append((r, vars_))
    while True:
        new = set()
        for r, vars_ in prepared:
            for vals in product(entities, repeat=len(vars_)):
                th = dict(zip(vars_, vals))
                ok = True
                for lit in r["body"]:
                    a = atom_str(lit["pred"], tuple(th[t] if is_var(t) else t for t in lit["args"]))
                    if (lit["channel"], a) not in F:
                        ok = False
                        break
                if not ok:
                    continue
                h = r["head"]
                a = atom_str(h["pred"], tuple(th[t] if is_var(t) else t for t in h["args"]))
                if a in vocab_set and (h["channel"], a) not in F:
                    new.add((h["channel"], a))
        if not new:
            return F
        F |= new


def compute_H(w, E, W, vocab_set, tag):
    rules = w["rules"]
    check_safety(rules)
    init = set()
    for a in E:
        init.add(("POS", a) if W[a] == "T" else ("NEG", a))
    F1 = closure_join(init, rules, vocab_set)
    F2 = closure_bruteforce(init, rules, vocab_set, w["entities"])
    if F1 != F2:
        note(f"{tag}: join closure and brute-force closure differ ({len(F1)} vs {len(F2)} facts); brute force used")
    F = F2
    chans = {}
    for ch, a in F:
        if a not in E:
            chans.setdefault(a, set()).add(ch)
    for a, chs in sorted(chans.items()):
        if len(chs) != 1:
            note(f"{tag}: H atom {a} has both channels (SPEC 8 assertion fails)")
            continue
        ch = next(iter(chs))
        if (ch == "POS") != (W[a] == "T"):
            note(f"{tag}: H atom {a} derived channel {ch} disagrees with world value {W[a]} (SPEC 8 assertion fails)")
    return set(chans)


# --------------------------------------------------------------------------- metrics

TF = ("T", "F")


def metrics(full, verdict, enc, I, H, K, W, vocab, units, val_units, alpha, eps):
    """full, verdict: dict atom -> value (missing = U). enc: dict over units. Returns dict of Fraction/None + n_q."""
    gf = lambda a: full.get(a, "U")
    gv = lambda a: verdict.get(a, "U")
    m = {}
    # fidelity
    m["fidelity"] = Fraction(sum(1 for a in I if gf(a) == W[a]), len(I)) if I else None
    # deviation
    D = [a for a in I if enc[a] in TF]
    m["deviation"] = Fraction(sum(1 for a in D if gf(a) != enc[a]), len(D)) if D else Fraction(0)
    # consistency, uncertainty
    if K:
        m["consistency"] = 1 - Fraction(sum(1 for a in K if gf(a) == "B"), len(K))
        m["uncertainty"] = Fraction(sum(1 for a in K if gv(a) == "U"), len(K))
    else:
        m["consistency"] = None
        m["uncertainty"] = None
    # new_true
    m["new_true"] = Fraction(sum(1 for a in H if gv(a) == W[a]), len(H)) if H else None
    # new_false, n_q
    Q = [a for a in vocab if a not in I and gv(a) in TF]
    n_q = len(Q)
    m["new_false"] = Fraction(sum(1 for a in Q if gv(a) != W[a]), n_q) if n_q else Fraction(0)
    # validation_agreement
    num = den = 0
    for a, u in val_units.items():
        vv = "U" if u[2] == "NOT_COMPUTED" else to_value(u[0], u[1], alpha)
        if vv in TF and gv(a) in TF:
            den += 1
            if vv == gv(a):
                num += 1
    m["validation_agreement"] = Fraction(num, den) if den else None
    # boundary_share
    if units:
        m["boundary_share"] = Fraction(sum(1 for u in units.values() if on_boundary(u, alpha, eps)), len(units))
    else:
        m["boundary_share"] = None
    m["n_q"] = n_q
    return m


def metrics_json(m):
    out = {}
    for key in ("fidelity", "deviation", "consistency", "uncertainty", "new_true", "new_false",
                "validation_agreement", "boundary_share"):
        out[key] = fstr(m[key])
    out["n_q"] = int(m["n_q"])
    return out


def feasible(m, tau):
    for key in ("fidelity", "consistency", "uncertainty", "new_true", "deviation"):
        if m[key] is None:
            return False
    return (m["fidelity"] >= tau["tau_s"] and m["deviation"] <= tau["tau_d"]
            and m["consistency"] >= tau["tau_t"] and m["uncertainty"] <= tau["tau_b"])


def score(m, tau):
    if not feasible(m, tau):
        return Fraction(0)
    return (1 - m["new_false"]) * m["new_true"]


# --------------------------------------------------------------------------- world loading

def load_world(path):
    with open(path, "r", encoding="utf-8") as fh:
        raw = fh.read()
    w = json.loads(raw)
    wdec = json.loads(raw, parse_float=Decimal)  # printed decimals (for sources_spanned)
    tag = f"{os.path.basename(path)}"
    vocab = vocabulary(w)
    vocab_set = set(vocab)
    assert len(vocab) == len(vocab_set)
    for a in w["true_atoms"]:
        assert a in vocab_set, (tag, a)
    for a in w["units"]:
        assert a in vocab_set, (tag, a)
    for a in w["validation_units"]:
        assert a in vocab_set, (tag, a)
    for ck, c in w["configs"].items():
        for view in ("full", "verdict"):
            for a, v in c[view].items():
                assert a in vocab_set, (tag, ck, view, a)
                assert v in ("T", "F", "B"), (tag, ck, view, a, v)
    true = set(w["true_atoms"])
    W = {a: ("T" if a in true else "F") for a in vocab}
    E = set(w["units"])
    H = compute_H(w, E, W, vocab_set, tag)
    K = E | H
    rel_dec = [Fraction(x) for x in wdec["source_reliabilities"]]
    for x in wdec["source_reliabilities"]:
        if not isinstance(x, Decimal) or -x.as_tuple().exponent > 3:
            note(f"{tag}: source reliability {x} not a decimal with at most 3 decimals")
    return dict(w=w, tag=tag, vocab=vocab, vocab_set=vocab_set, W=W, E=E, H=H, K=K, rel_dec=rel_dec)


def config_entries(w):
    """Yields (key, alpha_str, k_int) in input order."""
    out = []
    for ck in w["configs"]:
        a_str, k_str = ck.split("|")
        out.append((ck, a_str, int(k_str)))
    return out


def alpha_double(w, a_str):
    alpha = float(a_str)
    # The JSON number in "alphas" parsed to a double must be the same double.
    assert any(alpha == x for x in w["alphas"]), (a_str, w["alphas"])
    return alpha


def system_metrics(Wd, ck, a_str):
    w = Wd["w"]
    alpha = alpha_double(w, a_str)
    enc = enc_map(w["units"], alpha)
    I = {a for a in Wd["E"] if enc[a] != "U"}
    c = w["configs"][ck]
    return metrics(c["full"], c["verdict"], enc, I, Wd["H"], Wd["K"], Wd["W"], Wd["vocab"],
                   w["units"], w["validation_units"], alpha, w["epsilon_band"])


# --------------------------------------------------------------------------- step 0: tau

def compute_tau():
    cal_files = sorted(glob.glob(os.path.join(INP, "cal_*.json")))
    assert len(cal_files) == 40, len(cal_files)
    vals = {"fidelity": [], "consistency": [], "deviation": [], "uncertainty": []}
    for path in cal_files:
        Wd = load_world(path)
        w = Wd["w"]
        assert w["role"] == "calibration"
        assert list(w["configs"].keys()) == ["0.7|0"], w["configs"].keys()
        m = system_metrics(Wd, "0.7|0", "0.7")
        if len(Wd["H"]) < 10:
            note(f"{Wd['tag']}: |H| = {len(Wd['H'])} < 10 (PREREG 7 validity)")
        for key in vals:
            if m[key] is None:
                note(f"{Wd['tag']}: calibration metric {key} is undefined at 0.7|0")
            else:
                vals[key].append(m[key])
        out = {"world_seed": w["world_seed"], "metrics": {"0.7|0": metrics_json(m)}}
        write_json(os.path.join(OUT, f"cal_{w['world_seed']}.json"), out)
        assert os.path.basename(path) == f"cal_{w['world_seed']}.json"
    for key, v in vals.items():
        if len(v) != 40:
            note(f"tau: only {len(v)} defined values of {key}")
    asc = lambda key: sorted(vals[key])
    desc = lambda key: sorted(vals[key], reverse=True)
    tau = {
        "tau_s": asc("fidelity")[3],
        "tau_d": desc("deviation")[3],
        "tau_t": asc("consistency")[3],
        "tau_b": desc("uncertainty")[3],
    }
    write_json(os.path.join(OUT, "tau.json"), {k: fstr(tau[k]) for k in ("tau_s", "tau_d", "tau_t", "tau_b")})
    return tau


# --------------------------------------------------------------------------- per test world

def union_area(points):
    """Exact area of the union of [0,x] x [0,y] over points (x, y)."""
    pts = sorted(((x, y) for x, y in points if x > 0 and y > 0), key=lambda p: -p[0])
    area = Fraction(0)
    ymax = Fraction(0)
    for i, (x, y) in enumerate(pts):
        ymax = max(ymax, y)
        x_next = pts[i + 1][0] if i + 1 < len(pts) else Fraction(0)
        area += (x - x_next) * ymax
    return area


def test_world(path, tau):
    Wd = load_world(path)
    w = Wd["w"]
    tag = Wd["tag"]
    assert w["role"] == "test"
    assert os.path.basename(path) == f"{w['world_seed']}.json"
    if len(Wd["H"]) < 10:
        note(f"{tag}: |H| = {len(Wd['H'])} < 10 (PREREG 7 validity)")
    entries = config_entries(w)
    assert len(entries) == 30, len(entries)
    M = {}
    for ck, a_str, k in entries:
        M[ck] = system_metrics(Wd, ck, a_str)

    # step 4: feasible set
    feas = [ck for ck, _, _ in entries if feasible(M[ck], tau)]

    # step 5: Pareto front and hypervolume
    info = {ck: (a_str, k) for ck, a_str, k in entries}
    pts = {ck: (1 - M[ck]["new_false"], M[ck]["new_true"]) for ck in feas if M[ck]["new_true"] is not None}
    front = []
    for p, (px, py) in pts.items():
        dominated = False
        for q, (qx, qy) in pts.items():
            if q == p:
                continue
            if qx >= px and qy >= py and (qx > px or qy > py):
                dominated = True
                break
        if not dominated:
            front.append(p)
    front.sort(key=lambda ck: (-pts[ck][0], -pts[ck][1], Fraction(info[ck][0]), info[ck][1]))
    hv = union_area(pts.values())
    hv_front = union_area([pts[ck] for ck in front])
    assert hv == hv_front

    # step 6: G7a
    alpha_strs = []
    for _, a_str, _ in entries:
        if a_str not in alpha_strs:
            alpha_strs.append(a_str)
    vocab = Wd["vocab"]
    baseline_pos = False
    oracle_feasible_any = False
    oracle_pos_any = False
    for a_str in alpha_strs:
        alpha = alpha_double(w, a_str)
        enc = enc_map(w["units"], alpha)
        I = {a for a in Wd["E"] if enc[a] != "U"}
        views = {
            "echo": {a: enc[a] for a in vocab if a in enc and enc[a] != "U"},
            "all_false": {a: "F" for a in vocab},
            "all_unknown": {},
            "all_both": {a: "B" for a in vocab},
        }
        for name, view in views.items():
            m = metrics(view, view, enc, I, Wd["H"], Wd["K"], Wd["W"], vocab, w["units"],
                        w["validation_units"], alpha, w["epsilon_band"])
            if score(m, tau) > 0:
                baseline_pos = True
        oracle = {}
        for a in Wd["K"]:
            if a in I:
                oracle[a] = enc[a]
            else:
                oracle[a] = Wd["W"][a]
        m = metrics(oracle, oracle, enc, I, Wd["H"], Wd["K"], Wd["W"], vocab, w["units"],
                    w["validation_units"], alpha, w["epsilon_band"])
        if feasible(m, tau):
            oracle_feasible_any = True
            if score(m, tau) > 0:
                oracle_pos_any = True
    if not oracle_feasible_any:
        g7a = "UNDEFINED"
        if baseline_pos:
            note(f"{tag}: G7a: the oracle has no feasible point and a baseline scores > 0; written UNDEFINED (instruction: UNDEFINED iff the oracle has no feasible point)")
    elif (not baseline_pos) and oracle_pos_any:
        g7a = "HOLDS"
    else:
        g7a = "FAILS"
        if not baseline_pos:
            note(f"{tag}: G7a: no baseline scores > 0, the oracle is feasible but never scores > 0; written FAILS ('FAILS otherwise')")

    # step 7: T-1 at k = 0
    t1pts = [(a_str, M[ck]) for ck, a_str, k in entries if k == 0 and ck in feas]
    t1pts.sort(key=lambda p: Fraction(p[0]), reverse=True)  # largest alpha first
    distinct_u = {m["uncertainty"] for _, m in t1pts}
    increases = []
    violated = False
    for ap, mp in t1pts:
        for aq, mq in t1pts:
            if mq["uncertainty"] < mp["uncertainty"]:
                inc = mq["new_false"] - mp["new_false"]
                nq = mq["n_q"]
                bound = max(Fraction(1, 20), Fraction(1, nq)) if nq > 0 else Fraction(1, 20)
                increases.append(inc)
                if inc > bound:
                    violated = True
    if len(distinct_u) < 2:
        t1 = "UNDEFINED"
    elif violated:
        t1 = "FAILS"
    else:
        t1 = "HOLDS"

    # step 8: structure
    feasible_alphas = [a for a, _ in t1pts]
    defined = t1 != "UNDEFINED"
    st = {"feasible_alphas": feasible_alphas, "defined": defined, "alpha_min": None, "alpha_max": None,
          "sources_spanned": None, "wrong_class_atoms_spanned": None, "largest_increase": None}
    if defined:
        a_min = min(feasible_alphas, key=Fraction)
        a_max = max(feasible_alphas, key=Fraction)
        fmin, fmax = Fraction(a_min), Fraction(a_max)
        spanned = sum(1 for rho in Wd["rel_dec"] if fmin <= rho < fmax)
        enc_min = enc_map(w["units"], alpha_double(w, a_min))
        enc_max = enc_map(w["units"], alpha_double(w, a_max))
        wrong = sum(1 for a in w["units"] if is_class_atom(a) and enc_min[a] == "T" and enc_max[a] != "T"
                    and Wd["W"][a] == "F")
        assert increases
        st.update(alpha_min=a_min, alpha_max=a_max, sources_spanned=spanned,
                  wrong_class_atoms_spanned=wrong, largest_increase=fstr(max(increases)))

    out = {
        "world_seed": w["world_seed"],
        "metrics": {ck: metrics_json(M[ck]) for ck, _, _ in entries},
        "feasible": feas,
        "pareto_front": front,
        "hypervolume": fstr(hv),
        "outcomes": {"G7a": g7a, "T-1": t1},
        "t1_structure": st,
    }
    write_json(os.path.join(OUT, f"{w['world_seed']}.json"), out)
    return dict(seed=w["world_seed"], draw=w["draw_index"], given=w["given_outcomes_g1_g6"],
                G7a=g7a, T1=t1, st=st)


# --------------------------------------------------------------------------- verdict table

def wilson_lower(n_holds, n):
    z = 1.6448536269514722
    p = n_holds / n
    z2 = z * z
    centre = p + z2 / (2 * n)
    spread = z * math.sqrt(p * (1 - p) / n + z2 / (4 * n * n))
    return (centre - spread) / (1 + z2 / n)


def verdict_table(results):
    rows = []
    tests = ["G1", "G2", "G3", "G4", "G5", "G6", "G7", "T-1"]
    for t in tests:
        outs = []
        for r in results:
            if t in ("G1", "G2", "G3", "G4", "G5", "G6"):
                o = r["given"][t]
            elif t == "G7":
                o = r["G7a"]
            else:
                o = r["T1"]
            assert o in ("HOLDS", "FAILS", "UNDEFINED"), (t, o)
            outs.append((r["draw"], r["seed"], o))
        nh = sum(1 for _, _, o in outs if o == "HOLDS")
        nf = sum(1 for _, _, o in outs if o == "FAILS")
        nu = sum(1 for _, _, o in outs if o == "UNDEFINED")
        nd = nh + nf
        fails = sorted((d, s) for d, s, o in outs if o == "FAILS")
        ffw = fails[0][1] if fails else None
        if t != "T-1":
            verdict = "FAILS" if nf > 0 else ("HOLDS" if nd >= 16 else "INSUFFICIENT")
            wl = None
        else:
            if nd == 0:
                wl = None
                b = None
            else:
                b = wilson_lower(nh, nd)
                wl = format(b, ".3f")
            if nd < 16:
                verdict = "INSUFFICIENT"
            else:
                verdict = "HOLDS" if b >= 0.80 else "FAILS"
        rows.append({"test": t, "verdict": verdict, "n_holds": nh, "n_fails": nf, "n_undefined": nu,
                     "n_defined": nd, "wilson_lower": wl, "first_failing_world": ffw})
    defined = [r["st"] for r in results if r["T1"] != "UNDEFINED"]
    n = len(defined)
    if n == 0:
        counts = {"n": 0, "median": None, "even": None, "min": None, "max": None, "n_with_wrong_class_atom": 0}
    else:
        ss = sorted(s["sources_spanned"] for s in defined)
        if n % 2 == 1:
            med = str(ss[n // 2])
        else:
            tot = ss[n // 2 - 1] + ss[n // 2]
            med = str(tot // 2) if tot % 2 == 0 else f"{tot // 2}.5"
        counts = {"n": n, "median": med, "even": n % 2 == 0, "min": ss[0], "max": ss[-1],
                  "n_with_wrong_class_atom": sum(1 for s in defined if s["wrong_class_atoms_spanned"] >= 1)}
    return {"rows": rows, "t1_structure_counts": counts}


# --------------------------------------------------------------------------- io

def assert_no_float(o):
    if isinstance(o, float):
        raise AssertionError("float in output")
    if isinstance(o, dict):
        for v in o.values():
            assert_no_float(v)
    elif isinstance(o, list):
        for v in o:
            assert_no_float(v)


def write_json(path, obj):
    assert_no_float(obj)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(obj, fh, indent=1)
        fh.write("\n")


def main():
    tau = compute_tau()
    print("tau:", {k: fstr(v) for k, v in tau.items()})
    test_files = sorted(p for p in glob.glob(os.path.join(INP, "*.json"))
                        if not os.path.basename(p).startswith("cal_"))
    assert len(test_files) == 50, len(test_files)
    results = []
    for path in test_files:
        results.append(test_world(path, tau))
    vt = verdict_table(results)
    write_json(os.path.join(OUT, "verdict_table.json"), vt)
    with open(os.path.join(TASK, "scratch", "run_notes.json"), "w", encoding="utf-8") as fh:
        json.dump(NOTES, fh, indent=1)
    print("rows:")
    for r in vt["rows"]:
        print(" ", r)
    print("counts:", vt["t1_structure_counts"])
    print("notes:", len(NOTES))


if __name__ == "__main__":
    main()
