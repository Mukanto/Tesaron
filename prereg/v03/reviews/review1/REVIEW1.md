# Blind review 1: Tesaron v0.3 pre-registration (draft 1) and code

**Counts:** 0 blocking, 8 major, 8 minor (16 findings).

I saw no forbidden value. Every number below comes from one of three sources: the committed design JSONs; design
quantities I recomputed myself (feasibility, τ, definedness, denominators, baseline scores, G7a outcomes, the all_true arm);
or a development run whose output was redacted. The appendix lists the commands.

---

## Major

### R1-1: δ is below the resolution of one atom on about half of T-1's feasible points
- **Where:** PREREG §7: "| δ for T-1 (D2) | 0.05 | one new false conclusion in 20 decided ones |". Also §2, "Factors that
  bear on T-1", and §3.2 T-1.
- **Reason:**
  - The denominator of new_false is the number of decided atoms outside I (SPEC §8). I counted it at k = 0 on the power
    study's 50 development test worlds (decoder verdicts only; world truth was not read for these atoms).
  - At α₀ = 0.70 its median is 19, and it is below 20 on 29 of the 50 worlds.
  - At the 8684 feasible k = 0 points of the power study's 40 Q-40 draws, the median is 21 and it is below 20 at 44% of
    the points.
  - On 985 of the 1684 world-draws where T-1 is defined (58%), the lower point q of some T-1 pair has fewer than 20 decided
    atoms outside I. On those worlds, one wrong conclusion at q (with none at p) exceeds δ.
  - So δ does not mean "one in 20" on most worlds. It means "not one more wrong conclusion". This is the failure mode that
    v0.2 had to explain after its run for G8 ("the tolerance ε_d is below one atom").
  - It breaks protocol rule 9 and the checklist item "Tolerances are above the numerical resolution".
  - The denominator never fell along a T-1 pair (0 of 18 796 pairs), so the problem is granularity, not a shrinking
    reference set.
- **Fix:**
  - Correct the δ rationale in §7. State the granularity as a factor toward FAILS in §2.
  - Add a descriptive arm, the counterpart of v0.2's I-6 for G8: the number of T-1 FAILS worlds in which every violating
    pair has at most one more wrong decided atom outside I at q than at p. Print it next to the T-1 verdict.

### R1-2: The fixed T-1 wording overstates both verdicts
- **Where:**
  - PREREG §4: "T-1, HOLDS: 'T-1 holds: <claim>. …'" and "T-1, FAILS: 'T-1 does not hold: …'".
  - §3.3: "What a HOLDS means: the per-world rate is at least 0.80".
  - §7 power: "P(HOLDS | r) is 0.90 at r = 0.95, 0.50 at 0.90, 0.17 at 0.85".
- **Reason:**
  - The HOLDS sentence asserts the claim without a quantifier, although up to 20% of worlds may violate it.
  - The FAILS sentence reads as a refutation. Yet at a true per-world rate of 0.90, well above the threshold, a FAILS has
    probability 0.50, and at 0.85 it has probability 0.83.
  - Protocol rule 16: an underpowered FAILS reads "not demonstrated", not "refuted".
- **Fix:** Reword both sentences.
  - HOLDS: "T-1 holds on at least 80% of worlds (one-sided 95% Wilson bound): …".
  - FAILS: "T-1 is not demonstrated: <h> of <n> defined worlds hold (Wilson lower bound <b>, threshold 0.80); this does not
    show that the per-world rate is below 0.80; …".
  - Update `audit/v03/aggregate.py` and its wording tests to match.

### R1-3: The G7a verdict hides the baseline that scores, and three of the four judged baselines score 0 by definition
- **Where:**
  - PREREG §4: "Deterministic test, HOLDS: '<Id> holds: <claim>, in all <n_defined> defined test worlds …'" (applied to
    G7a).
  - §2: "all_false because it contradicts every T-encoded atom, which the calibrated τ_d and τ_s exclude".
  - `audit/v03/aggregate.py:21`.
- **Reason:**
  - The G7a HOLDS sentence gives no hint that the fifth SPEC §10 baseline scores. I reproduced the §2 claim exactly:
    under each of S2's 40 Q-40 draws, all_true scored on the same 22 of 30 development worlds, at α 0.95, 0.90 or 0.85.
  - echo, all_unknown and all_both have verdict U or B on every H atom (H atoms have no unit). Their new_true is
    therefore 0 by definition, whatever τ is.
  - So the only thing G7a tests in v0.3 is whether the constraints exclude all_false, plus the oracle anchor. Even that
    exclusion depends on the data, not on construction: it needs a T-encoded atom in I and τ_d below the share of T
    atoms.
  - The gate's minus world (N7) held on 7 of 100 development worlds (`g7.cert.json`). A detector qualifier on a few
    test worlds is therefore likely; §6.2 does not anticipate it.
- **Fix:**
  - Add a fixed sentence printed with every G7a verdict: "all_true, not judged, was feasible and scored > 0 on <n> of
    <N> test worlds (at α …); echo, all_unknown and all_both score 0 by the definition of new_true, so only all_false is
    excluded by the constraints."
  - Correct the §2 tautology bullet to "excluded on the development data", not "by construction".

### R1-4: The clone verification in the text is v0.2's tool and verifies v0.2's manifest
- **Where:**
  - PREREG §6.3: "Before the push, the freeze is verified in a fresh clone (`audit/clone_verify.py`)."
  - §8 step 7: "`py -m audit.clone_verify` verifies that commit in a fresh clone. Only if it verifies is the freeze
    pushed".
  - `audit/clone_verify.py:26` (`MANIFEST_REL = "prereg/FREEZE_v0.2.json"`, with no option to change it).
- **Reason:**
  - Run as written, the step verifies v0.2's manifest and prints "CLONE VERIFIES". The v0.3 freeze would then be pushed
    without its own clone check.
  - The v0.3 tool is `audit/v03/clone_verify.py`, which checks both manifests.
  - §9 likewise says only "the freeze verifier in `audit/`", where the v0.3 writer is `audit/v03/freeze.py`.
- **Fix:**
  - Name `py -m audit.v03.clone_verify` in §6.3 and §8 step 7.
  - Name `py -m audit.v03.freeze write` (and `verify --coverage`) in §8 step 7 and §9.

### R1-5: The pre-freeze check does not require the certificates to be FALSIFIABLE or verified
- **Where:**
  - PREREG §6.3: "Required certificates: every certificate must be FALSIFIABLE" and the pre-freeze list.
  - `audit/v03/prefreeze_check.py:63-81`: it compares only the "files" table.
  - `audit/v03/gate/certify.py:151-152`: GATE_TOOL.json is written whatever the verify exit codes are.
- **Reason:** `certify all --verify` can fail, or a certificate can be WEAK or UNTESTED. GATE_TOOL.json still records it
  (in `verify_exit` and `verdict`), and the pre-freeze check passes. The requirement is left to the operator, against
  protocol rule 17 and the checklist item "enforced by the runner, not left to the operator".
- **Fix:** In `check_gate_tool`, also require the following, and add tests:
  - all eight ids are present;
  - every `verify_exit == 0`;
  - every `verdict == "FALSIFIABLE"`, unless an approved waiver file names the id;
  - `tag == "v0.5.1"`;
  - each listed `body_sha256` equals the one in the committed `.cert.json`.

### R1-6: SPEC_v0.3.md will be frozen with "DRAFT 1, not frozen" in its header
- **Where:** `SPEC_v0.3.md:3`: "**Status: DRAFT 1, not frozen** (2026-11-23)."
- **Reason:**
  - SPEC_v0.3.md is in the manifest (§9). Nothing in §8 step 6 replaces its header.
  - The pre-freeze status check reads only PREREG_v0.3.md.
  - This repeats post-run audit A10 for the second frozen text.
- **Fix:**
  - Add a frozen status line for SPEC_v0.3.md to §8 step 6.
  - Extend `check_status_line` to every frozen Markdown file (PREREG_v0.3.md, SPEC_v0.3.md, and the F3 instructions if
    they ever get a status line).

### R1-7: The all_true numbers in §2 come from no committed, reproducible study (A2 only partly handled)
- **Where:**
  - PREREG §2: "The baseline all_true scores in v0.3 worlds (G7a data from the code step, checked by the designer) … 22
    of the 30 … only 6 of the 30 worlds have a source at or above 0.95, and 20 at or above 0.90".
  - `audit/v03/prefreeze_check.py:52-57` (STUDIES).
- **Reason:**
  - These printed numbers carry the G7a narrowing. No script or JSON in `prereg/v03/` produces them, so the pre-freeze
    reproduction check (A2) cannot cover them.
  - I recomputed them and they are correct: 22 in every draw, the same set; levels 0.95, 0.90 and 0.85; the other four
    baselines never score; 6 and 20.
- **Fix:**
  - Commit a small design study (for example `audit/design/v03_all_true_study.py` writing `prereg/v03/ALL_TRUE_STUDY.json`)
    and add it to STUDIES.
  - Or cite only numbers that an existing study JSON holds.

### R1-8: Several changes from v0.2 at once, with no arm that reproduces v0.2's own rule
- **Where:**
  - PREREG §10, which lists the world change (4 parameters), Q-40 and k = 0.
  - §5 I-6: "the opposite reading of A1, and close to v0.2's".
  - §2 expected paragraph: "v0.2's T-1, on worlds with three discrete sources, failed."
- **Reason:**
  - v0.3 changes the worlds, the τ rule and the configuration of calibration and feasibility together. Protocol rule 8
    asks for a control that separates the changes.
  - I-7 (D1-10 at k = 0) and I-6 (Q-40 with τ and feasibility at k₀) each change one rule. Neither is v0.2's rule, which
    took τ by D1-10 at (α₀, k₀) and read feasibility at any k, in effect the k = 0 set (post-run audit A1). So I-6 is not
    "close to v0.2's".
  - The expected paragraph invites the reader to explain a different v0.3 outcome by the worlds alone.
- **Fix:**
  - Add a descriptive arm "T-1 under v0.2's full rule on v0.3 worlds": τ by D1 on the first 10 calibration worlds at
    (α₀, k₀), feasible at some k. Commit its τ with the others.
  - Fix the I-6 wording.
  - Add one sentence to §4 or §5: a verdict that differs from v0.2's cannot be attributed to the new worlds alone.

## Minor

### R1-9: The factor list in §2 is incomplete in the HOLDS direction and has two loose sentences
- **Where:** PREREG §2, "Factors that bear on T-1".
- **Reason:**
  - Two mechanisms are missing:
    - a wrong derived conclusion that collides with another derivation becomes B, which is neither in the numerator nor
      in the denominator of new_false;
    - the consistency and deviation bounds (τ_d is 0 in 16 of 40 power-study draws) remove exactly the points where
      wrong conclusions clash with evidence.
  - Both point toward HOLDS.
  - "A single step therefore changes less than v0.2's jump" is loose: T-1 compares every pair in the feasible range, not
    single steps.
  - "a wrong class atom makes the entity's true class F" holds only when R6's (i, j) is (partner class, base class).
- **Fix:** Add the two mechanisms, and reword the two sentences ("can make", "adjacent levels").

### R1-10: The Wilson rule is not exactly a one-sided 95% test
- **Where:** PREREG §3.3: "the per-world rate is at least 0.80, at one-sided 95% confidence".
- **Reason:** From POWER_STUDY's need table, P(HOLDS | r = 0.80) is above 0.05 for n = 35, 36, 42, 43, 48 and 49. It is
  0.058 at n = 42, the median, and up to 0.062.
- **Fix:** Write "approximately (Wilson score bound; the exact size at r = 0.80 is 0.02–0.06 for n = 34–50)".

### R1-11: τ_d is often exactly 0 under Q-40
- **Where:** PREREG §7, the τ rule row.
- **Reason:** τ_d = 0/1 in 16 of 40 power-study draws and in 11 of 40 S2 draws, and in the development τ. Feasibility then
  tolerates no deviation at all, so a single atom decides it. This is a direct consequence of the chosen rule (not under
  review), but it is not disclosed.
- **Fix:** One sentence in §7.

### R1-12: The "no pilot" wording says "computes" where the code only discards; the development seed ranges are incomplete
- **Where:**
  - PREREG §2: "nobody computes new_false …", and the S2 row: "No new_true, new_false … quantity was computed".
  - The first §2 row: "development seeds 900000–900999 and 930000–930999".
- **Reason:**
  - `compute_metrics_exact` computes new_true and new_false in memory in S2, in the power study, in the T-1 gate's plus
    world and in the development runner. The values are dropped or redacted; I checked, and the redaction is complete.
  - The development runner also uses 931000–934999 (draw-sensitivity sets) and offsets up to 97xxxx.
- **Fix:** Write "nobody reads, prints, stores or reports". List the development ranges as `audit/v03/seeds.py` does.

### R1-13: The "not covered" list and the F3 map have small gaps
- **Where:** PREREG §6.1, "Not covered…"; `audit/v03/f3_compare.py:252`.
- **Reason:**
  - The list omits:
    - the G6 judge (F3 is given the G6 outcome too, not only G1–G5);
    - the default-feasibility and "UNDEFINED as FAILS" arms;
    - the G1 failed-parts text;
    - the wording of the fixed sentences, including the detector qualifier;
    - the I-6, I-7 and draw-sensitivity τ (F3 has no input for them).
  - A missing `verdict_table.json` maps to all eight tests, while §6.1 says a missing file → G7a and T-1.
- **Fix:** Complete the list, and state the verdict-table case in §6.1. Or map it like any other missing file.

### R1-14: F1, F2 and F4 do not run on the draw-sensitivity calibration worlds, and those sets can stop the run
- **Where:**
  - PREREG §6.1 F1: "every calibration world"; §8 step 10: "all test and calibration worlds".
  - `audit/v03/run_v03.py:286-288` and `205-210`.
- **Reason:**
  - The controls run on the 40 main calibration worlds only.
  - A `WorldSetError` in any of the 20 descriptive sets ends calibration, so the primary test gets no verdict. The
    probability is negligible, but the effect is not stated.
- **Fix:** Say "the 40 main calibration worlds". Add the stop condition to §7, or record a failed alternative set as
  "insufficient" instead of stopping.

### R1-15: One test starts git although TESARON_SKIP_GIT_TESTS=1
- **Where:** `audit/v03/gate/certify.py:121-125, 132-135`; `tests/test_v03_freeze.py:420` (`CE.main(["g9"])`).
- **Reason:** `main` calls `check_checkout()`, which runs `git -C <checkout> rev-parse …`, before it rejects the unknown id.
  The test passes either way, but it starts git. I deselected it, so my run shows 478 passed + 1 deselected.
- **Fix:** Validate the ids before `check_checkout()`.

### R1-16: Small mismatches between text and code
- **Where:**
  - PREREG §6.3 (T-1 plus world: "with new_false replaced by a constant") against `audit/v03/gate/common.py:143`, which
    also replaces new_true by 1/2.
  - `audit/twins/n7.py:11`: "(all_true then scores > 0)".
  - `audit/v03/aggregate.py:64`: an n = 0 structure sentence that §4 does not give.
  - §3.2 G8 hyp_count: the code summarizes defined worlds only.
  - §7: "an approximation scaled from S2 (0.92 / 0.53 / 0.19 / 0.04)", documented nowhere. S2's own Q-40 values for 30
    worlds are 0.67 / 0.30 / 0.11 / 0.03.
- **Fix:** Align the text with the code, or the code with the text, in each case. Source the 0.92 / 0.53 / 0.19 / 0.04
  numbers or drop them.

---

## What I checked and found right
- **Checks against the pre-registration:**
  - T-1 uses the 10 k = 0 points only (`audit/v03/per_world.py:100,90`).
  - G7a judges exactly four baselines and refuses other shapes.
  - all_true is scored by the same code and never judged.
  - G8 is outside the verdict table.
  - The Q-40, I-6, I-7 and draw-sensitivity τ follow §3.2 and §7. Validity, replacement, seeds and roles follow §7.
  - The aggregation and the §4 sentences match, apart from R1-16.
- **Numbers printed in the pre-registration:**
  - S1: 90/100 valid and 8% at radius 2.0; 83 degenerate at 1.5.
  - S1b: 0.99, 0.18 / 0.31 / 0.40 / 0.54, 2.2–4.0%.
  - S2: Q-40 recommended; median stability 0.79; 4/41 = 0.098 against 1/11 = 0.091.
  - Power study: 34–47 defined (median 42); 1–10 with no feasible point; 33–47 default-feasible; need 38 at n = 42 and 45
    at n = 50; P(HOLDS | r) 0.90 / 0.50 / 0.17 / 0.04.
  - All match the committed JSONs. S-10's reliability stream and overlap placement match the code.
- **Order of steps:** the runner enforces freeze → salt → CAL/TAU → test: a unique manifest commit, pushed; a salt commit
  that is a strict descendant; unique CAL and TAU commits that are strict descendants of the salt commit; the τ recheck;
  outputs written last.
- **No pilot:** the development runner's redaction boundary is complete. I checked every exposed key path of a real
  DEV_TEST.json. smoke_d4, f4_prefreeze, the design studies and the T-1 gate study expose nothing forbidden. The tests
  that touch development worlds assert structure only.
- **Gate:** all 8 certificates are FALSIFIABLE, with 100 samples and no flags, and their module_sha256 equals the current
  study files. The T-1 study's selection on definedness is sound: definedness does not depend on new_false.
- **F3:** the instructions are sufficient to recompute τ and every listed field from the blind inputs. The map in
  `f3_compare.py` is §6.1's, apart from R1-13.
- **Post-run audit A1–A11:**
  - Handled: A1 (decision plus I-6), A3, A4, A5 (main τ only), A7, A8, A9, A11.
  - Partly handled: A2 (R1-7), A6 (R1-13), A10 (R1-6).
- **v0.2 untouched:** v0.2's manifest still verifies on the copy (FREEZE OK, 115 files).
- **Protocol checklist:**
  - Ticked: tautology, known and prospective, interpretations, controls, fidelity, minus world, D4, blindness, power, label.
  - Not ticked: tolerances (R1-1); one change at a time (R1-8); steps enforced by code, for the certificate requirement
    (R1-5).

## Readiness
Not ready as it stands. Once R1-1 to R1-8 are fixed, the pre-registration is ready to freeze.

- R1-1, R1-7 and R1-8 add code: a descriptive arm, a small study and an extra τ. The designer should run the D4 smoke
  test, `certify all --verify` and the pre-freeze check again after them.
- The other fixes are text changes or small tool changes.

I found no defect that biases the T-1 verdict as computed. The major findings concern the following, which all have to be
settled before the freeze:
- what a verdict will mean (R1-1, R1-2, R1-3, R1-8);
- safeguards the text claims but the tools do not enforce (R1-4, R1-5, R1-6, R1-7).

---

## Appendix: commands run (all on the copy `out/scratch/repo`, interpreter `C:\Users\user\AppData\Local\Python\pythoncore-3.14-64\python.exe`)
For every run:
- the environment was set to `TRUTH_GATE_DIR=<task>\truthgate`, `TESARON_SKIP_GIT_TESTS=1`, `PYTHONDONTWRITEBYTECODE=1`,
  and TMP/TEMP inside `out/scratch/tmp`;
- PATH was restricted to `C:\Windows\System32;C:\Windows`, so that git could not be started.

1. Test suite, with the git-starting test removed: `python -B -m pytest -q -p no:cacheprovider --deselect
   tests/test_v03_freeze.py::GateDriverTests::test_the_driver_refuses_without_a_study_id_and_with_an_unknown_one tests`
   → **478 passed, 50 skipped, 1 deselected, 504 subtests passed** (275 s). This equals the designer's 479 passed / 50
   skipped once the deselected test is counted.
2. `python -B -m audit.freeze verify prereg/FREEZE_v0.2.json` → **FREEZE OK** (115 WRITABLE warnings, from the copy).
3. `python -B -m audit.v03.run_v03 test --dev-redacted --out out/scratch/dev_test --n-cal 40 --n-test 6 --n-alt 2
   --no-subprocess` → exit 0 (48 s).
   - It printed τ main 15/19, 0/1, 182/185, 108/155 (τ_s, τ_d, τ_t, τ_b), the I-6 and I-7 τ, and definedness only.
   - The T-1 row printed "REDACTED". DEV_TEST.json had no forbidden key without "REDACTED" (key-path scan,
     `logs/dev_test.log`).
4. `out/scratch/tools/design_checks.py a`: S2's 30 test worlds and its 40 Q-40 τ.
   - 6 worlds have a source ≥ 0.95, and 20 have one ≥ 0.90.
   - all_true scored on 22 worlds in every draw: the same set, at α 0.95, 0.90 and 0.85.
   - echo, all_false, all_unknown and all_both never scored. G7a HOLDS on 1200 of 1200 world-draws.
   - Two versions ran. The first called the repository's own `all_true_arm`, `baseline_points`, `collect_g7a` and
     `judge_g7a` once per draw; I stopped it as too slow, but its process finished anyway. The second computed the
     metrics once and applied each τ. Both gave the same results.
5. `out/scratch/tools/design_checks.py b`: the power study's 50 test worlds and its 40 Q-40 draws. It counts only the
   denominator of new_false (decided atoms outside I, k = 0).
   - The median per α runs from 1 (α 0.95) through 19 (α 0.70) to 37 (α 0.50).
   - At the feasible points: median 21; below 20 at 3804 of 8684.
   - T-1 pairs: 18 796; the denominator fell along none of them.
   - On 985 of 1684 defined world-draws, some pair has fewer than 20 at q.
6. Read-only JSON summaries of POWER_STUDY, TAU_RULE_STUDY, WORLD_STUDY, OVERLAP_STUDY and F4_PREFREEZE; SHA-256 of the
   gate study files against the certificates' module_sha256 (all 8 equal).

Not run, as the instructions require: `calibrate`, `test` or `reproduce` in real mode; `certify.py`;
`prefreeze_check.py`; `clone_verify.py`; anything that calls git. Because certify was not run, the certificates were not
re-verified against the current helper modules.
