"""F3 comparison: the run's own numbers against the F3 agent's results (PREREG sections 6.1 and 8), frozen with audit/.

    py -m audit.f3_compare RUN_DIR AGENT_DIR [-o F3_COMPARE.json]

RUN_DIR holds the run's outputs_results/<seed>.json and VERDICTS.json. AGENT_DIR holds what the fresh F3 agent wrote:
<seed>.json for every test world and verdict_table.json (the schema is audit/f3/OUTPUT_SCHEMA.json). The comparison is
fixed here, before the run, so that what counts as a disagreement is not chosen after the numbers are seen:

  - every metric of every grid point: exact string equality of the "p/q" values (null equals null only);
  - the feasible set (as a sorted list) and the Pareto front (as an ordered list): equality;
  - the hypervolume: exact string equality of "p/q";
  - the T-1 structure fields of every world (two booleans and three true / false / null values): equality;
  - the G7a, G8 and T-1 outcomes of every world: equality;
  - every row of the verdict table: the verdict, the four counts, the Wilson lower bound printed to three decimals and
    the first failing world: equality;
  - a world missing on either side, a missing or an extra field, a different type: a disagreement.

Every disagreement carries "affected_tests", the tests whose verdict it can change, by this fixed map (R3-2), and
"affects_verdict" = bool(affected_tests):
  - fidelity, deviation                                        -> G8, T-1
  - consistency, uncertainty, new_true, new_false, feasible    -> T-1
  - the T-1 structure fields                                   -> T-1
  - outcomes.X                                                 -> X (G7a, G8 or T-1)
  - verdict_table row X (any field)                            -> X (the row of G7 is G7a)
  - a missing or an extra world or file, a world seed that differs, an unreadable document -> G7a, G8, T-1
  - pareto_front, hypervolume, validation_agreement, boundary_share, an extra field        -> none
F3_COMPARE.json says what was compared, lists every disagreement, and counts them per test. Exit code 0 iff there is no
disagreement at all, 1 if there is one, 2 on a usage or I/O error.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ALL_TESTS = ("G7a", "G8", "T-1")
METRIC_TESTS = {
    "fidelity": ("G8", "T-1"), "deviation": ("G8", "T-1"), "consistency": ("T-1",), "uncertainty": ("T-1",),
    "new_true": ("T-1",), "new_false": ("T-1",), "validation_agreement": (), "boundary_share": (),
}
VERDICT_METRICS = ("fidelity", "deviation", "consistency", "uncertainty", "new_true", "new_false")
OTHER_METRICS = ("validation_agreement", "boundary_share")
OUTCOME_TESTS = ALL_TESTS
FIELD_TESTS = {"feasible": ("T-1",), "pareto_front": (), "hypervolume": ()}
T1_STRUCTURE_FIELDS = ("some_alpha_le_060_feasible", "alpha_ge_085_feasible", "t1_window_pairs", "t1_crossing_pairs",
                       "t1_cross_080_085")
WORLD_FIELDS = ("world_seed", "metrics", "feasible", "pareto_front", "hypervolume", "outcomes", "t1_structure")
TABLE_FIELDS = ("verdict", "n_holds", "n_fails", "n_undefined", "n_defined", "wilson_lower", "first_failing_world")
TABLE_LABEL = {"G7": "G7a"}  # the verdict-table row of G7 is G7a


def _dis(world, field, run, agent, affected) -> dict:
    affected = sorted(set(affected))
    return {"world_seed": world, "field": field, "run": run, "agent": agent, "affected_tests": affected,
            "affects_verdict": bool(affected)}


def _differs(a, b) -> bool:
    return a != b or type(a) is not type(b)


def compare_world(seed, run: dict, agent: dict) -> list:
    """Disagreements between the run's outputs_results document and the agent's document of one world."""
    if not isinstance(agent, dict):
        return [_dis(seed, "world document", "object", type(agent).__name__, ALL_TESTS)]
    found = []
    run_f3 = run.get("f3") or {}
    if agent.get("world_seed") is not None and str(agent.get("world_seed")) != str(seed):
        found.append(_dis(seed, "world_seed", seed, agent.get("world_seed"), ALL_TESTS))
    for key in sorted(set(agent) - set(WORLD_FIELDS)):
        found.append(_dis(seed, f"extra field {key}", "<absent>", "<present>", ()))

    run_m = run.get("metrics_exact") or {}
    agent_m = agent.get("metrics")
    if not isinstance(agent_m, dict):
        found.append(_dis(seed, "metrics", "present", agent_m, ("G8", "T-1")))
    else:
        for cfg in sorted(set(run_m) | set(agent_m)):
            if cfg not in agent_m or cfg not in run_m:
                found.append(_dis(seed, f"metrics[{cfg}]", run_m.get(cfg, "<missing>"), agent_m.get(cfg, "<missing>"),
                                  ("G8", "T-1")))
                continue
            if not isinstance(agent_m[cfg], dict):
                found.append(_dis(seed, f"metrics[{cfg}]", run_m[cfg], agent_m[cfg], ("G8", "T-1")))
                continue
            for name in sorted(set(run_m[cfg]) | set(agent_m[cfg])):
                a, b = run_m[cfg].get(name, "<missing>"), agent_m[cfg].get(name, "<missing>")
                if _differs(a, b):
                    found.append(_dis(seed, f"metrics[{cfg}].{name}", a, b, METRIC_TESTS.get(name, ("G8", "T-1"))))

    for key, tests in FIELD_TESTS.items():
        a, b = run_f3.get(key, "<missing>"), agent.get(key, "<missing>")
        if key == "feasible" and isinstance(a, list) and isinstance(b, list):
            a, b = sorted(a), sorted(b)
        if _differs(a, b):
            found.append(_dis(seed, key, a, b, tests))

    a_out, b_out = run_f3.get("outcomes") or {}, agent.get("outcomes")
    if not isinstance(b_out, dict):
        found.append(_dis(seed, "outcomes", a_out, b_out, ALL_TESTS))
    else:
        for test in sorted(set(a_out) | set(b_out) | set(OUTCOME_TESTS)):
            a, b = a_out.get(test, "<missing>"), b_out.get(test, "<missing>")
            if _differs(a, b):
                found.append(_dis(seed, f"outcomes.{test}", a, b, (test,) if test in OUTCOME_TESTS else ()))

    a_s, b_s = run_f3.get("t1_structure") or {}, agent.get("t1_structure")
    if not isinstance(b_s, dict):
        found.append(_dis(seed, "t1_structure", a_s, b_s, ("T-1",)))
    else:
        for name in sorted(set(a_s) | set(b_s) | set(T1_STRUCTURE_FIELDS)):
            a, b = a_s.get(name, "<missing>"), b_s.get(name, "<missing>")
            if _differs(a, b):
                found.append(_dis(seed, f"t1_structure.{name}", a, b, ("T-1",) if name in T1_STRUCTURE_FIELDS else ()))
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


def compare_table(run_rows: dict, agent_table: dict) -> list:
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
                              agent_rows.get(test, "<missing>"), (label,)))
            continue
        for field in TABLE_FIELDS:
            a, b = run_rows[test].get(field, "<missing>"), agent_rows[test].get(field, "<missing>")
            if _differs(a, b):
                found.append(_dis(None, f"verdict_table[{test}].{field}", a, b, (label,)))
    return found


def _load(path: Path):
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def compare_dirs(run_dir: Path, agent_dir: Path) -> dict:
    """The whole comparison as the F3_COMPARE.json document."""
    run_files = {p.stem: p for p in sorted((run_dir / "outputs_results").glob("*.json"))}
    agent_files = {p.stem: p for p in sorted(agent_dir.glob("*.json")) if p.name != "verdict_table.json"}
    disagreements = []
    for seed in sorted(set(run_files) | set(agent_files), key=str):
        if seed not in agent_files or seed not in run_files:
            disagreements.append(_dis(seed, "world file", "present" if seed in run_files else "<missing>",
                                      "present" if seed in agent_files else "<missing>", ALL_TESTS))
            continue
        disagreements += compare_world(seed, _load(run_files[seed]), _load(agent_files[seed]))
    table_path = agent_dir / "verdict_table.json"
    if not table_path.is_file():
        disagreements.append(_dis(None, "verdict_table.json", "present", "<missing>", ALL_TESTS))
    else:
        disagreements += compare_table(run_table_rows(_load(run_dir / "VERDICTS.json")), _load(table_path))
    by_test = {t: sum(t in d["affected_tests"] for d in disagreements) for t in ALL_TESTS}
    return {
        "what": "F3: the run's numbers against the F3 agent's results (audit/f3_compare.py, frozen before the run)",
        "n_worlds_run": len(run_files),
        "n_worlds_agent": len(agent_files),
        "n_disagreements": len(disagreements),
        "n_affecting_verdict": sum(d["affects_verdict"] for d in disagreements),
        "affected_tests": sorted(t for t, n in by_test.items() if n),
        "n_disagreements_by_affected_test": by_test,
        "all_equal": not disagreements,
        "disagreements": disagreements,
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="py -m audit.f3_compare", description=__doc__.split("\n\n")[0])
    ap.add_argument("run_dir")
    ap.add_argument("agent_dir")
    ap.add_argument("-o", "--output", default=None, help="default: RUN_DIR/F3_COMPARE.json")
    args = ap.parse_args(argv)
    run_dir, agent_dir = Path(args.run_dir), Path(args.agent_dir)
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
