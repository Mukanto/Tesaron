# audit

v0.2

The audit layer of Tesaron v0.2. The authoritative spec is `prereg/PREREG_v0.2.md` (DRAFT 5, not frozen).

## Modules

| Path | What |
|---|---|
| `seeds.py` | `seed(core, salt, role, i)` (section 7, with the run salt); `dev_seed(role, i)` maps into 900000-900999 (salt "dev") and is used only in dev mode |
| `exact.py` | exact comparisons: tolerances, tau and feasibility as `fractions.Fraction`; (numerator, denominator) pair arrays; the exact constrained Pareto front and hypervolume |
| `freeze.py` | freeze manifest write/verify, same format and core hash as the Truth_Gate's `freeze.py` (hashes are over raw bytes: see its docstring on line endings) |
| `oracle.py` | the oracle system of the G7a anchor |
| `worldset.py` | valid-world generation with replacement (PCM usable, \|H\| >= 10, at most 200 draws) |
| `system.py`, `twins/` | the System abstraction and the faulty twins N1a, N1b, N2, N3, N4, N5, N6, N7, N8, NT (section 6.2) |
| `checks.py` | G1-G6, G7a, G8 and T-1: `collect_gN(...)` gathers numeric arrays (exact values as integer pairs), `judge_gN(data)` returns True, False or None |
| `aggregate.py` | the verdict rules of sections 3.3 and 4 (deterministic G1-G7a, quantitative G8 and T-1 with the Wilson bound), the fixed wording, the T-1 regime sentence and structure counts, the G8 hypothesis counts, the expected-verdict paragraph and the limitation sentence |
| `descriptive.py` | cross-seed agreement (D4a), the whole-grid G8 reading (I-4), T-1 over all grid points (I-2), G7b, the T-1 structure arm (I-5), single-atom G8 failures (I-6), default-configuration feasibility |
| `per_world.py`, `subproc.py`, `hashing.py`, `cache.py`, `tau.py` | helpers |

## Independent implementations and the fidelity controls (section 6.1)

`indep/` holds the independent re-implementations. Nothing in it imports `tesaron.decoder`, `tesaron.encoder` or
`tesaron.belnap`; it reads rules, atoms, units and rows by attribute only.

| Path | What |
|---|---|
| `indep/h_closure.py` | the brute-force rule closure (every rule over every assignment of entities) and, from it, the independent H (F2) and the pass-1 and pass-2 fixpoints (F1, G6) |
| `indep/abduction.py` | the brute-force abduction candidate enumerator of SPEC section 7.3: candidates with scores, the ranking and the top-k cut (F1) |
| `indep/units.py` | the relation units (degrees from the world's source reliabilities, provenance), the class units' provenance and status, and the interface facts of all units at every alpha by the Belnap table (F4) |
| `indep/pcm_loop.py` | an explicit-loop PCM fit with its converged, iteration and degenerate flags, the centers and the class-unit mu-plus (F4) |
| `fidelity.py` | the controls on one world. F1: the decoder's pass-1 and pass-2 facts and statuses, its full ranked candidate list and its kept hypotheses against the independent ones at every grid configuration, and naive against semi-naive evaluation. F2: H. F4: PCM centers and class mu-plus to 1e-12, and exactly the PCM flags, the class and relation units and the interface facts |
| `f4_prefreeze.py` | F1 and F4 on 20 development worlds; writes `prereg/F4_PREFREEZE.json` |

## F3 (after the run)

| Path | What |
|---|---|
| `f3/INSTRUCTIONS_F3.md` | the instructions of the fresh F3 agent (frozen with the pre-registration) |
| `f3/OUTPUT_SCHEMA.json` | what the agent writes per world and for the verdict table |
| `f3_compare.py` | the frozen comparison of the agent's files with `run/outputs_results/` and `run/VERDICTS.json`: exact string equality of every fraction, the fixed map from a field to the tests it can affect, `F3_COMPARE.json` |

## Gate, freeze and run

| Path | What |
|---|---|
| `gate/` | one Truth_Gate study per test (`gN_study.py`, `t1_study.py`), `certify.py` (`all --verify` also writes `GATE_TOOL.json`; certificates are rewritten with LF), and the certificates `*.cert.json` |
| `prefreeze_check.py` | the pre-freeze check: `GATE_TOOL.json` against the current files, the freeze walk's file set against the git-tracked files, and every walked file's bytes against its staged blob |
| `clone_verify.py` | clones the repository at HEAD into a temporary folder and runs the freeze verifier there (after the freeze commit, before the push) |
| `design/draw_study.py` | the calibration-draw study; writes `prereg/DRAW_STUDY.json` |
| `smoke_d4.py` | the D4 smoke test on twenty development worlds (prints only defined / reachable / covered) |
| `run_v02.py` | `py -m audit.run_v02 calibrate|test|reproduce [--dev]`; real mode checks the freeze manifest, git history (one commit touches the manifest, `run/SALT.json`, `run/CAL_WORLDS.json` and `run/TAU.json`; the freeze, salt, CAL and TAU commits are on `origin/main`; the manifest covers the tracked frozen tree and equals the freeze commit), Python 3.14.2 and NumPy 2.4.1; `reproduce` reruns the test step in a clone of the result commit and compares `VERDICTS.json` byte for byte |

Layer 1, the gate, is run with `py -m audit.gate.certify all` (or one study, `g1` ... `t1`; `--quick` for a trial run,
`--verify` to re-run a certificate). The gate's leak guard blocks opening a file while a study runs, so `certify.py`
imports every audit and tesaron module before the guard is armed.

Every file that the audit code writes into the repository is written with LF line endings, and `.gitattributes` fixes
`* text=auto eol=lf`, so that a fresh clone reproduces the frozen bytes on any machine.

Tests that need git run on a temporary repository of their own; set `TESARON_SKIP_GIT_TESTS=1` to skip them.

Real mode of the runner needs `prereg/FREEZE_v0.2.json` and never runs before the freeze. Development mode
(`--dev`) uses the core string "dev", seeds in 900000-900999 and writes only to `run_dev/` (git-ignored).
