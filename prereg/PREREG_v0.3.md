# Pre-registration: Tesaron v0.3

**Status: FROZEN.** The manifest is `prereg/v03/FREEZE_v0.3.json`; the freeze commit, its date and the core hash are in `prereg/v03/FREEZE_RECORD.md`. The drafts and their changes are listed in §10.

- **Author:** Hazar Şimşek (theory and decisions). Design and draft: Claude (main session). Code: `kodlayici`
  (Sonnet 5.5). Blind review: a fresh agent in a separate session ("Independent").
- **Date written:** 2026-11-23 (drafts 1–3).
- **Structure:** follows the Truth_Gate `PREREG_TEMPLATE.md` (protocol v0.5.1).
- **Relation to v0.2:** v0.2 (`prereg/PREREG_v0.2.md`, `REPORT_v0.2.md`) is closed, and its verdicts stand. v0.3 is a new
  pre-registration with new worlds, a new freeze and a new salt. No v0.2 file is changed.
- **System and worlds:** `SPEC.md` (unchanged) and `SPEC_v0.3.md` (S-10: the v0.3 worlds; S-11: no other change).

## 1. Question

Does the Tesaron v0.1 pipeline, run on the v0.3 reference worlds, have the following properties?

**Primary test.** This is an empirical claim about the system, and the only test of v0.3 with a quantitative verdict:
- **T-1:** within the reasonable bounds, admitting weaker evidence (lowering α) does not increase the share of new
  false conclusions by more than δ or by one wrong conclusion, whichever is larger (R1-1).
  - **What is new in v0.3.**
    - Relation evidence comes from 8 sources whose reliabilities are drawn per world from U(0.55, 0.97).
    - Weak class evidence can be wrong: the two overlap entities of each world lie 80% of the way to another class
      (S-10).
    - Lowering α therefore admits sources one at a time, together with weak class evidence, some of it wrong. Inside
      each world's feasible α range, T-1 compares these graded steps of evidence admission. This is the graded form that
      AQ1 left to v0.3; its resolution is the 0.05 step of the α grid.
  - **Bounds and points at k = 0 (A1).** τ is calibrated at (α₀, k = 0), and T-1's points are the feasible
    configurations at k = 0. T-1 is about evidence admission only. Abduction is not part of it.

**Implementation and criterion checks.** As in v0.2, they are decided by construction and test that the code does what
the design says. They are regression checks, not discoveries:
- G1: membership is not probability;
- G2: encoding is reproducible;
- G3: meaning units need their data;
- G4: the decoder is deterministic;
- G5: validation data do not leak into pattern computation;
- G6: expansion makes no unevidenced claims;
- G7a: none of four degenerate baselines of SPEC §10 (echo, all_false, all_unknown, all_both) gets a positive score
  under the wisdom criterion (author decision, 2026-11-23). The fifth, all_true, is not excluded in v0.3 worlds (§2) and
  is reported as a descriptive arm. The criterion does not exclude degenerate strategies in general (v0.2 §2, AQ4).

**G8, creativity (abduction) preserves meaning,** is computed and reported in v0.3 with its v0.2 definition, but it gets
no verdict (author decision, 2026-11-23). v0.2's G8 verdict (FAILS, 15 of 30) stands.

The run is labelled a **model test on new worlds**.

## 2. Known and prospective

| Part | Known or prospective | Why |
|---|---|---|
| The code of v0.1 and its revisions S-1–S-9 (SPEC §15), and S-10–S-11 (`SPEC_v0.3.md`) | known | written and tested on development seeds below 1 000 000: 900000–900999 (v0.2), and from 930000 upward for v0.3 (the ranges and offsets of `audit/v03/seeds.py`) |
| v0.2's results on v0.2 worlds (`REPORT_v0.2.md`) | known to the designer and the author; public | T-1 FAILS (16 of 21 defined); it failed where the weakest of three discrete sources (0.60) was admitted, and on two worlds inside the window where only class atoms change. G8 FAILS (15 of 30). v0.2 worlds differ from v0.3 worlds: three fixed reliabilities, and class evidence that is never wrong. |
| Design study S1 (`prereg/v03/WORLD_STUDY.json`) | known to the designer and the author | a smaller prototype radius: no radius met the criteria. PCM fits become degenerate before world-false class atoms become common (S-10). No decoder run. |
| Design study S1b (`prereg/v03/OVERLAP_STUDY.json`) | known to the designer and the author | overlap fraction 0.8: validity 0.99; worlds with a world-false T class atom 0.18 / 0.31 / 0.40 / 0.54 at α 0.80 / 0.70 / 0.60 / 0.50; 2.2–4.0% of T class atoms world-false. No decoder run. |
| Design study S2 (`prereg/v03/TAU_RULE_STUDY.json`) | known to the designer and the author | four τ rules over 40 paired calibration draws on 30 development test worlds, at k = 0: τ ranges, T-1 definedness, default feasibility, G7a definedness, feasible-set stability (§7). It kept fidelity, deviation, consistency and uncertainty at k = 0 because feasibility needs them. The metric code computes new_true and new_false in memory with the others; the study drops them at once, and no new_true, new_false, T-1 or G8 quantity was read, printed or stored. |
| **No pilot** | a design decision | Before the freeze, nobody reads, prints, stores or reports new_false, a T-1 outcome or a G8 outcome on any v0.3 world, development worlds included: not the designer, the coder, the reviewers, the gate (whose T-1 `plus` world replaces new_false by a constant, §6.3), the development runner (whose outputs pass a redaction boundary) or the D4 smoke test (which prints definedness only). The metric code computes new_false in memory wherever it computes the other metrics; it is dropped or redacted at once. T-1's outcome on v0.3 worlds is therefore prospective for everyone. The denominators of new_false are design quantities (§2, "Resolution"). |
| The power study (`prereg/v03/POWER_STUDY.json`) | known to the designer and the author | Q-40 over 40 calibration draws (PCG64(3141)) on 50 development test worlds: T-1 definedness and P(HOLDS \| r) (§7). Design quantities only. |
| **The baseline all_true scores in v0.3 worlds** (G7a data from the code step, checked by the designer and by blind review 1; reproduced by the all_true study, `prereg/v03/ALL_TRUE_STUDY.json`) | known to the designer and the author | Under each of S2's 40 Q-40 draws, all_true was feasible and scored > 0 on 22 of the 30 development test worlds, at α 0.95, 0.90 or 0.85; echo, all_false, all_unknown and all_both never scored. The cause: with reliabilities from U(0.55, 0.97), only 6 of the 30 worlds have a source at or above 0.95, and 20 at or above 0.90. In 22 of the other 24 worlds, I at those α holds only T class atoms, so all_true contradicts no encoded atom and passes every constraint. In the remaining two, I is empty at 0.95, so the point is infeasible, and at 0.90 their I holds non-T atoms. In v0.2 the 0.95 source of every world put F atoms into I. This is a property of the criterion that the v0.3 worlds expose: the constraints cannot exclude "everything T" when the encoded evidence holds no F or B atom. G7a's claim was narrowed to the other four baselines (author, 2026-11-23). |
| Everything on calibration and test worlds | prospective | their seeds need a salt that is drawn only after the freeze commit is public (§7) |

**Factors that bear on T-1, known before the run.** They are listed in both directions; the designer has no pilot rate.
- **Toward FAILS:**
  - At low α, the feasible range can admit weak class evidence that is wrong (S1b). Through R6 (`¬c_j(X) ← c_i(X)`), a
    wrong class atom can make the entity's true class F, when R6's pair (i, j) is (partner class, base class). Through
    R1, it can derive further wrong class atoms. All of these count in new_false.
  - The weakest sources (reliability near 0.55) report the wrong polarity almost half the time.
  - In v0.2, T-1 failed where the weakest source was admitted.
- **Toward HOLDS:**
  - Bounds calibrated at k = 0 can exclude the lowest α levels, where fidelity falls.
  - The consistency and deviation bounds remove points where wrong conclusions clash with evidence. τ_d is exactly 0
    in 16 of the power study's 40 draws (§7).
  - Wrong evidence that enters I does not count in new_false, which is computed outside I. Only its derived
    consequences outside I count.
  - A wrong derived conclusion that collides with another derivation becomes B, which is in neither the numerator nor
    the denominator of new_false.
  - T-1 tolerates an increase of one wrong atom where δ is below one atom (R1-1, §3.2).
  - A step of 0.05 in α admits on average about one of the 8 sources, so adjacent α levels differ less than v0.2's
    levels around 0.60.
- **Resolution (R1-1).** The denominator of new_false, the number of decided atoms outside I, is small on development
  worlds at k = 0. On the power study's 50 development test worlds its median is 12 at α 0.80, 19 at 0.70 and 28 at
  0.60 (`prereg/v03/NQ_STUDY.json`). Below 20 decided atoms, one wrong atom is more than δ = 0.05. T-1's tolerance is
  therefore at least one atom (§3.2).

**Expected verdict.** The report prints the following text next to the T-1 verdict:

> Expected verdict: none. No pilot was run on v0.3 worlds before the freeze (PREREG v0.3 §2). Known factors point both
> ways (PREREG v0.3 §2). v0.2's T-1, on worlds with three discrete sources, failed. v0.3 changes the worlds, the τ rule,
> the configuration of calibration and feasibility, and T-1's tolerance together, so an outcome that differs from
> v0.2's cannot be attributed to the new worlds alone; the I-8 arm applies v0.2's full rule to the v0.3 worlds.

**The tautology question.**
- **G1–G7a are decided by construction,** as in v0.2:
  - μ⁻ of a class unit is hard-coded to 0;
  - a unit exists only with D_derive rows;
  - OBSERVED and DERIVED are exactly the pass-1 fixpoint;
  - G7a's four baselines: echo, all_unknown and all_both score 0 by the definition of new_true, because their verdict
    on every H atom is U or B. all_false contradicts every T-encoded atom, so the calibrated τ_d and τ_s excluded it on
    the development data; this exclusion depends on the data (a T-encoded atom in I, and τ_d below the share of T
    atoms), not on construction alone. In v0.3, G7a therefore tests in effect whether the constraints exclude
    all_false, plus the oracle anchor. all_true is not among the four (above).
- **T-1 is not decided by definition.**
  - Uncertainty is computed over K, and new_false over the decided atoms outside I. These sets partly overlap (E∖I and
    H belong to both).
  - Its dependence on the calibration draw is smaller than in v0.2 but not absent: under Q-40 the median stability of
    the feasible sets across draws is 0.79 (S2). The draw-sensitivity arm (§3.2) reports T-1's verdict under 20 further
    calibration draws.

## 3. Criteria

### 3.1 Shared definitions

- **Default configuration:** α₀ = 0.7, k₀ = 5, the Context defaults. G2–G5 use α₀; G4 uses (α₀, k₀); G6 uses
  (α₀, k = 10).
- **Calibration configuration (A1):** (α₀, k = 0).
- **Grid (D3):** α ∈ {0.95, 0.90, 0.85, 0.80, 0.75, 0.70, 0.65, 0.60, 0.55, 0.50} × k ∈ {0, 5, 10}; 30 configurations.
  T-1 uses the 10 configurations with k = 0 (A1).
- **What does not depend on k:** under A-6 the verdict view ignores hypotheses. So uncertainty, new_true and new_false
  at (α, k) equal their values at (α, 0). k changes fidelity, deviation and consistency.
- **τ (A3):** calibrated by the Q-40 rule of §7.
- **Feasible point:** a configuration whose fidelity ≥ τ_s, deviation ≤ τ_d, consistency ≥ τ_t and uncertainty ≤ τ_b.
  An undefined fidelity or new_true makes the point infeasible (`audit.exact.feasible`, unchanged from v0.2).
- **Exact comparisons:** every metric is a ratio of integer counts. All comparisons with τ, ε_f, ε_d and δ, all
  differences of metrics, and the order statistics of the τ rule are exact, as `fractions.Fraction` of the counts.
- **Per-world outcome:** every per-world check returns HOLDS, FAILS or UNDEFINED. UNDEFINED is returned only by the
  check's own stated definedness condition. A crash is not UNDEFINED; it ends the run (§8).
- **Anchor:** every check contains a part that zero or noise data cannot satisfy (K5).

### 3.2 Tests

| Id | Claim | Per-world HOLDS when | FAILS when | UNDEFINED when |
|---|---|---|---|---|
| G1 | Membership degrees are not turned into probabilities | (i) for every outlier entity with D_derive rows, Σ_k u_ek < 0.5; (ii) every class unit of every entity has μ⁻ = 0 exactly; (iii) anchor: the median own-class typicality of the normal entities is ≥ 0.5 | any of (i)–(iii) fails; the failed parts are recorded | never |
| G2 | Encoding is reproducible in the same context (same machine, same NumPy build) | the canonical hash of the encoding is identical in-process and in two subprocesses with `PYTHONHASHSEED` 0 and 1 (set explicitly); anchor: encoder seed + 1 gives a different hash | otherwise | never |
| G3 | A meaning unit needs its data (necessity) | at α₀, for every meaning unit, removing its provenance rows from D_derive and re-encoding makes the unit absent or U; anchor: at least one ablated unit was decided (T, F or B) before | some ablated unit stays decided | never |
| G4 | The decoder gives the same output for the same input (same machine, same NumPy build) | at (α₀, k₀), the canonical output hash is identical across the original order, 3 permutations of facts and rules, and 3 subprocesses with `PYTHONHASHSEED` 0, 1 and 4242; anchor: the output has at least one fact | otherwise | never |
| G5 | Validation data do not leak into pattern computation | after the D_validate feature values are replaced with garbage and its report polarities are flipped, the fitted centers are bit-identical, and the map atom → (μ⁺, μ⁻, status, provenance) of the D_derive units is identical; anchor: corrupting D_derive the same way changes the centers | otherwise | never |
| G6 | Expansion makes no unevidenced claims | at α₀ and k = 10, every fact with status OBSERVED or DERIVED is in the pass-1 fixpoint recomputed from the observed facts alone by the brute-force closure of `audit/indep`, and every fact outside that fixpoint has status HYPOTHESIS | otherwise | no abduction candidate at α₀, k = 10 |
| G7a | None of four degenerate baselines of SPEC §10 (echo, all_false, all_unknown, all_both) gets a positive score under the wisdom criterion | each of the four baselines at every α of the grid, scored as a single point under the τ of §7, is infeasible or scores 0; anchor: the oracle (§6.3) scores > 0 at some α | one of the four scores > 0 at some α | the oracle has no feasible point |
| T-1 | Within the reasonable bounds, admitting weaker evidence does not increase the share of new false conclusions by more than δ or by one wrong conclusion, whichever is larger (A1, R1-1) | for every pair of feasible points p, q at k = 0 with uncertainty(q) < uncertainty(p): new_false(q) − new_false(p) ≤ max(δ, 1/n_q), with δ = 0.05 and n_q the denominator of new_false at q (the number of decided atoms outside I); when n_q = 0 the tolerance is δ (author decision on R1-1, 2026-11-23) | some pair violates it | fewer than two feasible points at k = 0 with distinct uncertainty values |

**Descriptive arms.** They are reported and never part of a verdict:
- **G8 (author decision; v0.2 definition, D4b).** Per world:
  - HOLDS when, for every α of the grid and k ∈ {5, 10}, fidelity(α, 0) − fidelity(α, k) ≤ ε_f and
    deviation(α, k) − deviation(α, 0) ≤ ε_d, with ε_f = 0.05 and ε_d = 0.02. A comparison with an undefined fidelity is
    skipped.
  - UNDEFINED when there is no hypothesis at (α₀, k = 10), or when every comparison is skipped.
  - Reported: the HOLDS share among defined worlds with its Wilson lower bound; the number of worlds that fail only
    through single-atom changes (v0.2 I-6); and the minimum, median and maximum of SPEC §8's `hyp_count` at
    (α₀, k = 10) over the defined worlds (post-run audit A9).
- **G8 over the whole grid (I-4):** fidelity ≥ τ_s and deviation ≤ τ_d at every point.
- **all_true (§2):** per world, whether all_true is feasible and scores > 0 at some α under the τ of §7, and at which
  α levels; and the number of worlds where it does. It is scored exactly as G7a scores a baseline.
- **G7b, the system's own score:** per world, the system's hypervolume over the feasible grid points, and whether it is
  > 0.
- **Cross-seed stability (D4a):** the agreement of encoded values at α₀ under the world's encoder seed and a second seed
  (role `aux`), among atoms present in both encodings and outside the boundary band in both, for class atoms and for all
  atoms.
- **T-1 over all k = 0 points (I-2):** T-1 with every α level at k = 0 treated as feasible.
- **T-1's structure (I-5).** Per defined world:
  - the feasible α set at k = 0, its smallest level α_min and its largest level α_max;
  - **sources spanned:** the number of the world's 8 reliabilities ρ with α_min ≤ ρ < α_max. These sources are
    admitted at α_min but not at α_max, so they are the sources whose admission T-1 compares;
  - **wrong class atoms spanned:** the number of class atoms that are T-encoded at α_min, not T-encoded at α_max, and
    world-false;
  - the largest increase new_false(q) − new_false(p) over the pairs of the T-1 definition.

  On an undefined world only the feasible α set is recorded; the other fields are empty. The counts over the defined
  worlds are printed next to the T-1 verdict (§4).
- **Draw sensitivity (A3).** T-1's verdict under 20 further calibration draws.
  - Each draw b = 0, …, 19 has 40 valid calibration worlds with roles `world-calalt-<b>` and `enc-calalt-<b>` (§7),
    and its τ comes from the Q-40 rule.
  - Each draw's τ is applied to the same 50 test worlds.
  - Reported: how many draws give HOLDS, FAILS and "insufficient worlds", and the range of the number of defined worlds.
    A set without a τ (§7, Replacement) counts as "insufficient worlds" and is left out of that range.
  - The 20 τ values are computed and committed in the calibration step, before any test world exists (§8, step 9).
- **T-1 at k₀ (I-6):** τ calibrated at (α₀, k₀) on the same 40 calibration worlds by Q-40, with feasibility at
  (α, k₀). This is the opposite reading of A1. It changes one rule; it is not v0.2's rule.
- **T-1 under v0.2's τ rule (I-7):** τ by D1 (minimum and maximum) on the first 10 of the 40 calibration worlds (in draw
  order), at k = 0. It changes one rule.
- **T-1 under v0.2's full rule (I-8, R1-8):** τ by D1 on the first 10 calibration worlds at (α₀, k₀); a point α is
  feasible when (α, k) is feasible for some k ∈ {0, 5, 10}; tolerance δ only. This is v0.2's rule applied to the v0.3
  worlds, so it separates the change of worlds from the change of rules.
- **T-1 without the one-atom floor (I-9):** T-1 with tolerance δ only, at k = 0 under the τ of §7. It shows whether the
  floor (R1-1) decided the verdict.
- **Default feasibility:** for each test world, whether (α₀, 0) is feasible.
- **UNDEFINED as FAILS:** for T-1, the Wilson share with UNDEFINED worlds counted as FAILS.
- **The detector diagnostic** (§6.2).

### 3.3 From worlds to a test verdict

- **Deterministic tests (G1–G7a):** a test HOLDS if no defined test world FAILS and at least 16 test worlds are defined.
  - One FAILS world makes the test FAIL (A-8), even if fewer than 16 worlds are defined.
  - Otherwise, with fewer than 16 defined worlds, the verdict is "insufficient worlds".
- **The quantitative test (T-1):** it HOLDS if the one-sided 95% Wilson lower bound of the HOLDS share among defined
  worlds is ≥ 0.80 (z = 1.6448536269514722) and at least 16 worlds are defined.
  - Otherwise it FAILS; with fewer than 16 defined worlds the verdict is "insufficient worlds".
  - What a HOLDS means: the per-world rate is at least 0.80, at approximately one-sided 95% confidence. The Wilson
    score bound is not an exact test: the chance of a HOLDS at r = 0.80 is 0.02–0.06 for n = 34–50 (0.058 at n = 42).
  - What a FAILS means: the rate was not shown to be at least 0.80. It does not show that the rate is below 0.80.
  - With 50 defined worlds, the rule needs 45 HOLDS.
- **UNDEFINED worlds:** UNDEFINED never counts as HOLDS. UNDEFINED worlds are excluded from the share, and their number
  is reported for every test.
- **Multiplicity:** T-1 is the only quantitative test, at one-sided 5%. There is no combined verdict.

## 4. Verdict mapping

- Each test has its own verdict: HOLDS, FAILS or "insufficient worlds". There is no combined verdict for the
  architecture.
- The report gives a table with one row per test and the per-world counts (HOLDS / FAILS / UNDEFINED).

Fixed wording:
- **Deterministic test, HOLDS:** "<Id> holds: <claim>, in all <n_defined> defined test worlds (<n_undefined>
  undefined). (A check of the implementation or of the criterion, not a discovery.)"
- **Deterministic test, FAILS:** "<Id> does not hold: <n_fails> of <n_defined> defined test worlds fail; the first
  failing world is <seed>."
  - For G1 it adds: "Failed parts in the first failing world: <parts>."
  - The first failing world is the FAILS world with the smallest draw index.
- **G7a, with every verdict (R1-3):** "all_true, not judged, was feasible and scored > 0 on <n> of <N> test worlds
  (at α <levels>); echo, all_unknown and all_both score 0 by the definition of new_true, so among the four judged
  baselines only all_false can be excluded by the constraints." With n = 0 the parenthesis is omitted. <levels> lists the
  α levels at which all_true scored on some world, with two decimals, in decreasing order, separated by ", ".
- **T-1, HOLDS:** "T-1 holds on at least 80% of worlds (one-sided Wilson bound, approximately 95%): <claim>. <n_holds>
  of <n_defined> defined worlds hold (Wilson lower bound <b>, threshold 0.80); <n_undefined> undefined."
- **T-1, FAILS:** "T-1 is not demonstrated: <n_holds> of <n_defined> defined worlds hold (Wilson lower bound <b>,
  threshold 0.80); this does not show that the per-world rate is below 0.80; <n_undefined> undefined; the first failing
  world is <seed>."
- **T-1, additional sentences.** They are computed from the structure arm and the draw-sensitivity arm, and printed in
  this order with every T-1 verdict, "insufficient worlds" included:
  - "In these worlds T-1 compares graded steps of evidence admission at k = 0: over the <n> defined worlds, the
    feasible α range spanned a median of <m> of the 8 source reliabilities (minimum <a>, maximum <b>), and on <c> of
    them it admitted at least one world-false class atom." With an even number of worlds the median is the mean of the
    two middle values, and "a median of <m>" is then printed as "a median of <m> (the mean of the two middle values)".
    With no defined world the sentence is: "In these worlds T-1 compares graded steps of evidence admission at k = 0:
    there is no defined world, so no feasible α range was spanned."
  - "Under 20 further calibration draws, T-1's verdict was HOLDS <h> times, FAILS <f> times and 'insufficient worlds'
    <i> times (descriptive)."
  - Only with a HOLDS: "A HOLDS on worlds whose feasible range spans few sources compares few steps; see the structure
    counts."
- **Insufficient worlds:** "<Id>: insufficient worlds (<n_defined> defined, 16 required); no verdict."
- **G8, in the descriptive section only:** "G8 (descriptive, no verdict): <n_holds> of <n_defined> defined worlds hold
  (Wilson lower bound <b>); <n_undefined> undefined."

The expected-verdict paragraph of §2 is printed next to the T-1 verdict.

The following limitation sentence is printed next to every verdict and in the limitations section:

> These results come from synthetic worlds generated by code written by the same model family that designed and coded
> the system. The decoder was given the true rules. They say nothing about natural-language input.

## 5. Interpretations

| No. | Interpretation | Opposite reading | Can it change the verdict? | Sensitivity arm | Verdict under the opposite reading |
|---|---|---|---|---|---|
| I-1 | One shared set of 40 calibration and 50 test worlds, used by every test | a separate set for each test | no: the sets are exchangeable random draws from the same generator | none | same distribution |
| I-2 | "Points that satisfy the constraints" (A-7) means feasible points under the calibrated τ | all k = 0 points | yes | T-1 over all k = 0 points | descriptive only |
| I-3 | "One violation fails" (A-8) counts only FAILS worlds; UNDEFINED is not a violation | UNDEFINED counts as a violation | for G6 and G7a | the number of UNDEFINED worlds is reported for every test | reported |
| I-4 | G8 is read on the abduction axis (D4b) | the whole grid | G8 has no verdict in v0.3 | G8 over the whole grid | descriptive only |
| I-5 | T-1 tests the thesis in graded form inside each world's feasible α range | a test of the thesis at every α | it changes what a verdict means, not the verdict | T-1's structure arm, with counts printed next to the verdict; I-2 | the computed sentences say how many sources the ranges spanned |
| I-6 | Bounds and feasibility at k = 0 (A1) | bounds and feasibility at k₀ = 5 | yes | T-1 at k₀ | descriptive only |
| I-7 | τ by Q-40 (A3) | τ by v0.2's D1 on 10 worlds | yes | T-1 under D1 on the first 10 calibration worlds; the draw-sensitivity arm | descriptive only |
| I-8 | The v0.3 rules (k = 0, Q-40, one-atom floor) | v0.2's full rule on the v0.3 worlds | yes | T-1 under v0.2's full rule | descriptive only |
| I-9 | T-1's tolerance is at least one atom (R1-1) | tolerance δ only | yes | T-1 without the floor | descriptive only |

## 6. Controls

### 6.1 Fidelity controls

These are independent implementations of the code paths that decide verdicts, from the selected rows onward. The code
in `audit/indep` does not import `tesaron.decoder`, `tesaron.encoder` or `tesaron.belnap`.

**Not covered by an independent implementation** (post-run audit A6):
- the row selection and the derive/validate split (SPEC §5, steps 1–2), which are taken from the system. G2 tests only
  that they are reproducible, and G5 only that D_validate does not leak;
- the check code of G1–G6. F4 recomputes the encoder, and F1 the closure that G6 uses, but the G1–G6 judgments, and
  G1's failed-parts text, are given to F3 as inputs;
- the detector diagnostic and its "both hold" count;
- the descriptive arms other than T-1's structure: G8 and its summaries, all_true, G7b, D4a, default feasibility,
  "UNDEFINED as FAILS", I-2, I-6, I-7, I-8, I-9 and the draw-sensitivity arm. F3 has no input for the I-6, I-7, I-8 and
  draw-sensitivity τ;
- the wording of the fixed sentences, the detector qualifier included. The post-run audit reads them against §4;
- seed derivation, world validity and replacement. The post-run audit recomputes the seeds and checks validity.

| Id | What is compared | Independent implementation | Pass rule |
|---|---|---|---|
| F1 | the decoder's pass-1 fact set; its abduction candidates (the full ranked list with scores) and the kept top-k; and its pass-2 fact set; at every grid configuration | the brute-force closure and a brute-force candidate enumerator that follows SPEC §7.3. Pass 2 is recomputed from the independently enumerated hypotheses. Naive against semi-naive is also compared, for the derivation records. | equal sets, lists and records, on every test world and on the 40 main calibration worlds (at (α₀, 0) and (α₀, k₀)) |
| F2 | H | the same brute-force closure | equal sets on every test world and on the 40 main calibration worlds |
| F3 | τ (A5); every metric and n_q; the feasible set; the front; the hypervolume; every G7a and T-1 outcome; T-1's structure fields and their aggregated counts (A6); and the verdict table with each test's first failing world | after the run, a recomputation by a fresh agent in the Independent session. It uses the frozen instructions `audit/v03/f3/INSTRUCTIONS_F3.md` and output schema `audit/v03/f3/OUTPUT_SCHEMA.json`. It receives only inputs: world truth, rules, units, the full and verdict value lists, the source reliabilities, the grid, the draw indices, this file, the run's G1–G6 per-world outcomes labelled as given, and, for the 40 calibration worlds, the same inputs at (α₀, 0), from which it recomputes τ by Q-40. The instructions fix IEEE-double comparison both for the encoded values and for the boundary band (A8). After the agent has written its results, the frozen script `audit/v03/f3_compare.py` compares every field: exact string equality for the p/q fractions, exact equality otherwise. Its summary counts every row, G1–G6 included (A7). | 0 disagreements. Resolution of a disagreement, below. |
| F4 | the encoder: PCM's fitted centers, converged flag, iteration count and degeneracy flag; the class units' μ⁺, provenance and status; the relation units (μ⁺, μ⁻, provenance), with support degrees taken from the world's source reliabilities; and the interface facts of all units at every α | a direct numpy loop for PCM with its own degeneracy check, and direct recomputations from the D_derive rows and the Belnap table | centers and class μ⁺ equal to 1e-12; flags, iteration counts, provenance, statuses, relation units and fact sets exactly equal; on 20 development worlds before the freeze (`prereg/v03/F4_PREFREEZE.json`, with F1) and on every test world and the 40 main calibration worlds. The 800 worlds of the draw-sensitivity sets are not controlled; that arm is descriptive. |

**Resolution of an F3 disagreement.** It is mechanical:
- **The affected tests** of a disagreement are fixed in advance by the field-to-test map in `audit/v03/f3_compare.py`,
  which writes them on every disagreement:
  - τ, fidelity, deviation, consistency, uncertainty, new_true, new_false and the feasible set → T-1 and G7a;
  - n_q of a test world → T-1; n_q of a calibration world → none (it enters no τ and no test);
  - T-1's structure fields and their aggregated counts → T-1;
  - a per-world outcome or a verdict-table row of test X → X;
  - a missing verdict table → every test;
  - any other missing or extra world or file → G7a and T-1;
  - the front, the hypervolume, validation_agreement and boundary_share → none.
- A second fresh agent recomputes the disagreeing worlds from the same input and instructions. For a disagreement in τ
  or in the verdict table, it recomputes τ or the whole table.
- If its values equal the run's, the first agent erred. The verdicts stand, and both recomputations are reported.
- If its values equal the first agent's, the run's code is taken to be wrong. The affected tests get no verdict in this
  version; a new version needs a new freeze and a new salt (§8, step 11).
- Any other outcome also means no verdict for the affected tests.
- A disagreement with no affected test is reported and changes nothing.
- The agents' `NOTES.md` files are reported with `F3_COMPARE.json` and change nothing.

### 6.2 Detector controls: one faulty twin per test

The faulty twins are those of v0.2 (`audit/twins/`, unchanged), except as noted. Twins never change `tesaron/`; they wrap
or replace one function.

| Id | Test | How it violates the claim | Expected per-world outcome |
|---|---|---|---|
| N1a | G1 | normalize typicalities to sum 1 per entity (FCM-like) | FAILS (i) |
| N1b | G1 | μ⁻ = 1 − μ⁺ for class atoms | FAILS (ii) |
| N2 | G2 | the encoder's permutation does not come from the context seed: seed("n2", 2i) and seed("n2", 2i+1) in the real run | FAILS |
| N3 | G3 | every relation atom with no report gets a default μ⁺ = 0.8 (prior) | FAILS |
| N4 | G4 | abduction breaks ties by the iteration order of a Python `set` of strings. In v0.2 the twin's in-process hash depended on the parent's `PYTHONHASHSEED` (A11). In v0.3 every hash of the twin comes from three subprocesses with `PYTHONHASHSEED` 0, 1 and 4242, set explicitly; the first stands for the original order, and there are no in-process permutations. The twin is therefore reproducible. | FAILS |
| N5 | G5 | PCM is fitted on D_derive ∪ D_validate | FAILS |
| N6 | G6 | hypotheses are inserted with status OBSERVED | FAILS |
| N7 | G7a | the unconstrained criterion: feasibility is ignored, so every baseline point is scored. In v0.3 it fails through all_false, which then scores > 0 wherever some H atom is world-false (the comment in v0.2's `audit/twins/n7.py` names all_true, the v0.2 case). In the gate the minus world held on 7 of 100 development worlds, so the detector qualifier of a G7a HOLDS may appear on a few test worlds. | FAILS on most worlds |
| NT | T-1 | metric points with a built-in trade-off: new_false rises by 0.5 across the uncertainty span of the feasible points (0.2 in v0.2; raised so that, in the gate, where new_false is a constant, it exceeds the one-atom floor whenever the lowest-uncertainty feasible point has at least 3 decided atoms outside I). In a real run the trade-off is added to the real new_false, so NT can hold on a world where the real new_false falls by at least 1/2 − max(δ, 1/n_q), with n_q at the lowest-uncertainty feasible point; the diagnostic reports it. | FAILS on most worlds |

G8 has no twin in v0.3, because it has no verdict.

**Detector diagnostic in the real run:**
- On every test world, each twin is run, and its outcome is reported next to the fixed system's.
- It is a diagnostic, not a world filter.
- For each test, the report gives the number of worlds where both the fixed system and its twin HOLD. If that number is
  above 0, a HOLDS verdict is qualified: "the detector did not separate on <n> worlds".

### 6.3 Layer 1: the gate (Truth_Gate v0.5.1)

- **One study file per test with a verdict** (G1–G7a and T-1), in `audit/v03/gate/`. They run on v0.3 development worlds
  (seeds drawn from 930000–930999 by the study's rng). The criterion is the same judge function used in Layer 2; each
  check is split into collecting arrays and judging them.
- **The `plus` world** is a system on which the claim holds by construction:
  - **G1–G6:** the fixed system.
  - **G7a:** the actual criterion, applied to the baselines and to the oracle. The **oracle** keeps every atom of I at
    its encoded value, gives every other atom of K its world value, and leaves all other atoms U.
  - **T-1:** metric arrays shaped like the real data: the k = 0 grid metrics of a development world on which T-1 is
    defined at the study's τ, with new_false replaced by a constant (and new_true by 1/2; only its definedness counts).
    The study draws development worlds until it finds such a world. Undefined worlds would make the gate abstain, and
    definedness is not what the gate tests; the run reports it. The real new_false values are discarded before judging.
    They are never stored, printed or used ("no pilot", §2). The real denominators n_q of new_false are kept, because
    the one-atom floor needs them; they are design quantities.
- **The `minus` world** is `plus` with one declared change, the faulty twin: N7 for G7a, NT for T-1.
- **What the gate does not exercise:**
  - the subprocess parts of G2 and G4, which run only in Layer 2 and in the unit tests;
  - N4's real-run mechanism;
  - τ calibration, aggregation, seed derivation, world validity, the descriptive arms and the F controls. These are
    covered by the unit tests and by F3.
- **The driver:** `py -m audit.v03.gate.certify <id>` (and `--verify`), as in v0.2. It loads `truth_gate` from the local
  `kapi-oss` checkout at tag `v0.5.1`, and refuses to run on a modified or untracked checkout.
- **Required certificates:** every certificate must be FALSIFIABLE. A WEAK certificate is accepted only with a written
  reason and the author's approval.
- **Budget:** 100 samples per study.
- **Just before the freeze:** `certify all --verify` is run on the tree to be frozen. Its output, the kapi-oss commit and
  the SHA-256 of every file in `audit/` and `tesaron/` are written to `audit/v03/gate/GATE_TOOL.json`.
- **Pre-freeze check:** `audit/v03/prefreeze_check.py` refuses the freeze unless:
  - the file hashes in GATE_TOOL.json equal the current files;
  - GATE_TOOL.json lists all eight study ids, each with `verify_exit` 0, verdict FALSIFIABLE, tag `v0.5.1`, and a
    certificate body hash equal to the committed `.cert.json` (R1-5). The only exception is a verdict waived by the
    author's waiver file `audit/v03/gate/WAIVERS.json`: a JSON object from study id to a non-empty written reason, with
    the driver's ids (`g1`–`g7`, `t1`). It can waive only a WEAK verdict. A waiver file with any other key (for
    instance `G7a` or `T-1`), or with a value that is not a non-empty string, is refused whole. That file must exist
    when GATE_TOOL.json is written, because it lies in the hashed `audit/` tree. No waiver exists in this draft;
  - the files the freeze verifier would hash are exactly the git-tracked files under the manifest paths;
  - every such file's bytes equal its staged git blob;
  - the third line of this file and of `SPEC_v0.3.md` is the frozen status line of §8, step 6, and neither "not frozen"
    (in any case) nor "DRAFT" (in capitals) occurs in the first 12 lines of either file (post-run audit A10, R1-6);
  - every design study whose numbers this file prints (S1, S1b, S2, the power study, the all_true study and the n_q
    study) reproduces
    with the tree to be frozen: its JSON is equal to the committed one, apart from the `runtime_seconds` field
    (post-run audit A2, R1-7);
  - v0.2's manifest `prereg/FREEZE_v0.2.json` still verifies.
- **Line endings:** `.gitattributes` sets `* text=auto eol=lf`; every text file is stored with LF; code that writes into
  the repository writes LF. Before the push, the freeze is verified in a fresh clone with `py -m audit.v03.clone_verify`,
  which verifies both v0.3's and v0.2's manifests (R1-4).

## 7. Grid, N and tolerances

| Item | Value | Why |
|---|---|---|
| Grid (D3) | α ∈ {0.95, …, 0.50} in steps of 0.05 × k ∈ {0, 5, 10}; 30 configurations | as in v0.2. T-1 uses k = 0 (A1). |
| τ calibration rule (A3, Q-40) | Run the fixed system at (α₀, 0) on the 40 calibration worlds. Sort each metric's 40 values, duplicates included. τ_s is the 4th smallest fidelity, τ_t the 4th smallest consistency, τ_d the 4th largest deviation and τ_b the 4th largest uncertainty; all exact fractions. | A configuration is out of bounds when it is worse than the default is on all but about 10% of the calibration worlds. S2: Q-40 has about the expected leniency of v0.2's D1 on 10 worlds (order statistic at m/(n+1) = 0.098 against 0.091), but τ varies far less between calibration draws. By construction, each metric puts at most 3 calibration worlds out of bounds, so the default is feasible on at least 28 of the 40. On development data τ_d is often exactly 0 (16 of the power study's 40 draws, 11 of S2's), and feasibility then tolerates no deviation at all (R1-11). |
| T-1's tolerance (D2, R1-1) | max(δ, 1/n_q), δ = 0.05 | δ is one new false conclusion in 20 decided ones. The denominator n_q is often below 20 (§2), so the tolerance has a floor of one atom: a single additional wrong conclusion does not decide a pair when the denominator does not fall from p to q. It fell on none of the 18 796 T-1 pairs of the power study's development worlds (`prereg/v03/NQ_STUDY.json`; first found by blind review 2), but that is an empirical fact, not a property of the rule (protocol: tolerances above the numerical resolution). Author decision, 2026-11-23. |
| UNDEFINED worlds (D2) | excluded from the share; at least 16 defined worlds required | does not conflate "could not be tested" with "false" |
| G8 tolerances (descriptive) | ε_f = 0.05, ε_d = 0.02, compared exactly | unchanged from v0.2 |
| World validity (D5) | PCM usable (converged and not degenerate), and \|H\| ≥ 10. A calibration world is invalid if one of its four τ metrics at (α₀, 0) is undefined. A world whose generator fails after max_attempts (`WorldGenerationError`) is invalid. | as in v0.2, with the calibration configuration of A1 |
| Replacement | an invalid world is replaced by the next draw index; at most 200 draws per set, otherwise the run stops with no verdict. A draw-sensitivity set that does not reach 40 valid worlds within 200 draws does not stop the run: it has no τ and counts as "insufficient worlds" in that arm (R1-14). | S1b: 99 of 100 development worlds are valid |
| Calibration worlds | 40 valid worlds (A3) | Q-40 |
| Draw-sensitivity calibration sets | 20 further sets of 40 valid worlds | descriptive (§3.2) |
| Test worlds | 50 valid worlds (author, 2026-11-23) | power, below |
| Encoder seed | one per world, plus one `aux` seed per test world | |
| Seeds | seed(role, i) = 1 000 000 + (first 8 bytes of SHA-256("<core_sha256>\|<salt>\|<role>\|<i>") as a big-endian integer) mod 10⁹. The roles are `world-cal`, `world-test`, `enc-cal`, `enc-test`, `aux`, `perm`, `n2`, and `world-calalt-<b>` and `enc-calalt-<b>` for b = 0, …, 19. i is the draw index d, except for `perm` (i = 3d + p, p = 0, 1, 2) and `n2` (i = 2d and 2d + 1). | The salt is 32 random bytes drawn by the Independent session after it is given the id of the freeze commit already pushed to the public repository (§8). Before then nobody can compute the seeds. The core hash and the salt are v0.3's own, so v0.3's worlds are independent of v0.2's. The range is disjoint from the development ranges. |
| Versions | Python 3.14.2, NumPy 2.4.1 | The runner refuses other versions and records `sys.version`, `numpy.__version__`, the platform, and a canonical hash of each world and encoding. |
| Power | see below | protocol rule 16 |
| Drift | zero on one machine and NumPy build by construction (G2, G4) | |

**Power of T-1** (author decision on N, 2026-11-23; `prereg/v03/POWER_STUDY.json`).
- The study: 40 calibration draws of 40 development worlds (PCG64(3141), pool 930100–930999), each with Q-40 at k = 0,
  evaluated on the first 50 valid development test worlds from 930000.
- T-1 was defined on 34–47 of the 50 worlds (median 42); no draw had fewer than 16. 1–10 worlds had no feasible α
  (median 3), and the default (α₀, 0) was feasible on 33–47 (median 42.5).
- For n = 42 defined worlds the Wilson rule needs 38 HOLDS; for n = 50 it needs 45.
- Averaged over the draws, P(HOLDS | r) is 0.90 at r = 0.95, 0.50 at 0.90, 0.17 at 0.85 and 0.04 at 0.80. The last
  value is the chance of a HOLDS at the threshold.
- The author chose 50 test worlds on an approximation: the designer scaled the T-1-defined share of each of S2's 40
  Q-40 draws to 50 worlds. The power study replaces it.
- The one-atom floor (R1-1) does not change definedness, so these figures hold under it.
- These are figures of the development system; definedness also depends on the system.

**Alternatives the author did not choose (for the record):**
- **A1:** feasibility at k₀ = 5 with τ at k₀; the v0.2 rule (feasible at some k, τ at k₀) stated explicitly;
  feasibility at every k.
- **A3:** Q-20; D1 on 10 worlds (v0.2). D1 on 40 worlds was a contrast in S2, not a candidate.
- **A4:** a smaller prototype radius (S1 chose none; radius 2.0 fails the third criterion); sources that also report
  class atoms (an encoder change); continuous reliabilities only.
- **G8:** re-tested unchanged as a second primary test; left out of v0.3.
- **N:** 30 or 40 test worlds.

## 8. Run plan

1. ~~The author decides A1, A3, A4, G8 and N, and approves the S-10 defaults (8 sources, U(0.55, 0.97), q scaling).~~
   Done 2026-11-23.
2. **Code (`kodlayici`):** `audit/v03/` (runner, checks, F3 materials, gate studies, the power study) and new tests. No
   v0.2 file is changed.
3. **D4 smoke test** on development worlds only. For each check it prints only the number of defined worlds, reachable
   (yes/no) and covered (yes/no). No counts of HOLDS, no verdict values, no new_false.
4. **Gate certificates** for G1–G7a and T-1 (§6.3), then F4 on 20 development worlds.
5. **Blind review 1** in the Independent session, of this text and the code. Its findings are handled with the repair
   loop and recorded. The author decides whether further blind reviews are needed.
6. **Just before the freeze:**
   - this file's status block (the bold status line and its two bullets) is replaced by the frozen status line,
     exactly: "**Status: FROZEN.** The manifest is `prereg/v03/FREEZE_v0.3.json`; the freeze commit, its date and the
     core hash are in `prereg/v03/FREEZE_RECORD.md`. The drafts and their changes are listed in §10.";
   - the status line of `SPEC_v0.3.md` (its third line) is replaced, exactly, by: "**Status: FROZEN** with
     `prereg/PREREG_v0.3.md`, by the manifest `prereg/v03/FREEZE_v0.3.json`; see `prereg/v03/FREEZE_RECORD.md`." (R1-6);
   - `certify all --verify` is run and GATE_TOOL.json written;
   - with the status lines and GATE_TOOL.json in place, the full test suite runs on the tree to be frozen and must pass
     (R2-2);
   - the pre-freeze check is run (§6.3).
7. **The author's approval, then the freeze:**
   - `prereg/v03/FREEZE_v0.3.json` is written with `py -m audit.v03.freeze write` and checked with
     `py -m audit.v03.freeze verify --coverage`, from a tree whose frozen files are all tracked (R1-4).
   - The freeze record (date, core hash, freeze commit, platform string of the run machine, sign-off) goes into
     `prereg/v03/FREEZE_RECORD.md`, outside the manifest.
   - The freeze is committed. `py -m audit.v03.clone_verify` verifies that commit in a fresh clone (both manifests).
     Only if it verifies is the freeze pushed, with the author's OK. Exactly one commit ever touches the manifest.
8. **The salt:**
   - The Independent session is given the id of the pushed freeze commit and the core hash. It draws 32 random bytes,
     records them with the commit id and the core hash in its own folder, and reports them.
   - The designer writes them to `run/v03/SALT.json` (salt, freeze commit, core hash, who drew them, time), adds the
     salt to the freeze record, and commits and pushes both (author's OK).
9. **Calibrate.** Before it, `git fetch origin` is run; the runner reads only the local ref `origin/main`. It refuses
   unless all of the following hold:
   - the manifest verifies;
   - exactly one commit touches `FREEZE_v0.3.json` (with full history); it is the freeze commit, and it is on
     `origin/main`;
   - the manifest lists exactly the files tracked under the §9 manifest paths in the freeze commit;
   - the manifest and every frozen file are tracked, unmodified, and identical to their content in the freeze commit;
   - exactly one commit touches `run/v03/SALT.json`; it is a strict descendant of the freeze commit and on
     `origin/main`; the file names the freeze commit, and its core hash equals the verified manifest's.

   The runner then generates and validates the 40 calibration worlds and the 20 draw-sensitivity sets, and computes τ
   (Q-40 at (α₀, 0)), the I-6 τ (Q-40 at (α₀, k₀)), the I-7 τ (D1 on the first 10 at (α₀, 0)), the I-8 τ (D1 on the
   first 10 at (α₀, k₀)) and the 20 draw-sensitivity τ.
   `run/v03/CAL_WORLDS.json` and `run/v03/TAU.json` (all of these τ) are committed and pushed, with the author's OK,
   before any test world exists.
10. **Test.** The runner:
    - refuses unless everything in step 9 holds, and exactly one commit touches each of `CAL_WORLDS.json` and
      `TAU.json`, a strict descendant of the salt commit and on `origin/main`;
    - regenerates the calibration worlds and recomputes every τ, and refuses unless the world records and every τ
      equal the committed ones exactly;
    - generates and validates the 50 test worlds;
    - runs F1, F2 and F4 on all test worlds and the 40 main calibration worlds first, and stops with no verdict on any
      disagreement;
    - only then runs G1–G7a, T-1, the detector diagnostic and the descriptive arms. It holds the outputs in memory,
      builds the verdict table and the descriptive summary, and only then writes any output, so a crash leaves no
      outcome on disk.
11. **Stop, crash and rerun.**
    - A stop or a crash ends the run with no verdict.
    - Any change to the code after that is a new version, with a deviation note, a new freeze and a new salt.
    - The first complete run is the result. Its outputs are committed and pushed at once (author's OK).
    - `py -m audit.v03.run_v03 reproduce`, run in a fresh clone of the result commit on the machine whose platform
      string is in the freeze record, repeats the test step into `run/v03_repro/` and compares the SHA-256 of its
      `VERDICTS.json` with the committed one. It must reproduce it byte for byte; the outcome is reported.
12. **F3** (§6.1) and the **blind post-run audit**, both in the Independent session.
    - The audit has two parts. Part 1 judges the design without results. Part 2 judges the results, the draft report and
      the provenance. The designer checks in the transcript that Part 1 was written before any result was opened.
    - Provenance: `run/v03/SALT.json` matches the Independent session's record; and, in a fresh clone of the public
      repository that the audit makes itself, the freeze, salt, CAL/TAU and result commits are in the order of steps
      7–11.
13. **Report** the pre-registered table as it is, with the fixed wording, the expected-verdict paragraph and the
    limitation sentence.

## 9. Freeze

- **Files in the manifest:**
  - this file, `SPEC.md` and `SPEC_v0.3.md`;
  - `tesaron/**` and `audit/**`;
  - the `.json` files directly in `prereg/v03/`, except the manifest itself: the design studies S1, S1b and S2, the
    power study, the all_true study, the n_q study, and F4;
  - `pyproject.toml` and `tests/**`.
- **Outside the manifest:**
  - `README.md`, `LICENSE`, `.gitattributes` and `.gitignore`;
  - the freeze record;
  - `prereg/v03/reviews/`: the instructions and reports of the blind reviews, published with the freeze commit;
  - `run/`;
  - v0.2's own records: `prereg/PREREG_v0.2.md`, `prereg/FREEZE_v0.2.json`, v0.2's freeze record, studies and reviews,
    and `REPORT_v0.2.md`.
- **Manifest:** `prereg/v03/FREEZE_v0.3.json`, written by `audit/v03/freeze.py`, which uses the format and algorithm of
  v0.2's freeze verifier `audit/freeze.py` by import (R1-4).
- **v0.2's own manifest** (`prereg/FREEZE_v0.2.json`) still verifies after v0.3's freeze, because no v0.2 file changes.
  The pre-freeze check confirms this.

## 10. Changes from v0.2

| Change | Source |
|---|---|
| v0.3 worlds: 8 sources with reliabilities U(0.55, 0.97) per world; q_true 0.1875, q_false 0.0075; overlap fraction 0.8 (S-10) | AQ1 (continuous reliabilities); A4 and its realisation (author, 2026-11-23); S1, S1b |
| τ and T-1's feasibility at k = 0 | A1 (author) |
| τ by Q-40 on 40 calibration worlds | A3 (author); S2 |
| G8 descriptive; T-1 the only primary test; no G8 twin or gate study | author, 2026-11-23 |
| G7a's claim narrowed to four baselines; all_true descriptive | author, 2026-11-23, after the code step found all_true scoring on development worlds |
| 50 test worlds | author, 2026-11-23 |
| No pilot: no new_false, T-1 or G8 outcome on any v0.3 world before the freeze; T-1's gate `plus` world uses a constant new_false | designer |
| New T-1 structure arm (sources spanned, wrong class atoms spanned); draw-sensitivity arm; I-6 and I-7 | designer; post-run audit A1 and A3 |
| T-1's tolerance max(δ, 1/n_q), with the claim stated accordingly | author decision on R1-1 |
| I-8 (v0.2's full rule on the v0.3 worlds) and I-9 (T-1 without the floor) | designer, R1-8 and R1-1 |
| F3 recomputes τ and the aggregated structure counts | post-run audit A5, A6 |
| A complete "not covered" list | A6 |
| `f3_compare` summary counts every row | A7 |
| F3 instructions fix the float rule for the boundary band | A8 |
| G8's hypothesis summary uses SPEC §8's `hyp_count` | A9 |
| The pre-freeze check requires the frozen header and reproducible design studies | A10, A2 |
| N4's subprocesses get explicit `PYTHONHASHSEED` values | A11 |

**Repairs after blind review 1** (`prereg/v03/reviews/`; 0 blocking, 8 major, 8 minor):

| Finding | Repair |
|---|---|
| R1-1 δ below one atom | T-1's tolerance max(δ, 1/n_q) (author decision); the resolution stated in §2 and §7; I-9 without the floor; NT raised to 0.5 |
| R1-2 T-1 wording | the HOLDS and FAILS sentences of §4 say what a verdict means; §3.3 |
| R1-3 G7a | a fixed sentence on all_true and on the three baselines that score 0 by definition; the §2 tautology bullet; the N7 note in §6.2 |
| R1-4 tool names | `audit.v03.clone_verify` and `audit.v03.freeze` in §6.3, §8 and §9 |
| R1-5 certificates | the pre-freeze check requires all eight FALSIFIABLE and verified certificates |
| R1-6 SPEC header | a frozen status line for `SPEC_v0.3.md`, checked like this file's |
| R1-7 all_true numbers | the all_true study, `prereg/v03/ALL_TRUE_STUDY.json`, reproduced by the pre-freeze check |
| R1-8 several changes at once | I-8, v0.2's full rule on the v0.3 worlds; the I-6 wording; the expected-verdict paragraph |
| R1-9 factors | two mechanisms toward HOLDS; two sentences reworded |
| R1-10 Wilson | "approximately"; the exact size at r = 0.80 |
| R1-11 τ_d = 0 | stated in §7 |
| R1-12 "computes" | "reads, prints, stores or reports"; the development seed ranges |
| R1-13 not covered | the list completed; a missing verdict table affects every test |
| R1-14 draw-sensitivity sets | F1, F2 and F4 named for the 40 main calibration worlds; a failed set counts as insufficient and does not stop the run |
| R1-15 a test starts git | the gate driver checks the study ids before the checkout |
| R1-16 small mismatches | the T-1 plus world's new_true, the N7 comment, the n = 0 structure sentence, the hyp_count summary and the power approximation are stated |

**Repairs after blind review 2** (targeted; `prereg/v03/reviews/`; 14 of review 1's repairs fixed and 2 partly fixed;
0 blocking, 3 major, 7 minor new findings):

| Finding | Repair |
|---|---|
| R1-1 leftover, R2-1 the T-1 claim | the claim says "by more than δ or by one wrong conclusion, whichever is larger" in §1, §3.2 and the printed sentence |
| R1-14 leftover | §8 step 10 names the 40 main calibration worlds |
| R2-2 stage-dependent tests | the tests no longer depend on the draft stage; §8 step 6 runs the full suite on the tree to be frozen |
| R2-3 the n_q numbers | the n_q study, `prereg/v03/NQ_STUDY.json`, reproduced by the pre-freeze check; the worlds named in §2 |
| R2-4 the G7a sentence | "can be excluded" |
| R2-5 waivers | an object with non-empty reasons, driver ids, WEAK only |
| R2-6 NT | the condition stated with max(δ, 1/n_q) |
| R2-7 the floor | "when the denominator does not fall from p to q" |
| R2-8 n_q in the F3 map | a test world's n_q → T-1; a calibration world's → none |
| R2-9 all_true row | the two worlds with an empty I at 0.95 are stated |
| R2-10 stale texts | `audit/v03/freeze.py` updated; T-1's tolerance and I-8/I-9 listed among the changes from v0.2. The comment in v0.2's `audit/exact.py` ("at most 1.2") is in a frozen v0.2 file and stays; its bound `MAX_RATIO = 3` covers NT's maximum of 1.5. |
