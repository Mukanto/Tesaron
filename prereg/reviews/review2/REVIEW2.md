# Blind review 2: Tesaron v0.2 pre-registration (draft 4) and its audit code

**Counts.**
- Repairs of review 1 (22 findings): fixed 18, partly fixed 4, not fixed 0, made worse 0.
- New findings: blocking 1, major 6, minor 6 (13 in all).

**How this review was done.**
- I read PREREG draft 4, SPEC.md (§15 in full), all of `audit/` (including `gate/`, `twins/`, `indep/`), the parts of
  `tesaron/` that decide verdicts, the certificates, GATE_TOOL.json, F4_PREFREEZE.json, the tests, review 1, GATE.md
  and the protocol checklist.
- I ran code only on the writable copy `out/scratch/repo`, with the required interpreter and environment variables,
  on development seeds only. I did not run the gate, `certify.py`, git, or `run_v02.py` without `--dev`.
- **Blindness.** I computed no outcome of the fixed system for G8 or T-1 and no HOLDS count or rate for them. The
  numbers below are design quantities: feasibility, definedness, τ, baseline scores, and checks on synthetic data. The
  T-1 certificate's plus-stream HOLDS count is in a given file; I do not repeat it.
- Commands and results are in the appendix.

---

## Part A. Repairs of review 1

| Id | Status | Evidence |
|---|---|---|
| R1-1 (blocking, AQ2) | partly fixed | The decision is carried out in code: G7a is deterministic (`aggregate.py:10`); `collect_g7a`/`judge_g7a` (`checks.py:313-353`) test the five baselines at every α as single points, with the oracle (`oracle.py`) as anchor and UNDEFINED rule; N7 is the unconstrained criterion (`twins/n7.py`); G7b is descriptive (`descriptive.py:210-219`). The new certificate's minus changes `base_feasible`, with 0 UNDEFINED in 100 minus samples. **But the claim overreaches again.** "gives no degenerate strategy a positive score" (§1 l.36, §3.2 l.104, `aggregate.py:21`) is false in these worlds, and the check covers only the five named baselines (R2-1). |
| R1-2 (blocking, AQ1) | fixed | §1 l.19-25 states what T-1 tests. §2 l.67-71 corrects the tautology answer. I-5 is added (l.175). The structure arm is in §3.2 l.115-119 and `descriptive.t1_structure` (l.222-240): window pairs, crossing pairs, feasible α set, α ≤ 0.60. The verdict sentence is in §4 l.156-157 and `aggregate.py:36-39, 114-115`. The text is honest about the decision. Caveat: the fixed sentence is not true under every calibration draw (R2-3). |
| R1-3 | partly fixed | The salt is in the seed formula (`seeds.py:24-37`, §7 l.260), and the runner checks the commit order (`run_v02.py:144-166, 426-430`). But the runner does not bind the manifest it verifies, or the salt, to the freeze commit. After a code change it accepts the old salt. "On the remote branch" is a local ref. The salt's provenance is unchecked (R2-2). |
| R1-4 | fixed | `recheck_calibration` (`run_v02.py:298-310`) regenerates the calibration worlds, recomputes τ exactly, and compares τ and `sha256(CAL_WORLDS.json)`. TAU must be committed after the salt (`run_v02.py:162-166`). The push of TAU is not checked (part of R2-2). |
| R1-5 | fixed | §3.1 l.82-84 and the §7 grid row l.249 state the k-invariance and what k changes. |
| R1-6 | fixed | G1–G7a are labelled as checks decided by construction (§1 l.28-36, §2 l.60-66). `DETERMINISTIC_NOTE` is printed (`aggregate.py:31, 99-100`). G3 reads "(necessity)" in §3.2 l.100. Residue: the printed claim `aggregate.py:17` drops "(necessity)" (R2-9). |
| R1-7 | fixed | The rule for an undefined fidelity is in §3.2 l.105 and `checks.py:388-394`. The FAILS sentence is in §4 l.154-155 and `aggregate.py:32-35, 112-113`. I-6 is in §5 l.176. The I-6 arm's code miscounts (R2-5). |
| R1-8 | fixed | §3.1 l.86-88. All τ, feasibility, G8 and T-1 comparisons use `Fraction` (`exact.py`, `checks.py:398-459`), and NT is exact (`twins/nt.py`). Only the Wilson bound is compared as a float. Its smallest margin to 0.80 for n = 16–30 is 9.1e-4 (n = 27, 25 holds), so this is safe. |
| R1-9 | partly fixed | The power table (§7 l.265-276) and the meaning of HOLDS (§3.3 l.133) are corrected. I reproduced the table, except the 16–19 row: r = 0.90 gives 0.135–0.185 and r = 0.80 gives 0.014–0.028. But l.279-280 ("3–4 of 30 were UNDEFINED … about 26–27 defined worlds") contradicts §2 l.50 and the calibration-draw study (R2-4). |
| R1-10 | fixed | §2 l.53-58, and `aggregate.EXPECTED_PARAGRAPH` (l.40-45) next to G8 and T-1 (l.131). It does not mention "insufficient worlds" (R2-4). |
| R1-11 | fixed (as asked) | F1 uses the brute-force closure at every grid configuration for pass 1 and pass 2 (`fidelity.py:122-157`, `indep/h_closure.py`). G6 uses the same closure (`checks.py:270-284`). F3 gets blind input (`run_v02.py:216-238`; the test asserts that metrics and outcomes are absent), and the disagreement rule is written (§6.1 l.188). F4 also checks μ⁺ (`indep/pcm_loop.py:124-151`), and the 20-world record exists (max 2.2e-15 / 4.4e-16). New gaps: abduction and relation units have no independent check (R2-6); the F3 comparison and its resolution rule are not fixed (R2-7). |
| R1-12 | fixed | F1, F2 and F4 run on all test worlds before any check, and only STOPPED.json is written on a disagreement (`run_v02.py:327-334`). The stop, crash and rerun rules are in §8 step 11 l.330-334. The runner does not enforce "a new freeze and a new salt" (R2-2), and per-world outputs are written before the loop ends (R2-11). |
| R1-13 | fixed | `default_feasibility` (`descriptive.py:263-265`) and `undefined_as_fails` (`aggregate.py:137-141`) are reported (`run_v02.py:395-396`; §3.2 l.120-121). |
| R1-14 | partly fixed | Versions are pinned and refused (`run_v02.py:55-56, 75-80`). The environment is recorded in CAL_WORLDS, TEST_WORLDS and VERDICTS (l.278, 337, 401), and world and encoding hashes too (l.210-213). §3.2 limits G2 and G4 to one machine and one NumPy build. The printed claims `aggregate.py:16, 18` drop that limit (R2-9). |
| R1-15 | fixed | `certify all --verify` writes GATE_TOOL.json with the verify exit codes and the SHA-256 of 82 files (`certify.py:254-291`). All 82 match the current tree, and all nine certificates are FALSIFIABLE with verify exit 0. There is a T-1 study on real-shaped window data (`gate/common.py:124-157`) and a G7a study with an N7 minus. Residue: no tool checks GATE_TOOL.json against the frozen tree (R2-12). |
| R1-16 | fixed | "DRAFT 4" / "draft 4" (l.3, l.10) and `audit/README.md`. FREEZE_RECORD.md is outside the manifest (§9 l.349). Residue: §8 step 7 puts the salt in the record before it is drawn (R2-10); SPEC and prereg/README text is stale (R2-8). |
| R1-17 | fixed | §7 l.255-260 lists `n2`, "draw index" and the replacement reasons. `WorldGenerationError` is the only exception caught (`worldset.py:93`). An undefined default metric invalidates a calibration world (`worldset.py:47-54`), and `compute_taus` raises on one (`exact.py:119-132`). Residue: perm's index 3i + p is not in §7 (R2-10). |
| R1-18 | fixed | G1 (ii) checks all class units (`checks.py:79, 95-96, 107-109`). G5 compares the full unit-map digest (`checks.py:230-266`). G2 uses two explicit subprocess seeds, 0 and 1 (`per_world.py:19`). The G5 and G6 wording in §3.2 is fixed. Residue: the study names in `g3_study.py` and `g5_study.py` keep the old wording (R2-9). |
| R1-19 | fixed | §4 l.150-153 and `aggregate.py:104-111` print counts and the Wilson bound. |
| R1-20 | fixed | The primary tests are named (§1), multiplicity is stated (§3.3 l.136-137), the run is labelled (l.38), and the n/a checklist items are in §10 l.401-403. Residue: the "directional hypotheses" checklist item is not written (R2-3). |
| R1-21 | fixed | The reading of the diagnostic is in §6.2 l.208-212. `both_hold` and the qualifier are in `run_v02.py:365-379` and `aggregate.py:116-119`. |
| R1-22 | fixed | `audit/freeze.py` is frozen with `audit/`. The runner uses it (`run_v02.py:40, 84-105`) and does not import truth_gate (a test checks this). |

---

## Part B. New findings

### Blocking

#### R2-1 (blocking). G7a's claim is false in these worlds; the check covers only the five named baselines

**Where:**
- PREREG §1 l.36 and §3.2 G7 row l.104;
- §2 l.66;
- `audit/aggregate.py:21` (`CLAIMS["G7"]`);
- the study name in `audit/gate/g7_study.py:35`.

**Quote:** "The wisdom criterion gives no degenerate strategy a positive score"; "the baselines cannot score by their
definitions".

**Reason.**
- **Claim and check differ in scope.** The check tests five baselines (`checks.py:318-353`). The claim is about all
  degenerate strategies.
- **Two equally degenerate strategies do score.**
  - "echo+F" keeps enc(a) on every atom that has a unit and sets every other atom to F; this is the closed-world
    default. "echo+T" does the same with T.
  - I scored them under the gate τ (D1 on ten development calibration worlds) on 30 development worlds:
    - echo+F was feasible with a positive score at some α on 29 worlds;
    - echo+T on 30;
    - the oracle was feasible on 30, so G7a was defined on all 30.
  - These are design quantities; no output of the system under test is used.
- **Why they score.**
  - On I they agree with the oracle (full = enc). So they have the oracle's fidelity and consistency, deviation 0, and
    uncertainty 0, and they are feasible wherever the oracle is, that is, wherever G7a is defined.
  - echo+F's new_true is the share of false atoms in H, and echo+T's is the share of true atoms in H. new_false is
    below 1 for both.
- **Consequence.** A HOLDS would print "G7a holds: The wisdom criterion gives no degenerate strategy a positive score",
  a sentence that is false in these worlds.
- **The §2 sentence is also inexact.**
  - Only echo, all_unknown and all_both fail by definition.
  - all_true and all_false fail through the calibrated τ_d and τ_s.
  - Over 40 development calibration draws, τ_d ranged from 0 to 4/59.

**Fix** (the author decides; AQ2's claim text changes).
- Narrow the claim in §1, §3.2, `aggregate.CLAIMS` and the study name. For example: "None of the five degenerate
  baselines of SPEC §10 (echo, all_true, all_false, all_unknown, all_both) gets a positive score under the criterion."
- Add to §2: "The criterion does not exclude degenerate strategies in general: keeping enc on I and setting every other
  atom to F (or T) is feasible wherever the oracle is, and scores > 0 on development worlds."
- If the general claim is wanted, add echo+F and echo+T to G7a's baselines. Say in §2 that G7a is then expected to FAIL.
- Replace "by their definitions" with "by their definitions (echo, all_unknown, all_both) or through the calibrated
  τ_d and τ_s (all_true, all_false)".

### Major

#### R2-2 (major). The runner does not bind the run to the frozen tree or to the drawn salt; after a code change it accepts the old salt

**Where:**
- `audit/run_v02.py:112-118` (`add_commit` returns the oldest commit that added the file), `:144-159`, `:162-166`,
  `:426-430`;
- PREREG §8 steps 8, 9 and 11 (l.311-334);
- `tests/test_audit_runner_fidelity.py:266, 319`.

**Quote:** "Any change to the code after that is a new version, with a deviation note, a new freeze and a new salt"
(step 11); "the commit that added `FREEZE_v0.2.json` is on the remote branch" (step 9).

**Reason.**
- **The verified manifest is not tied to the freeze commit.**
  - `verify_freeze` checks the manifest in the working tree against the files in the working tree.
  - Nothing checks that the manifest or the frozen files are committed, or that they equal their content in the
    freeze commit. `check_committed_clean` is applied to SALT.json and TAU.json, not to the manifest.
- **The freeze commit is the oldest add commit.** `add_commit` takes the oldest commit with status A. A manifest that
  is rewritten later (status M, or deleted and re-added) still maps to the first freeze commit.
- **The salt is not bound to the core hash.** SALT.json does not record the core hash, and the runner compares the salt
  with nothing.
- **Consequence.**
  - Edit the code, rewrite the manifest (even without committing it), recalibrate and commit a new TAU.json. The runner
    accepts the old salt.
  - The new core hash gives new seeds, and so a new set of test worlds. This is the forking path that step 11 forbids.
  - Conversely, the legitimate path is refused while the manifest path is unchanged: a new freeze commit with a new
    SALT.json that names it fails "does not name the freeze commit".
- **A modified SALT.json is accepted.** Only the file's first add commit is checked. The test at l.319 commits such a
  modification and is refused only because the new salt is not hex.
- **"On the remote branch" is a local ref.** The check reads the local ref `origin/main`, and the tests create it with
  `git update-ref` (l.266), so no push is needed. The push of TAU.json is not checked.
- **The salt's provenance is unchecked.** The runner cannot know who drew the salt, and no post-run check is
  pre-registered.
- **The checklist requires this.** "Every step that must come before the data … is enforced by the runner."

**Fix.**
- Record `core_sha256` in SALT.json. Refuse unless it equals the core hash of the verified manifest.
- Refuse unless the manifest and every frozen file are committed, unmodified, and identical to their content in the
  freeze commit: `git diff --quiet <freeze> -- <paths>`, and an empty `git status --porcelain` for them.
- Refuse unless exactly one commit touches each of the manifest, SALT.json and TAU.json. Or define the freeze commit as
  the last commit that touches the manifest, and refuse any later change.
- Pre-register a post-run check by the Independent session:
  - SALT.json's salt and freeze commit equal those it drew and recorded at the time;
  - the freeze, salt and TAU commits are on the public remote, verified there.
- Say in §8 that the runner sees only the local remote-tracking ref.

#### R2-3 (major). T-1's description and fixed sentence depend on the calibration draw, and a HOLDS can come from the draw alone

**Where:**
- PREREG §1 l.21-23, I-5 l.175, §4 l.156-157, §2 l.71;
- `audit/aggregate.py:36-39`;
- CHECKLIST: "Directional hypotheses are identified".

**Quote:** "In these worlds this compares the window α 0.65–0.80, where only class atoms change, with the regime where
the 0.60 source is admitted."

**Reason.**
- **The sentence's premise depends on the draw.** It is fixed text. Its premise, that no α ≥ 0.85 is feasible, holds
  under the development τ but not under every D1 draw.
- **Design study.** 40 calibration draws of 10 development worlds each, evaluated on the same 30 development test
  worlds.
  - In 15 draws, some test world had a feasible α ≥ 0.85, the regime where the 0.80 source is excluded.
  - In 4 draws this held on 6, 15, 24 and 27 of the 30 worlds.
  - Across the draws, τ_b ranged 0.504–0.804, τ_s 0.769–0.889, τ_t 0.951–0.987, and τ_d from 0 to 4/59.
- **The sentence then misdescribes the test.** When α 0.85 is feasible, T-1 also compares pairs across the 0.80-source
  boundary.
- **A tight draw alone can produce HOLDS.**
  - §2 says that T-1 is mostly decided by whether the bounds admit α ≤ 0.60, and those bounds move a lot with the draw.
  - So a tight draw could produce HOLDS on most defined worlds, whatever trade-off the system has.
  - This is the checklist's directional-hypothesis item: a generic factor that produces the predicted direction. §10
    does not address it.
- **The structure arm is not next to the verdict.** It is listed per world in the descriptive output only.

**Fix.**
- Print next to the T-1 verdict, from `t1_structure`:
  - the number of defined worlds with some α ≤ 0.60 feasible;
  - the number with some α ≥ 0.85 feasible;
  - the window and crossing outcomes.
- Make the sentence computed, not fixed: "On <a> of <n> defined worlds the feasible set reached α ≤ 0.60; on <b> it
  reached α ≥ 0.85."
- Add a caveat to the HOLDS sentence: "A HOLDS can result from bounds that exclude the 0.60 source on most worlds."
- Write the directional-hypothesis item in §10.

#### R2-4 (major). The power and definedness statements contradict each other, and the expected-verdict paragraph leaves out "insufficient worlds"

**Where:** PREREG §7 l.278-282; §2 l.50; §2 l.53-58; `audit/aggregate.py:40-45`.

**Quote:** "On development worlds 3–4 of 30 were UNDEFINED, which means about 26–27 defined worlds. There,
P(HOLDS | 0.95) is about 0.61."

**Reason.**
- **§7 contradicts §2.** §2 (draft 4) says that definedness depends strongly on the calibration draw (11 and 17 of 20).
  §7 keeps review 1's single-draw figure.
- **Design study** (the same 40 draws and 30 worlds as in R2-3):
  - T-1 was defined on 10–30 worlds, median 22;
  - fewer than 16 defined ("insufficient worlds") in 2 of the 40 draws;
  - 16–19 defined in 6 more draws, where every defined world must hold and P(HOLDS | 0.95) is 0.38–0.44;
  - worlds with no feasible point: 0–17, median 6;
  - the default (0.7, 5) was feasible on 6–25 of 30 worlds, median 17.
- **"Insufficient worlds" is a realistic T-1 outcome.**
  - P(HOLDS | r) averaged over draws is below the n = 30 figure: 0.70 at n = 22, at most 0.44 for 16–19.
  - The expected-verdict paragraph printed next to T-1 names only FAIL.
- **§2 is wrong about G7a.** "G8 and G7a do not use feasibility" is wrong for G7a: its baseline rule and its UNDEFINED
  rule use feasibility. It is robust in practice, though: the oracle was feasible on 30 of 30 worlds in every draw.

**Fix.**
- Replace l.279-280 with the draw dependence: the range above, P(insufficient), and P(HOLDS | r) averaged over
  calibration draws. A short simulation on development draws, as in the appendix, is enough.
- Add to the expected-verdict paragraph: "T-1 may also end in 'insufficient worlds'."
- Correct the 16–19 row: r = 0.90 → 0.14–0.19, r = 0.80 → 0.01–0.03.
- Correct the §2 sentence: "G8 does not use feasibility; G7a's definedness uses the oracle's feasibility."

#### R2-5 (major). The pre-registered I-6 arm counts multi-atom changes as single-atom changes

**Where:**
- `audit/descriptive.py:256-259` (`g8_single_atom_only`);
- `audit/exact.py:140-146` (`encode_pairs`);
- `tesaron/criterion/metrics.py:152-161` (`Fraction` reduces to lowest terms).

**Quote:** `if bad_f and drop * int(fid[i, j, 1]) > 1:  # the raw denominator is the number of atoms of I`

**Reason.**
- **The stored denominator is reduced.** Fractions are stored in lowest terms, so the stored denominator is |I| / gcd,
  not |I|. A value of 0 has a stored denominator of 1.
- **Two-atom changes are counted as one.** On synthetic G8 data (`i6_check.py`), both of these return True
  ("single-atom only"):
  - a deviation rise from 0 to 2/40, stored as 1/20;
  - a fidelity drop from 11/18 to 9/18, stored as 1/2.
- **Consequence.** The reported "g8_failing_only_through_single_atom_changes" (VERDICTS) would be inflated. That
  favours the reading that G8 fails only through single atoms.

**Fix.**
- Pass the raw denominators from `collect_g8` as integer arrays: |I| and the number of decided encoded atoms per α
  (neither depends on k). Compute the change in atoms from them.
- Add unit tests with 2/40 and 9/18.

#### R2-6 (major). Abduction, the relation units and the interface facts have no independent check, though §6.1 claims one for every verdict path

**Where:**
- PREREG §6.1 l.182;
- `audit/fidelity.py:139-145` (the pass-2 input is built from `out.hypotheses`);
- `tesaron/decoder/abduction.py:29-81`;
- the relation units in `tesaron/encoder/core.py`;
- `tesaron/belnap/interface.py:38-55`.

**Quote:** "These are independent implementations of the code paths that decide verdicts."

**Reason.**
- **Abduction is checked nowhere.**
  - F1 recomputes pass 2 from the decoder's own hypotheses.
  - No independent code checks which candidates exist, their scores, the ranking, or the top-k cut.
  - F3 receives the decoder's full and verdict lists, so it inherits them.
- **This matters for the primary test.** G8 compares fidelity and deviation at k > 0 with k = 0, and the k > 0 outputs
  come from exactly this step. G6's definedness depends on it too.
- **The relation units and the interface facts are not recomputed either.**
  - The relation units' degrees are the max support of the positive and of the negative reports in D_derive.
  - The interface facts are the Belnap table at α.
  - F4 covers only PCM and the class μ⁺.

**Fix.**
- Add to `audit/indep` a brute-force candidate enumerator that follows SPEC §7.3:
  - ground each rule over all entity assignments;
  - the head is an OBSERVED fact;
  - exactly one body literal is missing, it is ground and in the vocabulary, and its atom is U;
  - score = the number of distinct (rule, θ); rank by score, then by (channel, pred, args).
- Compare the full ranked list at every (α, k > 0) in F1.
- Recompute the relation units and the interface facts independently.
- Or narrow the §6.1 sentence to the paths that are actually covered.

#### R2-7 (major). F3 is not yet operational: no frozen comparison script, an undefined resolution rule, and inputs that do not cover the whole verdict table

**Where:** PREREG §6.1 F3 row l.188; §8 step 12; `audit/run_v02.py:216-259`. There is no comparison script in `audit/`.

**Quote:** "compared by a script after the agent has written its results"; "no verdict for the affected tests until it
is resolved".

**Reason.**
- **No comparison script exists.** It would be written after the run, with the run's numbers visible. What counts as a
  disagreement (which fields, what equality) would then be a free choice.
- **"Until it is resolved" is undefined.** Repairing the run's code conflicts with §8 step 11. A second F3 agent is not
  described. Either path would be chosen after the fact.
- **The input does not cover the whole table.** The scope includes "the verdict table", but the blind input has no
  G1–G6 outcomes.
- **The F3 instruction and output format are not fixed.**

**Fix.**
- Before the freeze, write and freeze `audit/f3_compare.py` (the fields compared, exact equality of the p/q strings,
  the output) and the F3 instruction and output schema.
- Pre-register the resolution:
  - a disagreement that traces to the run's code means no verdict for the affected tests in this version (a new
    version, a new freeze, a new salt);
  - one that traces to the agent means a second fresh agent recomputes, and both are reported.
- For the verdict table, give the agent the G1–G6 per-world outcomes after the blind part.

### Minor

#### R2-8 (minor). Stale text in frozen and repository files

**Where:**
- SPEC §11 l.372-373 (seeds "from the freeze-manifest hash", no salt; SPEC is frozen);
- SPEC §1 l.34, and SPEC's title "for v0.1";
- PREREG §2 l.44 "S-1–S-6" (S-7 exists);
- `prereg/README.md` l.4-6 (still a placeholder);
- the docstring at `audit/system.py:237` ("S-1..S-6").

**Fix.** Update these texts. Say in §9 whether `prereg/README.md` is frozen.

#### R2-9 (minor). Printed claims and gate study names differ from §3.2

**Where:**
- `aggregate.py:16, 18`: the G2 and G4 claims drop "(same machine, same NumPy build)" (R1-14);
- `aggregate.py:17`: G3 drops "(necessity)";
- `g5_study.py:35` "pattern computation does not leak into validation data", the wording R1-18 corrected;
- `g3_study.py:35` "meaning units are grounded in data".

**Fix.** Align them. The study names change the module hash, so do this before the planned `certify all --verify`.

#### R2-10 (minor). Ordering and index details

**Where:**
- §8 step 7 (l.308) records the salt in FREEZE_RECORD.md at the freeze, but the salt is drawn in step 8;
- §7 l.260 says "i is the draw index", but perm uses 3i + p (`seeds.py:6`, `per_world.py:36-38`).

**Fix.** Record the salt in step 8. State perm's index in §7.

#### R2-11 (minor). Partial outputs on a crash, and no procedure for the byte-for-byte rerun

**Where:** `run_v02.py:342-349`, `:170-172`; §8 step 11.

**Reason.**
- **Partial outputs.** Per-world files with fixed outcomes are written inside the loop. A crash leaves the outcomes of
  the earlier worlds on disk.
- **No rerun procedure.** Real mode writes only to `run/` and refuses to overwrite, so the rerun has no stated procedure
  (where it runs, and on which machine).

**Fix.**
- Write the per-world files after the loop, or into a temporary folder that is renamed at the end.
- State that the reproduction runs in a fresh clone of the result commit, on the machine whose platform string is
  recorded in FREEZE_RECORD.md. Commit VERDICTS.json at once.

#### R2-12 (minor). Gate-tool and freeze hygiene

**Where:** `certify.py:242-247`; `audit/freeze.py:41-54`; §6.3 l.242-243.

**Reason.**
- Nothing checks GATE_TOOL.json against the frozen tree. All 82 hashes match today; I checked them here.
- The tag check `git diff --quiet v0.5.1 -- …` ignores untracked files.
- The freeze walk includes git-ignored files that exist locally, such as `*.quick.cert.json`. A fresh clone lacks them,
  so verifying the clone would fail.

**Fix.**
- At the freeze, check that `GATE_TOOL["files"]` equals the current hashes.
- Add `git status --porcelain --untracked-files=all -- truth_gate kapi protocol` to the tag check.
- Freeze from a clean checkout.

#### R2-13 (minor). G1 details

**Where:** `checks.py:107-112`; §3.2 G1 row.

**Reason.**
- **(ii) is weaker than its claim.** It checks only "encoded F at α₀", while the claim is that μ⁻ is never derived from
  μ⁺. A twin with μ⁻ = μ⁺/2 would pass.
- **The FAILS sentence does not say which part failed.** If the anchor (iii) fails, the report would read as if
  membership degrees had been turned into probabilities. The risk is low: on 30 development worlds, the lowest
  per-world median own-class typicality was 0.720.

**Fix.**
- Make (ii) "every class unit has μ⁻ = 0" (SPEC §5).
- Record which part of G1 failed in the check data and in the FAILS sentence.

---

## Readiness

**Not ready to freeze in this state.**

What is needed first:
- **The author decides R2-1.** Either narrow G7a's claim, or widen its baselines and expect a FAIL.
- **Six major repairs, R2-2 to R2-7.** Four of them change frozen code: the runner's commit and salt checks, the I-6
  arm, an independent abduction check, and an F3 comparison script. After that, run the unit tests again, re-certify
  (the study names change), and regenerate GATE_TOOL.json.

Once those are fixed, the draft is ready to freeze. The minor findings can be repaired in the same pass. A short
targeted re-check of the changed runner checks and the new F-control code is advisable.

The repairs of review 1 are otherwise carried out carefully. The machinery matches the text closely, all nine
certificates are FALSIFIABLE and current, and the exact arithmetic is sound.

What the run can still show is narrow, and the text should keep saying so:
- G1–G7a are decided by construction;
- G8 is close to a zero-tolerance test;
- T-1 depends mainly on whether the calibrated bounds admit the 0.60 source, and those bounds vary strongly between
  calibration draws;
- both primary tests are expected to FAIL, and T-1 may end in "insufficient worlds".

---

## Appendix: commands and results

**Setup.**
- Interpreter: `C:\Users\user\AppData\Local\Python\pythoncore-3.14-64\python.exe` (Python 3.14.2, NumPy 2.4.1).
- Environment: `TRUTH_GATE_DIR=<task>/truthgate`, `TESARON_SKIP_GIT_TESTS=1`, `PYTHONDONTWRITEBYTECODE=1`.
- Copy: `repo/` was copied to `out/scratch/repo` and made writable. My scripts are in `out/scratch/scripts/` and the
  logs in `out/scratch/`.
- Not run: the gate, `certify.py`, git, and `run_v02.py` without `--dev`. I did not create `run/`.

**Results.**

1. **Unit tests:** `python -m unittest discover -s tests` (in the copy).
   - Result: `Ran 236 tests … OK (skipped=9)`, that is 227 OK and 9 skipped, as the designer reported.
   - The skipped git tests started no git process. The dev end-to-end test wrote `run_dev/`; I did not read its verdict
     files.
2. **Certificates and GATE_TOOL:** `python -I scripts/cert_summary.py repo/audit/gate`.
   - All nine certificates are FALSIFIABLE, in full mode, with tool 0.5.1, NumPy 2.4.1 and Python 3.14.2.
   - Every body hash verifies, and every `module_sha256` matches its study file.
   - GATE_TOOL.json: verdicts and body hashes match, and verify exit is 0 for all nine. Its 82 file hashes all match the
     current `audit/` and `tesaron/`; none is missing or unrecorded.
   - G7: the minus `changed_keys` is `['base_feasible']`, with 0 UNDEFINED.
   - T-1 has the informational flags `K1_ABSTAINED` (18 of 100 plus samples and 24 of 100 minus samples abstain). The
     plus and minus streams draw different worlds.
3. **Wilson thresholds and power:** `python -I scripts/wilson_power.py`.
   - HOLDS needed: n for n = 16–19, n − 1 for 20–27, n − 2 for 28–30.
   - The §7 rows for n = 30, 28, 27, 26, 24 and 20 are reproduced.
   - Row 16–19: 0.377–0.440, 0.135–0.185, 0.046–0.074, 0.014–0.028.
   - The smallest float margin of the Wilson bound to 0.80 is 9.1e-4.
   - P(HOLDS | 12/17, n = 30) = 0.0026.
4. **I-6 arm on synthetic data:** `python -I scripts/i6_check.py`. The two-atom changes 0 → 2/40 and 11/18 → 9/18 both
   return "single atom only" = True.
5. **Further degenerate strategies:** `python -I scripts/hybrid_baselines.py repo 30`.
   - Setup: 30 development worlds (dev "world-test" mapping) under the gate τ = (41/50, 1/47, 65/66, 98/165).
   - The oracle was feasible on 30. echo+F had a feasible positive score at some α on 29, and echo+T on 30.
   - The lowest per-world median own-class typicality (G1 anchor) was 0.720.
6. **Calibration-draw study:** `python -I scripts/definedness3.py repo 40 30` (also `definedness.py` and
   `definedness2.py`, same draws).
   - Setup: 40 draws of 10 valid development calibration worlds (rng seed 20261122, world seeds disjoint from the test
     pool), evaluated on the same 30 development test worlds.
   - T-1 defined: 10–30 worlds, median 22. Per-draw counts: 10, 14, 17, 17, 17, 18, 19, 19, 20 ×5, 21 ×6, 22 ×3,
     23 ×3, 25 ×4, 26 ×6, 27 ×2, 28, 29, 30.
   - No feasible point: 0–17 worlds, median 6. Default feasible: 6–25, median 17. G7a defined: 30 of 30 in every draw.
     G8 defined (does not depend on τ): 30.
   - Some α ≥ 0.85 feasible: on no world in 25 draws, and per draw 1, 1, 2 ×9, 6, 15, 24, 27 in the other 15.
   - τ ranges: τ_s 0.769–0.889, τ_t 0.951–0.987, τ_b 0.504–0.804. τ_d ranged from 0 (in 2 draws) to 4/59, and was
     above 1/20 in 3 draws.
   - No T-1 or G8 outcome was computed.
7. **Timing:** `python -I scripts/timing.py`. One world: generation and encoding 1.05 s, the 30-point grid 0.33 s.
