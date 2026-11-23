# Run record: Tesaron v0.3

This record is outside the freeze manifest (PREREG v0.3 §9). It is appended to, never rewritten. The freeze and the salt
are in `prereg/v03/FREEZE_RECORD.md`.

## Calibration and test (PREREG v0.3 §8, steps 9–10)

| Step | Commit | What |
|---|---|---|
| Calibration | `6cd2408` | `py -m audit.v03.run_v03 calibrate`: 40 main calibration worlds, 1 draw rejected (\|H\| < 10); main τ at (α₀ = 0.7, k = 0) by Q-40: τ_s 39/49, τ_d 0/1, τ_t 43/44, τ_b 11/16; also the τ of I-6, I-7 and I-8 and of the 20 draw-sensitivity sets |
| Test | `ecef50f` | `py -m audit.v03.run_v03 test`: 50 test worlds, 2 draws rejected (\|H\| < 10), 269.1 s; F1, F2 and F4 agreed on all 50 test worlds and the 40 main calibration worlds; outputs written unedited |

- Real mode was run once for each step; there was no stopped or refused real-mode run. The first complete run is the
  result (PREREG v0.3 §8, step 11).
- Each commit was pushed to `https://github.com/Mukanto/Tesaron.git` (`main`) with the author's approval before the
  next step ran: the calibration ("Devam edelim", 2026-11-23) before the test; the test results ("Devam edelim",
  2026-11-23) before the reproduction, after which `git ls-remote` showed `main` at
  `ecef50fb79c2c57414d1a52363bd8aa4f3c05dca`.

## Reproduction (PREREG v0.3 §8, step 11)

- 2026-11-23: a fresh clone of the public repository (`https://github.com/Mukanto/Tesaron.git`), whose `main` and
  HEAD were the result commit `ecef50f`, on the run machine (`Windows-11-10.0.26300-SP0`, Python 3.14.2, NumPy 2.4.1).
  The designer checked that the clone's `tesaron` and `audit` packages, and the runner's subprocesses, load from the
  clone.
- In the clone, `py -m audit.v03.run_v03 reproduce` (17:46:19–17:56:08 UTC) passed every real-mode check, among them
  the manifest check, and repeated the test step into `run/v03_repro/`.
- Result: `REPRODUCED: byte-identical`. SHA-256 of both `VERDICTS.json` files:
  `a63bad63426a7700172ffab1f7b4b0a7c152834eeb353aa56a65ff87466bd153`.
- The designer also compared the other outputs: `RESULTS.json`, `TEST_WORLDS.json` and all 180 files of
  `outputs_input/` and `outputs_results/` are byte-identical to the committed ones.
- Afterwards, in the same clone, `py -m audit.freeze verify prereg/v03/FREEZE_v0.3.json` and
  `py -m audit.freeze verify prereg/FREEZE_v0.2.json` each gave `FREEZE OK`.

## F3, independent recomputation (PREREG v0.3 §6.1, §8 step 12)

- **Who:** a fresh agent (general-purpose, Opus) in the Independent session, task `tesaron_v03_f3`, agent
  `a223bb6bd3a9f6ab8`. It ran without interruption (2026-11-23, 17:47:31–17:52:47 UTC).
- **What it had:** the frozen `audit/v03/f3/INSTRUCTIONS_F3.md` and `OUTPUT_SCHEMA.json`, a short cover note on the
  folder layout (`run/v03/f3_agent/COVER.md`), `SPEC.md`, `SPEC_v0.3.md`, `PREREG_v0.3.md` and the 90 blind input files
  of `run/v03/outputs_input/` (50 test worlds, 40 calibration worlds). It had none of the run's own numbers: no τ, no
  metric, no G7a or T-1 outcome. The designer checked the inputs for result fields before sending: the only outcomes in
  them are the G1–G6 outcomes labelled as given.
- **Transcript checks by the designer:**
  - no forbidden call (no context-mode tool, no Agent, Task, WebFetch or WebSearch), no git, no network;
  - the only path outside the task folder is the permitted interpreter;
  - the 96 files it was given (the inputs and the reading list) are unchanged (SHA-256 manifest);
  - it wrote its checking scripts into a `scratch/` folder of its task folder, outside `out/` (inside the permitted
    folder; not compared).
- **Comparison:** `py -m audit.v03.f3_compare run/v03 <agent out>` gave **0 disagreements** (0 affecting a verdict) on
  50 of 50 test worlds and 40 of 40 calibration worlds:
  - τ (all four values);
  - every metric and n_q at every grid point of every test world, and at (α₀, 0) of every calibration world;
  - the feasible sets, the fronts and the hypervolumes;
  - the T-1 structure fields and their aggregated counts;
  - the G7a and T-1 outcomes;
  - every verdict-table row, G1–G6 included.

  The result is `run/v03/F3_COMPARE.json`.
- **The agent's files:** in `run/v03/f3_agent/` (50 world files, 40 calibration files, `tau.json`,
  `verdict_table.json`, `NOTES.md`, its code `code/f3.py`, and the cover note). They had no CRLF line endings; the
  comparison run on the copies gives a byte-identical `F3_COMPARE.json`.
- **Its notes** (`NOTES.md`) report no unclear point that mattered for these inputs. It also ran a second closure
  algorithm for H, and it checked that the pass-1 closure of its own encoded values equals the input's `full` and
  `verdict` lists at all 540 k = 0 configurations (50 × 10 test, 40 calibration).
