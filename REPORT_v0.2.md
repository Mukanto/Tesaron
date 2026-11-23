# Tesaron v0.2: report

**Status: final, after the blind post-run audit** (§9). The verdicts and numbers are those of the run; the audit
changed none of them. It led to corrections of what this report claims about its controls and to the disclosures in §8.

- **Author:** Hazar Şimşek (theory and decisions). Design, verification and this report: Claude (main session).
  Code: `kodlayici` (Sonnet 5.5). Blind reviews, F3 and the post-run audit: fresh agents in a separate session
  ("Independent").
- **Pre-registration:** [`prereg/PREREG_v0.2.md`](prereg/PREREG_v0.2.md), draft 5, frozen at commit `8b09a6f`. Its
  header still reads "DRAFT 5, not frozen": the designer did not update it before the freeze, and a frozen file cannot
  be changed. The manifest `prereg/FREEZE_v0.2.json` and the freeze record decide what is frozen.
- **Run label:** a model test on new worlds (PREREG §1).

## 1. What was tested

Tesaron v0.1 turns semantic information into data and back: a fuzzy encoder selects data in a context, the meaning
units carry a degree of support and of refutation, a Belnap interface maps them to four values, a two-channel Datalog
decoder deduces and abduces, and a constrained-Pareto criterion scores the result against reference worlds whose
meaning is known by construction.

v0.2 tests it on 30 new synthetic worlds:
- **two primary tests,** which are empirical claims about the system:
  - **T-1:** within the reasonable bounds, admitting weaker evidence does not increase new false conclusions by more
    than δ = 0.05;
  - **G8:** creativity (abduction) preserves meaning;
- **seven implementation and criterion checks** (G1–G7a), which are decided by construction and test that the code does
  what the design says.

## 2. How the run was protected

| Step | Record |
|---|---|
| Freeze | commit `8b09a6f`; manifest `prereg/FREEZE_v0.2.json`, 115 files, core hash `fc0fabd8…659ed0`; verified in a fresh clone before the push |
| Gate | Truth_Gate v0.5.1: nine certificates, all FALSIFIABLE |
| Salt | drawn by the Independent session after the freeze commit was public (2026-11-22T16:17:50Z); commit `127faa0` |
| Calibration | commit `f3c60ff`: 10 worlds; τ_s = 57/70, τ_d = 3/68, τ_t = 193/198, τ_b = 3/5 |
| Test | commit `fcb4ea5`: 30 worlds, no draw rejected; F1, F2 and F4 agreed on every world |
| Reproduction | a fresh public clone reproduced `VERDICTS.json` byte for byte; the post-run audit reproduced it again from an export of the result commit |
| F3 | a fresh agent recomputed, from blind inputs, every metric, the feasible sets, fronts and hypervolumes, the T-1 structure fields, the G7a, G8 and T-1 outcomes and the verdict table: 0 disagreements on 30 worlds. What F3 did not recompute is listed in §4. |
| Post-run audit | a fresh agent, blind to the results in its first part: no finding changes a verdict; every provenance check passed (§9) |

Each commit was pushed with the author's approval before the next step ran. Details:
[`prereg/FREEZE_RECORD.md`](prereg/FREEZE_RECORD.md) and [`run/RUN_RECORD.md`](run/RUN_RECORD.md).

## 3. Verdicts (the pre-registered table, PREREG §4)

| Test | Verdict | HOLDS | FAILS | UNDEFINED | Wilson lower bound |
|---|---|---|---|---|---|
| G1 | HOLDS | 30 | 0 | 0 | — |
| G2 | HOLDS | 30 | 0 | 0 | — |
| G3 | HOLDS | 30 | 0 | 0 | — |
| G4 | HOLDS | 30 | 0 | 0 | — |
| G5 | HOLDS | 30 | 0 | 0 | — |
| G6 | HOLDS | 30 | 0 | 0 | — |
| G7a | HOLDS | 30 | 0 | 0 | — |
| **G8** | **FAILS** | 15 | 15 | 0 | 0.356 |
| **T-1** | **FAILS** | 16 | 5 | 9 | 0.585 |

**The fixed wording, as the runner printed it** (`run/VERDICTS.json`):

> G1 holds: Membership degrees are not turned into probabilities, in all 30 defined test worlds (0 undefined). (A
> check of the implementation or of the criterion, not a discovery.)
>
> G2 holds: Encoding is reproducible in the same context (same machine, same NumPy build), in all 30 defined test
> worlds (0 undefined). (A check of the implementation or of the criterion, not a discovery.)
>
> G3 holds: A meaning unit needs its data (necessity), in all 30 defined test worlds (0 undefined). (A check of the
> implementation or of the criterion, not a discovery.)
>
> G4 holds: The decoder gives the same output for the same input (same machine, same NumPy build), in all 30 defined
> test worlds (0 undefined). (A check of the implementation or of the criterion, not a discovery.)
>
> G5 holds: Validation data do not leak into pattern computation, in all 30 defined test worlds (0 undefined). (A
> check of the implementation or of the criterion, not a discovery.)
>
> G6 holds: Expansion makes no unevidenced claims, in all 30 defined test worlds (0 undefined). (A check of the
> implementation or of the criterion, not a discovery.)
>
> G7a holds: None of the five degenerate baselines of SPEC §10 (echo, all_true, all_false, all_unknown, all_both) gets
> a positive score under the wisdom criterion, in all 30 defined test worlds (0 undefined). (A check of the
> implementation or of the criterion, not a discovery.)
>
> G8 does not hold: 15 of 30 defined worlds hold (Wilson lower bound 0.356, threshold 0.80); 0 undefined; the first
> failing world is 580411434. At most α the tolerance ε_d is below one atom, so a world fails when abduction changes
> the value of a single decided encoded atom. Hypotheses at (α₀, k = 10) over the defined worlds: minimum 10, median
> 10 (the mean of the two middle values), maximum 10.
>
> T-1 does not hold: 16 of 21 defined worlds hold (Wilson lower bound 0.585, threshold 0.80); 9 undefined; the first
> failing world is 322899240. In these worlds T-1 compares regimes of the three source reliabilities: on 6 of 21
> defined worlds the feasible set reached α ≤ 0.60, where the 0.60 source is admitted, and on 0 it reached α ≥ 0.85,
> where the 0.80 source is excluded. T-1's outcome depends strongly on the calibrated bounds, which vary between
> calibration draws. It is not a graded test of the thesis. Structure (I-5): of 21 defined worlds, 6 had some feasible
> α ≤ 0.60 and 0 some feasible α ≥ 0.85. Pairs inside α 0.65–0.80: 18 hold, 2 fail, 1 none. Pairs crossing 0.60/0.65:
> 3/3/15. Pairs crossing 0.80/0.85: 0/0/21.

**Printed next to the G8 and T-1 verdicts** (PREREG §2):

> Expected verdicts given the pilot (R1-10). If the test worlds behave like the development worlds, T-1 and G8 are
> expected to FAIL. T-1 may also end in "insufficient worlds": on development worlds its number of defined worlds
> varied strongly between calibration draws. Under the 28/30 rule, P(HOLDS) is about 0.003 at a per-world rate of 0.71
> (T-1), and about 0 at 0.30 (G8). The test τ will differ from the development τ, which is a caveat. A different
> outcome would mean that the test worlds, or for T-1 the calibrated bounds, differ from the development ones (see the
> structure counts).

**Printed next to every verdict:**

> These results come from synthetic worlds generated by code written by the same model family that designed and coded
> the system. The decoder was given the true rules. They say nothing about natural-language input.

There is no combined verdict for the architecture (PREREG §4).

**Notes on the printed text, added after the run** (they change no verdict):
- **The expected-verdict paragraph uses stale pilot rates** (post-run audit A2, B3). Its rates, 0.71 for T-1 and 0.30 for
  G8, come from the draft-2 pilot. The designer did not rerun the pilot with the frozen code. With the frozen code, the
  30 development test worlds of `prereg/DRAW_STUDY.json` give:
  - G8: 15 of 30 hold (0.50);
  - T-1: 722 of 918 defined world-draws hold (0.786) over the study's 40 calibration draws, and the T-1 verdict is
    HOLDS in 3, FAILS in 34 and "insufficient worlds" in 3 of the 40 draws.

  Both the audit and the designer recomputed these figures after the run. So "about 0.003" understates the chance of a
  T-1 HOLDS under development behaviour. The run's rates (G8 0.50, T-1 16 of 21 = 0.76) are close to the frozen code's
  development rates.
- **The G8 hypothesis count is the cap** (A9, B4). It counts the kept abduction candidates at k = 10, which cannot
  exceed 10, so "10 in every world" says only that every world had at least 10 candidates. It is not SPEC §8's
  `hyp_count`.

## 4. Controls

- **Fidelity controls.** F1 (closure, abduction candidates, pass 2), F2 (H) and F4 (encoder, units, interface facts)
  agreed with the system on all 30 test worlds before any check ran.
- **F3, an independent recomputation from blind inputs,** found 0 disagreements (`run/F3_COMPARE.json`).
  - **What F3 was given:** τ, the units, the decoder's full and verdict value lists, and the G1–G6 per-world outcomes.
  - **What F3 therefore did not recompute:** the τ calibration, the G1–G6 checks, the detector diagnostic, the
    descriptive arms, the G8 hypothesis summary, and the aggregated T-1 structure counts.
  - **What the post-run audit checked instead:** τ against the stored calibration metrics, and the verdict table, the
    structure counts and the descriptive aggregates against the per-world outputs. All agreed.
  - **The agent's notes** (`run/f3_agent/NOTES.md`) record its conventions:
    - IEEE-double comparisons for the boundary band;
    - the instructions' definition of a hypothesis;
    - checks it made on its own, among them a second closure algorithm with the same H.
- **The F3 materials.** Besides the frozen instructions, the F3 agent had a short cover note on the folder layout,
  published as `run/f3_agent/COVER.md`. Its files were copied into the repository with line endings normalised to LF;
  the comparison gives the same result on the copies.
- **Detector diagnostic** (PREREG §6.2). Every faulty twin FAILS on every world where its test is defined: N1a, N1b,
  N2–N8 on 30 of 30; NT on 21 of 21 (9 undefined, the same worlds as T-1). No world has both the system and its twin
  holding, so no HOLDS verdict carries the "detector did not separate" qualifier.
- **Reproduction.** Byte-identical in a fresh clone of the public repository.

## 5. Descriptive arms (reported, never part of a verdict)

| Arm | Value |
|---|---|
| Default configuration (α₀, k₀) feasible | 21 of 30 worlds |
| G7b, the system's own hypervolume > 0 | 26 of 30 worlds |
| G8 over the whole grid (I-4): fidelity ≥ τ_s and deviation ≤ τ_d at every point | 6 of 30 worlds |
| G8 worlds that fail only through single-atom changes (I-6) | 1 of 15 failing worlds |
| T-1 over all grid points (I-2) | 3 HOLDS, 27 FAILS, 0 UNDEFINED |
| T-1 and G8 with UNDEFINED counted as FAILS | T-1: 16 of 30 (Wilson 0.387); G8: 15 of 30 (Wilson 0.356) |
| Cross-seed agreement at α₀ (D4a), outside the boundary band | all atoms 2579 of 2870; class atoms 1497 of 1621 |

**T-1's structure on the five failing worlds** (from the per-world structure arm):
- three worlds (114870193, 822668002, 868207235) fail on pairs that cross the 0.60/0.65 boundary, where the weakest
  source is admitted; their pairs inside α 0.65–0.80 hold;
- two worlds (318260273, 322899240) admit no α ≤ 0.60 and fail on pairs inside α 0.65–0.80, where only class atoms
  change. No development world had shown such a failure: the post-run audit found none on the 30 development test
  worlds under any of the 40 calibration draws.

Of the 16 holding worlds, 13 admitted no α ≤ 0.60, so on them only the class-only window was compared.

## 6. Interpretations (PREREG §5)

| No. | Opposite reading | Verdict under it |
|---|---|---|
| I-1 | a separate world set per test | not run (exchangeable draws; the same distribution) |
| I-2 | T-1 over all grid points | descriptive only (PREREG §5): 3 of 30 worlds hold |
| I-3 | UNDEFINED counts as a violation | no change: G6 and G7a have no UNDEFINED world |
| I-4 | G8 over the whole grid | descriptive only (PREREG §5): 6 of 30 worlds hold |
| I-5 | T-1 as a graded test of the thesis | not tested here; the computed sentences say which regimes were compared |
| I-6 | a one-atom tolerance for G8 | not a verdict; 1 of the 15 failing worlds fails only through single-atom changes |

## 7. What the results show and what they do not

- **G1–G7a hold.** The implementation does what the design says on 30 new worlds: membership is not probability,
  encoding and decoding are reproducible on one machine and NumPy build, units need their data, validation data do not
  leak, expansion makes no unevidenced claims, and none of the five degenerate baselines scores under the criterion.
  These are checks of the construction, not discoveries. The criterion does not exclude degenerate strategies in
  general (PREREG §2).
- **G8 fails.** In 15 of 30 worlds, abduction at k = 5 or 10 lowers fidelity by more than 0.05 or raises deviation by
  more than 0.02 at some α. Because ε_d is below one atom at most α, G8 is close to a test of whether abduction changes
  any decided encoded atom; with a one-atom tolerance, 1 of the 15 failing worlds would not fail. The verdict agrees
  with the pilot; the per-world rate (0.50) is higher than the draft-2 pilot's (0.30) and equal to the frozen code's
  rate on development worlds (§3, notes).
- **T-1 fails.** In 5 of 21 defined worlds, a feasible point with lower uncertainty has a share of new false conclusions
  more than 0.05 higher. Three of them fail where the weakest source (0.60) is admitted, as the development worlds
  suggested. Two fail inside the class-only window, which the development worlds had not shown. Nine worlds were
  undefined (fewer than two feasible points with distinct uncertainty). T-1 is not a graded test of the author's
  thesis: with three discrete source reliabilities it compares the regimes the calibrated bounds admit, and on 13 of
  the 16 holding worlds those bounds excluded the weakest source. Which T-1 verdict results is largely decided by the
  calibration draw (§3, notes; §8).
- **Nothing here concerns natural language** or any data not generated by this code (§8, first item).

## 8. Limitations

- **The pre-registered limitation:**

  > These results come from synthetic worlds generated by code written by the same model family that designed and
  > coded the system. The decoder was given the true rules. They say nothing about natural-language input.

- **The post-run audit's observations on the design.** They are post-hoc and change no verdict; they are recorded
  for a later version.
  - **T-1's feasible set is the set at k = 0 (A1).** Abduction only adds facts, so it can only lower fidelity and
    consistency and raise deviation. A point feasible at k > 0 is therefore feasible at k = 0, and T-1's feasible α set
    equals the set at k = 0, while τ is calibrated at k₀ = 5. The pre-registration did not say this. A post-hoc reading
    with feasibility at k₀ only gives T-1 17 of 21 (Wilson 0.637): still FAILS.
  - **T-1 depends mainly on the calibration draw (A3).** τ takes extremes over 10 worlds. On development worlds the
    T-1 verdict varies between HOLDS, FAILS and "insufficient worlds" across calibration draws (§3, notes). The
    pre-registration disclosed this, and the structure counts are printed next to the verdict.
  - **In these worlds weak class evidence is never wrong evidence (A4).** No class atom is ever encoded F, and every
    T-encoded class atom was world-true at every α on development worlds. So the class-only window adds only correct
    atoms to I. According to the audit, new_false can rise there only through derivations that combine those class
    atoms with relation reports already admitted at 0.80. This generic factor toward T-1 holding is missing from the
    pre-registration's directional factors.
  - **τ has no independent recomputation (A5).** F3 takes τ as given. The audit found τ equal to the extremes of the
    stored calibration metrics.
  - **Paths without an independent recomputation are missing from the "not covered" list (A6):** the G1–G5 check code,
    the aggregation of the T-1 structure counts, and the detector "both hold" count. The audit recomputed the last two
    and the verdict table from the per-world outputs.
  - **Smaller items:**
    - `f3_compare.py`'s summary omits the G1–G6 rows from its affected-test counts (A7); there was no disagreement;
    - the F3 instructions fix IEEE-double comparison only for the encoded values, not for the boundary band (A8); the
      agent used doubles, and the metric is in no verdict;
    - the N4 twin's in-process hash seed is not fixed (A11); N4 failed on every world, and both reproductions were
      byte-identical.

## 9. Deviations and the post-run audit

**Deviations from the plan and from the frozen text:**
- None from the run plan (PREREG §8, steps 6–12).
- The expected-verdict paragraph rests on stale pilot rates (§3, notes). This is the designer's error: the pilot was
  not rerun with the frozen code.
- The pre-registration's header was not updated before the freeze (see the top of this report).
- In the salt request the designer misspelled the `main` commit with an extra digit. The Independent session recorded
  the value the remote printed (`prereg/FREEZE_RECORD.md`).
- **F3:**
  - The agent had a cover note besides the frozen instructions, which PREREG §6.1 says are given unchanged. The note
    only describes the folder and its rules, and it is published (`run/f3_agent/COVER.md`).
  - The agent's files were copied with line endings normalised (§4).
  - The agent wrote two scratch files into its task folder outside `out/`. They are inside the permitted folder and
    are not compared.
- The agents of reviews 2 and 3 and of the post-run audit each stopped once on a usage limit and were resumed. Review
  1's agent was stopped and its task sent again. The F3 agent ran without interruption.

**The blind post-run audit** (PREREG §8, step 12; task `tesaron_v02_postrun`, a fresh agent in the Independent session).
Its instructions and reports are published in `run/postrun_audit/`.
- **Order of its work:** it wrote its first part without the results, certificates, reviews or freeze record, and
  opened them only afterwards. The designer checked this order in its transcript.
- **Findings:** none high. 5 medium and 6 low on the design (§8), and 1 medium and 5 low on the draft of this report.
  This version corrects the report findings: the claimed reach of F3, the stale pilot rates, the hypothesis cap, the
  "descriptive only" readings of I-2 and I-4, the limitation section, and the deviations above.
- **Recomputations:** it recomputed every seed, τ, the verdict table, the structure counts, the T-1 outcomes and the
  descriptive arms, and found every value equal to the run's.
- **Its own reproduction:** it reran the test step from an export of the result commit, and `VERDICTS.json` came out
  byte-identical.
- **Provenance:**
  - the salt, freeze commit and core hash in `run/SALT.json` equal the record the Independent session wrote when it
    drew the salt;
  - in a fresh clone of the public repository, the manifest verifies and is touched by one commit;
  - the history runs freeze → freeze record → salt → calibration → test outputs, each run file is touched by exactly
    one commit, and the committed run files are byte-identical to the run's.
  - It could not check push times, which git does not record.
