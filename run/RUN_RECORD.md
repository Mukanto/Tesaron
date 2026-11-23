# Run record: Tesaron v0.2

This record is outside the freeze manifest. It is appended to, never rewritten. The freeze and the salt are in
`prereg/FREEZE_RECORD.md`.

## Calibration and test (PREREG §8, steps 9–10)

| Step | Commit | What |
|---|---|---|
| Calibration | `f3c60ff` | `py -m audit.run_v02 calibrate`: 10 worlds, 0 draws rejected; τ_s 57/70, τ_d 3/68, τ_t 193/198, τ_b 3/5 |
| Test | `fcb4ea5` | `py -m audit.run_v02 test`: 30 worlds, 0 draws rejected, 167 s; F1, F2 and F4 agreed on every world; outputs written unedited |

Each commit was pushed to `https://github.com/Mukanto/Tesaron.git` (`main`) with the author's approval before the
next step ran.

## Reproduction (PREREG §8, step 11)

- 2026-11-22: a fresh clone of `fcb4ea5` from the public repository, on the run machine (`Windows-11-10.0.26300-SP0`,
  Python 3.14.2, NumPy 2.4.1).
- In the clone: `py -m audit.freeze verify prereg/FREEZE_v0.2.json` gave `FREEZE OK`.
- `py -m audit.run_v02 reproduce` passed every real-mode check and repeated the test step into `run_repro/`.
- Result: `REPRODUCED: byte-identical`. SHA-256 of both `VERDICTS.json` files:
  `6a0c09ab1a98b82643645116f6f01330f0495b72b9b55296a6e24d34d7c2172f`.

## F3, independent recomputation (PREREG §6.1, §8 step 12)

- **Who:** a fresh agent (general-purpose, Opus) in the Independent session, task `tesaron_v02_f3`.
- **What it had:** the frozen `audit/f3/INSTRUCTIONS_F3.md` and `OUTPUT_SCHEMA.json`, a short cover note on the folder
  layout, `SPEC.md`, `PREREG_v0.2.md` and the 30 blind input files (`run/outputs_input/`). It had none of the run's
  own numbers.
- **Transcript checks by the designer:**
  - no forbidden call, no git, no network;
  - the only outside path is the permitted interpreter;
  - the inputs are unchanged.
  - It wrote two scratch files into a `scratch/` folder of its task folder instead of `out/` (inside the permitted
    folder; not compared).
- **Comparison:** `py -m audit.f3_compare run <agent out>` gave **0 disagreements** on 30 of 30 worlds:
  - every metric at every grid point;
  - the feasible sets, the fronts and the hypervolumes;
  - the T-1 structure fields;
  - the G7a, G8 and T-1 outcomes;
  - every verdict-table row.

  The result is `run/F3_COMPARE.json`.
- **The agent's files:** in `run/f3_agent/` (30 world files, `verdict_table.json`, `NOTES.md`, its code), with line
  endings normalised to LF; the comparison run on these copies gives the same result. Its notes record its conventions,
  among them the IEEE-double reading of `boundary_share`, a metric that no verdict uses.

## Blind post-run audit (PREREG §8, step 12; appended 2026-11-23)

- **Who:** a fresh agent (general-purpose, Opus) in the Independent session, task `tesaron_v02_postrun`. It stopped
  once on a usage limit, before writing any output, and was resumed.
- **Part 1:** written to `PART1.md` before the agent opened any result, certificate, review or freeze record. The
  designer confirmed the order in the transcript: the first command excluded `part2/`; `PART1.md` was written once, at
  tool call 47, before the first access to `part2/`, and never changed.
- **Transcript checks:**
  - no forbidden call;
  - the outside paths are the permitted interpreter, the salt record, the public clone and a harness file;
  - the inputs are unchanged.
- **Result:** no high finding. Part 1 has 5 medium and 6 low findings on the design; Part 2 has 1 medium and 5 low on
  the draft report. Every provenance check passed: salt record, clone verification, commit order, one commit per run
  file, byte-identical files. The audit also reproduced `VERDICTS.json` byte for byte.
- **Files:** `run/postrun_audit/` (`INSTRUCTIONS.md`, `PART1.md`, `PART2.md`, `AUDIT.json`).
- **Designer's check of A2:** the frozen-code development rates, G8 15 of 30 and T-1 722 of 918 world-draws with
  verdicts 3 HOLDS / 34 FAILS / 3 insufficient over 40 draws, were recomputed with an independent script and agree.
- **Report:** `REPORT_v0.2.md` was corrected after the audit and is final.
