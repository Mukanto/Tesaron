# Targeted blind review 3 of a pre-registration and its code: Tesaron v0.2 (draft 5)

You are an independent reviewer. You did not write this pre-registration or this code. You have not seen any discussion
of them except the two earlier reviews in `review1/` and `review2/`. Work only with the files in this task folder.

This is a **targeted** review. Review 2 found 1 blocking, 6 major and 6 minor defects (R2-1 … R2-13). Draft 5 and its
code are meant to repair them. Your job is to check those repairs and the new code they added, not to review the whole
design again.

**Running code.** You may run Python, but only with this interpreter:
`C:\Users\user\AppData\Local\Python\pythoncore-3.14-64\python.exe` (Python 3.14.2, NumPy 2.4.1).
- Run it only on a scratch copy inside `out/scratch/`. Copy `repo/` there first and make the copy writable.
- When you run anything, set these environment variables:
  - `TRUTH_GATE_DIR` to this folder's `truthgate/` directory;
  - `TESARON_SKIP_GIT_TESTS=1`, so that the tests that need git are skipped instead of starting git;
  - `PYTHONDONTWRITEBYTECODE=1`.
- Do not run `audit/run_v02.py` without `--dev`, and do not create `run/`.
- Do not run `audit/gate/certify.py` or `audit/prefreeze_check.py` (they call git); the certificates are given as files.
- The suite's development end-to-end test writes `run_dev/` in your copy. Do not read its verdict files.
- The designer ran the suite in the original repository: 319 tests OK; with `TESARON_SKIP_GIT_TESTS=1`, 319 tests OK
  with 23 skipped.

## What you review

- **`repo/prereg/PREREG_v0.2.md`:** draft 5, not frozen. §10 maps each finding of review 2 to its change. The author's
  decisions AQ4 (G7a's claim narrowed) and AQ5 (T-1's design unchanged, reporting strengthened) are in §7 and §10.
- **The code that changed for draft 5,** mainly:
  - `repo/audit/run_v02.py` (the binding of the run to the freeze commit and the salt; outputs written after the loop;
    the F3 fields and the blind input);
  - `repo/audit/indep/abduction.py`, `repo/audit/indep/units.py` and `repo/audit/fidelity.py` (F1 and F4);
  - `repo/audit/f3/` and `repo/audit/f3_compare.py` (F3);
  - `repo/audit/prefreeze_check.py` and `repo/audit/gate/certify.py` (freeze hygiene);
  - `repo/audit/descriptive.py`, `repo/audit/checks.py` and `repo/audit/aggregate.py` (I-6, T-1 structure, G1,
    the printed wording);
  - `repo/audit/design/draw_study.py` and `repo/prereg/DRAW_STUDY.json` (the calibration-draw study behind §7);
  - `repo/prereg/F4_PREFREEZE.json`, the regenerated certificates and `repo/audit/gate/GATE_TOOL.json`;
  - SPEC §15 S-8 and S-9.
- **`review2/REVIEW2.md` and `review2/REVIEW2.json`:** the review whose findings were repaired.

## Context files (read what you need)

- `repo/README.md`, `repo/SPEC.md`, `review1/REVIEW1.md`.
- `truthgate/docs/GATE.md`, `truthgate/protocol/PROTOCOL.md`, `truthgate/protocol/CHECKLIST.md`.

## What to do

1. **Check the repairs.** For every finding of review 2 (R2-1 … R2-13), decide whether draft 5 and the code fixed it:
   fixed / partly fixed / not fixed / made worse. Give the evidence (section, or file and line). For R2-1 and R2-3,
   judge whether the text and the code carry out the author's decisions AQ4 and AQ5 correctly and honestly; do not
   judge the decisions themselves.
2. **Look for new defects in the changed code and text.** Cover at least:
   - the runner's git checks: can a run proceed with a frozen tree, salt, calibration or τ that is not the one
     committed and pushed in the stated order, or is a legitimate run refused?
   - the independent enumerator and units: do they follow SPEC §5–§7.3 literally, and are they independent of the code
     they check?
   - F3: can the instructions, the schema and the comparison script be followed without a free choice, and does the
     comparison cover every field a verdict uses?
   - the pre-freeze check: does it catch a frozen tree that a fresh clone would not reproduce?
   - text against code: every printed sentence of §4 against `aggregate.py`.
3. **Readiness.** Is the pre-registration ready to freeze once your blocking and major findings, if any, are fixed?

## Output

Write two files to `out/`:

- **`REVIEW3.md`:** start with counts. Part A: a table of R2-1 … R2-13 with status and evidence. Part B: new findings,
  ordered by severity (blocking / major / minor), each with an id (R3-1, …), the passage, the reason and a concrete
  fix. End with a short readiness judgment. If you ran code, list the commands and results in an appendix.
- **`REVIEW3.json`:** `{"repairs": [{"id", "status", "evidence"}], "counts": {...}, "findings": [{"id", "severity",
  "where", "quote", "reason", "fix"}], "readiness": "..."}`.

## Rules

- Read and write only inside this task folder. No network, no git, no other agents.
- Do not edit the inputs. Work on copies in `out/scratch/`.
- **Blindness:**
  - Do not compute or report the fixed system's per-world outcomes, or any HOLDS counts or rates, for G8 or T-1 on any
    world. Do not compute on development worlds whether some α ≤ 0.60 is feasible.
  - Design quantities are fine: feasibility, denominators, definedness, twin outcomes, baseline scores.
- Be concrete. Say "unclear" when you cannot decide. Do not pad.
