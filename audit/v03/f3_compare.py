"""F3 comparison of Tesaron v0.3: the run's own numbers against the F3 agent's results (PREREG_v0.3 sections 6.1 and 8), frozen
with audit/.

    py -m audit.v03.f3_compare RUN_DIR AGENT_DIR [-o F3_COMPARE.json]

RUN_DIR is the run folder (run/v03): its outputs_results/<seed>.json (test worlds) and outputs_results/cal_<seed>.json
(calibration worlds), VERDICTS.json and TAU.json. AGENT_DIR holds what the fresh F3 agent wrote: <seed>.json for every test
world, cal_<seed>.json for every calibration world, tau.json and verdict_table.json (the schema is
audit/v03/f3/OUTPUT_SCHEMA.json). The comparison is fixed here, before the run, so that what counts as a disagreement is not
chosen after the numbers are seen:

  - tau (four values): exact string equality of the "p/q" values;
  - every metric of every grid point of every test world, and the eight metrics of every calibration world at (alpha0, 0):
    exact string equality of the "p/q" values (null equals null only); and n_q, the denominator of new_false (the number of
    decided atoms outside I in the verdict view, an integer), which T-1's one-atom floor uses (R1-1): equality of the integers;
  - the feasible set (as a sorted list) and the Pareto front (as an ordered list): equality;
  - the hypervolume: exact string equality of "p/q";
  - the T-1 structure fields of every test world (feasible_alphas, defined, alpha_min, alpha_max, sources_spanned,
    wrong_class_atoms_spanned and largest_increase as "p/q"): equality;
  - the G7a and T-1 outcomes of every test world: equality;
  - every row of the verdict table (G1 to G6, G7 = G7a, T-1): the verdict, the four counts, the Wilson lower bound printed to
    three decimals and the first failing world: equality;
  - the aggregated T-1 structure counts (n, median as text, even, min, max, n_with_wrong_class_atom): equality;
  - a world or file missing on either side, a missing or an extra field, a different type: a disagreement.

Every disagreement carries "affected_tests", the tests whose verdict it can change, by this fixed map (PREREG v0.3 section 6.1),
and "affects_verdict" = bool(affected_tests):
  - tau, fidelity, deviation, consistency, uncertainty, new_true, new_false (also those of a calibration world) and the
    feasible set                                                                    -> T-1 and G7a
  - n_q of a test world (only T-1 reads it)                                         -> T-1 (R2-8)
  - n_q of a calibration world (it enters no tau and no test)                       -> none (R2-8)
  - T-1's structure fields and their aggregated counts                              -> T-1
  - outcomes.X                                                                    -> X (G7a or T-1)
  - a verdict-table row of test X (any field)                                     -> X (G1 ... G6, G7a, T-1; the row of G7 is G7a)
  - a missing or an extra world or file, a world seed that differs, an unreadable document -> G7a and T-1
  - the front, the hypervolume, validation_agreement, boundary_share, an extra field        -> none
F3_COMPARE.json says what was compared, lists every disagreement, and counts them per test. Its summary counts every row,
G1 to G6 included (post-run audit A7). Exit code 0 iff there is no disagreement at all, 1 if there is one, 2 on a usage or I/O
error.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ALL_TESTS = ("G1", "G2", "G3", "G4", "G5", "G6", "G7a", "T-1")  # every test with a row in the verdict table
OUTCOME_TESTS = ("G7a", "T-1")  # the outcomes F3 recomputes per world
VERDICT_TESTS = ("G7a", "T-1")  # what a metric, the feasible set, tau or a missing world can change
TAU_NAMES = ("tau_s", "tau_d", "tau_t", "tau_b")
VERDICT_METRICS = ("fidelity", "deviation", "consistency", "uncertainty", "new_true", "new_false")
OTHER_METRICS = ("validation_agreement", "boundary_share")
# n_q, the denominator of new_false (R1-1): only T-1's one-atom floor reads it, so a disagreement in the n_q of a test world can
# change T-1 only (G7a never reads it), and the n_q of a calibration world enters no tau and no test (R2-8)
N_Q_TESTS = {"test": ("T-1",), "calibration": ()}
METRIC_TESTS = {**{m: VERDICT_TESTS for m in VERDICT_METRICS}, "n_q": N_Q_TESTS["test"], **{m: () for m in OTHER_METRICS}}
STRUCTURE_TESTS = ("T-1",)  # T-1's structure fields and their aggregated counts
FIELD_TESTS = {"feasible": VERDICT_TESTS, "pareto_front": (), "hypervolume": ()}
T1_STRUCTURE_FIELDS = ("feasible_alphas", "defined", "alpha_min", "alpha_max", "sources_spanned",
                       "wrong_class_atoms_spanned", "largest_increase")
STRUCTURE_COUNT_FIELDS = ("n", "median", "even", "min", "max", "n_with_wrong_class_atom")
WORLD_FIELDS = ("world_seed", "metrics", "feasible", "pareto_front", "hypervolume", "outcomes", "t1_structure")
CAL_FIELDS = ("world_seed", "metrics")
CAL_KEY = "0.7|0"
TABLE_FIELDS = ("verdict", "n_holds", "n_fails", "n_undefined", "n_defined", "wilson_lower", "first_failing_world")
TABLE_LABEL = {"G7": "G7a"}  # the verdict-table row of G7 is G7a
NON_WORLD_FILES = ("tau", "verdict_table")  # stems of the agent's files that are not world files


def _dis(world, field, run, agent, affected) -> dict:
    affected = sorted(set(affected))
    return {"world_seed": world, "field": field, "run": run, "agent": agent, "affected_tests": affected,
            "affects_verdict": bool(affected)}


def _differs(a, b) -> bool:
    return a != b or type(a) is not type(b)


def _metric_tests(name: str, calibration: bool) -> tuple:
    """The tests a disagreement in the metric `name` can affect, by `METRIC_TESTS` (n_q of a calibration world: `N_Q_TESTS`; a
    name the schema does not know, an extra field for instance, can affect G7a and T-1)."""
    if name == "n_q" and calibration:
        return N_Q_TESTS["calibration"]
    return METRIC_TESTS.get(name, VERDICT_TESTS)


def _compare_metrics(seed, run_m, agent_m, prefix="metrics", calibration=False) -> list:
    """Disagreements between two {config key: {metric: "p/q" or null}} dicts of a test world or (calibration) of a
    calibration world."""
    found = []
    if not isinstance(agent_m, dict):
        return [_dis(seed, prefix, "present", agent_m, VERDICT_TESTS)]
    for cfg in sorted(set(run_m) | set(agent_m)):
        if cfg not in agent_m or cfg not in run_m:
            found.append(_dis(seed, f"{prefix}[{cfg}]", run_m.get(cfg, "<missing>"), agent_m.get(cfg, "<missing>"),
                              VERDICT_TESTS))
            continue
        if not isinstance(agent_m[cfg], dict):
            found.append(_dis(seed, f"{prefix}[{cfg}]", run_m[cfg], agent_m[cfg], VERDICT_TESTS))
            continue
        for name in sorted(set(run_m[cfg]) | set(agent_m[cfg])):
            a, b = run_m[cfg].get(name, "<missing>"), agent_m[cfg].get(name, "<missing>")
            if _differs(a, b):
                found.append(_dis(seed, f"{prefix}[{cfg}].{name}", a, b, _metric_tests(name, calibration)))
    return found


def compare_world(seed, run: dict, agent: dict) -> list:
    """Disagreements between the run's outputs_results document and the agent's document of one test world."""
    if not isinstance(agent, dict):
        return [_dis(seed, "world document", "object", type(agent).__name__, VERDICT_TESTS)]
    found = []
    run_f3 = run.get("f3") or {}
    if agent.get("world_seed") is not None and str(agent.get("world_seed")) != str(seed):
        found.append(_dis(seed, "world_seed", seed, agent.get("world_seed"), VERDICT_TESTS))
    for key in sorted(set(agent) - set(WORLD_FIELDS)):
        found.append(_dis(seed, f"extra field {key}", "<absent>", "<present>", ()))
    found += _compare_metrics(seed, run.get("metrics_exact") or {}, agent.get("metrics"))

    for key, tests in FIELD_TESTS.items():
        a, b = run_f3.get(key, "<missing>"), agent.get(key, "<missing>")
        if key == "feasible" and isinstance(a, list) and isinstance(b, list):
            a, b = sorted(a), sorted(b)
        if _differs(a, b):
            found.append(_dis(seed, key, a, b, tests))

    a_out, b_out = run_f3.get("outcomes") or {}, agent.get("outcomes")
    if not isinstance(b_out, dict):
        found.append(_dis(seed, "outcomes", a_out, b_out, OUTCOME_TESTS))
    else:
        for test in sorted(set(a_out) | set(b_out) | set(OUTCOME_TESTS)):
            a, b = a_out.get(test, "<missing>"), b_out.get(test, "<missing>")
            if _differs(a, b):
                found.append(_dis(seed, f"outcomes.{test}", a, b, (test,) if test in OUTCOME_TESTS else ()))

    a_s, b_s = run_f3.get("t1_structure") or {}, agent.get("t1_structure")
    if not isinstance(b_s, dict):
        found.append(_dis(seed, "t1_structure", a_s, b_s, STRUCTURE_TESTS))
    else:
        for name in sorted(set(a_s) | set(b_s) | set(T1_STRUCTURE_FIELDS)):
            a, b = a_s.get(name, "<missing>"), b_s.get(name, "<missing>")
            if _differs(a, b):
                found.append(_dis(seed, f"t1_structure.{name}", a, b, STRUCTURE_TESTS if name in T1_STRUCTURE_FIELDS else ()))
    return found


def compare_cal_world(seed, run: dict, agent: dict) -> list:
    """Disagreements between the run's cal_<seed>.json and the agent's: the eight metrics at (alpha0, 0)."""
    label = f"cal_{seed}"
    if not isinstance(agent, dict):
        return [_dis(label, "world document", "object", type(agent).__name__, VERDICT_TESTS)]
    found = []
    if agent.get("world_seed") is not None and str(agent.get("world_seed")) != str(seed):
        found.append(_dis(label, "world_seed", seed, agent.get("world_seed"), VERDICT_TESTS))
    for key in sorted(set(agent) - set(CAL_FIELDS)):
        found.append(_dis(label, f"extra field {key}", "<absent>", "<present>", ()))
    found += _compare_metrics(label, run.get("metrics_exact") or {}, agent.get("metrics"), calibration=True)
    return found


def compare_tau(run_tau: dict, agent_tau) -> list:
    """Disagreements between the run's main tau (TAU.json "main": "p/q" strings) and the agent's tau.json."""
    if not isinstance(agent_tau, dict):
        return [_dis(None, "tau", "present", agent_tau, VERDICT_TESTS)]
    found = []
    for key in sorted(set(agent_tau) - set(TAU_NAMES)):
        found.append(_dis(None, f"tau extra field {key}", "<absent>", "<present>", ()))
    for name in TAU_NAMES:
        a, b = run_tau.get(name, "<missing>"), agent_tau.get(name, "<missing>")
        if _differs(a, b):
            found.append(_dis(None, f"tau.{name}", a, b, VERDICT_TESTS))
    return found


def run_table_rows(verdicts: dict) -> dict:
    """{test id: {field: value}} from the run's VERDICTS.json, with the Wilson bound as printed (three decimals)."""
    rows = {}
    for row in verdicts["table"]["rows"]:
        wl = row.get("wilson_lower")
        rows[row["test"]] = {
            "verdict": row["verdict"], "n_holds": row["n_holds"], "n_fails": row["n_fails"],
            "n_undefined": row["n_undefined"], "n_defined": row["n_defined"],
            "wilson_lower": None if wl is None else f"{wl:.3f}",
            "first_failing_world": row.get("first_failing_world"),
        }
    return rows


def run_structure_counts(verdicts: dict) -> dict:
    """The aggregated T-1 structure counts of the run (the "structure" of the T-1 row), the fields F3 recomputes."""
    for row in verdicts["table"]["rows"]:
        if row["test"] == "T-1":
            return {k: (row.get("structure") or {}).get(k, "<missing>") for k in STRUCTURE_COUNT_FIELDS}
    return {}


def compare_table(run_rows: dict, run_counts: dict, agent_table: dict) -> list:
    found = []
    agent_rows = {}
    if isinstance(agent_table, dict) and isinstance(agent_table.get("rows"), list):
        for row in agent_table["rows"]:
            if isinstance(row, dict) and "test" in row:
                agent_rows[row["test"]] = row
    else:
        return [_dis(None, "verdict_table", "rows", agent_table, ALL_TESTS)]
    for test in sorted(set(run_rows) | set(agent_rows)):
        label = TABLE_LABEL.get(test, test)
        affected = (label,) if label in ALL_TESTS else ()
        if test not in run_rows or test not in agent_rows:
            found.append(_dis(None, f"verdict_table[{test}]", run_rows.get(test, "<missing>"),
                              agent_rows.get(test, "<missing>"), affected))
            continue
        for field in TABLE_FIELDS:
            a, b = run_rows[test].get(field, "<missing>"), agent_rows[test].get(field, "<missing>")
            if _differs(a, b):
                found.append(_dis(None, f"verdict_table[{test}].{field}", a, b, affected))
    agent_counts = agent_table.get("t1_structure_counts")
    if not isinstance(agent_counts, dict):
        found.append(_dis(None, "verdict_table.t1_structure_counts", run_counts, agent_counts, STRUCTURE_TESTS))
    else:
        for key in sorted(set(agent_counts) - set(STRUCTURE_COUNT_FIELDS)):
            found.append(_dis(None, f"verdict_table.t1_structure_counts extra field {key}", "<absent>", "<present>", ()))
        for name in STRUCTURE_COUNT_FIELDS:
            a, b = run_counts.get(name, "<missing>"), agent_counts.get(name, "<missing>")
            if _differs(a, b):
                found.append(_dis(None, f"verdict_table.t1_structure_counts.{name}", a, b, STRUCTURE_TESTS))
    return found


def _load(path: Path):
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _split(files: dict) -> tuple:
    """({test stem: path}, {calibration stem (without 'cal_'): path})"""
    test = {s: p for s, p in files.items() if not s.startswith("cal_")}
    cal = {s[len("cal_"):]: p for s, p in files.items() if s.startswith("cal_")}
    return test, cal


def compare_dirs(run_dir: Path, agent_dir: Path) -> dict:
    """The whole comparison as the F3_COMPARE.json document."""
    run_files = {p.stem: p for p in sorted((run_dir / "outputs_results").glob("*.json"))}
    agent_files = {p.stem: p for p in sorted(agent_dir.glob("*.json")) if p.stem not in NON_WORLD_FILES}
    run_test, run_cal = _split(run_files)
    agent_test, agent_cal = _split(agent_files)
    disagreements = []
    for kind, run_set, agent_set, fn in (("world", run_test, agent_test, compare_world),
                                         ("calibration world", run_cal, agent_cal, compare_cal_world)):
        for seed in sorted(set(run_set) | set(agent_set), key=str):
            if seed not in agent_set or seed not in run_set:
                disagreements.append(_dis(seed, f"{kind} file", "present" if seed in run_set else "<missing>",
                                          "present" if seed in agent_set else "<missing>", VERDICT_TESTS))
                continue
            disagreements += fn(seed, _load(run_set[seed]), _load(agent_set[seed]))
    tau_path = agent_dir / "tau.json"
    if not tau_path.is_file():
        disagreements.append(_dis(None, "tau.json", "present", "<missing>", VERDICT_TESTS))
    else:
        disagreements += compare_tau(_load(run_dir / "TAU.json")["main"], _load(tau_path))
    table_path = agent_dir / "verdict_table.json"
    if not table_path.is_file():
        disagreements.append(_dis(None, "verdict_table.json", "present", "<missing>", ALL_TESTS))
    else:
        verdicts = _load(run_dir / "VERDICTS.json")
        disagreements += compare_table(run_table_rows(verdicts), run_structure_counts(verdicts), _load(table_path))
    by_test = {t: sum(t in d["affected_tests"] for d in disagreements) for t in ALL_TESTS}
    return {
        "what": "F3: the run's numbers against the F3 agent's results (audit/v03/f3_compare.py, frozen before the run)",
        "n_worlds_run": len(run_test),
        "n_worlds_agent": len(agent_test),
        "n_calibration_worlds_run": len(run_cal),
        "n_calibration_worlds_agent": len(agent_cal),
        "n_disagreements": len(disagreements),
        "n_affecting_verdict": sum(d["affects_verdict"] for d in disagreements),
        "affected_tests": sorted(t for t, n in by_test.items() if n),
        "n_disagreements_by_affected_test": by_test,
        "all_equal": not disagreements,
        "disagreements": disagreements,
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="py -m audit.v03.f3_compare", description=__doc__.split("\n\n")[0])
    ap.add_argument("run_dir")
    ap.add_argument("agent_dir")
    ap.add_argument("-o", "--output", default=None, help="default: RUN_DIR/F3_COMPARE.json")
    args = ap.parse_args(argv)
    run_dir, agent_dir = Path(args.run_dir), Path(args.agent_dir)
    for folder in (run_dir, agent_dir):
        if not folder.is_dir():
            print(f"cannot compare: {folder} is not a folder", file=sys.stderr)
            return 2
    try:
        doc = compare_dirs(run_dir, agent_dir)
        out = Path(args.output) if args.output else run_dir / "F3_COMPARE.json"
        with open(out, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(doc, fh, indent=1, sort_keys=True)
            fh.write("\n")
    except (OSError, ValueError, KeyError) as exc:
        print(f"cannot compare: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    print(f"F3: {doc['n_disagreements']} disagreements ({doc['n_affecting_verdict']} affect a verdict: "
          f"{', '.join(doc['affected_tests']) or 'none'}); wrote {out}")
    return 0 if doc["all_equal"] else 1


if __name__ == "__main__":
    sys.exit(main())
