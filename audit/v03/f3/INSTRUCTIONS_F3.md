# F3 instructions (Tesaron v0.3)

This text is frozen with the pre-registration (PREREG v0.3 section 9). It is given unchanged to the F3 agent and, if a
disagreement must be resolved, to a second fresh agent (PREREG v0.3 section 6.1).

You are the F3 agent of the Tesaron v0.3 pre-registration (PREREG v0.3 section 6.1, control F3). You recompute, from
scratch and independently, the numbers that the run's verdicts rest on, including the calibrated bounds τ. You write your
results to files. A frozen script (`audit/v03/f3_compare.py`) later compares them with the run's own numbers, field by
field. You never see the run's own numbers.

## What you may use

- The inputs: the input folder you are given, a copy of the run's `run/v03/outputs_input/`. It holds one file
  `<world_seed>.json` for each of the 50 test worlds and one file `cal_<world_seed>.json` for each of the 40 calibration
  worlds. Nothing else from the run.
- `SPEC.md` (sections 1, 5, 6, 7.1, 7.2, 8, 9 and 10), `SPEC_v0.3.md`, `PREREG_v0.3.md` (sections 1 to 4 and 7) and
  `OUTPUT_SCHEMA.json`, as given in your task folder. SPEC sections 7.1 and 7.2 give the rule semantics that H needs: a NEG
  body literal requires a NEG fact, and a NEG head adds a NEG fact (strong negation).
- Your own code. Write it yourself. Do not import `tesaron` or `audit`, and do not read any file outside your task folder. The
  run's own metrics, check data and outcomes (`run/v03/outputs_results/`, `VERDICTS.json`, `RESULTS.json`, `TAU.json`) are not
  in your task folder; do not look for them.
- Python with the standard library `fractions` module. No floats in any value you write. A float comparison is made only where
  this text says so: step 1 and the boundary band (step 3), always as IEEE doubles.

## What an input file holds

A test-world file and a calibration-world file have the same fields. They differ in `role`, in `alphas`, `ks` and `configs`
(below) and in `given_outcomes_g1_g6` (test worlds only).

- `role` ("test" or "calibration"), `world_seed`, `draw_index` (the index of this world in the draw order of its set).
- `entities`, `n_classes`, `n_relations`, `base_classes`, `outliers`, `overlaps`.
- `rules`: id, head and body. A literal has `pred`, `args` and `channel` ("POS" or "NEG"); an argument that starts with an
  upper-case letter is a variable.
- `true_atoms`: the atoms with world value T. Every other vocabulary atom has world value F.
- `source_reliabilities`: the 8 reliabilities of the world's sources, as decimal numbers with at most 3 decimals.
- `epsilon_band`.
- `units` and `validation_units`: atom -> [mu_pos, mu_neg, status, provenance]. A status "NOT_COMPUTED" gives value U at every
  alpha.
- `default_configuration` ([alpha0, k0]) and `calibration_configuration` ([alpha0, 0]).
- `alphas`, `ks` and `configs`.
  - A test world has the 10 alphas 0.95 ... 0.50, the ks 0, 5 and 10, and a `configs` entry "<alpha>|<k>" for each of the 30
    configurations.
  - A calibration world has `alphas` [0.7], `ks` [0] and a single `configs` entry, "0.7|0".
  - Each entry has `full` and `verdict`, each listing only the atoms whose value is not U.
- `given_outcomes_g1_g6` (test worlds only): the run's G1 to G6 outcomes of this world. They are given: do not recompute them.

An atom is written `pred(arg1,arg2)`. The vocabulary is every class atom `c<k>(e)` and every relation atom `r<a>(x,y)` with x
different from y. A class atom is an atom whose predicate starts with "c".

There is no τ in any file. You compute it from the 40 calibration worlds (step 0).

## Step 0. τ from the calibration worlds

For each of the 40 `cal_<world_seed>.json` files, compute the metrics of steps 1 to 3 at the single configuration "0.7|0", and
write them (see "What you write"). Then, with the 40 values of each metric, duplicates included, sorted:
- `tau_s` is the 4th smallest fidelity and `tau_t` the 4th smallest consistency;
- `tau_d` is the 4th largest deviation and `tau_b` the 4th largest uncertainty.

"4th smallest" is the element with 0-based index 3 of the ascending list; "4th largest" is the element with 0-based index 3
of the descending list. All comparisons are on exact fractions. Every calibration world has these four metrics defined (an
undefined one makes a world invalid, and the run does not offer invalid worlds); if you find one, say so in `NOTES.md`.

## What you compute, per test world

The metrics and the feasible set use the τ of step 0.

1. **Encoded values.** enc(a) for every atom with a unit, at every alpha: pos = (mu_pos >= alpha), neg = (mu_neg >= alpha),
   equality counts; value T, F, B or U from (pos, neg); a NOT_COMPUTED unit gives U. Compare as IEEE doubles, with mu_pos,
   mu_neg and alpha exactly as printed in the input (a JSON number parsed to a double).
2. **Sets** (SPEC section 8): E, I (enc is not U, per alpha), H (from the world truth and the world rules, with a brute-force
   closure), K = E union H.
3. **Metrics** at every configuration, as exact fractions: fidelity, deviation, consistency, uncertainty, new_true, new_false,
   validation_agreement, boundary_share (SPEC section 8), from `full` and `verdict` of the configuration. An atom that is not
   listed in `full` or `verdict` has value U. A metric with an empty denominator is null where SPEC section 8 says None;
   deviation and new_false are 0 then ("0/1").
   - **`n_q`, a ninth value at every configuration (R1-1):** the denominator of new_false, as an integer (not a fraction):
     the number of vocabulary atoms that are not in I at this alpha (enc is U, or the atom has no unit) and whose `verdict`
     value is T or F. new_false is the share of these atoms whose `verdict` value differs from their world value, and "0/1"
     when n_q is 0. Write `n_q` in the integer form of the schema, also when it is 0, at every configuration of a test world and
     at "0.7|0" of a calibration world. It does not depend on k, but write it at every configuration.
   - **The boundary band** is a float comparison. A unit is on the boundary at alpha if `abs(mu_pos - alpha) < epsilon_band` or
     `abs(mu_neg - alpha) < epsilon_band`. Evaluate each subtraction, the absolute value and the comparison as IEEE doubles,
     with mu, alpha and `epsilon_band` as parsed from the input. Do not evaluate it on decimal fractions: for example 0.95 -
     0.90 is 0.04999999999999993 as doubles, which is below 0.05, although it is exactly 0.05 as decimals.
4. **Feasible set:** the configurations with fidelity >= tau_s, deviation <= tau_d, consistency >= tau_t and uncertainty <=
   tau_b (exact fraction comparison; a null fidelity, consistency, uncertainty or new_true makes a point infeasible). It is
   defined over all 30 configurations.
5. **Pareto front and hypervolume** over the feasible points with a defined new_true: x = 1 - new_false, y = new_true. Front: the
   points that no other point dominates (at least as large in both coordinates and larger in one); order x descending, y
   descending, then alpha ascending, then k ascending. Hypervolume: the exact area of the union of the rectangles [0, x] x [0, y],
   as "p/q".
6. **G7a** (PREREG section 3.2; the test id in the verdict table is "G7"). G7a has **four** baselines. A single point scores
   x * y = (1 - new_false) * new_true if it is feasible (step 4, with your τ), and 0 if it is infeasible. A feasible point scores
   > 0 exactly when new_true > 0 and new_false < 1.
   - For every alpha, compute the metrics of the four baselines of SPEC section 10 that G7a judges: echo is enc(a) for every
     vocabulary atom, U for an atom without a unit; all_false, all_unknown and all_both are F, U and B for every vocabulary
     atom. Each baseline has the same value in `full` and `verdict`. Do **not** compute all_true: it is a descriptive arm that
     F3 does not cover.
   - Also compute the metrics of the oracle: every atom of I keeps enc, every other atom of K gets its world value T or F, every
     other atom is U. The oracle too has the same value in `full` and `verdict`.
   - A baseline or the oracle is a single point, so its feasibility does not depend on k: use its metrics at each alpha.
   - HOLDS iff each of the four baselines at every alpha scores 0 (it is infeasible, or feasible with x * y = 0), and the oracle
     scores > 0 at some alpha (feasible and x * y > 0 at the same alpha); UNDEFINED iff the oracle has no feasible point; FAILS
     otherwise.
7. **T-1** (PREREG section 3.2) is read at k = 0 only. A feasible point of T-1 is a configuration of the feasible set (step 4)
   with k = 0: at most 10 points, one per alpha. For every pair (p, q) of them with uncertainty(q) < uncertainty(p),
   new_false(q) - new_false(p) <= max(1/20, 1/n_q), where n_q is the `n_q` of step 3 at the configuration q (the point with the
   lower uncertainty); when n_q is 0 the bound is 1/20. Compare as exact fractions. UNDEFINED if fewer than two of these points
   have distinct uncertainty values; FAILS if some pair violates the bound; HOLDS otherwise.
8. **T-1 structure** (PREREG section 3.2, I-5). Write seven fields. Alpha levels are written as strings spelled as in the
   input's configuration keys ("0.95", "0.9", ..., "0.5").
   - `feasible_alphas`: the alpha levels of the feasible T-1 points of step 7, largest first. Written for every world.
   - `defined`: true iff the T-1 outcome of step 7 is not UNDEFINED.
   - On an undefined world the other five fields are null. On a defined world:
     - `alpha_min` and `alpha_max`: the smallest and the largest level of `feasible_alphas`;
     - `sources_spanned`: the number of the world's 8 `source_reliabilities` rho with alpha_min <= rho < alpha_max. Compare as
       decimal numbers (the printed values), not as parsed doubles;
     - `wrong_class_atoms_spanned`: the number of class atoms that have a unit (in `units`, not in `validation_units`), are
       T-encoded at alpha_min (value T), are not T-encoded at alpha_max (value F, B or U) and are world-false (not in
       `true_atoms`). Use the encoded values of step 1;
     - `largest_increase`: the largest value of new_false(q) - new_false(p) over the pairs (p, q) of step 7, as an exact fraction
       "p/q". It can be negative ("-1/20") or zero ("0/1").

## The verdict table (once, over all test worlds)

From the G1 to G6 outcomes that the test inputs give and your own G7a and T-1 outcomes (PREREG sections 3.3 and 4). One row per
test, with the test ids "G1" ... "G6", "G7" (for G7a) and "T-1". There is no G8 row: G8 has no verdict in v0.3, and F3 does not
cover it.
- Count n_holds, n_fails, n_undefined and n_defined = n_holds + n_fails for every test.
- `first_failing_world` of every row: the `world_seed` of the world whose outcome for that test is FAILS and whose `draw_index` is
  the smallest, or null if no world's outcome is FAILS (whatever the verdict is).
- Deterministic tests G1 to G7a: FAILS if any world's outcome is FAILS; else HOLDS if at least 16 worlds are defined (outcome
  not UNDEFINED); else INSUFFICIENT. Their `wilson_lower` is null.
- T-1: INSUFFICIENT if fewer than 16 worlds are defined; otherwise HOLDS iff the one-sided Wilson lower bound of n_holds /
  n_defined is at least 0.80, else FAILS.
- `wilson_lower` for T-1: null if n_defined = 0; otherwise (also with fewer than 16 defined worlds) the bound as an IEEE double,
  computed in this order with n = n_defined and z = 1.6448536269514722: p = n_holds / n; z2 = z * z; centre = p + z2 / (2 * n);
  spread = z * sqrt(p * (1 - p) / n + z2 / (4 * n * n)); bound = (centre - spread) / (1 + z2 / n). Write it as Python's
  `format(bound, ".3f")`. The HOLDS/FAILS decision compares the unrounded double with 0.80.
- `t1_structure_counts`, next to the rows: computed from the structure of step 8 over the worlds whose T-1 outcome is defined.
  - `n`: their number;
  - `median`: the median of their `sources_spanned`, as text: the middle value for an odd `n`, and the mean of the two middle
    values for an even `n`, written as a whole number ("3") or with one decimal ("2.5");
  - `even`: true iff `n` is even;
  - `min` and `max`: the smallest and the largest `sources_spanned`;
  - `n_with_wrong_class_atom`: the number of these worlds with `wrong_class_atoms_spanned` >= 1.
  - For `n` = 0, `median`, `even`, `min` and `max` are null.

## What F3 does not cover

You do not compute these, and you write no field for them: the G1 to G6 outcomes (given), G8 and its summaries, the all_true
arm, G7b, cross-seed agreement, T-1 over all k = 0 points (I-2), T-1 at k0 (I-6), T-1 under v0.2's rule (I-7), T-1 under v0.2's full
rule (I-8), T-1 without the one-atom floor (I-9), the draw-sensitivity arm, the detector diagnostic, and the first-failing-world sentences of the report.

## What you write

Into your own output folder, in exactly the format of `OUTPUT_SCHEMA.json`:
- `<world_seed>.json` for every test-world input file;
- `cal_<world_seed>.json` for every calibration-world input file (the eight metrics and `n_q` at "0.7|0");
- `tau.json` (step 0);
- `verdict_table.json`.

Fractions are strings "p/q" in lowest terms (an integer n is "n/1"; a negative value has a leading minus); undefined is null.
The one exception is `n_q`, which is a plain JSON integer.
Configuration keys are those of the input's `configs`. Do not write any other JSON file into the folder.

## If something is unclear

Do not guess a convention. Write what you did in `NOTES.md` in your output folder and still write all files. The notes are read
by the Independent session, not by the comparison script. NOTES.md is reported with `F3_COMPARE.json` and changes nothing.
