# Blind post-run audit: Tesaron v0.2

You are an independent auditor of a pre-registered computational study. You did not design it. Your job is to find
defects that could change the study's verdicts or the honesty of its report, and to say how each one would fail.

The audit has **two parts, in this order.** Write Part 1 completely, to `out/PART1.md`, **before you open anything in
`part2/`.** Do not change `out/PART1.md` after you have opened `part2/`; put any later thoughts into Part 2.

**Running code.** You may run Python, but only with this interpreter:
`C:\Users\user\AppData\Local\Python\pythoncore-3.14-64\python.exe` (Python 3.14.2, NumPy 2.4.1).
- Run it only on scratch copies inside `out/scratch/`. Make the copies writable.
- Set `PYTHONDONTWRITEBYTECODE=1`. Set `TESARON_SKIP_GIT_TESTS=1` if you run the unit tests.
- Do not run `audit/gate/certify.py`.
- Part 1's copy lacks the gate certificates and GATE_TOOL.json, so the unit tests and checks that read them fail
  there; that is expected and is not a finding.

## Part 1: the study, without its results

**Files you may read in Part 1:** everything in `part1/` and `truthgate/`. `part1/repo/` is the study's repository at
the frozen state, without its run outputs, its gate certificates, its earlier reviews and its freeze record.

**Do not read in Part 1:** anything in `part2/`.

Examine, following `truthgate/protocol/templates/BLIND_AUDIT_PROMPT.md` (sections "What to examine" 1–6):
1. **Criteria.** Can each criterion (G1–G8, T-1; PREREG §3.2) hold and fail? Is any decided by definitions? Does each
   do what its pre-registered claim says? Is UNDEFINED handled as the pre-registration says?
2. **Worlds.** Are the synthetic worlds adequate for what they are used to show?
3. **Fidelity.** Is every code path that decides a verdict compared with an independent implementation (PREREG §6.1)?
4. **Controls.** Can every faulty twin (PREREG §6.2) make its test fail? Could any pass vacuously?
5. **Does the verdict follow?** Does every outcome pattern map to exactly one verdict (PREREG §3.3, §4)? Do the
   interpretations (§5) change a verdict?
6. **Arbitrary choices.** Which tolerances, thresholds and grid points decide a verdict, and would a reasonable
   alternative have given another one?

The study has had three blind reviews before the freeze; you do not see them. Report what you find yourself.

## Part 2: the results, the report and the provenance

Only after `out/PART1.md` is written, open `part2/`. It holds:
- `part2/run/`: the run's outputs as committed (calibration, test worlds, per-world inputs and results, verdicts, the
  F3 comparison and the F3 agent's files, the run record);
- `part2/FREEZE_RECORD.md`: the freeze record;
- `part2/REPORT_v0.2_DRAFT.md`: the draft report.

Examine:
1. **The report against the results.** Does the draft report state every verdict, count, bound and descriptive value
   exactly as in `part2/run/VERDICTS.json`? Are the fixed sentences verbatim? Is every verdict the one PREREG §3.3 and
   §4 give for those counts? You may recompute the verdict table from the per-world outputs.
2. **Honesty of the report.** Does any sentence claim more than the results and the pre-registration allow? Is anything
   the pre-registration requires missing (PREREG §8 step 13: the table, the fixed wording, the expected-verdict
   paragraph, the limitation sentence)? Are the deviations complete?
3. **Provenance.**
   - **The salt.** Compare `part2/run/SALT.json` with the salt record that your own session wrote when it drew the
     salt: `E:\Independent\tasks\tesaron_v02_salt\SALT_RECORD.json`. You may read that one file outside this folder.
     The salt, the freeze commit and the core hash must be equal.
   - **The public repository.** Clone `https://github.com/Mukanto/Tesaron.git` into `out/scratch/clone/`. This clone
     is the only network access and the only git use allowed in this task. In the clone, check:
     - that `prereg/FREEZE_v0.2.json` verifies (`python -m audit.freeze verify prereg/FREEZE_v0.2.json`) and is touched
       by exactly one commit;
     - the commit order: the freeze commit, then the commit that adds `run/SALT.json`, then the one that adds
       `run/CAL_WORLDS.json` and `run/TAU.json`, then the one that adds the test outputs; each run file touched by
       exactly one commit; each commit a descendant of the one before (`git log --full-history`,
       `git merge-base --is-ancestor`);
     - that the files in `part2/run/` that are committed in the clone are byte-identical to the clone's copies.
   - Say which of these checks you could and could not do.

## Output

Write to `out/`:
- **`PART1.md`** (before Part 2) and **`PART2.md`**: each a table, one row per finding, sorted by severity, in the format
  of `BLIND_AUDIT_PROMPT.md` (Id, Severity, Location, Claim, Failure scenario, Verdict impact). Use ids A1, A2, … in
  Part 1 and B1, B2, … in Part 2. After each table, list what you checked and found sound, one line each.
- **`AUDIT.json`:** `{"part1": [{"id", "severity", "location", "claim", "failure_scenario", "verdict_impact"}],
  "part2": [...], "provenance": {"salt_matches": true/false/null, "clone_freeze_verifies": ..., "commit_order_ok": ...,
  "files_identical": ..., "notes": "..."}, "summary": "..."}`.

## Rules

- Read and write only inside this task folder, except the one salt record named above and the one public clone.
- No other agents. Do not edit the inputs.
- Do not propose fixes unless a finding needs one to be understood; a proposal is not an approval by the author.
- Be concrete. Say "unclear" when you cannot decide. Do not pad.
