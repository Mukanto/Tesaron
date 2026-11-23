# Blind review 2 (targeted) of a pre-registration and its code: Tesaron v0.3, draft 2

You are an independent reviewer. You did not write this pre-registration or this code, and you have not seen any
discussion of them except the earlier blind review in `review1/`. Work only with the files in this task folder.

**Running code.** You may run Python, but only with this interpreter:
`C:\Users\user\AppData\Local\Python\pythoncore-3.14-64\python.exe` (Python 3.14.2, NumPy 2.4.1).
- Run it only on a scratch copy inside `out/scratch/`. Copy `repo/` there first and make the copy writable.
- When you run anything, set these environment variables:
  - `TRUTH_GATE_DIR` to this folder's `truthgate/` directory;
  - `TESARON_SKIP_GIT_TESTS=1`, so that the tests that need git are skipped;
  - `PYTHONDONTWRITEBYTECODE=1`.
- Run the v0.3 runner (`audit/v03/run_v03.py`) only with `--dev-redacted`, with its output folder inside `out/scratch/`.
  Do not run `calibrate`, `test` or `reproduce` in real mode, and do not create `run/`.
- Do not run `audit/v03/gate/certify.py`, `audit/v03/prefreeze_check.py`, `audit/v03/clone_verify.py`, or anything else
  that calls git. The certificates are given as files.
- The designer ran the suite in the original repository: 572 passed (504 subtests). On a copy of this folder's `repo/`
  with `TESARON_SKIP_GIT_TESTS=1`: 522 passed, 50 skipped (504 subtests), in about 4.5 minutes.

## What you review

- **`repo/prereg/PREREG_v0.3.md`:** draft 2, not frozen. Its §10 ends with a table, "Repairs after blind review 1",
  listing how each finding of review 1 was handled. The author decided R1-1 (T-1's tolerance is max(δ, 1/n_q)). Do not
  judge that decision; judge whether the text and the code carry it out correctly.
- **`review1/REVIEW1.md` and `review1/REVIEW1.json`:** the first blind review, of draft 1.
- **The code:** `repo/audit/v03/`, `repo/audit/design/v03_*.py`, `repo/prereg/v03/*.json`, `repo/tests/test_v03_*.py`.
  `repo/SPEC_v0.3.md` and `repo/SPEC.md` are the specs. The gate certificates in `repo/audit/v03/gate/*.cert.json`
  were regenerated after the repairs.

## Context files (read what you need)

- **`repo/REPORT_v0.2.md` and `v02_postrun_audit/`:** the closed predecessor and its audit findings A1–A11.
- **The gate and the protocol:** `truthgate/docs/GATE.md`, `truthgate/protocol/PROTOCOL.md`,
  `truthgate/protocol/CHECKLIST.md`.

## What to do

1. **Check the repairs.** For every finding of review 1 (R1-1 … R1-16), decide whether draft 2 and the code fixed it:
   fixed / partly fixed / not fixed / made worse. Give the evidence: the section, or the file and line.
2. **Look for new defects that the repairs introduced,** and for anything review 1 missed in the parts the repairs
   touched. At least:
   - T-1's one-atom floor: is n_q counted exactly as SPEC §8's denominator of new_false? Is the floor applied exactly
     where §3.2 says (main T-1, draw sensitivity, I-2, I-6, I-7) and not in I-8 and I-9? Does F3 recompute n_q?
   - the new arms I-8 (v0.2's full rule) and I-9, and the I-8 τ in the calibration step and its recheck;
   - the NT twin at 0.5, in the gate and in Layer 2;
   - the G7a sentence and the T-1 HOLDS and FAILS sentences of §4, against the code;
   - the all_true study and the numbers it backs in §2;
   - the pre-freeze check: the certificate requirements, the waiver file, the SPEC_v0.3 status line, the study list;
   - the draw-sensitivity set that has no τ;
   - the redaction boundary, extended to I-8 and I-9 ("no pilot", §2);
   - the regenerated certificates: do they match the current study files?
3. **Readiness.** Is draft 2 ready to freeze once your blocking and major findings are fixed?

## Output

Write two files to `out/`:

- **`REVIEW2.md`:**
  - **Part A:** a table of the 16 review-1 findings, with the status and evidence for each.
  - **Part B:** the new findings, ordered by severity. Each one has:
    - an id (R2-1, R2-2, …);
    - the passage: the section and a quote, or the file and line;
    - the reason;
    - a concrete fix.
  - Severity levels:
    - **blocking:** do not freeze in this state;
    - **major:** fix before the freeze;
    - **minor:** clarity.
  - Start with the counts. End with a short readiness judgment.
  - If you ran code, list the commands and their results in an appendix.
- **`REVIEW2.json`:** `{"repairs": [{"id", "status", "evidence"}], "counts": {...}, "findings": [{"id", "severity",
  "where", "quote", "reason", "fix"}], "readiness": "..."}`.

## Rules

- Read and write only inside this task folder, except for the one interpreter named above. No network, no git, no other
  agents.
- Do not edit the inputs. Work on copies in `out/scratch/`.
- **Blindness.** On any v0.3 world, development worlds included, do not compute, print or report any of:
  - new_false or new_true values;
  - any T-1 or G8 outcome or HOLDS count;
  - T-1's structure fields beyond the feasible α set;
  - the draw-sensitivity, I-2, I-6, I-7, I-8 or I-9 outcomes.

  Design quantities are fine: feasibility, τ, definedness, the denominators n_q, the G1–G7a outcomes, the all_true arm,
  twin outcomes other than T-1's, and baseline scores. If you see a forbidden value by accident, say so without
  repeating it.
- Be concrete. Say "unclear" when you cannot decide. Do not pad.
