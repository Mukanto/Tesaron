# Blind review 2 of a pre-registration and its code: Tesaron v0.2 (draft 4)

You are an independent reviewer. You did not write this pre-registration or this code. You have not seen any discussion
of them except the earlier review in `review1/`. Work only with the files in this task folder.

**Running code.** You may run Python, but only with this interpreter:
`C:\Users\user\AppData\Local\Python\pythoncore-3.14-64\python.exe` (Python 3.14.2, NumPy 2.4.1).
- Run it only on a scratch copy inside `out/scratch/`. Copy `repo/` there first and make the copy writable.
- When you run anything, set these environment variables:
  - `TRUTH_GATE_DIR` to this folder's `truthgate/` directory;
  - `TESARON_SKIP_GIT_TESTS=1`, so that the tests that need git are skipped instead of starting git;
  - `PYTHONDONTWRITEBYTECODE=1`.
- Do not run `audit/run_v02.py` without `--dev`, and do not create `run/`.
- Do not run `audit/gate/certify.py` (it calls git); the certificates are given as files.
- The suite's development end-to-end test writes `run_dev/` in your copy. Do not read its verdict files.
- The designer ran the suite in the original repository: 236 tests OK, and with `TESARON_SKIP_GIT_TESTS=1`, 227 OK and
  9 skipped.

## What you review

- **`repo/prereg/PREREG_v0.2.md`:** draft 4, not frozen. §10 lists how each finding of review 1 was handled.
- **`repo/audit/`:** the audit layer. **`repo/tesaron/`:** the system under test. Its spec, `repo/SPEC.md`, includes
  the pre-freeze revisions S-1–S-7 in §15.
- **`repo/audit/gate/*.cert.json` and `repo/audit/gate/GATE_TOOL.json`:** the gate certificates, regenerated for draft
  4, and the gate tool record.
- **`repo/prereg/F4_PREFREEZE.json`** and **`repo/tests/`**.
- **`review1/REVIEW1.md` and `review1/REVIEW1.json`:** the first blind review of draft 3.

## Context files (read what you need)

- **`repo/README.md`:** what the system is.
- **`truthgate/docs/GATE.md`:** the gate's reference.
- **`truthgate/protocol/PROTOCOL.md`, `truthgate/protocol/CHECKLIST.md` and
  `truthgate/protocol/templates/PREREG_TEMPLATE.md`:** the methods protocol and its template.
- **`truthgate/truth_gate/`:** the gate's code, if you need it.

## What to do

1. **Check the repairs.** For every finding of review 1 (R1-1 … R1-22), decide whether draft 4 and the code fixed it:
   fixed / partly fixed / not fixed / made worse.
   - Give the evidence: the section, or the file and line.
   - Review 1 left two blocking findings to the author (R1-1, R1-2). The author decided them: AQ1 and AQ2 in §10. Judge
     whether the text and the code now carry out those decisions correctly and honestly. Do not judge the decisions
     themselves.
2. **Look for new defects** that the repairs introduced, or that review 1 missed. Cover at least:
   - pre-registration against code;
   - whether each criterion can fail;
   - the gate certification;
   - blindness and forking paths: the salt and commit-order checks, the τ recomputation, the stop and rerun rules;
   - exact arithmetic;
   - the independence of F1–F4;
   - power and wording.
3. **Readiness.** Is the pre-registration ready to freeze once your blocking and major findings are fixed?

## Output

Write two files to `out/`:

- **`REVIEW2.md`:**
  - **Part A:** a table of the 22 review-1 findings, with the status and evidence for each.
  - **Part B:** the new findings, ordered by severity. Each one has:
    - an id (R2-1, R2-2, …);
    - the passage: the section and a quote, or the file and line;
    - the reason;
    - a concrete fix.
  - Severity levels:
    - **blocking:** do not freeze in this state;
    - **major:** fix before the freeze;
    - **minor:** clarity.
  - Start with counts. End with a short readiness judgment.
  - If you ran code, list the commands and their results in an appendix.
- **`REVIEW2.json`:** `{"repairs": [{"id", "status", "evidence"}], "counts": {...}, "findings": [{"id", "severity",
  "where", "quote", "reason", "fix"}], "readiness": "..."}`.

## Rules

- Read and write only inside this task folder. No network, no git, no other agents.
- Do not edit the inputs. Work on copies in `out/scratch/`.
- **Blindness:**
  - Do not compute or report the fixed system's per-world outcomes, or any HOLDS counts or rates, for G8 or T-1 on any
    world.
  - Design quantities are fine: feasibility, denominators, definedness, twin outcomes, baseline scores.
- Be concrete. Say "unclear" when you cannot decide. Do not pad.
