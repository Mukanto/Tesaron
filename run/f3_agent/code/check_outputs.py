"""Structural check of the F3 outputs against OUTPUT_SCHEMA.json (hand-written, standard library only)."""
import glob
import json
import math
import os
import re
import sys
from fractions import Fraction

FRAC = re.compile(r"^[0-9]+/[1-9][0-9]*$")
KEY = re.compile(r"^[0-9.]+[|](0|5|10)$")
METRICS = ["fidelity", "deviation", "consistency", "uncertainty", "new_true", "new_false", "validation_agreement",
           "boundary_share"]
OUTC = {"HOLDS", "FAILS", "UNDEFINED"}


def no_floats(o, path, errs):
    if isinstance(o, float):
        errs.append("float at " + path)
    elif isinstance(o, dict):
        for k, v in o.items():
            no_floats(v, path + "/" + str(k), errs)
    elif isinstance(o, list):
        for i, v in enumerate(o):
            no_floats(v, path + "/" + str(i), errs)


def frac_ok(s, nullable, errs, where):
    if s is None:
        if not nullable:
            errs.append("null not allowed at " + where)
        return
    if not isinstance(s, str) or not FRAC.match(s):
        errs.append("bad fraction %r at %s" % (s, where))
        return
    n, d = s.split("/")
    f = Fraction(int(n), int(d))
    if f.numerator != int(n) or f.denominator != int(d):
        errs.append("not lowest terms %r at %s" % (s, where))


def main(task):
    out = os.path.join(task, "out")
    inp = os.path.join(task, "inputs")
    errs = []
    inputs = sorted(glob.glob(os.path.join(inp, "*.json")))
    jsons = sorted(os.path.basename(p) for p in glob.glob(os.path.join(out, "*.json")))
    expected = sorted([os.path.basename(p) for p in inputs] + ["verdict_table.json"])
    if jsons != expected:
        errs.append("json file set mismatch: extra %s missing %s" % (sorted(set(jsons) - set(expected)),
                                                                     sorted(set(expected) - set(jsons))))
    for p in inputs:
        d = json.load(open(p, encoding="utf-8"))
        name = os.path.basename(p)
        o = json.load(open(os.path.join(out, name), encoding="utf-8"))
        no_floats(o, name, errs)
        req = ["world_seed", "metrics", "feasible", "pareto_front", "hypervolume", "outcomes", "t1_structure"]
        if sorted(o.keys()) != sorted(req):
            errs.append("%s keys %s" % (name, sorted(o.keys())))
        if o["world_seed"] != d["world_seed"] or not isinstance(o["world_seed"], int):
            errs.append(name + " world_seed")
        if sorted(o["metrics"].keys()) != sorted(d["configs"].keys()) or len(o["metrics"]) != 30:
            errs.append(name + " metric keys")
        for k, m in o["metrics"].items():
            if not KEY.match(k):
                errs.append(name + " bad key " + k)
            if sorted(m.keys()) != sorted(METRICS):
                errs.append(name + " metric names at " + k)
            for mk in METRICS:
                frac_ok(m.get(mk), True, errs, "%s %s %s" % (name, k, mk))
        for k in o["feasible"] + o["pareto_front"]:
            if k not in d["configs"]:
                errs.append(name + " unknown key " + k)
        if not set(o["pareto_front"]) <= set(o["feasible"]):
            errs.append(name + " front not subset of feasible")
        if len(set(o["feasible"])) != len(o["feasible"]):
            errs.append(name + " duplicate feasible")
        frac_ok(o["hypervolume"], False, errs, name + " hypervolume")
        if sorted(o["outcomes"].keys()) != ["G7a", "G8", "T-1"]:
            errs.append(name + " outcomes keys")
        for v in o["outcomes"].values():
            if v not in OUTC:
                errs.append(name + " outcome " + str(v))
        t = o["t1_structure"]
        if sorted(t.keys()) != sorted(["some_alpha_le_060_feasible", "alpha_ge_085_feasible", "t1_window_pairs",
                                       "t1_crossing_pairs", "t1_cross_080_085"]):
            errs.append(name + " t1 keys")
        for f in ("some_alpha_le_060_feasible", "alpha_ge_085_feasible"):
            if not isinstance(t[f], bool):
                errs.append(name + " " + f)
        for f in ("t1_window_pairs", "t1_crossing_pairs", "t1_cross_080_085"):
            if t[f] is not None and not isinstance(t[f], bool):
                errs.append(name + " " + f)
    vt = json.load(open(os.path.join(out, "verdict_table.json"), encoding="utf-8"))
    no_floats(vt, "verdict_table", errs)
    if list(vt.keys()) != ["rows"]:
        errs.append("verdict_table keys")
    tests = [r["test"] for r in vt["rows"]]
    if tests != ["G1", "G2", "G3", "G4", "G5", "G6", "G7", "G8", "T-1"]:
        errs.append("verdict rows %s" % tests)
    for r in vt["rows"]:
        if sorted(r.keys()) != sorted(["test", "verdict", "n_holds", "n_fails", "n_undefined", "n_defined",
                                       "wilson_lower", "first_failing_world"]):
            errs.append("row keys " + r["test"])
        if r["verdict"] not in ("HOLDS", "FAILS", "INSUFFICIENT"):
            errs.append("row verdict " + r["test"])
        if r["n_defined"] != r["n_holds"] + r["n_fails"] or r["n_defined"] + r["n_undefined"] != len(inputs):
            errs.append("row counts " + r["test"])
        w = r["wilson_lower"]
        if w is not None and not re.match(r"^[0-9][.][0-9]{3}$", w):
            errs.append("row wilson " + r["test"])
        if r["first_failing_world"] is not None and not isinstance(r["first_failing_world"], int):
            errs.append("row ffw " + r["test"])
    print("errors:", len(errs))
    for e in errs[:50]:
        print(e)


if __name__ == "__main__":
    main(sys.argv[1])
