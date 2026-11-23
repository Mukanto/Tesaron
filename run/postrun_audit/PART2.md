# Blind post-run audit, Tesaron v0.2: Part 2 (results, report, provenance)

Opened after `out/PART1.md` was written. `PART1.md` was not changed afterwards. Read: `part2/` (run outputs, freeze
record, draft report), the salt record `E:\Independent\tasks\tesaron_v02_salt\SALT_RECORD.json` (read only), and one
public clone in `out/scratch/clone/`. Scripts: `out/scratch/p2check.py`, `textcheck.py`, `ksens.py`, `repro_driver.py`
(outputs `p2check_out.txt`, `repro_out.txt`).

I found no number in the draft report that differs from the run's outputs, and no verdict that differs from the
pre-registered mapping. Every provenance check passed. The findings concern what the report claims about its controls,
and items that the pre-registration requires the report to print or report.

| Id | Severity | Location | Claim | Failure scenario | Verdict impact |
|---|---|---|---|---|---|
| B1 | medium | `REPORT_v0.2_DRAFT.md` §2 table, row F3 ("recomputed every number from blind inputs") and §4 ("an independent recomputation") | The report claims more than F3 did. Under PREREG §6.1, F3 was given τ, the G1–G6 per-world outcomes, the units and the decoder's full and verdict lists. It did not recompute the τ calibration, the G1–G6 checks, the detector diagnostic, the descriptive arms, the G8 hypothesis summary or the aggregated T-1 structure counts. | A reader takes τ and G1–G6 as independently confirmed. An error there (Part 1, A5 and A6) would still have given "0 disagreements". This audit found no such error: τ equals the extremes of the `metrics_exact` in `CAL_WORLDS.json`, and the table, structure counts and descriptive aggregates recompute from the per-world outputs. The sentence still overstates the control. | None on the verdicts. It overstates how far the results were verified. |
| B2 | low | Report §3 and §7; PREREG §4 ("printed next to every verdict and in the limitations section") and §8 step 13 | The limitation sentence appears once, under the table. The report has no limitations section; §7 only refers back to "the limitation sentence above". | A reader of §7, or of the G8 or T-1 paragraph alone, does not see the limitation next to the verdict, as the pre-registration requires. | None. A required element is placed incompletely. |
| B3 | low | Report §3 (expected-verdict paragraph) and §7 ("The result agrees with the pilot (6 of 20 held there)"); Part 1, A2 | The pilot rates behind the expected-verdict paragraph (T-1 0.71, G8 0.30) come from draft-2 code. The run gave T-1 16/21 = 0.76 and G8 15/30 = 0.50. The frozen code gives 0.79 and 0.50 on development worlds (Part 1). "Agrees with the pilot" is true of the verdict only, and the report does not say the paragraph's numbers are stale. | A reader infers a G8 per-world rate near 0.30 and that a T-1 HOLDS was a 0.003 event. Under the frozen code's development behaviour a T-1 HOLDS occurred in 3 of 40 calibration draws. | None. It affects the reading of the outcome, not the verdicts. |
| B4 | low | Report §3, G8 sentence "minimum 10, median 10 … maximum 10"; `audit/per_world.py:107`; Part 1, A9 | Every one of the 30 worlds sits at the cap: the count is the number of kept abduction candidates, which cannot exceed k = 10. The report does not say this, so the sentence gives no information about "few hypotheses" (§10 directional item). The F3 notes record that SPEC's `hyp_count` is a different count. | A reader takes "10 hypotheses per world" as a measured size of abduction. It is the cap. | None. |
| B5 | low | Report §6, rows I-2 and I-4 ("Verdict under it: FAILS") | PREREG §5 gives the opposite readings of I-2 and I-4 as "descriptive only". The report turns those descriptive arms into verdicts by applying the Wilson rule (I-2: 3 of 30; I-4: 6 of 30). | A reader may count these as extra pre-registered verdicts. | None. The labelling is not pre-registered. |
| B6 | low | Report §8 "Deviations" and §4; `run/RUN_RECORD.md` (F3 section); PREREG §6.1 | The deviations and the control reporting are incomplete. (a) The F3 agent got a "short cover note on the folder layout" besides the frozen instructions, which §6.1 says are given unchanged. Its content is not shown, so whether it mattered is unclear. (b) The designer normalised line endings of the agent's files before the comparison. (c) The agent's `NOTES.md` is not reported with `F3_COMPARE.json`, as §6.1 requires. (d) `run/RUN_RECORD.md`, `run/F3_COMPARE.json` and `run/f3_agent/` are not in the public repository (its `main` is at the result commit `fcb4ea5`), although the report links `run/RUN_RECORD.md`. | A reader cannot see from the report that the F3 input went beyond the frozen text or that its files were edited. The public links to the run record and F3 files do not resolve yet. | None on the verdicts. It affects the completeness and honesty of the record. |

## Checked and found sound

- **Verdict table**, recomputed with my own code from `RESULTS.json`, cross-checked against `outputs_results/` and using the draw order of `TEST_WORLDS.json`. G1–G7a: 30/0/0, HOLDS. G8: 15/15/0, Wilson 0.356, FAILS, first failing world 580411434. T-1: 16/5/9, n_defined 21, Wilson 0.585, FAILS, first failing world 322899240. All of this equals `VERDICTS.json` and the report's table, and every verdict is the one PREREG §3.3/§4 gives for these counts.
- **Fixed wording**: the nine verdict paragraphs, the expected-verdict paragraph and the limitation sentence in the report are verbatim equal to `VERDICTS.json`, checked by machine after whitespace normalisation of the quote blocks.
- **T-1 structure counts** recomputed from the per-world structure fields over the 21 defined worlds: 6 with α ≤ 0.60, 0 with α ≥ 0.85; window 18/2/1; crossing 0.60/0.65 3/3/15; crossing 0.80/0.85 0/0/21. The report's per-world statements in §5 and §7 hold: 114870193, 822668002 and 868207235 fail on crossing pairs with holding window pairs; 318260273 and 322899240 have no α ≤ 0.60 and fail inside the window; 13 of the 16 holding worlds have no α ≤ 0.60.
- **"No development world had shown such a failure"**: on the 30 development test worlds under all 40 `DRAW_STUDY` τ draws, the frozen code gives 0 window-pair failures.
- **T-1 outcomes**, recomputed with my own code from the committed exact metrics and τ: equal to the run's on all 30 worlds. The Part 1 A1 sensitivity (feasibility at k₀ only) gives 17/21, Wilson 0.637, still FAILS (one world, 822668002, changes), so A1 does not change this verdict.
- **G8**: the single-atom world is 318260273 (one deviation atom at α 0.85, k 10). "With a one-atom tolerance, 1 of the 15 failing worlds would not fail" is correct. The hypothesis summary equals the per-world counts (all 10).
- **Descriptive arms** recomputed from the per-world outputs, all equal to `VERDICTS.json` and the report: default feasible 21/30; G7b > 0 on 26/30; G8 whole grid 6/30; I-6 1/15; T-1 over all points 3/27/0; UNDEFINED as FAILS T-1 16/30 (0.387), G8 15/30 (0.356); cross-seed 2579/2870 and 1497/1621.
- **Detector diagnostic**: N1a, N1b and N2–N8 FAIL on 30/30, NT on 21/21. NT is undefined on exactly the 9 T-1-undefined worlds, both_hold is 0 everywhere, and no qualifier applies, as the report says.
- **Seeds**: all 30 test (world, encoder, aux) seeds and all 10 calibration (world, encoder) seeds recompute from the salt and core hash by the §7 formula with my own code. Draws are 0–29 and 0–9 with no rejection.
- **τ**: the extremes of the calibration worlds' `metrics_exact` give 57/70, 3/68, 193/198 and 3/5, equal to `TAU.json`, the inputs of every world and `RESULTS.json`. `sha256(CAL_WORLDS.json)` equals the hash in `TAU.json`. The core hash is the same in every run file and in the manifest.
- **Blind inputs**: draw indices, the given G1–G6 outcomes and τ in `outputs_input/` equal the run's values. `F3_COMPARE.json` reports 0 disagreements on 30/30 worlds.
- **Gate**: the clone holds 9 certificates, each with verdict FALSIFIABLE and none WEAK.
- **Reproduction by this audit.** I exported the result commit `fcb4ea5` from the clone (`git archive`) into a scratch
  folder and called the frozen `audit.run_v02.run_test` there in real mode, without the git checks. The call used the
  salt from `run/SALT.json`, passed the version and freeze checks, and went through the calibration recheck (the
  regenerated calibration worlds and τ equal the committed ones) and F1/F2/F4 on all 30 worlds. `VERDICTS.json` is
  byte-identical: SHA-256 `6a0c09ab…c2172f`, the value in `RUN_RECORD.md`. `TEST_WORLDS.json`, `RESULTS.json` and all
  60 per-world files are identical too. It ran in 231 s on this machine.

## Provenance

| Check | Result |
|---|---|
| Salt (`run/SALT.json` against `tesaron_v02_salt/SALT_RECORD.json`) | salt `e892db2a…916ec8`, freeze commit `8b09a6f3…65bb603` and core hash `fc0fabd8…659ed0` are equal. The record's SHA-256 is `277ee953…a6a18`, as SALT.json and the freeze record state. The remote `main` seen before the draw is `70960f1`. |
| Clone freeze verification | `python -m audit.freeze verify prereg/FREEZE_v0.2.json` in the fresh clone gave `FREEZE OK`, exit 0. The only warnings are WRITABLE, because git does not keep read-only bits. The manifest lists 115 files. |
| Manifest touched by exactly one commit | yes, `8b09a6f` (`git log --full-history`) |
| Commit order | `8b09a6f` (freeze) → `70960f1` (freeze record only) → `127faa0` (adds `run/SALT.json`, and the salt in the freeze record) → `f3c60ff` (adds `run/CAL_WORLDS.json` and `run/TAU.json`) → `fcb4ea5` (adds the 63 test-output files). The history is linear, each commit is the parent of the next, and `merge-base --is-ancestor` holds for each step. `origin/main` = HEAD = `fcb4ea5`. No frozen file changes after the freeze commit; the only non-`run/` change is `prereg/FREEZE_RECORD.md`, which is outside the manifest. |
| Each run file touched by exactly one commit | yes: all 66 tracked files under `run/` (1 in `127faa0`, 2 in `f3c60ff`, 63 in `fcb4ea5`) |
| `part2/run/` against the clone | the 66 committed files are byte-identical. 36 files are not in the clone: `RUN_RECORD.md`, `F3_COMPARE.json` and `f3_agent/` (34 files), so they could not be compared. |
| Commit dates against the salt time | freeze 19:07:21+03:00 < salt drawn 16:17:50Z (19:17:50+03:00) < salt commit 19:18:34 < calibration 19:20:43 < test 19:26:36. Author dates are self-reported and do not prove the push times. |

Checks I could do: all of the above. Checks I could not do: the times at which commits reached the remote (git does not
record push times; the order of the push steps rests on the records); the content of the F3 cover note; the
reproduction run in a clone of the public repository as §8 step 11 describes it (I reran the test step from an export of
the result commit instead, see above); the unit tests and the gate (not run, as instructed for the gate).
