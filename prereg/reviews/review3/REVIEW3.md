# Targeted blind review 3: Tesaron v0.2 pre-registration (draft 5) and the code changed for it

**Counts.**
- Repairs of review 2 (13 findings): fixed 11, partly fixed 2 (R2-11, R2-12), not fixed 0, made worse 0.
- New findings: blocking 0, major 1, minor 9 (10 in all).

**How this review was done.**
- I read PREREG draft 5 and review 2. I read the code that changed: `run_v02.py`, `indep/abduction.py`, `indep/units.py`,
  `fidelity.py`, `f3/`, `f3_compare.py`, `prefreeze_check.py`, `gate/certify.py`, `descriptive.py`, `checks.py`,
  `aggregate.py`, `design/draw_study.py` and `f4_prefreeze.py`. I also read the parts of `tesaron/` they check, SPEC §1
  and §5–§15, the new tests, and the Truth_Gate checklist and `freeze.py`.
- I ran code only on the writable copy `out/scratch/repo`, with the required interpreter and environment variables. I
  did not run git, `certify.py`, `prefreeze_check.py`, the gate, or `run_v02.py` (not even with `--dev`, except through
  the unit tests). I did not read the `run_dev/` outputs that the unit tests wrote.
- **Blindness.** I computed no G8 or T-1 outcome on any world, no HOLDS count or rate, and no low-α feasibility. What
  I computed are design quantities: hashes, line endings, G7a and baseline feasibility (a property of the criterion,
  not of the system), metric equality counts, and the draw-study figures.
- Commands and results are in the appendix.

---

## Part A. Repairs of review 2

| Id | Status | Evidence |
|---|---|---|
| R2-1 (blocking, AQ4) | fixed | The claim is narrowed in §1 l.38-39, §3.2 l.113, `aggregate.py:21-22` and the G7 study name (`g7_study.py:35`); the check is unchanged (`checks.py:331-366`). §2 l.54 records that echo+F and echo+T score, and l.72-73 says how each baseline fails. **AQ4 is carried out correctly and honestly.** I also checked the per-baseline sentence across draws: under each of the 40 τ of `DRAW_STUDY.json`, on the 30 development test worlds, no baseline was feasible with a positive score, and the oracle anchor held. all_true's smallest deviation over worlds and α is 3/11 and all_false's is 3/7, against a largest τ_d of 6/53, so the deviation bound alone excludes them by a wide margin. (τ_s alone would not: all_true's largest fidelity is 18/25, just below the smallest τ_s, 13/18.) |
| R2-2 | fixed | The runner checks: exactly one commit for the manifest, SALT, CAL_WORLDS and TAU (`run_v02.py:116-125`); the manifest and frozen files tracked, clean and identical to the freeze commit (`:183-195`); SALT a strict descendant of the freeze commit, naming it and the core hash (`:198-223`); CAL and TAU strict descendants of the salt commit (`:226-235`); every commit on `origin/main`, with the local-ref limit stated (`:143-149`, §8 l.369-370). The post-run audit checks salt provenance and the public remote (§8 l.394-399). The git tests (`test_audit_runner_fidelity.py:235-499`) cover the review-2 scenarios; they were skipped here. Residues: R3-7. |
| R2-3 (AQ5) | fixed | The T-1 sentence is computed (`aggregate.py:93-99`). The structure arm has the α ≥ 0.85 flag and the 0.80/0.85 arm (`descriptive.py:72-97`). The counts are printed next to the verdict (`aggregate.py:83-90, 197-204`) with the HOLDS caveat (`:37-39`). The directional item is written (§10 l.494-504). **AQ5 is carried out correctly:** `judge_t1` and the design are unchanged, and only the reporting is strengthened. §1 l.21-25, §2 l.74-80 and I-5 (l.197) say honestly that T-1 is mostly decided by the draw-dependent bounds. Residues: R3-5 (one printed sentence contradicts the caveat), R3-9 (sentence order), R3-3 (F3 does not cross-check the structure counts). |
| R2-4 | fixed | Every figure in §7 l.314-325 reproduces from `DRAW_STUDY.json`: defined 11–30 (median 23), insufficient in 3 draws, 16–19 in 5, default feasible 9–29 (median 19.5), no feasible point 0–15 (median 5.5), α ≥ 0.85 in 13 draws (up to 25), the τ ranges, G7a defined 30/30, and mean P(HOLDS \| r) 0.588 / 0.264 / 0.098 / 0.032. The 16–19 row (l.311) is correct. Regenerating `DRAW_STUDY.json` with the current code gives the same file byte for byte. "Insufficient worlds" is in §2 l.59-60 and `aggregate.py:42-43`. The G7a feasibility sentence is corrected (§2 l.53). |
| R2-5 | fixed | Raw integer denominators `n_I` and `n_decided` are stored per α (`checks.py:378-384, 394-395`) and used in `descriptive.py:100-117`. They equal SPEC §8's denominators: \|I\| and the decided encoded atoms, both independent of k. The unit tests with 2/40 and 9/18 exist (`test_audit_checks.py:348-374`). |
| R2-6 | fixed | `indep/abduction.py:40-76` follows SPEC §7.3 condition by condition: the head is OBSERVED in F1; exactly one body literal is missing, by position; it is ground by the head and the other literals; it is in the vocabulary; its atom is U; the score is the number of distinct (rule, θ); the ranking is score, then (channel, pred, args) with POS first (S-9). It grounds over all entity assignments and does not import tesaron.decoder, encoder or belnap. F1 compares the full ranked list with scores at every α, the kept top-k at every (α, k), pass 2 recomputed from the independent hypotheses, and the statuses (`fidelity.py:54-99`). F4 adds relation units and interface facts (`indep/units.py`, `fidelity.py:127-155`). Regenerating `F4_PREFREEZE.json` gives the same file byte for byte (7353 candidates, 600 configurations). Residue: R3-8. |
| R2-7 | fixed | `audit/f3/INSTRUCTIONS_F3.md`, `OUTPUT_SCHEMA.json` and `f3_compare.py` exist and are frozen (§9). The resolution rule is in §6.1 l.215-221. The G1–G6 outcomes are given and labelled (`run_v02.py:285-312`). **Partial dry run:** I implemented steps 1–6 of the instructions from the text alone (metrics, feasible set, front, hypervolume, G7a; no G8 or T-1). On 5 development worlds, all 1200 metric fields, the feasible sets, fronts, hypervolumes and G7a outcomes equal the run's. Residues: R3-2, R3-3, R3-4. |
| R2-8 | fixed | SPEC §1 l.33-35 and §11 l.374-376 are updated (S-8). `prereg/README.md` is written and is outside the manifest (§9 l.412). §2 l.47 reads "S-1–S-9". `system.py:19` reads "S-1..S-7", which is accurate because S-8 and S-9 changed no code. Residue: `audit/README.md` (R3-10). |
| R2-9 | fixed | `aggregate.CLAIMS` equals the §3.2 claims, and the nine study names equal them with a lower-case first letter (`g*_study.py`, `t1_study.py:18`). The certificates were regenerated: every module hash matches its study file, all nine are FALSIFIABLE, and verify exit is 0. |
| R2-10 | fixed | The salt enters the freeze record in step 8 (§8 l.361-362, l.367-368). The perm and n2 indices are in §7 l.295, matching `per_world.py:30, 38`. |
| R2-11 | partly fixed | Per-world outputs are held in memory during the loop (`run_v02.py:434-443`), and the rerun is described (§8 l.392-393). But outcomes are still written before aggregation can crash, and the described rerun is refused by the runner (R3-6). |
| R2-12 | partly fixed | `prefreeze_check.py` compares GATE_TOOL.json with the current files: all 90 hashes match here, and none is missing or unrecorded. It compares the freeze walk with `git ls-files`. The tag check refuses untracked files (`certify.py:78-83`). But review 2's "freeze from a clean checkout" was replaced by a check of file **sets**, not of file **bytes**, so a frozen tree that a fresh clone does not reproduce still passes (R3-1). |
| R2-13 | fixed | G1 (ii) is now "every class unit has μ⁻ = 0" (`checks.py:111-113`). The failed parts are recorded (`per_world.py:104-105`, `run_v02.py:347`) and printed (`aggregate.py:180-181`; §3.2 l.107, §4 l.161). |

---

## Part B. New findings

### Major

#### R3-1 (major). The pre-freeze check does not catch a frozen tree that a fresh clone would not reproduce (line endings, uncommitted edits)

**Where:**
- `audit/prefreeze_check.py:77-110`: `check_tracked_set` compares path sets only;
- `audit/freeze.py:27-32`: hashes over raw bytes. The Truth_Gate tool's warning about this (`truthgate/protocol/tools/freeze.py:21-22`, quoted below) was not carried over;
- `run_v02.py:190-195`: `git status` and `git diff` hide line-ending conversion;
- no `.gitattributes` in the repository;
- PREREG §6.3 l.276-278, §8 l.359-361, l.392-393 and l.397-399.

**Quote:** "the files the freeze verifier would hash are exactly the git-tracked files under the manifest paths (no
ignored or untracked file)". The Truth_Gate tool warns: "A tool that rewrites line endings (for example a git checkout
with autocrlf) changes the hash".

**Reason.**
- **The tree has mixed line endings.** Of the 116 files under the §9 manifest paths, 53 are CRLF-only and 63 are LF-only.
  - CRLF-only: `run_v02.py`, `checks.py`, `aggregate.py`, `descriptive.py`, all nine certificates and study files,
    `GATE_TOOL.json`, `F4_PREFREEZE.json`, `DRAW_STUDY.json`, and most of `tesaron/encoder` and `tesaron/worlds`.
  - LF-only: SPEC, PREREG, `f3_compare.py`, `prefreeze_check.py`, `indep/*`, `tesaron/decoder/*`.
  - GATE_TOOL's 90 hashes and the nine certificates' module hashes are over exactly these bytes. With CRLF converted to
    LF, 41 of the 90 hashes and all 9 module hashes no longer match.
- **Whether a clone reproduces these bytes depends on git settings that the repository does not fix.**
  - With `core.autocrlf=true` (the Git for Windows default) or `input`, CRLF is normalised to LF on commit. A checkout
    then gives all-LF or all-CRLF files, and neither reproduces a mixed tree. The original bytes cannot be recovered
    from the repository at all.
  - With `autocrlf=false` the blobs keep the bytes. A clone made with `autocrlf=true` still converts the 63 LF files.
- **Nothing before the run notices.**
  - On the designer's machine the working tree is unchanged, so `verify_manifest` passes.
  - `git status` and `git diff`, used by both the pre-freeze check and the runner, ignore line-ending conversion.
  - The first fresh clone in the plan is the step-11 rerun or the step-12 audit, after the run. If the clone does not
    verify, the runner refuses there, and the pre-registered byte-for-byte reproduction and the public verification of
    the freeze fail.
- **The same gap for uncommitted edits.** A tracked file with an uncommitted edit passes the pre-freeze check. The
  runner refuses it only after the freeze is pushed and the salt drawn (`run_v02.py:190-192`), which forces a new
  version.
- **Unclear whether it bites.** I cannot run git here, so I cannot tell which case holds. It is cheap to rule out.

**Fix.**
- Before the freeze, add `.gitattributes` with `* -text`, or one fixed `eol`. Renormalise once, so that the blob bytes
  equal the hashed bytes on every machine. Then re-run `certify all --verify`: the module hashes change if bytes change.
- In `prefreeze_check`, for every walked file, require that its SHA-256 equals that of `git cat-file blob :<path>`.
  Also require an empty `git status --porcelain --untracked-files=all -- <paths>`.
- Add to §8 step 7: after the freeze commit and before the push, clone it into a temporary folder and run
  `py -m audit.freeze verify prereg/FREEZE_v0.2.json` there. Record the result in FREEZE_RECORD.md.
- Optionally, let the runner also compare each manifest hash with the blob in the freeze commit
  (`git cat-file blob <freeze>:<path>`).
- Carry the Truth_Gate tool's line-ending warning over into `audit/freeze.py`.

### Minor

#### R3-2 (minor). The F3 resolution rule leaves "the affected tests" to be chosen after the fact

**Where:** PREREG §6.1 l.215-221; `f3_compare.py:16-19, 36-37`: one boolean `affects_verdict`;
`INSTRUCTIONS_F3.md` l.90-93.

**Quote:** "The affected tests get no verdict in this version"; "A disagreement on a field that no verdict uses is
reported and changes nothing."

**Reason.**
- The script says only that a disagreement affects some verdict, not which one.
- A fidelity disagreement feeds G8 directly and T-1 through feasibility. Whether T-1 is "affected" when the feasible
  sets agree would be decided with the numbers in view.
- A disagreement only in the verdict table has no "disagreeing worlds" for the second agent.
- What happens with the agent's NOTES.md is not stated.

**Fix.**
- Add a fixed field-to-test map to `f3_compare` and write `affected_tests` for each disagreement:
  - fidelity and deviation → G8 and T-1;
  - consistency, uncertainty, new_true, new_false and the feasible set → T-1;
  - `outcomes.X` and `verdict_table[X]` → X;
  - a missing world or file → G7a, G8 and T-1.
- State that the second agent recomputes the whole table for a table-only disagreement.
- State that NOTES.md is reported with F3_COMPARE.json and changes nothing.

#### R3-3 (minor). F3 does not cover the computed parts of the printed verdict text

**Where:** `OUTPUT_SCHEMA.json` (per-world fields); `f3_compare.py`; `aggregate.py:64-99` (structure counts and the T-1
sentence), `:102-120` (hypothesis summary), `:155` (first failing world); PREREG §6.1 l.212 ("and the verdict table").

**Reason.** Several numbers printed with the verdicts are not compared by F3:
- **The T-1 structure counts and the computed T-1 sentence.** These are the AQ5 safeguard against a HOLDS produced by
  the draw alone. F3 already recomputes everything they need.
- **The first failing world.** It needs the world order, and the blind input has no draw index.
- **The G8 hypothesis summary.** The number of kept hypotheses cannot be derived from the full and verdict lists:
  pass-2 consequences also have full not U and verdict U.

**Fix.**
- Add a per-world `t1_structure` (the five fields) to the schema and to the comparison.
- Add the draw index to the blind input, and add the first failing world to the table rows.
- For the hypothesis summary, either let F3 recompute the kept hypotheses from rules and units, or say in §6.1 that it
  is not covered.

#### R3-4 (minor). Two conventions F3 needs are outside its reading list

**Where:** `INSTRUCTIONS_F3.md` l.15-16 ("SPEC.md (sections 1, 5, 6, 8, 9 and 10)"), l.40-41, l.56-57.

**Reason.**
- **Rule semantics for H.** SPEC §8 defines H through `seminaive_eval`. The rule semantics are in SPEC §7.1–§7.2, which
  the agent is not given: a NEG body literal means a NEG fact is present, and a NEG head adds a NEG fact. NEG heads (R5,
  R6) do affect H.
- **The oracle's verdict view.** It is not stated. For the baselines it is ("the same value in full and verdict").
  Uncertainty, new_true and new_false read verdict.
- In my dry run I had to choose both: strong negation, and the oracle's verdict equal to its full. With those choices
  every field matched.

**Fix.** Add SPEC §7.1–§7.2 to the reading list, or write both rules into the instructions. Add "the oracle has the same
value in full and verdict".

#### R3-5 (minor). The expected-verdict paragraph contradicts the T-1 HOLDS caveat

**Where:**
- PREREG §2 l.63 and `aggregate.py:44-45`, printed next to T-1 and G8;
- against §2 l.78-80 and `aggregate.py:37-39`.

**Quote:** "A different outcome would mean that the test worlds differ from the development worlds."

**Reason.** For T-1 the draft itself says that a HOLDS can come from the calibration draw alone. On a T-1 HOLDS the
report would print both sentences.

**Fix:** "A different outcome would mean that the test worlds, or for T-1 the calibrated bounds, differ from the
development ones (see the structure counts)."

#### R3-6 (minor). Outcomes still reach the disk before aggregation, and the stated rerun is refused (residue of R2-11)

**Where:** `run_v02.py:441-457` against `:473-504`; `:239-241`, `:426-431`; PREREG §8 l.386-387 and l.392-393.

**Reason.**
- **Outcomes before aggregation.** `outputs_results/*.json` (fixed outcomes and check data) and `RESULTS.json` are
  written before `verdict_table` and `VERDICTS.json`. An exception there, in the twin summary or in a write leaves every
  outcome on disk. §8 says instead that "a crash leaves no outcome on disk".
- **The rerun is refused.** A fresh clone of the result commit already holds `run/TEST_WORLDS.json` and the outputs, and
  real mode refuses to overwrite them. So the rerun cannot run as described. The missing steps are not stated:
  - delete the result files, keeping SALT, CAL_WORLDS and TAU;
  - run the test step;
  - compare with the committed `VERDICTS.json`, and say how. `git diff` hides line-ending differences (R3-1).

**Fix.**
- Build the table and the descriptive summary before writing anything. Or write into `run/.partial/` and rename it at
  the end.
- State the rerun steps, or add a `--reproduce` mode that writes to `run_repro/` and compares the bytes with
  `run/VERDICTS.json`.

#### R3-7 (minor). Runner residues: history simplification, manifest coverage, calibration content

**Where:** `run_v02.py:119`; `:100-105` and `:165-180`; `:389-401`.

**Reason.**
- **"Exactly one commit touches" is not checked literally.** `git log -- <path>` uses default history simplification.
  A side-branch commit that touched the manifest, SALT or TAU is hidden when the merge keeps the other side's content.
  The risk is low: the contents at HEAD are still checked, and the salt's provenance is audited after the run.
- **The manifest's coverage is not checked.** Only the runner file must be listed in the manifest. A manifest written
  from a subset of the §9 paths would pass. Modules imported from `audit/` or `tesaron/` that it does not list are not
  covered by `check_frozen_tree`.
- **The calibration worlds are not compared.** `recheck_calibration` compares the recomputed τ with TAU.json. It does not
  compare the regenerated calibration worlds (seeds, hashes) with `CAL_WORLDS.json`; it checks only the sha link
  between the two files.

**Fix.**
- Use `git log --full-history`.
- Refuse unless the manifest's file set equals the files tracked under `prefreeze_check.MANIFEST_PATHS` in the freeze
  commit, or at least unless every loaded module under ROOT is listed.
- Compare the regenerated world records with `CAL_WORLDS.json["worlds"]`.

#### R3-8 (minor). §6.1's statement of what is not covered is incomplete

**Where:** PREREG §6.1 l.204-206; `fidelity.py:118-155`; `indep/units.py:33` (support taken from `ctx.support`);
`indep/pcm_loop.py:53` (the converged flag is discarded) and `:57-84`.

**Quote:** "they are covered only by G2 and G5".

**Reason.**
- G2 tests reproducibility and G5 non-leakage. Neither tests that the selection and the split follow SPEC §5 steps 1–2.
- These parts are also taken from the system without an independent check:
  - the support degrees;
  - the unit statuses;
  - the class-unit provenance, which G3 ablates by;
  - PCM's converged and degenerate flags, which decide world validity (D5) and NOT_COMPUTED.
- The independent loop already returns the converged flag and the iteration count, but F4 drops them.

**Fix.** List these as not covered. Or add them to F4: the converged flag and iteration count, a recomputed degeneracy
check, class-unit provenance and status, and support degrees taken from the world's reliabilities.

#### R3-9 (minor). Small differences between §4 and `aggregate.py`

- **T-1 order.**
  - The code prints the regime sentence, then the HOLDS caveat, then the structure counts (`aggregate.py:200-204`).
  - §4 l.170-179 lists the structure counts before the caveat, and the caveat says "see the structure counts".
- **T-1 with "insufficient worlds".** The code drops the regime sentence but prints the structure counts (l.200). §4
  does not say so.
- **G8 median with an even n.** The code adds " (the mean of the two middle values)" (l.115). This is not in §4 l.168-169.
- **Capitals.**
  - G1: "Failed parts …" (l.181) against §4's "failed parts …".
  - G7a HOLDS: "G7a holds: None of the five …", with a capital N in mid-sentence (from `CLAIMS`, l.21).

**Fix.** Align §4 or the code. The sentence order is the one that matters.

#### R3-10 (minor). Stale frozen text in `audit/README.md`

**Where:** `audit/README.md` (frozen with `audit/**`).

**Reason.**
- Its `indep/`, `fidelity.py` row describes only the closure, the brute-force H and the PCM/μ⁺ check, not the abduction
  enumerator, the relation units or the interface facts.
- It does not list `f3/`, `f3_compare.py`, `prefreeze_check.py` or `design/`.

**Fix.** Update it before the final `certify all --verify`, since its hash is in GATE_TOOL.json.

---

## Readiness

**Not ready to freeze until R3-1 is fixed.**
- **The fix is cheap but changes file bytes:** a `.gitattributes`, a content check in the pre-freeze check, and a
  verification in a fresh clone before the push.
- **What has to be redone afterwards:** the certificates, GATE_TOOL.json and the pre-freeze check.
- **The minor findings** can be repaired in the same pass. R3-2, R3-3 and R3-5 touch AQ5's reporting and F3, so they are
  worth doing.
- **After that, the draft is ready to freeze.** Another blind review is not needed. A check that the freeze manifest
  verifies in a fresh clone is enough.

The review-2 repairs are otherwise careful and complete:
- the runner's commit and salt binding works as described;
- the abduction enumerator follows SPEC §7.3 literally;
- the F3 instructions can be followed for the metrics, the feasible set, the front, the hypervolume and G7a;
- every §7 figure, F4_PREFREEZE.json and DRAW_STUDY.json reproduce exactly;
- all 319 tests pass (23 skipped).

The text keeps saying what the run can show:
- G1–G7a are decided by construction;
- G8 is close to a zero-tolerance test;
- T-1 is mostly decided by draw-dependent bounds, and may end in "insufficient worlds";
- both primary tests are expected to FAIL.

---

## Appendix: commands and results

**Setup.**
- Interpreter: `C:\Users\user\AppData\Local\Python\pythoncore-3.14-64\python.exe` (Python 3.14.2, NumPy 2.4.1).
- Environment: `TRUTH_GATE_DIR=<task>\truthgate`, `TESARON_SKIP_GIT_TESTS=1`, `PYTHONDONTWRITEBYTECODE=1`.
- Copy: `repo/` was copied to `out/scratch/repo` and made writable. My scripts are in `out/scratch/scripts/` and the logs
  in `out/scratch/logs/`.
- Not run: git, `certify.py`, `prefreeze_check.py`, the gate, and `run_v02.py` outside the unit tests. I did not create
  `run/`.

**Results.**
1. **Unit tests:** `python -m unittest discover -s tests` (in the copy).
   - Result: `Ran 319 tests … OK (skipped=23)`.
   - The dev end-to-end test wrote `run_dev/`; I did not read its outputs.
2. **Hashes:** `python -I scripts/hash_check.py repo` and `scripts/body_hash.py repo`.
   - GATE_TOOL.json lists 90 files, all present, all with equal hashes; there are no unrecorded files.
   - All nine certificates are FALSIFIABLE, in full mode, and their body hashes verify with the gate's own
     canonicalisation (`ensure_ascii=False`).
   - Every module hash equals the SHA-256 of its study file as given (with CRLF).
   - After converting CRLF to LF, 41 of the 90 file hashes and all 9 module hashes differ.
3. **Line endings:** `python -I scripts/eol_list.py repo`. Under the manifest paths: 53 CRLF-only files, 63 LF-only
   files, none mixed. There is no `.gitattributes`.
4. **§7 against DRAW_STUDY.json:** `python -I scripts/draw_study_check.py repo`.
   - Every figure of §7 l.311-325 is reproduced, including the need table for n = 16–30.
   - Mean P(HOLDS \| r): 0.588, 0.264, 0.098, 0.032.
5. **Regeneration:** `python -m audit.f4_prefreeze` (29 s) and `python -m audit.design.draw_study` (105 s), in the copy;
   then `scripts/cmp_json.py`. Both files are byte-identical to the given ones.
6. **G7a across calibration draws:** `python -I scripts/g7a_draws.py repo`.
   - The 30 development test worlds equal the study's.
   - Under each of the 40 τ: 0 G7a FAILS worlds and 0 UNDEFINED.
   - all_true: smallest deviation 3/11, largest fidelity 18/25. all_false: 3/7 and 10/17.
   - τ_d ranges 0–6/53 and τ_s 13/18–44/51.
7. **Partial F3 dry run:** `python -I scripts/f3_dryrun.py repo 5`.
   - Steps 1–6 were implemented from the instruction text; G8 and T-1 outcomes were not computed.
   - The blind input was built by `run_v02.blind_input` with placeholder G1–G6 values, under the gate τ.
   - Result on 5 development worlds: 1200 of 1200 metric fields equal; feasible set, front, hypervolume and G7a equal on
     5 of 5.
   - Choices I had to make: strong negation, and the oracle's verdict equal to its full (R3-4).
