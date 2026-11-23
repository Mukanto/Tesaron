# Blind review 1 of a pre-registration and its code: Tesaron v0.3

You are an independent reviewer. You did not write this pre-registration or this code, and you have not seen any
discussion of them. Work only with the files in this task folder.

**Running code.** You may run Python, but only with this interpreter:
`C:\Users\user\AppData\Local\Python\pythoncore-3.14-64\python.exe` (Python 3.14.2, NumPy 2.4.1).
- Run it only on a scratch copy inside `out/scratch/`. Copy `repo/` there first and make the copy writable.
- When you run anything, set these environment variables:
  - `TRUTH_GATE_DIR` to this folder's `truthgate/` directory;
  - `TESARON_SKIP_GIT_TESTS=1`, so that the tests that need git are skipped instead of starting git;
  - `PYTHONDONTWRITEBYTECODE=1`.
- Run the v0.3 runner (`audit/v03/run_v03.py`) only with `--dev-redacted`, with its output folder inside `out/scratch/`.
  Do not run `calibrate`, `test` or `reproduce`, and do not create `run/`.
- Do not run `audit/v03/gate/certify.py`, `audit/v03/prefreeze_check.py`, `audit/v03/clone_verify.py`, or anything else
  that calls git. The certificates are given as files.
- The designer ran the suite in the original repository: 529 passed (504 subtests). The designer also ran it on a copy
  of this folder's `repo/` with `TESARON_SKIP_GIT_TESTS=1`: 479 passed, 50 skipped (504 subtests), in about 4 minutes.

## What you review

- **`repo/prereg/PREREG_v0.3.md`:** the v0.3 pre-registration, a draft, not frozen. §10 lists what changed from v0.2
  and why. The author's decisions in it (A1, A3, A4 and its realisation, G7a's narrowing, G8 descriptive, 50 test
  worlds, the S-10 defaults) are not under review as decisions. Judge whether the text and the code carry them out
  correctly and honestly.
- **`repo/SPEC_v0.3.md`:** the v0.3 worlds (S-10). `repo/SPEC.md` is v0.2's frozen spec, still valid for everything
  else.
- **`repo/audit/v03/`:** the v0.3 audit layer:
  - the runner;
  - the checks, the aggregation and the redaction boundary;
  - the twins;
  - the F3 materials and `f3_compare.py`;
  - the gate studies, certificates and driver;
  - the freeze, pre-freeze and clone tools.

  It reuses parts of the v0.2 audit layer in `repo/audit/`. `repo/tesaron/` is the system under test, unchanged since
  v0.2.
- **`repo/audit/design/v03_*.py` and `repo/prereg/v03/*.json`:** the design studies S1, S1b, S2, the power study, and
  F4 before the freeze.
- **`repo/tests/test_v03_*.py`:** the v0.3 tests.

## Context files (read what you need)

- **`repo/REPORT_v0.2.md` and `repo/prereg/PREREG_v0.2.md`:** the closed predecessor.
- **`v02_postrun_audit/`:** v0.2's blind post-run audit. Its findings A1–A11 are the source of several v0.3 changes.
- **`repo/README.md`:** what the system is.
- **`truthgate/docs/GATE.md`:** the gate's reference.
- **The protocol:** `truthgate/protocol/PROTOCOL.md`, `truthgate/protocol/CHECKLIST.md` and
  `truthgate/protocol/templates/PREREG_TEMPLATE.md`.

## What to look for

Find defects that would make the results uninterpretable, biased, or weaker than claimed. Cover at least these:

1. **Pre-registration against code.**
   - Does each check implement §3.2 exactly, including thresholds, anchors and UNDEFINED conditions? In particular:
     - T-1 at k = 0 only;
     - G7a with four baselines;
     - the all_true arm;
     - G8 as descriptive only.
   - Do these match the text: the Q-40 τ rule, the I-6 and I-7 τ, the draw-sensitivity arm, the structure arm, the
     seeds and roles, world validity and replacement, the aggregation, and the fixed wording of §4?
   - Is the order freeze → salt → calibration (all τ committed) → test enforced by the code, not left to the operator?
2. **The v0.3 worlds (S-10).**
   - The reliability stream, the overlap entities and the q scaling.
   - Do they do what S-10 says?
   - Are S1, S1b, S2 and the power study computed as their docstrings say, and do they support the numbers printed in
     the pre-registration?
3. **Can each criterion fail?**
   - Is any check decided by definition or vacuous?
   - Do the anchors stop zero or noise data from holding?
   - Does each twin violate its claim?
   - Is T-1 meaningful with continuous reliabilities, or does it reduce to something trivial?
4. **"No pilot" (§2).**
   - Can any code path compute and expose new_false, a T-1 outcome or a G8 outcome on v0.3 worlds before the freeze?
     Think of the dev runner, the redaction boundary, the gate studies (the T-1 `plus` world), the design studies and
     the tests.
   - Is the redaction complete?
5. **The gate.**
   - Are the `plus` and `minus` worlds right?
   - Could a certificate be FALSIFIABLE for a reason unrelated to the claim?
   - Is the T-1 study's world selection (it draws until T-1 is defined) sound?
6. **F3.**
   - Could a fresh agent recompute everything §6.1 lists from the blind inputs and the instructions alone, τ included?
   - Is the field-to-test map of `f3_compare.py` the one in §6.1?
   - Are the "not covered" items complete?
7. **Blindness and forking paths after the freeze.** Could anything be adjusted with knowledge of results: τ, worlds,
   replacement, UNDEFINED handling, the descriptive arms, reruns?
8. **The pre-freeze and freeze tools.**
   - Do they check what §6.3 and §8–§9 say: the frozen header, the design-study reproduction, the v0.2 manifest, the
     manifest paths, and the clone verification?
9. **Power and wording** (§3.3, §4, §7).
   - Are the numbers right?
   - Is the fixed wording honest about what a verdict means?
10. **v0.2's audit findings A1–A11.** Has each been handled as §10 says?
11. **Anything else** a skeptical methods reviewer would raise. Check the protocol's checklist against the draft.

## Output

Write two files to `out/`:

- **`REVIEW1.md`:**
  - **Findings,** ordered by severity. Each one has:
    - an id (R1-1, R1-2, …);
    - the passage: the section and a quote, or the file and line;
    - the reason;
    - a concrete fix.
  - Severity levels:
    - **blocking:** do not freeze in this state;
    - **major:** fix before the freeze;
    - **minor:** clarity.
  - Start with the counts. End with a short readiness judgment: is the pre-registration ready to freeze once your
    blocking and major findings are fixed?
  - If you ran code, list the commands and their results in an appendix.
- **`REVIEW1.json`:** `{"counts": {...}, "findings": [{"id", "severity", "where", "quote", "reason", "fix"}],
  "readiness": "..."}`.

## Rules

- Read and write only inside this task folder, except for the one interpreter named above. No network, no git, no other
  agents.
- Do not edit the inputs. Work on copies in `out/scratch/`.
- **Blindness.** On any v0.3 world, development worlds included, do not compute, print or report any of:
  - new_false or new_true values;
  - any T-1 or G8 outcome or HOLDS count;
  - T-1's structure fields beyond the feasible α set;
  - the draw-sensitivity, I-2, I-6 or I-7 outcomes.

  Design quantities are fine: feasibility, τ, definedness, denominators, the G1–G7a outcomes, the all_true arm, twin
  outcomes other than T-1's, and baseline scores. If you see a forbidden value by accident, say so in the review without
  repeating it.
- Be concrete. Say "unclear" when you cannot decide. Do not pad.
