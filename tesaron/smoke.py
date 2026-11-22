"""Smoke run: the full pipeline on one world over the default grid (SPEC section 12).

    py -m tesaron.smoke --world-seed 900001 --encoder-seed 900101 [--out FILE]

Prints a JSON summary. Nothing is written to disk unless --out is given. The summary carries an
"output_hash": the canonical hash of everything except the run time.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import asdict, replace

from tesaron.criterion import (
    DEFAULT_GRID,
    PLACEHOLDER_TAUS,
    compute_metrics_for,
    hypervolume,
    make_baselines,
    pareto_front,
    point_score,
)
from tesaron.criterion.wisdom import ALPHAS, make_point
from tesaron.encoder import Context, encode
from tesaron.pipeline import evaluate
from tesaron.serialize import canonical_hash, to_jsonable
from tesaron.worlds import generate_world

SEED_MIN, SEED_MAX = 900000, 900999  # SPEC section 11


def _seed(text: str) -> int:
    n = int(text)
    if not (SEED_MIN <= n <= SEED_MAX):
        raise argparse.ArgumentTypeError(f"v0.1 seeds must lie in {SEED_MIN}..{SEED_MAX} (SPEC section 11)")
    return n


def _metrics_dict(m) -> dict:
    d = asdict(m)
    d["x"] = m.x
    d["y"] = m.y
    return d


def build_summary(world_seed: int, encoder_seed: int) -> dict:
    world = generate_world(world_seed)
    context = Context.from_world(world, encoder_seed)
    encoding = encode(world, context)
    taus = PLACEHOLDER_TAUS

    preds: dict[str, int] = {}
    for a in sorted(world.true_atoms):
        preds[a.pred] = preds.get(a.pred, 0) + 1
    world_stats = {
        "seed": world.seed,
        "draws_needed": world.attempts,
        "n_entities": len(world.entities),
        "base_classes": list(world.base_classes),
        "outliers": list(world.outliers),
        "overlaps": list(world.overlaps),
        "n_feature_rows": len(world.feature_rows),
        "n_report_rows": len(world.report_rows),
        "n_base_relation_facts": len(world.base_facts),
        "n_true_atoms": len(world.true_atoms),
        "true_atoms_per_predicate": preds,
        "rules": {r.id: _rule_str(r) for r in world.rules},
        "source_reliabilities": world.source_reliabilities,
    }
    enc_stats = {
        "n_selected": len(encoding.selected_ids),
        "n_derive": len(encoding.derive_ids),
        "n_validate": len(encoding.validate_ids),
        "pcm_iterations": encoding.fit.n_iter,
        "pcm_converged": encoding.fit.converged,
        "pcm_degenerate": encoding.fit.degenerate,
        "pcm_centers": encoding.fit.centers,
        "n_units": len(encoding.units),
        "n_validation_units": len(encoding.validation_units),
    }

    per_alpha: dict[str, dict] = {}
    grid = []
    points = []
    for alpha, k in DEFAULT_GRID:
        ctx = replace(context, alpha=alpha, k_abduction=k)
        _, m = evaluate(world, ctx, encoding)
        pt = make_point((alpha, k), m, taus)
        points.append(pt)
        per_alpha.setdefault(
            str(alpha), {"E": m.size_E, "I": m.size_I, "H": m.size_H, "K": m.size_K}
        )
        grid.append(
            {"alpha": alpha, "k_abduction": k, "metrics": _metrics_dict(m), "feasible": pt.feasible,
             "score": point_score(pt)}
        )
    front = pareto_front(points)

    baselines: dict[str, dict] = {}
    for alpha in ALPHAS:
        ctx = replace(context, alpha=alpha)
        per_alpha_b = {}
        for name, out in make_baselines(encoding.units, alpha, context.vocabulary).items():
            m = compute_metrics_for(world, ctx, encoding, out)
            pt = make_point((alpha, 0), m, taus)
            per_alpha_b[name] = {"metrics": _metrics_dict(m), "feasible": pt.feasible, "score": point_score(pt)}
        baselines[str(alpha)] = per_alpha_b

    return {
        "world_seed": world_seed,
        "encoder_seed": encoder_seed,
        "world": world_stats,
        "encoder": enc_stats,
        "sets_per_alpha": per_alpha,
        "taus": {
            "label": "placeholder, not frozen",
            "tau_s": taus.tau_s, "tau_d": taus.tau_d, "tau_t": taus.tau_t, "tau_b": taus.tau_b,
        },
        "grid": grid,
        "front": [{"alpha": p.config[0], "k_abduction": p.config[1], "x": p.x, "y": p.y} for p in front],
        "hypervolume": hypervolume(front),
        "baselines": baselines,
    }


def _rule_str(rule) -> str:
    def lit(l) -> str:
        return ("~" if l.channel.name == "NEG" else "") + f"{l.pred}({','.join(l.args)})"

    return f"{lit(rule.head)} <- " + " & ".join(lit(l) for l in rule.body)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m tesaron.smoke", description=__doc__.splitlines()[0])
    ap.add_argument("--world-seed", type=_seed, required=True)
    ap.add_argument("--encoder-seed", type=_seed, required=True)
    ap.add_argument("--out", default=None, help="also write the JSON summary to this file")
    args = ap.parse_args(argv)

    t0 = time.perf_counter()
    summary = build_summary(args.world_seed, args.encoder_seed)
    summary = to_jsonable(summary)
    summary["output_hash"] = canonical_hash(summary)  # everything except the run time
    summary["run_time_s"] = round(time.perf_counter() - t0, 3)
    text = json.dumps(summary, indent=2, sort_keys=True, ensure_ascii=True)
    print(text)
    if args.out:
        with open(args.out, "w", encoding="ascii") as fh:
            fh.write(text + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
