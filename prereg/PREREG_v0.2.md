# Pre-registration: Tesaron v0.2

**Status: DRAFT 5, not frozen.**
- It includes the author's decisions D1–D5, I-1, Q-ε_d, AQ1–AQ5, and the repairs of blind reviews 1–3 (§10).
- Nothing in this file is final until the freeze in §9.

- **Author:** Hazar Şimşek (theory and decisions). Design and draft: Claude (main session). Code: `kodlayici`
  (Sonnet 5.5). Blind review: a fresh agent in a separate session ("Independent").
- **Date written:** 2026-11-22 (drafts 1–5).
- **Version:** draft 5.
- **Structure:** follows the Truth_Gate `PREREG_TEMPLATE.md` (protocol v0.5.1).

## 1. Question

Does the Tesaron v0.1 pipeline, run on reference worlds whose meaning is known by construction, have the following
properties?

**Primary tests.** These are empirical claims about the system:
- **T-1, the author's thesis in the form this design can test (AQ1):** within the reasonable bounds, admitting weaker
  evidence (lowering α) does not increase the share of new false conclusions by more than δ.
  - In these worlds relation evidence has three reliability levels (0.95, 0.80, 0.60). So T-1 compares, in practice,
    the regimes of these sources that the calibrated bounds admit (I-5, AQ5). Under the development calibration these
    were a window where only class atoms change (α 0.65–0.80) and the regime where the weakest source is admitted
    (α ≤ 0.60). Under other calibration draws the bounds also admit α ≥ 0.85, where the 0.80 source is excluded, or
    exclude α ≤ 0.60 (§2). The report prints which regimes the bounds admitted.
  - A graded test of the thesis needs continuous source reliabilities. It is left to a separate pre-registration
    (v0.3).
- **G8:** creativity (abduction) preserves meaning.

**Implementation and criterion checks.** These are decided by construction, and they test that the code does what the
design says. They are regression checks, not discoveries:
- G1: membership is not probability;
- G2: encoding is reproducible;
- G3: meaning units need their data;
- G4: the decoder is deterministic;
- G5: validation data do not leak into pattern computation;
- G6: expansion makes no unevidenced claims;
- **G7 (G7a, AQ2, AQ4):** none of the five degenerate baselines of SPEC §10 gets a positive score under the wisdom
  criterion. The criterion does not exclude degenerate strategies in general (§2).

The run is labelled a **model test on new worlds**.

## 2. Known and prospective

| Part | Known or prospective | Why |
|---|---|---|
| The code of v0.1 and its revisions S-1–S-9 (SPEC §15) | known | Written and tested on development seeds 900000–900999 |
| The full creativity grid on development world 900001 (encoder seed 900101) | known to the designer and the author | It was printed by the smoke command. Over the whole grid, new_false rose as uncertainty fell. From α 0.80 to 0.70 it did not rise (0.031 → 0.028); from 0.70 to 0.60 it jumped (0.028 → 0.224), where the 0.60 source is admitted. |
| Medians and ranges of \|H\|, new_true, new_false, fidelity and uncertainty at α 0.7, k 0 over development worlds 900000–900099 | known to the designer | v0.1 diagnostic (descriptive) |
| Pilot counts on 20 development worlds (first D4 run, under dev-calibrated τ): T-1 HOLDS on 12 of 17 defined, G8 on 6 of 20 | known to the designer and, through this file, to the author | Draft 2 did not define "covered" in the D4 output, and it was printed as a count. This was the designer's error. |
| The structure of T-1 on development worlds, from blind review 1 (R1-2) | known to the designer and the author | τ_b excluded every α ≥ 0.85 on 20 of 20 worlds. Inside α 0.65–0.80, new_false never rose toward lower uncertainty. Where α = 0.60 was feasible, new_false rose from 0.65 to 0.60 by 0.071–0.188 (> δ). The reviewer withheld the count that would give a pilot rate. |
| Twin outcomes, k-invariance, denominators, baseline scores and feasibility on development worlds, from blind review 1 | known | design quantities, listed in the review's appendix |
| **T-1's definedness and regimes depend strongly on the calibration draw** (design quantities, drafts 4 and 5) | known to the designer and the author | Two development sets were each calibrated on their own 10 worlds by D1. Of 20 test worlds, 7 and 2 had no feasible point, and T-1 was defined on 11 and 17. Float and exact comparisons gave identical counts. Blind review 2 and its replication (`prereg/DRAW_STUDY.json`) repeated this over 40 calibration draws each, on 30 development test worlds (§7). The number of defined worlds, the default's feasibility, and whether α ≥ 0.85 is feasible all vary widely between draws. D1 takes extremes over only 10 worlds, so τ, and with it the feasible sets, vary a lot between calibration draws. With 30 test worlds, T-1 may therefore end in "insufficient worlds" (fewer than 16 defined), and its power is lower than the n = 30 row of §7 suggests. G8 does not use feasibility. G7a's baseline rule and its definedness do; the oracle was feasible on every development test world under every draw. |
| **Degenerate strategies outside the five baselines** (blind review 2, R2-1) | known to the designer and the author | "echo+F" keeps enc on I and sets every other atom to F; "echo+T" sets them to T. On I they equal the oracle, so they are feasible wherever the oracle is. They score > 0 whenever H holds a world-false (echo+F) or world-true (echo+T) atom. On 30 development worlds under a development τ, they scored > 0 on 29 and on 30. The criterion therefore does not exclude degenerate strategies in general; G7a claims only the five baselines of SPEC §10 (AQ4). |
| Everything on calibration and test worlds | prospective | Their seeds need a salt that is drawn only after the freeze commit is public (§7, R1-3), so nobody can compute them before the freeze |

**Expected verdicts given the pilot (R1-10).**
- If the test worlds behave like the development worlds, T-1 and G8 are expected to FAIL.
- T-1 may also end in "insufficient worlds": on development worlds its number of defined worlds varied strongly between
  calibration draws (§7).
- Under the 28/30 rule, P(HOLDS) is about 0.003 at a per-world rate of 0.71 (T-1), and about 0 at 0.30 (G8).
- The test τ will differ from the development τ, which is a caveat.
- A different outcome would mean that the test worlds, or for T-1 the calibrated bounds, differ from the development
  ones (see the structure counts) (R3-5).
- The report prints this paragraph next to the T-1 and G8 verdicts.

**The tautology question.**
- **G1–G7a are decided by construction.** They are regression checks of the code and of the criterion, labelled so in
  the report:
  - μ⁻ of a class unit is hard-coded to 0;
  - a unit exists only with D_derive rows;
  - OBSERVED and DERIVED are exactly the pass-1 fixpoint;
  - the five baselines cannot score: echo, all_unknown and all_both by their definitions; all_true and all_false
    because they change many decided encoded atoms, which the calibrated τ_d and τ_s exclude.
- **T-1 is not decided by definition, but its outcome is mostly decided by one discrete event** (I-5):
  - Uncertainty is computed over K, and new_false over the decided atoms outside I. These sets overlap: E∖I and H belong
    to both, and the complement of I shrinks as α falls.
  - The coupling is therefore partial, not absent.
  - What decides T-1 on most worlds is whether the D1 bounds admit α ≤ 0.60. Those bounds vary strongly between
    calibration draws, so a draw whose bounds exclude α ≤ 0.60 on most worlds can produce a HOLDS whatever trade-off
    the system has (R2-3). The structure counts printed next to the verdict show whether this happened.
- **G8 is empirical.** With ε_d below one atom at most α, G8 in practice asks whether abduction changes any decided
  encoded atom (I-6).

## 3. Criteria

### 3.1 Shared definitions

- **Default configuration:** α₀ = 0.7, k₀ = 5 (the Context defaults).
- **Grid (D3):** α ∈ {0.95, 0.90, 0.85, 0.80, 0.75, 0.70, 0.65, 0.60, 0.55, 0.50} × k ∈ {0, 5, 10}; 30
  configurations.
- **What does not depend on k (R1-5):** under A-6 the verdict view ignores hypotheses. So uncertainty, new_true and
  new_false at (α, k) equal their values at (α, 0), and the Pareto points and the T-1 coordinates depend on α only. k
  changes fidelity, deviation and consistency, and therefore feasibility. T-1 compares at most 10 distinct α levels.
- **τ values (D1):** calibrated by the rule in §7.
- **Exact comparisons (R1-8):** every metric is a ratio of integer counts. All comparisons with τ, ε_f, ε_d and δ, and
  all differences of metrics, are made exactly, as rationals (`fractions.Fraction` of the counts). τ values are stored
  as exact fractions.
- **Per-world outcome:** every per-world check returns HOLDS, FAILS or UNDEFINED. UNDEFINED is returned only by the
  check's own stated definedness condition. A crash is not UNDEFINED; it ends the run (§8).
- **Anchor:** every check contains a part that zero or noise data cannot satisfy, so that it can pass the gate's
  vacuity probes (K5).

### 3.2 Tests

| Id | Claim | Per-world HOLDS when | FAILS when | UNDEFINED when |
|---|---|---|---|---|
| G1 | Membership degrees are not turned into probabilities | (i) for every outlier entity with D_derive rows, Σ_k u_ek < 0.5; (ii) every class unit of **every** entity has μ⁻ = 0 exactly (SPEC §5: μ⁻ is never derived from μ⁺); (iii) anchor: the median own-class typicality of the normal entities is ≥ 0.5 | any of (i)–(iii) fails; the failed parts are recorded (R2-13) | never |
| G2 | Encoding is reproducible in the same context (same machine, same NumPy build) | the canonical hash of the encoding is identical in-process and in two subprocesses with `PYTHONHASHSEED` 0 and 1 (set explicitly); anchor: encoder seed + 1 gives a different hash | otherwise | never |
| G3 | A meaning unit needs its data (necessity) | at α₀, for every meaning unit, removing its provenance rows from D_derive and re-encoding makes the unit absent or U; anchor: at least one ablated unit was decided (T, F or B) before | some ablated unit stays decided | never |
| G4 | The decoder gives the same output for the same input (same machine, same NumPy build) | at (α₀, k₀), the canonical output hash is identical across the original order, 3 permutations of facts and rules, and 3 subprocesses with `PYTHONHASHSEED` 0, 1 and 4242; anchor: the output has at least one fact | otherwise | never |
| G5 | Validation data do not leak into pattern computation | after the D_validate feature values are replaced with garbage and its report polarities are flipped, the fitted centers are bit-identical, and the map atom → (μ⁺, μ⁻, status, provenance) of the D_derive units is identical; anchor: corrupting D_derive the same way changes the centers | otherwise | never |
| G6 | Expansion makes no unevidenced claims | at α₀ and k = 10, every fact with status OBSERVED or DERIVED is in the pass-1 fixpoint recomputed from the observed facts alone by the brute-force closure of `audit/indep` (R1-11), and every fact outside that fixpoint has status HYPOTHESIS | otherwise | no abduction candidate at α₀, k = 10 |
| G7 (G7a) | None of the five degenerate baselines of SPEC §10 (echo, all_true, all_false, all_unknown, all_both) gets a positive score under the wisdom criterion (AQ2, AQ4) | every baseline (echo, all_true, all_false, all_unknown, all_both) at every α of the grid, scored as a single point, is infeasible or scores 0; anchor: the oracle (§6.3) scores > 0 at some α | some baseline scores > 0 at some α | the oracle has no feasible point |
| G8 | Creativity (abduction) preserves meaning (D4b) | for every α of the grid and k ∈ {5, 10}: fidelity(α, 0) − fidelity(α, k) ≤ ε_f and deviation(α, k) − deviation(α, 0) ≤ ε_d. An (α, k) comparison where a fidelity is undefined (I empty) is skipped. Anchor: at least one hypothesis at α₀, k = 10 | some (α, k) violates either bound | no hypothesis at α₀, k = 10, or every comparison is skipped |
| T-1 | Within the reasonable bounds, admitting weaker evidence does not increase new false conclusions by more than δ (AQ1, I-5) | for every pair of feasible points p, q with uncertainty(q) < uncertainty(p): new_false(q) − new_false(p) ≤ δ, with δ = 0.05 (D2) | some pair violates it | fewer than two feasible points with distinct uncertainty values |

**Descriptive arms.** These are reported, never part of a verdict:
- **G7b, the system's own score (AQ2):** per world, the system's hypervolume over the grid, and whether it is > 0.
- **Cross-seed stability (D4a):** the agreement of encoded values at α₀ under the world's encoder seed and a second seed
  (role `aux`). It is computed among atoms present in both encodings and outside the boundary band in both, for class
  atoms and for all atoms.
- **G8 over the whole grid (I-4):** fidelity ≥ τ_s and deviation ≤ τ_d at every point.
- **T-1 over all grid points (I-2).**
- **T-1's structure (I-5, R1-2, R2-3):** per world:
  - the feasible α set;
  - whether some α ≤ 0.60 is feasible, and whether some α ≥ 0.85 is feasible;
  - T-1 restricted to pairs that cross the 0.60/0.65 boundary;
  - T-1 restricted to pairs that cross the 0.80/0.85 boundary;
  - T-1 restricted to pairs inside α 0.65–0.80.

  Its counts over the defined worlds are printed next to the T-1 verdict (§4).
- **Default feasibility (R1-13):** for each test world, whether the default (α₀, k₀) is feasible.
- **UNDEFINED as FAILS (R1-13):** for T-1 and G8, the Wilson share with UNDEFINED worlds counted as FAILS.
- **The detector diagnostic** (§6.2).

### 3.3 From worlds to a test verdict

- **Deterministic tests (G1–G7a):** the test HOLDS if no defined test world FAILS and at least 16 test worlds are
  defined. One FAILS world makes the test FAIL (A-8), even if fewer than 16 worlds are defined. Otherwise, with fewer
  than 16 defined worlds, the verdict is "insufficient worlds".
- **Quantitative tests (G8, T-1):** the test HOLDS if the one-sided 95% Wilson lower bound of the HOLDS share among
  defined worlds is ≥ 0.80 (z = 1.6448536269514722) and at least 16 worlds are defined. Otherwise the test FAILS; with
  fewer than 16 defined worlds the verdict is "insufficient worlds".
  - With 30 defined worlds, the Wilson rule is exactly the author's "at least 28 of 30" (A-8).
  - What a HOLDS means: the per-world rate is at least 0.80, at one-sided 95% confidence.
- **UNDEFINED worlds (D2):** UNDEFINED never counts as HOLDS. UNDEFINED worlds are excluded from the share, and their
  number is reported for every test.
- **Multiplicity (R1-20):** there is no combined verdict. Each quantitative test runs at one-sided 5%; over the two
  primary tests, the family-wise error is up to about 10%.

## 4. Verdict mapping

- Each test has its own verdict: HOLDS, FAILS or "insufficient worlds". There is no combined verdict for the
  architecture.
- The report gives a table with one row per test and the per-world counts (HOLDS / FAILS / UNDEFINED).

Fixed wording:
- **Deterministic test, HOLDS:** "<Id> holds: <claim>, in all <n_defined> defined test worlds (<n_undefined>
  undefined). (A check of the implementation or of the criterion, not a discovery.)"
- **Deterministic test, FAILS:** "<Id> does not hold: <n_fails> of <n_defined> defined test worlds fail; the first
  failing world is <seed>." For G1 it adds: "Failed parts in the first failing world: <parts>." (R2-13) The first
  failing world is the FAILS world with the smallest draw index.
- **Quantitative test, HOLDS:** "<Id> holds: <claim>. <n_holds> of <n_defined> defined worlds hold (Wilson lower bound
  <b>, threshold 0.80); <n_undefined> undefined."
- **Quantitative test, FAILS:** "<Id> does not hold: <n_holds> of <n_defined> defined worlds hold (Wilson lower bound
  <b>, threshold 0.80); <n_undefined> undefined; the first failing world is <seed>."
- **G8, FAILS, additional sentence (R1-7):** "At most α the tolerance ε_d is below one atom, so a world fails when
  abduction changes the value of a single decided encoded atom."
- **G8, every verdict, additional sentence (R2-3):** "Hypotheses at (α₀, k = 10) over the defined worlds: minimum
  <a>, median <m>, maximum <b>." With an even number of worlds the median is the mean of the two middle values, and
  the sentence says so.
- **T-1, additional sentences (I-5, AQ5, R2-3, R3-9).** They are computed from the structure arm over the defined
  worlds and printed in this order with every T-1 verdict, "insufficient worlds" included:
  - "In these worlds T-1 compares regimes of the three source reliabilities: on <a> of <n> defined worlds the
    feasible set reached α ≤ 0.60, where the 0.60 source is admitted, and on <b> it reached α ≥ 0.85, where the 0.80
    source is excluded. T-1's outcome depends strongly on the calibrated bounds, which vary between calibration draws.
    It is not a graded test of the thesis."
  - "Structure (I-5): of <n> defined worlds, <a> had some feasible α ≤ 0.60 and <b> some feasible α ≥ 0.85. Pairs
    inside α 0.65–0.80: <h> hold, <f> fail, <u> none. Pairs crossing 0.60/0.65: <h>/<f>/<u>. Pairs crossing
    0.80/0.85: <h>/<f>/<u>."
  - Only with a HOLDS: "A HOLDS can result from calibrated bounds that exclude the 0.60 source on most worlds; see the
    structure counts."
- **Insufficient worlds:** "<Id>: insufficient worlds (<n_defined> defined, 16 required); no verdict."

The expected-verdict paragraph of §2 is printed next to the T-1 and G8 verdicts.

The following limitation sentence is printed next to every verdict and in the limitations section:

> These results come from synthetic worlds generated by code written by the same model family that designed and coded
> the system. The decoder was given the true rules. They say nothing about natural-language input.

## 5. Interpretations

| No. | Interpretation | Opposite reading | Can it change the verdict? | Sensitivity arm | Verdict under the opposite reading |
|---|---|---|---|---|---|
| I-1 | "10 calibration and 30 test worlds per G" (A-8) means one shared set of 10 calibration and 30 test worlds, used by every test and by T-1 (author: "uygun", 2026-11-22) | a separate set for each test | no: the sets are exchangeable random draws from the same generator | none | same distribution |
| I-2 | "Points that satisfy the constraints" (A-7) means grid points that are feasible under the calibrated τ | all grid points | yes | T-1 is also computed over all grid points and reported as descriptive, never as the verdict | descriptive only |
| I-3 | "One violation fails" (A-8) counts only FAILS worlds; UNDEFINED is not a violation | UNDEFINED counts as a violation | for G6 and G7a among the deterministic tests | the number of UNDEFINED worlds is reported for every test | reported |
| I-4 | G8 is read on the abduction axis (D4b) | the whole grid | yes | the whole-grid reading is reported as descriptive | descriptive only |
| I-5 | With three discrete source reliabilities, T-1 compares the source regimes that the D1 bounds admit: under the development calibration, the class-only window α 0.65–0.80 and the regime α ≤ 0.60; under other draws also α ≥ 0.85, or no α ≤ 0.60 (AQ1, AQ5) | T-1 as a graded test of the thesis | it changes what a verdict means, not the verdict | T-1's structure arm (§3.2), with its counts printed next to the verdict | the computed verdict sentences say which regimes were compared |
| I-6 | G8's ε_d is below one atom at most α (Q-ε_d (a)) | a tolerance of one atom | yes | the number of worlds that fail only through a single-atom change is reported | descriptive only |

## 6. Controls

### 6.1 Fidelity controls

These are independent implementations of the code paths that decide verdicts, from the selected rows onward. The code
in `audit/indep` does not import `tesaron.decoder`, `tesaron.encoder` or `tesaron.belnap`.

**Not covered by an independent implementation** (R2-6, R3-8):
- the row selection and the derive/validate split (SPEC §5, steps 1–2), which are taken from the system. G2 tests only
  that they are reproducible and G5 only that D_validate does not leak; neither tests that they follow SPEC §5;
- the G8 hypothesis summary printed next to the G8 verdict (§4). F3 does not recompute it; F1 checks the kept
  hypotheses it counts.

| Id | What is compared | Independent implementation | Pass rule |
|---|---|---|---|
| F1 | the decoder's pass-1 fact set; its abduction candidates (the full ranked list with scores) and the kept top-k; and its pass-2 fact set; at every grid configuration | the brute-force closure and a brute-force candidate enumerator that follows SPEC §7.3 (R2-6). Pass 2 is recomputed from the independently enumerated hypotheses, not from the decoder's. Naive against semi-naive is also compared, for the derivation records. | equal sets, lists and records, on every test world |
| F2 | H | the same brute-force closure | equal sets on every test world |
| F3 | every metric, the feasible set, the front, the hypervolume, every G7a, G8 and T-1 outcome, T-1's structure fields, and the verdict table with each test's first failing world (R3-3) | after the run, a recomputation by a fresh agent in the Independent session, with the frozen instructions `audit/f3/INSTRUCTIONS_F3.md` and output schema `audit/f3/OUTPUT_SCHEMA.json`. It receives only the inputs: world truth, rules, units, the full and verdict value lists, τ, the grid, the draw index, this file, and the run's G1–G6 per-world outcomes, labelled as given (F3 does not recompute them; it needs them only for the verdict table). The run's own metrics, check data and outcomes are in a separate file. After the agent has written its results, the frozen script `audit/f3_compare.py` compares every field: exact string equality for the p/q fractions, exact equality otherwise (R2-7). | 0 disagreements. Resolution of a disagreement, below. |
| F4 | the encoder: PCM's fitted centers, converged flag, iteration count and degeneracy flag; the class units' μ⁺, provenance and status; the relation units (μ⁺, μ⁻, provenance), with support degrees taken from the world's source reliabilities; and the interface facts of all units at every α | a direct numpy loop for PCM with its own degeneracy check (SPEC §5, step 3), and direct recomputations from the D_derive rows and the Belnap table (R2-6, R3-8) | centers and class μ⁺ equal to 1e-12; flags, iteration counts, provenance, statuses, relation units and fact sets exactly equal; on the 20 development worlds before the freeze (recorded in `prereg/F4_PREFREEZE.json`, with F1) and on every test world |

**Resolution of an F3 disagreement** (R2-7, R3-2). It is mechanical:
- **The affected tests** of a disagreement are fixed in advance by the field-to-test map in `audit/f3_compare.py`,
  which writes them on every disagreement: fidelity and deviation → G8 and T-1; consistency, uncertainty, new_true,
  new_false, the feasible set and T-1's structure fields → T-1; a per-world outcome or a verdict-table row of test X →
  X; a missing or extra world or file → G7a, G8 and T-1; the front, the hypervolume, validation_agreement and
  boundary_share → none.
- A second fresh agent recomputes the disagreeing worlds from the same input and instructions. For a disagreement in
  the verdict table only, it recomputes the whole table.
- If its values equal the run's, the first agent erred. The verdicts stand, and both recomputations are reported.
- If its values equal the first agent's, the run's code is taken to be wrong. The affected tests get no verdict in this
  version; a new version needs a new freeze and a new salt (§8, step 11).
- Any other outcome also means no verdict for the affected tests.
- A disagreement with no affected test is reported and changes nothing.
- The agents' `NOTES.md` files are reported with `F3_COMPARE.json` and change nothing.

### 6.2 Detector controls: one faulty twin per test

Each faulty twin lives in `audit/twins/`. Twins never change `tesaron/`; they wrap or replace one function.

| Id | Test | How it violates the claim | Expected per-world outcome |
|---|---|---|---|
| N1a | G1 | normalize typicalities to sum 1 per entity (FCM-like) | FAILS (i) |
| N1b | G1 | μ⁻ = 1 − μ⁺ for class atoms | FAILS (ii) |
| N2 | G2 | the encoder's permutation does not come from the context seed. The repeated runs use different seeds that do not come from the context: in the real run, seed("n2", 2i) and seed("n2", 2i+1), where i is the draw index; in the gate, rng-drawn seeds. Both versions are deterministic and reproducible. | FAILS |
| N3 | G3 | every relation atom with no report gets a default μ⁺ = 0.8 (prior) | FAILS |
| N4 | G4 | abduction breaks ties by an order that is not canonical: in the real run, the iteration order of a Python `set` of strings, across subprocesses; in the gate, a different rng-drawn order for each repeated run | FAILS |
| N5 | G5 | PCM is fitted on D_derive ∪ D_validate | FAILS |
| N6 | G6 | hypotheses are inserted with status OBSERVED | FAILS |
| N7 | G7a | the unconstrained criterion: feasibility is ignored, so every baseline point is scored | FAILS (all_true then scores > 0) |
| N8 | G8 | abduction overwrites observations. At every k > 0, the first min(k, n) observed facts of decided encoded atoms (canonical order; n = their number) are removed, and the opposite-channel fact is added with status HYPOTHESIS. Deduction then runs as usual. | FAILS |
| NT | T-1 | metric points with a built-in trade-off: new_false rises by 0.2 as uncertainty falls | FAILS |

**Detector diagnostic in the real run** (R1-21):
- On every test world, each twin of G1–G8 is run, and its outcome is reported next to the fixed system's.
- It is a diagnostic, not a world filter. Selecting worlds by twin behaviour would bias the selection.
- For each test, the report also gives the number of worlds where both the fixed system and its twin HOLD. If that
  number is above 0, the HOLDS verdict is qualified: "the detector did not separate on <n> worlds".

### 6.3 Layer 1: the gate (Truth_Gate v0.5.1)

- **One study file per test,** in `audit/gate/`. Worlds run on development worlds (seeds drawn from 900000–900999 by
  the study's rng). The criterion is the same judge function used in Layer 2; each check is split into collecting
  arrays and judging them.
- **The `plus` world** is a system on which the claim holds by construction:
  - **G1–G6:** the fixed system.
  - **G7a:** the actual criterion, applied to the baselines and to the oracle. The **oracle** keeps every atom of I at
    its encoded value, gives every other atom of K its world value, and leaves all other atoms U.
  - **G8:** abduction without propagation. Pass 2 adds the hypotheses, which are U atoms, and does not deduce.
  - **T-1:** metric arrays shaped like the real data (R1-15): the grid metrics of a development world, restricted to
    α 0.65–0.80.
- **The `minus` world** is `plus` with one declared change, the faulty twin:
  - G7a: N7, the unconstrained criterion;
  - G8: N8 applied to G8's `plus`;
  - T-1: NT applied to T-1's `plus`.
- **What the gate does not exercise:**
  - the subprocess parts of G2 and G4, which run only in Layer 2 and in the unit tests;
  - N4's real-run mechanism;
  - τ calibration, aggregation, seed derivation, world validity and the F controls. These are covered by the unit tests
    and by F3.
- **The driver.** The studies are run with `py -m audit.gate.certify <id>` (and `--verify`).
  - It imports the study's modules before the leak guard, then calls `truth_gate.cli.main`.
  - It loads `truth_gate` from the local `kapi-oss` checkout, records that checkout's commit, and refuses to run if
    `truth_gate/`, `kapi/` or `protocol/` differ from tag `v0.5.1` or hold untracked files (R2-12).
- **Required certificates:** every certificate must be FALSIFIABLE. A WEAK certificate is accepted only with a written
  reason and the author's approval.
- **Budget:** 100 samples per study.
- **Just before the freeze** (R1-15): `certify all --verify` is run on the tree to be frozen. Its output, the kapi-oss
  commit and the SHA-256 of every file in `audit/` and `tesaron/` are written to `audit/gate/GATE_TOOL.json`.
- **Pre-freeze check** (R2-12, R3-1): `audit/prefreeze_check.py` refuses the freeze unless the file hashes in
  GATE_TOOL.json equal the current files of `audit/` and `tesaron/`; the files the freeze verifier would hash are
  exactly the git-tracked files under the manifest paths (no ignored or untracked file); and every such file's bytes
  equal its staged git blob.
- **Line endings** (R3-1): `.gitattributes` sets `* text=auto eol=lf`, and every text file is stored with LF, so that a
  clone on any machine and with any `core.autocrlf` setting reproduces the hashed bytes. Code that writes files into
  the repository writes LF.

## 7. Grid, N and tolerances

| Item | Value | Why |
|---|---|---|
| Grid (D3) | α ∈ {0.95, …, 0.50} in steps of 0.05 × k ∈ {0, 5, 10}; 30 configurations | The source supports 0.95, 0.80 and 0.60 give relation atoms only three regimes. The finer α steps resolve the class atoms. k adds no T-1 pairs (§3.1). |
| τ calibration rule (D1) | Run the fixed system at (α₀, k₀) on the 10 calibration worlds. τ_s = min fidelity, τ_d = max deviation, τ_t = min consistency, τ_b = max uncertainty; all exact fractions. | The default configuration defines what "reasonable" looks like; a configuration is out of bounds when it is worse than the worst the default showed. By construction, the default is feasible on every calibration world (not on every test world: R1-13). |
| δ for T-1 (D2) | 0.05 | one new false conclusion in 20 decided ones |
| UNDEFINED worlds (D2) | excluded from the share; at least 16 defined worlds required | does not conflate "could not be tested" with "false" |
| G2b (D4a) | descriptive only (§3.2) | Different encoder seeds select different rows, so most of the variation is legitimate evidence variation |
| G8 tolerances (D4b; Q-ε_d (a)) | ε_f = 0.05, ε_d = 0.02, compared exactly | With fewer than 50 decided encoded atoms (most α ≥ 0.65), a single changed atom already exceeds ε_d. The author kept the value with this in view (I-6). |
| World validity (D5) | PCM usable (converged and not degenerate), and \|H\| ≥ 10. A calibration world is invalid if one of its four τ metrics at the default configuration (fidelity, deviation, consistency, uncertainty) is undefined. new_true is always defined under \|H\| ≥ 10. A world whose generator fails after max_attempts (a dedicated exception) is invalid. | Phase D lesson: a world must leave room to measure |
| Replacement | an invalid world is replaced by the next draw index. At most 200 draws per set, otherwise the run stops with no verdict. | |
| Calibration worlds | 10 valid worlds (A-8) | |
| Test worlds | 30 valid worlds (A-8, I-1, AQ3) | |
| Encoder seed | one per world, plus one `aux` seed per test world for the descriptive cross-seed comparison | |
| Seeds (R1-3) | seed(role, i) = 1 000 000 + (first 8 bytes of SHA-256("<core_sha256>\|<salt>\|<role>\|<i>") as a big-endian integer) mod 10⁹. The roles are `world-cal`, `world-test`, `enc-cal`, `enc-test`, `aux`, `perm` and `n2`. i is the draw index d, except for `perm` (i = 3d + p, p = 0, 1, 2: the three G4 permutations) and `n2` (i = 2d and 2d + 1) (R2-10). | The salt is 32 random bytes drawn by the Independent session after it is given the id of the freeze commit already pushed to the public repository (§8). Before then the seeds cannot be computed by anyone, the designer included. The range is disjoint from the development range. |
| Versions (R1-14) | Python 3.14.2, NumPy 2.4.1 (the versions used for the certificates) | The runner refuses other versions. CAL_WORLDS, TEST_WORLDS and VERDICTS record `sys.version`, `numpy.__version__`, the platform, and a canonical hash of each world and encoding. G2 and G4 claim determinism on one machine and one NumPy build only. |
| Power (AQ3, R1-9) | see the table below | protocol rule 16 |
| Drift | zero on one machine and NumPy build by construction (G2, G4) | protocol rule, run-to-run drift |

**Power of the quantitative tests (AQ3).** The table gives the minimum number of HOLDS worlds under the Wilson rule, and
P(HOLDS) for a true per-world rate r.

| Defined worlds n | HOLDS needed | r = 0.95 | r = 0.90 | r = 0.85 | r = 0.80 |
|---|---|---|---|---|---|
| 30 | 28 | 0.812 | 0.411 | 0.151 | 0.044 |
| 28 | 26 | 0.837 | 0.459 | 0.187 | 0.061 |
| 27 | 26 | 0.606 | 0.233 | 0.072 | 0.019 |
| 26 | 25 | 0.624 | 0.251 | 0.082 | 0.023 |
| 24 | 23 | 0.661 | 0.292 | 0.106 | 0.033 |
| 20 | 19 | 0.736 | 0.392 | 0.176 | 0.069 |
| 16–19 | all n | 0.38–0.44 | 0.14–0.19 | 0.05–0.07 | 0.01–0.03 |

- With 30 defined worlds, a system whose true per-world rate is 0.95 gets a HOLDS with probability 0.81.
- **T-1's number of defined worlds depends strongly on the calibration draw** (§2, R2-4). The calibration-draw study
  `prereg/DRAW_STUDY.json` has 40 draws of 10 development calibration worlds (PCG64(1729)), each evaluated on the same
  30 development test worlds. It replicates blind review 2's study with different draws. Its design quantities:
  - T-1 was defined on 11–30 worlds (median 23). It had fewer than 16 ("insufficient worlds") in 3 of 40 draws, and
    16–19 in 5 more.
  - The default was feasible on 9–29 worlds (median 19.5); 0–15 worlds had no feasible point (median 5.5).
  - Some α ≥ 0.85 was feasible on at least one world in 13 of 40 draws (on up to 25 worlds).
  - τ_s ranged over 13/18–44/51, τ_d over 0–6/53, τ_t over 18/19–129/130 and τ_b over 73/138–39/49.
  - G7a was defined on all 30 worlds in every draw.
- **Averaged over the draws,** with an insufficient draw counted as no HOLDS, T-1's P(HOLDS | r) is 0.59 at r = 0.95,
  0.26 at 0.90, 0.10 at 0.85 and 0.03 at 0.80. Blind review 2's own 40 draws gave similar figures (defined on 10–30
  worlds, median 22; insufficient in 2 of 40).
- These figures reflect the development system's behaviour; definedness also depends on the system (R1-13).
- G8 does not use τ. Its number of defined worlds is the number of worlds with a hypothesis at (α₀, k = 10); the
  table above applies.
- The author kept 30 test worlds (AQ3). Drawing until 30 worlds are defined was rejected, because definedness depends
  on the system's quality (R1-13).

**Alternatives the author did not choose (for the record):**
- **D1:** medians ± 0.05; fixed values.
- **D2:** δ 0.02 or 0.10; UNDEFINED counted as FAILS (reported as descriptive instead).
- **D3:** the v0.1 grid.
- **D4a:** a confirmatory G2b.
- **D4b:** the whole-grid G8.
- **D5:** \|H\| ≥ 20; no minimum.
- **Q-ε_d (b):** a one-atom tolerance.
- **AQ1 (b):** redesign the worlds now with continuous reliabilities.
- **AQ2:** G7b as a confirmatory test.
- **AQ3:** draw until 30 worlds are defined, or 34 test worlds.
- **AQ4:** the narrowed G7a claim plus a descriptive arm that scores echo+F and echo+T; or echo+F and echo+T added to
  G7a's baselines with the general claim kept (G7a then expected to FAIL).
- **AQ5:** a change of D1 or N after the draw dependence became known (rejected: the pilot is known, so a change would
  steer T-1 in a predictable direction).

## 8. Run plan

1. ~~The author decides D1–D5, Q-ε_d, AQ1–AQ3.~~ Done 2026-11-22.
2. **Code (`kodlayici`):** the audit layer as described, including the draft-4 repairs (§10).
3. **D4 smoke test** on development worlds only. For each check it prints only the number of defined worlds, reachable
   (yes/no) and covered (yes/no). No counts of HOLDS, and no verdict values.
4. **Gate certificates** for G1–G8 and T-1 (§6.3), then F4 on 20 development worlds (`prereg/F4_PREFREEZE.json`).
5. **Blind reviews 2 and 3** in the Independent session: review 2 of the draft-4 text and code, and review 3,
   targeted at the draft-5 repairs and the code they added (the author's choice, 2026-11-22). Findings are handled with
   the repair loop and recorded. Review 3 judged that no further blind review is needed once its findings are repaired;
   the fresh-clone verification of step 7 takes its place.
6. **Just before the freeze:** `certify all --verify`, GATE_TOOL.json written, and the pre-freeze check (§6.3).
7. **The author's approval, then the freeze:**
   - `prereg/FREEZE_v0.2.json` is written with the freeze verifier, from a tree whose frozen files are all tracked.
   - The freeze record (date, core hash, freeze commit, platform string of the run machine, sign-off) goes into
     `prereg/FREEZE_RECORD.md`, which is outside the manifest (R1-16). The salt is added to it in step 8 (R2-10).
   - The freeze is committed. Before the push, `py -m audit.clone_verify` clones that commit into a fresh folder and
     runs the freeze verifier there (R3-1); its result goes into the freeze record. Only if it verifies is the freeze
     pushed, with the author's OK. Exactly one commit ever touches the manifest.
8. **The salt (R1-3, R2-2):**
   - The Independent session is given the id of the pushed freeze commit and the core hash. It draws 32 random bytes,
     records them with the commit id and the core hash in its own folder, and reports them.
   - The designer writes them to `run/SALT.json` (salt, freeze commit, core hash, who drew them, time), adds the salt
     to the freeze record, and commits and pushes both.
9. **Calibrate.** Before it, `git fetch origin` is run; the runner itself reads only the local remote-tracking ref
   `origin/main` and uses no network. The runner refuses unless all of the following hold (R2-2):
   - the manifest verifies;
   - exactly one commit touches `FREEZE_v0.2.json` (with full history); it is the freeze commit, and it is on
     `origin/main`;
   - the manifest lists exactly the files tracked under the §9 manifest paths in the freeze commit (R3-7);
   - the manifest and every frozen file are tracked, unmodified, and identical to their content in the freeze commit;
   - exactly one commit touches `run/SALT.json`; it is a strict descendant of the freeze commit and on `origin/main`;
     the file names the freeze commit, and its core hash equals the verified manifest's.

   It then generates and validates the calibration worlds and computes τ by D1. `run/CAL_WORLDS.json` and
   `run/TAU.json` are committed and pushed before any test world exists.
10. **Test** (R1-4, R1-12). The runner:
    - refuses unless everything in step 9 holds, and exactly one commit touches each of `CAL_WORLDS.json` and
      `TAU.json`, a strict descendant of the salt commit and on `origin/main`;
    - regenerates the calibration worlds and recomputes τ, and refuses unless the world records equal those in
      `CAL_WORLDS.json` (R3-7), τ equals `TAU.json` exactly, and `sha256(CAL_WORLDS.json)` matches;
    - generates and validates the 30 test worlds;
    - runs F1, F2 and F4 on all of them first, and stops with no verdict on any disagreement;
    - only then runs G1–G8, T-1, the detector diagnostic and the descriptive arms. It holds the per-world outputs in
      memory, builds the verdict table and the descriptive summary, and only then writes any output, so a crash leaves
      no outcome on disk (R2-11, R3-6).
11. **Stop, crash and rerun (R1-12, R2-11).**
    - A stop or a crash ends the run with no verdict.
    - Any change to the code after that is a new version, with a deviation note, a new freeze and a new salt.
    - The first complete run is the result. Its outputs, `VERDICTS.json` included, are committed and pushed at once.
    - The rerun is `py -m audit.run_v02 reproduce`, run in a fresh clone of that result commit on the machine whose
      platform string is in the freeze record (R3-6). It repeats the test step with every real-mode check into
      `run_repro/`, reading SALT, CAL_WORLDS and TAU from `run/`, and compares the SHA-256 of its `VERDICTS.json` with
      the committed one. It must reproduce it byte for byte; the outcome is reported.
12. **F3** (independent recomputation, blind input, §6.1) and the **blind post-run audit**, both in the Independent
    session. The post-run audit also checks (R2-2):
    - that `run/SALT.json` holds the salt, freeze commit and core hash that the Independent session recorded in step 8;
    - that the freeze, salt, CAL/TAU and result commits are on the public remote, in the order of steps 7–11. The
      Independent session checks this in a fresh clone of the public repository that it makes itself (the only
      network access of that task).
13. **Report** the pre-registered table as it is, with the fixed wording, the expected-verdict paragraph and the
    limitation sentence.

## 9. Freeze

- **Files in the manifest:**
  - this file and `SPEC.md`;
  - `tesaron/**` and `audit/**` (twins, checks, gate studies, the runner, the freeze verifier, the pre-freeze check,
    the design study, and `audit/f3/` with `audit/f3_compare.py`);
  - `audit/gate/*.cert.json` and `audit/gate/GATE_TOOL.json`;
  - `prereg/F4_PREFREEZE.json` and `prereg/DRAW_STUDY.json`;
  - `pyproject.toml` and `tests/**`.
- **Outside the manifest:** `README.md`, `prereg/README.md`, `LICENSE`, `.gitattributes`, `.gitignore`, the freeze
  record, and `prereg/reviews/` (the instructions and reports of blind reviews 1–3, published with the freeze commit;
  their transcripts are kept by the designer).
- **Manifest:** `prereg/FREEZE_v0.2.json`, written by the freeze verifier in `audit/` (R1-22). It uses the same format
  and algorithm as Truth_Gate's `freeze.py`.
- **Freeze record:** `prereg/FREEZE_RECORD.md`, outside the manifest (date, core hash, freeze commit, platform string,
  sign-off; the salt is added in §8 step 8).

## 10. Changes in drafts 3, 4 and 5

These changes were made before any calibration or test world existed.

**Draft 3** (found while the audit layer was built):

| No. | Change | Why | By |
|---|---|---|---|
| P3-1 | G7: UNDEFINED only when no feasible grid point exists | Draft 2 wrote "no feasible point (hypervolume 0)" as if the two were the same | Claude (a drafting error) |
| P3-2 | Gate `plus` worlds for empirical claims are systems on which the claim holds by construction | With the system under test as `plus`, a certificate mixes "the criterion cannot fail" with "the system fails" | Claude (a design error) |
| P3-3 | N8 acts on every world | The draft-2 twin acted only on rare conflicts | Claude |
| P3-4 | N2 in the real run uses derived seeds | The detector diagnostic must be reproducible | Claude |
| P3-5 | The gate driver and its check against `v0.5.1` | The leak guard blocks repository imports in a plain run | Claude |
| P3-6 | D4 "covered" is yes/no | The first D4 run disclosed pilot counts (§2) | Claude |
| P3-7 | `encode_from_rows` split out (SPEC S-6) | G3 needs to re-encode a changed D_derive | Claude |
| Q-ε_d | ε_d stays 0.02 | The author chose option (a) | author |

**Draft 4** (blind review 1, `tesaron_v02_review1`: 2 blocking, 13 major and 7 minor findings; the review is published
with the frozen state):

| Finding | Change |
|---|---|
| R1-1 (blocking) | G7 becomes G7a, a deterministic property of the criterion, with the oracle as the anchor and the unconstrained criterion as its twin. G7b, the system's score, becomes descriptive (author, AQ2). |
| R1-2 (blocking) | T-1 keeps its design and is stated as what it tests: admitting the weakest source within the bounds. I-5 is added, with a structure arm and the verdict sentence; a graded test is left to v0.3 (author, AQ1). The tautology answer in §2 is corrected. |
| R1-3 | Seeds include a salt drawn after the freeze commit is public. The runner checks the commit order. |
| R1-4 | The runner recomputes τ and checks `CAL_WORLDS.json` before testing |
| R1-5 | The k-invariance of the wisdom quantities is stated (§3.1) |
| R1-6 | G1–G7a are labelled as checks decided by construction; G3's claim reads "necessity" |
| R1-7 | G8's zero-tolerance character, the FAILS sentence and the rule for an undefined fidelity are stated (I-6) |
| R1-8 | All comparisons are exact rationals |
| R1-9 | A power table for n = 16 to 30, and a corrected meaning of HOLDS (30 test worlds kept, AQ3) |
| R1-10 | The expected verdicts given the pilot (§2), printed next to the T-1 and G8 verdicts |
| R1-11 | F1 and G6 use the brute-force closure; F3 gets blind input and a wider scope, with a disagreement rule; F4 also checks μ⁺ |
| R1-12 | F controls on all test worlds before any check; stop, crash and rerun rules |
| R1-13 | Descriptive arms for UNDEFINED as FAILS, and for the default's feasibility per world |
| R1-14 | Versions pinned and recorded; determinism claims limited to one machine and NumPy build |
| R1-15 | `certify all --verify` and file hashes in GATE_TOOL.json just before the freeze; a T-1 study on real-shaped data; a G7a study |
| R1-16 | Version labels fixed; the freeze record moved outside the manifest |
| R1-17 | Role `n2` listed; "i is the draw index"; replacement reasons stated; a calibration world with an undefined metric is invalid |
| R1-18 | G1 (ii) checks all entities; G5 compares full unit maps; G2's subprocess seeds are explicit; the G5 and G6 wording is fixed |
| R1-19 | The quantitative wording includes counts and the Wilson bound |
| R1-20 | Primary tests named; multiplicity stated; the run labelled; checklist items that do not apply are written down (below) |
| R1-21 | A reading for the detector diagnostic |
| R1-22 | The freeze verifier is part of `audit/` and is frozen with it |

**Two deviations in review 1, recorded:**
- The unit-test suite started two read-only `git rev-parse` calls inside the reviewer's folder (both failed), against
  the no-git rule. The designer had not foreseen it.
- The instructions said the G7 and G8 certificates predated draft 3. They had already been regenerated.

**Draft 5** (blind review 2, `tesaron_v02_review2`: 1 blocking, 6 major and 6 minor findings; of the 22 repairs of
review 1, 18 were judged fixed and 4 partly fixed, R1-1, R1-3, R1-9 and R1-14, whose residues are R2-1, R2-2, R2-4
and R2-9; the review is published with the frozen state):

| Finding | Change |
|---|---|
| R2-1 (blocking) | G7a's claim is narrowed to the five baselines of SPEC §10, and §2 records that echo+F and echo+T score; the test is unchanged. The tautology answer says how each baseline fails (author, AQ4). |
| R2-2 | The runner binds the run to the freeze: exactly one commit for each of the manifest, SALT, CAL_WORLDS and TAU; the frozen files identical to the freeze commit; the core hash in SALT.json; every commit on `origin/main`. The post-run audit checks the salt's provenance and the public remote (§8). |
| R2-3 | The T-1 sentence is computed from the structure arm, which gains an α ≥ 0.85 field and a 0.80/0.85 crossing arm; the counts are printed next to the verdict, with a HOLDS caveat; the directional-hypothesis item is written (below). The design is unchanged (author, AQ5). |
| R2-4 | §7's power statement uses a calibration-draw study (`prereg/DRAW_STUDY.json`, a replication of the reviewer's); "insufficient worlds" is in the expected-verdict paragraph; the 16–19 row and the G7a feasibility sentence of §2 are corrected. |
| R2-5 | The I-6 arm counts atoms from raw integer denominators |
| R2-6 | F1 covers abduction with a brute-force enumerator and recomputes pass 2 from it; F4 covers the relation units and the interface facts; §6.1 states what is not covered. SPEC S-9 writes down the channel order of the ranking. |
| R2-7 | F3's instructions, output schema and comparison script are written and frozen; a mechanical resolution rule; the G1–G6 outcomes are given for the verdict table |
| R2-8 | SPEC revision S-8 (§1 and §11); `prereg/README.md`; "S-1–S-9"; the docstring in `audit/system.py` |
| R2-9 | The printed claims and the gate study names equal §3.2 |
| R2-10 | The salt enters the freeze record in step 8; the `perm` and `n2` indices are stated in §7 |
| R2-11 | Per-world outputs are written after the last world; the rerun procedure is stated |
| R2-12 | A pre-freeze check; untracked files are refused in the gate driver's tag check |
| R2-13 | G1 (ii) checks μ⁻ = 0 on every class unit; the failed parts are recorded and printed |

**Notes on review 2.**
- The reviewer's agent stopped once on a usage limit and was resumed. The transcript checks found no forbidden call, no
  git call, and no change to the inputs.
- The reviewer left out one count from the T-1 gate certificate (a design quantity of the gate study, not an outcome
  of the system).

**Draft 5, continued** (targeted blind review 3, `tesaron_v02_review3`: 0 blocking, 1 major and 9 minor findings; of
the 13 repairs of review 2, 11 were judged fixed and 2 partly fixed, R2-11 and R2-12, whose residues are R3-6 and
R3-1; AQ4 and AQ5 were judged carried out correctly; the review is published with the frozen state):

| Finding | Change |
|---|---|
| R3-1 (major) | `.gitattributes` with `eol=lf` and every text file stored with LF; the pre-freeze check compares each file with its staged blob; `audit/clone_verify.py` verifies the freeze in a fresh clone before the push (§6.3, §8 step 7) |
| R3-2 | A fixed field-to-test map in `f3_compare.py` defines the affected tests; the whole table is recomputed for a table-only disagreement; NOTES.md changes nothing (§6.1) |
| R3-3 | F3 also covers T-1's structure fields and each test's first failing world (the draw index is in the blind input); §6.1 says that the G8 hypothesis summary is checked by F1, not F3 |
| R3-4 | The F3 instructions add SPEC §7.1–§7.2 to the reading list and state the oracle's verdict view |
| R3-5 | The expected-verdict paragraph names the calibrated bounds as a source of a different T-1 outcome |
| R3-6 | The verdict table and summary are built before any output is written; the rerun is the `reproduce` subcommand |
| R3-7 | Full history in the unique-commit check; the manifest must list exactly the tracked files under the §9 paths; the regenerated calibration world records are compared with CAL_WORLDS.json |
| R3-8 | F4 adds PCM's flags and iteration count, the class units' provenance and status, and support degrees from the world; §6.1 lists what remains uncovered |
| R3-9 | The T-1 sentences are printed in the §4 order with every T-1 verdict; §4 states the G1 and G8 details as printed |
| R3-10 | `audit/README.md` describes the new modules |

**Notes on review 3.**
- The reviewer's agent stopped once on a usage limit, right after it began reading the instructions, and was
  resumed. The transcript checks found no forbidden call, no git call, and no change to the inputs.
- In its own scratch copy the reviewer regenerated `F4_PREFREEZE.json` and `DRAW_STUDY.json` and found both
  byte-identical to the given files.

**Directional hypotheses** (checklist; R2-3):
- **T-1** predicts a direction: new_false does not rise by more than δ as uncertainty falls. Generic factors that can
  produce it:
  - calibrated bounds that exclude α ≤ 0.60 on most worlds, so that only the class-only window is compared, where
    new_false did not rise on development worlds; the structure counts next to the verdict report this;
  - few feasible points per world (two feasible points give one pair); the feasible α set of each world is in the
    structure arm.
- **G8** predicts that abduction does not lower fidelity or raise deviation. A generic factor: few hypotheses, which
  change little. The number of hypotheses at (α₀, k = 10) is recorded per world, and its minimum, median and maximum
  are reported next to the G8 verdict.
- **G1–G7a** are decided by construction and have no directional reading.

**Checklist items that do not apply:**
- "Input dates" and the "new inputs" condition: not applicable; the worlds are synthetic and generated from seeds.
- "Model predicts each estimated component": not applicable; there is no physical model with estimated components.
