# F3 instructions (Tesaron v0.2)

This text is frozen with the pre-registration (PREREG section 9). It is given unchanged to the F3 agent and, if a
disagreement must be resolved, to a second fresh agent (PREREG section 6.1).

You are the F3 agent of the Tesaron v0.2 pre-registration (PREREG section 6.1, control F3). You recompute, from scratch
and independently, the numbers that the run's verdicts rest on. You write your results to files. A frozen script
(`audit/f3_compare.py`) later compares them with the run's own numbers, field by field. You never see the run's own
numbers.

## What you may use

- The inputs: the input folder you are given, a copy of the run's `run/outputs_input/` with one file
  `<world_seed>.json` per test world. Nothing else from the run.
- `SPEC.md` (sections 1, 5, 6, 7.1, 7.2, 8, 9 and 10), `PREREG_v0.2.md` (sections 3, 4 and 5) and
  `OUTPUT_SCHEMA.json`, as given in your task folder. SPEC sections 7.1 and 7.2 give the rule semantics that H needs:
  a NEG body literal requires a NEG fact, and a NEG head adds a NEG fact (strong negation).
- Your own code. Write it yourself. Do not import `tesaron` or `audit`, and do not read any file outside your task
  folder. The run's own metrics, check data and outcomes (`run/outputs_results/`, `run/VERDICTS.json`,
  `run/RESULTS.json`) are not in your task folder; do not look for them.
- Python with the standard library `fractions` module. No floats in any value you write, except where this text says
  that a comparison is a float comparison.

## What an input file holds

`world_seed`, `draw_index` (the index of this world in the draw order), `entities`, `n_classes`, `n_relations`,
`base_classes`, `outliers`, `overlaps`, `rules` (id, head, body; a literal has `pred`, `args`, `channel` "POS" or "NEG"; an argument that starts with an upper-case letter is a variable),
`true_atoms` (the atoms with world value T; every other vocabulary atom has world value F), `epsilon_band`, `units` and
`validation_units` (atom: [mu_pos, mu_neg, status, provenance]; a status "NOT_COMPUTED" gives value U at every alpha),
`taus` (tau_s, tau_d, tau_t, tau_b as "p/q"), `alphas`, `ks`, `default_configuration` ([alpha0, k0]), `configs` (for every
configuration "<alpha>|<k>": `full` and `verdict`, each listing only the atoms whose value is not U), and
`given_outcomes_g1_g6` (the run's G1 to G6 outcomes of this world, given: do not recompute them).
An atom is written `pred(arg1,arg2)`. The vocabulary is every class atom `c<k>(e)` and every relation atom
`r<a>(x,y)` with x different from y.

## What you compute, per world

1. **Encoded values.** enc(a) for every atom with a unit, at every alpha: pos = (mu_pos >= alpha), neg = (mu_neg >=
   alpha), equality counts; value T, F, B or U from (pos, neg); a NOT_COMPUTED unit gives U. Compare floats as IEEE
   doubles, with alpha exactly as printed in the input.
2. **Sets** (SPEC section 8): E, I (enc is not U, per alpha), H (from the world truth and the world rules, with a brute-force
   closure), K = E union H.
3. **Metrics** at every configuration, as exact fractions: fidelity, deviation, consistency, uncertainty, new_true,
   new_false, validation_agreement, boundary_share (SPEC section 8), from `full` and `verdict` of the configuration. An
   atom that is not listed in `full` or `verdict` has value U. A metric with an empty denominator is null where SPEC
   section 8 says None; deviation and new_false are 0 then ("0/1").
4. **Feasible set:** the configurations with fidelity >= tau_s, deviation <= tau_d, consistency >= tau_t and uncertainty
   <= tau_b (exact fraction comparison; a null fidelity, consistency, uncertainty or new_true makes a point infeasible).
5. **Pareto front and hypervolume** over the feasible points with a defined new_true: x = 1 - new_false, y = new_true.
   Front: the points that no other point dominates (at least as large in both coordinates and larger in one); order x
   descending, y descending, then alpha ascending, then k ascending. Hypervolume: the exact area of the union of the
   rectangles [0, x] x [0, y], as "p/q".
6. **G7a** (PREREG section 3.2; the test id in the verdict table is "G7"). A single point scores x * y =
   (1 - new_false) * new_true if it is feasible (step 4, with the world's τ), and 0 if it is infeasible. A feasible
   point scores > 0 exactly when new_true > 0 and new_false < 1.
   - For every alpha, compute the metrics of the five baselines of SPEC section 10: echo is enc(a) for every vocabulary
     atom, U for an atom without a unit; all_true, all_false, all_unknown and all_both are T, F, U and B for every
     vocabulary atom. Each baseline has the same value in `full` and `verdict`.
   - Also compute the metrics of the oracle: every atom of I keeps enc, every other atom of K gets its world value T or
     F, every other atom is U. The oracle too has the same value in `full` and `verdict`.
   - HOLDS iff every baseline at every alpha scores 0 (it is infeasible, or feasible with x * y = 0), and the oracle
     scores > 0 at some alpha (feasible and x * y > 0 at the same alpha); UNDEFINED iff the oracle has no feasible
     point; FAILS otherwise.
7. **G8** (PREREG section 3.2): for every alpha and k in {5, 10}, skip the comparison if fidelity(alpha, 0) or
   fidelity(alpha, k) is null; otherwise require fidelity(alpha, 0) - fidelity(alpha, k) <= 1/20 and
   deviation(alpha, k) - deviation(alpha, 0) <= 1/50. Anchor: at least one hypothesis at (alpha0, k = 10); a hypothesis
   exists iff some atom has full not U and verdict U at that configuration. UNDEFINED if there is no hypothesis or every
   comparison is skipped; HOLDS iff no comparison violates a bound; FAILS otherwise.
8. **T-1** (PREREG section 3.2): over the feasible points, for every pair (p, q) with uncertainty(q) < uncertainty(p),
   new_false(q) - new_false(p) <= 1/20. UNDEFINED if fewer than two feasible points have distinct uncertainty values;
   FAILS if some pair violates the bound; HOLDS otherwise.
9. **T-1 structure** (PREREG section 3.2, I-5). A feasible point is a configuration of the feasible set (step 4). Write
   five fields:
   - `some_alpha_le_060_feasible`: true iff some feasible point has alpha <= 0.60;
   - `alpha_ge_085_feasible`: true iff some feasible point has alpha >= 0.85;
   - `t1_crossing_pairs`, `t1_cross_080_085`, `t1_window_pairs`: the T-1 check of step 8 restricted to a set of pairs
     (p, q) of feasible points, with uncertainty(q) < uncertainty(p) and new_false(q) - new_false(p) <= 1/20 as there.
     The pairs of `t1_crossing_pairs` are those where one point has alpha <= 0.60 and the other alpha >= 0.65; of
     `t1_cross_080_085` those where one has alpha <= 0.80 and the other alpha >= 0.85; of `t1_window_pairs` those where
     both alphas lie in {0.80, 0.75, 0.70, 0.65}. Each field is null if no pair of its set has distinct uncertainty,
     false if some pair of its set violates the bound, true otherwise.

## The verdict table (once, over all test worlds)

From the G1 to G6 outcomes that the inputs give and your own G7a, G8 and T-1 outcomes (PREREG sections 3.3 and 4). One
row per test, with the test ids "G1" … "G6", "G7" (for G7a), "G8" and "T-1":
- Count n_holds, n_fails, n_undefined and n_defined = n_holds + n_fails for every test.
- `first_failing_world` of every row: the `world_seed` of the world whose outcome for that test is FAILS and whose
  `draw_index` is the smallest, or null if no world's outcome is FAILS (whatever the verdict is).
- Deterministic tests G1 to G7a: FAILS if any world's outcome is FAILS; else HOLDS if at least 16 worlds are defined
  (outcome not UNDEFINED); else INSUFFICIENT. Their `wilson_lower` is null.
- G8 and T-1: INSUFFICIENT if fewer than 16 worlds are defined; otherwise HOLDS iff the one-sided Wilson lower bound
  of n_holds / n_defined is at least 0.80, else FAILS.
- `wilson_lower` for G8 and T-1: null if n_defined = 0; otherwise (also with fewer than 16 defined worlds) the bound as
  an IEEE double, computed in this order with n = n_defined and z = 1.6448536269514722: p = n_holds / n; z2 = z * z;
  centre = p + z2 / (2 * n); spread = z * sqrt(p * (1 - p) / n + z2 / (4 * n * n)); bound = (centre - spread) /
  (1 + z2 / n). Write it as Python's `format(bound, ".3f")`. The HOLDS/FAILS decision compares the unrounded double
  with 0.80.

## What you write

Into your own output folder: `<world_seed>.json` for every input file and `verdict_table.json`, in exactly the format
of `OUTPUT_SCHEMA.json`. Fractions are strings "p/q" in lowest terms (an integer n is "n/1"); undefined is null.
Configuration keys are those of the input's `configs`. Do not write any other JSON file into the folder.

## If something is unclear

Do not guess a convention. Write what you did in `NOTES.md` in your output folder and still write all files. The notes
are read by the Independent session, not by the comparison script. NOTES.md is reported with F3_COMPARE.json and changes
nothing.
