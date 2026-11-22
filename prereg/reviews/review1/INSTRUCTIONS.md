# Blind review 1 of a pre-registration and its code: Tesaron v0.2

You are an independent reviewer. You did not write this pre-registration or this code, and you have not seen any
discussion of them. Work only with the files in this task folder.

**Running code.** You may run Python, but only with this interpreter:
`C:\Users\user\AppData\Local\Python\pythoncore-3.14-64\python.exe` (it has numpy).
- Run it only on a scratch copy inside `out/scratch/`. Copy `repo/` there first and make the copy writable.
- Set the environment variable `TRUTH_GATE_DIR` to this folder's `truthgate/` directory when you run anything that
  imports `truth_gate`.
- Do not run `audit/run_v02.py` without `--dev`, and do not create `run/`.
- Do not run `audit/gate/certify.py`. It calls git, which you may not use; the certificates are given as files.
- In this folder, one unit test errors by design:
  `test_audit_runner_fidelity.CertifyDriverTests.test_checkout_matches_the_tag_and_is_recorded`. It needs a git
  checkout of the gate, and `truthgate/` here is a plain copy. The designer ran the suite here with this interpreter
  and `PYTHONDONTWRITEBYTECODE=1`: 192 tests, 191 passed, and that one test errored. The same suite passes 192 of 192 in
  the original repository. `repo/audit/gate/GATE_TOOL.json` records the gate's commit and its check against tag
  `v0.5.1`.

## What you review

The pre-registration and the code that implements it:

- **`repo/prereg/PREREG_v0.2.md`:** draft 3, not frozen. Your findings decide what changes before the freeze.
- **`repo/audit/`:** the audit layer, which implements the pre-registration. It contains:
  - the per-world checks (collect + judge);
  - the faulty twins;
  - the independent implementations;
  - the gate studies;
  - the aggregation;
  - the runner.
- **`repo/tesaron/`:** the system under test. Its spec is `repo/SPEC.md`, including the pre-freeze revisions in §15.
- **`repo/audit/gate/*.cert.json`:** the gate certificates. They were produced with Truth_Gate 0.5.1, *before* the
  draft-3 changes to G7 and G8 were implemented, so G7 and G8 will be regenerated.
- **`repo/tests/`:** the unit tests.

## Context files (read what you need)

- **`repo/README.md`:** what the system is.
- **`truthgate/docs/GATE.md`:** the gate's reference (worlds, checks K1–K8, verdicts, the leak guard).
- **`truthgate/protocol/PROTOCOL.md` and `truthgate/protocol/CHECKLIST.md`:** the methods protocol that the
  pre-registration follows.
- **`truthgate/protocol/templates/PREREG_TEMPLATE.md`:** the template it follows.
- **`truthgate/truth_gate/`:** the gate's code, if you need it.

## What to look for

Find defects that would make the results uninterpretable, biased, or weaker than claimed. Cover at least these
questions:

1. **Pre-registration against code.**
   - Does each `collect_*`/`judge_*` pair implement §3.2 exactly, including thresholds, anchors and UNDEFINED
     conditions?
   - Do the twins do what §6.2 says?
   - Do these match the text: the aggregation (§3.3: Wilson bound, at least 16 defined worlds), the seed derivation
     (§7), the τ rule (D1), world validity (D5), and the descriptive arms?
   - Is the order "calibrate, commit TAU, then test worlds" (§8) enforced by the code, not left to the operator?
2. **Can each criterion fail?**
   - Is any criterion decided by definition, or vacuous?
   - Do the anchors stop zero or noise data from holding?
   - Does each twin violate its claim on (nearly) every world?
3. **The gate certification (§6.3, §10 P3-2).**
   - Are the `plus` and `minus` worlds the right ones?
   - Could a certificate be FALSIFIABLE for a reason unrelated to the claim?
   - What does a certificate not cover (for example the subprocess parts of G2 and G4)?
4. **Metrics and the wisdom criterion** (SPEC §8–9). Are there defects in E, I, H, K, the metrics, the feasibility rule,
   the Pareto front or the hypervolume that would bias G7, G8 or T-1?
5. **T-1, the author's thesis.**
   - Is the pairwise rule sound?
   - Does the D1 feasible set make it trivially true or trivially false?
   - How does the disclosure of pilot counts (§2) bear on the design?
6. **Blindness and forking paths.** After the freeze, can anything be adjusted with knowledge of results (τ, worlds,
   replacement, UNDEFINED handling, reruns)?
7. **Determinism claims (G2, G4).** Would they hold on another machine or another numpy version? Are there floating-point
   or ordering risks?
8. **Fidelity controls F1–F4.** Are they really independent of the code they check?
9. **Power and wording** (§3.3, §4, §7). Are the numbers right? Is the fixed wording honest about what a verdict means?
10. **Anything else** a skeptical methods reviewer would raise. Check the protocol's checklist against the draft.

## Output

Write two files to `out/`:

- **`REVIEW1.md`:**
  - Findings ordered by severity, each with:
    - an id (R1-1, R1-2, …);
    - the passage: the section and a quote, or the file and line;
    - the reason;
    - a concrete fix.
  - Severity levels:
    - **blocking:** do not freeze in this state;
    - **major:** fix before the freeze; without the fix the pre-registration is weaker or ambiguous;
    - **minor:** clarity.
  - Start with counts per severity. End with a short overall judgment: is the design worth running once the blocking
    and major findings are fixed?
- **`REVIEW1.json`:** `{"counts": {...}, "findings": [{"id", "severity", "where", "quote", "reason", "fix"}],
  "overall": "..."}`.

If you ran code, list the commands and their results in an appendix of `REVIEW1.md`.

## Rules

- Read and write only inside this task folder. No network, no git, no other agents.
- Do not edit the inputs. Work on copies in `out/scratch/`.
- Be concrete: quote the passage or give the file and line, and give a fix that can be written into the text or the code.
  Do not rewrite the whole draft.
- Say "unclear" when you cannot decide. Do not pad: a short list of real problems beats a long list of preferences.
