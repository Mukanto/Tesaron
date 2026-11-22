# Blind review 1: Tesaron v0.2 pre-registration (draft 3) and its audit code

**Counts:** blocking 2, major 13, minor 7 (22 findings).

**How this review was done.**
- I read the pre-registration, SPEC.md, all of `audit/`, the parts of `tesaron/` that decide verdicts, the
  certificates, the tests, and GATE.md, PROTOCOL.md, CHECKLIST.md and the template.
- I ran code only on a writable copy in `out/scratch/repo`, on development worlds only (dev seed mapping,
  900000–900999), with the dev τ from the D1 rule (`audit.gate.common.gate_taus`).
- I did not compute or report the fixed system's per-world outcomes of G7, G8 or T-1, so this review adds no new
  pilot counts. Where a finding needs dev numbers, I give design quantities: feasibility, denominators, baseline
  scores, twin outcomes and definedness.
- I did not run the gate. Commands and results are in the appendix.

---

## Blocking

### R1-1 (blocking). G7 does not test its stated claim, and its baseline comparison never decides anything

**Where:**
- PREREG §1 (line 24): "no false high score is possible".
- §3.2, G7 row (line 75).
- §6.3 (line 171): "G7 and G8: these are empirical claims about the system".
- `audit/aggregate.py:21`; `audit/checks.py:305-334`; `audit/gate/g7_study.py`.

**Reason.**
- **Claim and check differ.**
  - The claim is about the criterion.
  - The check is about the system: HOLDS iff the system's hypervolume `hv_system > 0` and every baseline's score is
    below it.
  - §6.3 itself calls G7 an empirical claim about the system.
  - Example: a world where the system has feasible points but hypervolume 0 FAILS (P3-1). The report would then print
    "G7 does not hold" next to the claim "The wisdom criterion cannot give a false high score", although no baseline
    received any score.
- **The baselines cannot score.** This follows from their definitions:
  - echo's verdict is enc(a). That is U on every atom of H, because H ∩ E = ∅. So new_true = 0, y = 0 and the score
    is 0.
  - all_unknown and all_both have fidelity 0, so they are infeasible for any τ_s > 0.
  - all_false breaks τ_d, because most decided encoded atoms are T.
  - all_true is feasible only if at most a τ_d share of the decided encoded atoms is F.
  - On 30 development worlds, no baseline had a positive score at any α. echo was feasible at 77 (world, α) pairs and
    always scored 0.
  - So G7 HOLDS exactly when hv_system > 0: some feasible α derives at least one correct atom of H while
    new_false < 1.
- **The certificate tests only that anchor.**
  - In `g7.cert.json`, `minus_check.changed_keys` is `['hv_system']`; `hv_baselines` is identical in plus and minus.
  - So the certificate shows that the judge separates hv_system > 0 from hv_system = 0. It shows nothing about a
    baseline outscoring the system.
  - 42 of the 100 minus samples are UNDEFINED.
- **The baseline rule is ambiguous.**
  - "every baseline (…, each over every α of the grid) has a lower hypervolume" can mean the baseline's front over all
    α, or each α on its own.
  - The code uses each α's single-point score (`checks.py:313-320`).
  - The two readings agreed on 30 of 30 development worlds, but the text should say which one applies.

**Fix.**
- Rename G7 to what is tested, in §1, §3.2, the §4 wording, `aggregate.CLAIMS` and the study name. Suggested: "G7:
  under the constrained-Pareto criterion the system's hypervolume is positive and above every degenerate baseline's."
- Add to §3.2: "By their definitions, echo scores 0 and all_unknown and all_both are infeasible, so in practice the
  test is hv_system > 0."
- If the property of the criterion is wanted, add a separate deterministic check, G7c: "On every test world, every
  baseline at every α of the grid is infeasible or scores 0." One FAILS world fails it. Its gate study needs a `minus`
  world in which a baseline is feasible with a positive score.
- State one baseline rule: either "the hypervolume of the baseline's feasible front over the 10 α values", or per α.
  Make `collect_g7` follow it.

### R1-2 (blocking). One discrete event decides T-1: whether the bounds admit the 0.60 source. The tautology answer in §2 is wrong

**Where:**
- PREREG §2 (line 49): "T-1 is not decided by definition: a point's uncertainty and its new_false are computed from
  different atom sets (K and the complement of I)."
- §3.2, T-1 row (line 77); §7 grid and τ rule (lines 199-200).
- SPEC §3: source reliabilities (0.95, 0.80, 0.60). SPEC §7.4 and §8: the verdict ignores hypotheses.

**Reason** (development worlds, dev τ from D1; see the appendix).
- **Only α matters.** Uncertainty and new_false do not depend on k (R1-5), so T-1 compares at most 10 α levels.
- **The top of the feasible set is fixed at 0.80.**
  - Relation atoms have three regimes, one per source (0.95, 0.80, 0.60).
  - τ_b, the default's maximum uncertainty, excluded every α ≥ 0.85 on 20 of 20 development worlds: uncertainty jumps
    when the 0.80 source drops out.
- **T-1 cannot fail between 0.65 and 0.80.** In that window only class atoms change (own-class typicalities crossing
  α). The largest new_false rise toward lower uncertainty in the window was 0.000 on 20 of 20 development worlds.
- **T-1 fails only through α ≤ 0.60.**
  - That is where the third source (support 0.60) enters.
  - On every development world where α = 0.60 was feasible, new_false rose by at least 0.071 (> δ) from 0.65 to 0.60.
  - Whether α = 0.60 is feasible depends mainly on two bounds, fidelity ≥ τ_s and consistency ≥ τ_t. At α = 0.60
    these failed on 12 and 10 of 20 worlds.
  - So it depends on the extremes of the default on 10 calibration worlds, and on how many wrong third-source reports
    a world happens to draw.
- **So, per world, T-1 holds roughly when the D1 bounds exclude the third source.**
  - The median uncertainty span among feasible points was 0.047.
  - The k values add duplicate points, not new pairs.
- **The §2 argument is also inaccurate.**
  - E∖I and H belong both to K and to the complement of I.
  - The complement of I shrinks as α falls.
- **Consequence.** A HOLDS or FAILS will be read as evidence on the author's general thesis. In fact it counts the
  worlds on which the calibrated bounds keep the third source out.

**Fix** (the author decides; any change to T-1 now is made with the §2 pilot in view and must say so).
- Correct the tautology paragraph in §2.
- Add an interpretation I-5 to §5: "With three discrete source reliabilities and D1, T-1 compares α ∈ {0.65…0.80},
  where only class atoms change, with the third-source regime α ≤ 0.60."
- Add a descriptive sensitivity arm. Per world, report:
  - the feasible α set;
  - whether some α ≤ 0.60 is feasible;
  - T-1 restricted to pairs that cross the 0.60/0.65 boundary, and T-1 restricted to pairs inside the window.
- Then choose one of two options:
  - accept T-1 as a test of the third-source switch, and reword the claim and the verdict sentence to say so; or
  - change the design before the freeze so that T-1 sees graded variation. Examples: per-world source reliabilities
    drawn from a continuous range, or a definedness condition that the feasible set crosses at least one relation
    regime boundary or has an uncertainty span of at least a stated value.

---

## Major

### R1-3 (major). Anyone can compute the test seeds, and run the whole test, before the freeze

**Where:**
- PREREG §2 (line 38): "Their seeds are derived from the freeze hash after the freeze (§7), so nobody can have seen
  them".
- §7 (line 210); `audit/seeds.py:32-34`.
- `truthgate/truth_gate/freeze.py:38-41`: `core_sha256` is the SHA-256 of the sorted `path:sha256` lines, with no time
  and no outside input.
- `audit/run_v02.py:63-83`.

**Reason.**
- `core_sha256` is a pure function of file contents that the designer controls.
- Anyone can compute it for a candidate tree, derive `seed("world-test", i)` and run the checks. If the result is
  unwelcome, they can edit a comment and freeze again.
- The runner only needs a manifest that verifies. It does not check that the manifest is committed or pushed. So this
  sequence is possible: `freeze write`, `calibrate`, `test`, delete the manifest, edit, freeze again.
- "nobody can have seen them" therefore rests on trust, not on the design (protocol rule 17).

**Fix.**
- Mix into every seed a value that is fixed only after the freeze:
  `seed(role, i) = 1 000 000 + (first 8 bytes of SHA-256("<core>|<salt>|<role>|<i>")) mod 10⁹`.
- The salt can be 32 random bytes that the Independent session draws once it has the pushed freeze commit, recorded
  with that commit id in `run/SALT.json`. A public beacon value at a stated time after the push also works.
- The runner refuses unless all three hold:
  - `FREEZE_v0.2.json` is committed in HEAD;
  - HEAD is on the remote branch;
  - `SALT.json` is committed after it.

### R1-4 (major). `test` does not check that TAU.json is the D1 result of the calibration worlds

**Where:**
- §8 step 7 (line 240): "τ goes into `run/TAU.json`, which is hashed and committed before any test world is
  generated".
- `audit/run_v02.py:211-217`: τ is read from the file; only `core_sha256` is compared.
- `run_v02.py:90-100`: the file must only be tracked, committed and unmodified.

**Reason.**
- A TAU.json that was edited and then committed passes.
- `cal_worlds_sha256` is written but never checked.
- The commit can stay local.
- So the order "calibrate, commit TAU, then test" is enforced only in the sense that a file exists in git.

**Fix.**
- In `run_test`, regenerate the 10 calibration worlds from `seed("world-cal" / "enc-cal", i)`. This is cheap and
  deterministic.
- Recompute τ by D1 and refuse unless it equals TAU.json exactly, as floats.
- Also refuse unless `sha256(CAL_WORLDS.json)` equals `cal_worlds_sha256`, and unless the TAU commit descends from the
  freeze commit.

### R1-5 (major). The wisdom quantities do not depend on k; abduction affects G7 and T-1 only through feasibility

**Where:**
- §3.1 (line 57) and §7 (line 199): "Finer α steps … give T-1 more pairs".
- SPEC §7.4: the verdict uses OBSERVED and DERIVED facts only.
- `tesaron/decoder/decode.py:22, 40-45, 85-94`.

**Reason.**
- Pass-2 facts have status HYPOTHESIS, and the verdict ignores them. So uncertainty, new_true and new_false at
  (α, k) equal their values at (α, 0). The largest difference was 0.0 over 30 development worlds.
- Every Pareto point (x, y) and every coordinate of T-1 therefore depends on α only.
- k changes only fidelity, deviation and consistency, and so only feasibility. Feasibility differed across k at some α
  on 8 of 30 development worlds.
- G7's "hypervolume over the grid" is a hypervolume over at most 10 distinct points, and abduction can never raise it.
- The draft says none of this, so a reader will assume that creativity is scored.

**Fix.**
- State in §3.1 and in the report that, under A-6, the Pareto axes and the T-1 coordinates do not depend on k.
- Say that G7 and T-1 depend on k only through feasibility, and that T-1 compares α levels (at most 10 distinct
  uncertainty values).
- Ask the author whether hypotheses are meant to count anywhere in the wisdom criterion.

### R1-6 (major). G1, G3 and G6 are also decided by construction but are not labelled as implementation tests; G3 checks only one direction of grounding

**Where:**
- §2 (lines 45-47) and §4 (line 109): only G2, G4 and G5 are labelled.
- §6.3 (line 170): "G1–G6: these are properties the design guarantees".
- `audit/aggregate.py:12`; `checks.py:96-157, 254-279`; `tesaron/encoder/core.py:35-80`; `decode.py:71-78`.

**Reason.**
- **G1.**
  - Part (ii) holds because the class units' μ⁻ is hard-coded to 0 (`core.py:57`).
  - Part (i) holds by the generator's geometry: outliers at radius 7, prototypes at 3 and η = 0.72 give each class a
    typicality of about 0.04.
- **G3.**
  - A unit exists only if it has rows in D_derive (`core.py:41-79`). Removing its provenance therefore always removes
    the unit, and `decided_after` is False by construction.
  - G3 shows that provenance is necessary, not that it is complete. A class unit's degree depends on every D_derive
    feature row through the fitted centers, and those rows are not in its provenance.
- **G6.** `decode` gives OBSERVED or DERIVED status exactly to the pass-1 fixpoint (`decode.py:72-78`). The
  "independent" naive fixpoint shares its engine (R1-11).
- §6.3 already says that the design guarantees G1–G6, which contradicts §2 and §4.

**Fix.**
- In §2, §4 and `aggregate.IMPLEMENTATION_TESTS`, give all of G1–G6 the label "(a test of the implementation, not a
  discovery)", and call them regression checks (protocol rule 1.1).
- In G3's claim, write: "removing a unit's provenance removes the unit (necessity); a class unit's provenance does not
  include the rows that fit the centers."

### R1-7 (major). G8 is a zero-tolerance test at most α, and neither the claim nor the wording says so

**Where:**
- §3.2, G8 row (line 76); §7 (line 204); §10 Q-ε_d.
- `checks.py:351-361`; the FAILS wording in `aggregate.py`.

**Reason.**
- **Denominators on 30 development worlds:**
  - decided encoded atoms (the deviation denominator): 18–43 at α ≥ 0.85, 36–70 at 0.65–0.80, 52–92 at ≤ 0.60;
  - |I|: 18 to 96.
- **One atom is enough to fail.**
  - With ε_d = 0.02, one changed atom fails the world wherever the denominator is below 50, which covers almost every
    α ≥ 0.65.
  - With ε_f = 0.05, one atom fails wherever |I| < 20.
- **So, on most worlds, G8 checks that no decided encoded atom changes** in any of its 20 (α, k) comparisons. The
  quantitative rule then needs at least 28 of 30 such worlds.
- **The FAILS wording overstates.** "G8 does not hold" reads as "abduction does not preserve meaning".
- **The anchor never acts on real data.** "≥ 1 hypothesis at (α₀, k = 10)" is the same as the definedness condition,
  so it only works against the gate's probes.
- **A NaN fidelity is unstated.** The code treats it as "no violation" (`checks.py:358`), but §3.2 does not say so. No
  None value occurred on the development worlds.

**Fix.**
- Add to §3.2 and §4: "At most α, ε_d is below one atom; a world FAILS if abduction changes the value of one decided
  encoded atom at any α."
- FAILS wording: "G8 does not hold: in <n_fails> of <n_defined> worlds abduction changed at least one decided encoded
  atom beyond the tolerance."
- State the rule for NaN.
- Do not change ε: the author fixed it.

### R1-8 (major). Floating-point rounding decides comparisons at exactly the tolerance

**Where:**
- §7 (line 204): "Both are well above the floating-point resolution, since the metrics are ratios of integers".
- `checks.py:356-359` (G8) and `checks.py:407-408` (T-1).

**Reason.**
- ε_f = 1/20, ε_d = 1/50 and δ = 1/20 are themselves values that the metrics can reach.
- Example: with |I| = 20, fidelity going from 4/20 to 3/20 gives `4/20 - 3/20 = 0.05000000000000002 > 0.05`. That is
  a violation, although the rule (≤ ε) holds exactly.
- With equal denominators of 18–99:
  - 79 of the 194 differences of exactly 0.05 evaluate as violations;
  - 34 of the 50 differences of exactly 0.02 do too.
- The development worlds have |I| of 20, 40, 60 and 80, and decided denominators of 50.

**Fix.**
- Compare exact rationals: `fractions.Fraction` of the integer counts, or integer cross-multiplication.
- Or pre-register a margin: a violation only if the difference exceeds ε + 1e-9.
- State the rule in §3.2.

### R1-9 (major). The power statement assumes 30 defined worlds; with UNDEFINED worlds power falls, and with 19 or fewer every world must hold

**Where:**
- §7 (line 211): "P(HOLDS) is 0.81 if the true per-world rate is 0.95 … A HOLDS verdict means a per-world rate of
  roughly 0.9 or more".
- §3.3.

**Reason.**
- **Minimum number of HOLDS worlds under the Wilson rule:**
  - n = 16 to 19 defined worlds: all n;
  - n = 20 to 27: n − 1;
  - n = 28 to 30: n − 2.
- **P(HOLDS) when the true per-world rate is 0.95:**

  | Defined worlds n | P(HOLDS) |
  |---|---|
  | 30 | 0.81 |
  | 28 | 0.84 |
  | 27 | 0.61 |
  | 26 | 0.62 |
  | 20 | 0.74 |
  | 16–19 | 0.38–0.44 |

- **About 26–27 defined worlds is realistic.** On development worlds, 3 of 30 had no feasible point (G7 undefined) and
  4 of 30 left T-1 undefined. At 26–27 defined worlds, P(HOLDS | 0.95) is about 0.61.
- **"Roughly 0.9 or more" is wrong.**
  - At n = 30, P(HOLDS) is 0.15 for a rate of 0.85 and 0.04 for 0.80.
  - HOLDS means a rate of at least 0.80 at one-sided 95% confidence.

**Fix.**
- Replace the power row with a table of P(HOLDS | rate, n_defined) for n = 16 to 30.
- Then choose one:
  - raise N_TEST, for example draw until each quantitative test has 30 defined worlds (pre-register this, because it
    conditions on definedness), or set N_TEST = 34;
  - or state the lower power.
- Reword: "HOLDS: the per-world rate is at least 0.80 at one-sided 95% confidence."

### R1-10 (major). The disclosed pilot makes FAILS of T-1 and G8 nearly certain, and §2 does not draw that consequence

**Where:** §2 (line 37), the pilot row; §7 (line 211).

**Reason.**
- The pilot rates are 12/17 ≈ 0.71 for T-1 and 6/20 = 0.30 for G8. Under the 28/30 rule, P(HOLDS) is about 0.003 for
  T-1 and about 0 for G8, if the test worlds behave like the pilot.
- So these two verdicts are almost known before the freeze. The test τ will differ from the dev τ, which is a caveat.
- Presenting them as prospective results overstates what they add. G7's pilot used a reading that has since changed.

**Fix.**
- Add a row to §2: "Expected verdicts given the pilot: T-1 FAILS (P(HOLDS) ≈ 0.003 at rate 0.71), G8 FAILS (≈ 0 at
  0.30); a different outcome would mean the test worlds differ from the development worlds."
- Print the same sentence next to these two verdicts in the report.

### R1-11 (major). F1 and G6's "independent recomputation" share the decoder's engine; F3 is not blind and its scope and consequence are open; F4 compares only the centers

**Where:**
- §2 (line 47); §6.1 (lines 129-139): "These are independent implementations of the code paths that decide verdicts".
- `audit/fidelity.py:14-31, 45-50`; `tesaron/decoder/datalog.py:164-225`; `checks.py:254-262`;
  `run_v02.py:144-178`.

**Reason.**
- **F1 is not independent.**
  - `naive_eval` and `seminaive_eval` are one function, `_fixpoint`, with a flag.
  - They share `match_literals`, `_match`, `instantiate`, `build_index`, the vocabulary filter and the record logic.
  - A bug in matching substitutions would therefore hit the decoder, F1, G4's fixpoint check and G6 alike.
  - The only truly independent closure, `audit/indep/h_closure.py`, is used only for H.
- **F3 is not blind, and its scope and consequence are open.**
  - `world_payload` hands the run's own metrics, check data and outcomes to the "independent" agent.
  - §6.1 lists only the metrics, the front, the hypervolume and T-1. It leaves out G7's baselines, G8 and the Wilson
    aggregation.
  - Nothing says what happens if F3 disagrees.
- **F4 compares only the fitted centers.**
  - The class units' typicalities (`_build_units`) are not checked.
  - §6.1 says F4 runs on 20 development worlds before the freeze; the unit test uses 4. I ran 20: the largest
    difference was 1.3e-15.

**Fix.**
- **F1:** compare the decoder's pass-1 and pass-2 fact sets with `brute_force_closure` (`audit/indep`) at every grid
  configuration, and keep naive against semi-naive for the records.
- **G6:** use the same brute-force closure as its recomputation.
- **F3:**
  - give the agent only the truth, the rules, the units and the full and verdict lists;
  - move "metrics", "check_data" and "fixed_outcomes" to a separate file that a script compares afterwards;
  - extend the scope to every G7, G8 and T-1 outcome and to the verdict table;
  - pre-register: "a disagreement on a number that affects a verdict means no verdict for the affected tests until it
    is resolved, and it is reported."
- **F4:** also compare the class units' μ⁺ to 1e-12, and record the 20-world F4 run made before the freeze.

### R1-12 (major). The run writes partial results before it stops; what follows a stop, a crash or a rerun is not pre-registered

**Where:**
- §3.1 (line 61): "A crash is not UNDEFINED; it is a failure of the run and is reported as such".
- §6.1 (line 138); `run_v02.py:237-247`.

**Reason.**
- `run_test` evaluates one world at a time. Before a failing F1, F2 or F4 control stops the run, the outcomes of all
  earlier worlds are already written to `outputs/`.
- A repair and a rerun would therefore be made with partial results seen.
- The draft does not say what follows a stop or a crash: whether the repair is a new version, whether a rerun is
  allowed, and which outputs count.

**Fix.**
- Run F1, F2 and F4 on all test worlds first, and evaluate the checks only if all of them agree.
- Add to §8: "A stop or a crash ends the run with no verdict. Any change to the code is a new version with a deviation
  note and new seeds (salt). The first complete run is the result. A rerun with the frozen code must reproduce
  VERDICTS.json byte for byte, and it is reported."

### R1-13 (major). The UNDEFINED worlds of G7 and T-1 depend on the outcome, and the default itself is often outside the bounds

**Where:** the G7 and T-1 UNDEFINED rules in §3.2; §5, I-3 (line 122); §7, τ rule (line 200): "By construction, the
default is feasible on every calibration world."

**Reason.**
- The τ values are extremes over 10 calibration worlds. With discrete metrics, τ_d was 1/52 on the development worlds,
  so a single deviating atom decides feasibility.
- On 30 development worlds:
  - the default (0.7, 5) was infeasible on 7;
  - 3 had no feasible point, so G7 was UNDEFINED;
  - T-1 was UNDEFINED on 4.
- A world with no feasible point is one where the system is worse than the calibration envelope everywhere, so it is
  among the system's worst worlds. Excluding it raises G7's HOLDS share.
- I-3's sensitivity arm reports only the count.

**Fix.**
- Add a descriptive sensitivity arm next to the G7 and T-1 verdicts: the Wilson share with UNDEFINED counted as FAILS.
- Report, for each test world, whether the default is feasible.

### R1-14 (major). Determinism holds only on one machine with one NumPy build; versions are not pinned, so a rerun elsewhere opens a forking path

**Where:** G2 and G4 in §3.2; §7, drift (line 212); `pyproject.toml:14` (`numpy>=1.26`); the outputs of
`run_v02.py`.

**Reason.**
- **Seeded streams can change between NumPy versions.** NumPy does not guarantee that `Generator` methods return the
  same stream across versions (NEP 19). `permutation`, `integers`, `normal` and `uniform` build the worlds and the
  splits.
- **Low-order bits can change between machines.**
  - PCM uses a BLAS matrix product, whose last bits can differ between CPUs.
  - A typicality close to an α can then flip.
  - Rounding to 12 digits in the canonical hash does not make hashes portable.
- **G2 and G4 compare runs on one machine only.**
- **Nothing records or enforces versions.**
  - TAU.json, TEST_WORLDS.json and VERDICTS.json do not record Python, NumPy or the platform.
  - The runner does not refuse another version.
  - A rerun on another machine could give another verdict, and a choice between runs.

**Fix.**
- Record `sys.version`, `numpy.__version__`, the platform and a canonical hash of each world and encoding in
  CAL_WORLDS, TEST_WORLDS and VERDICTS.
- Freeze the versions used for the certificates (Python 3.14.2, NumPy 2.4.1) in §7, and make the runner refuse other
  versions.
- Limit the claims of G2 and G4 to "the same machine and NumPy build".

### R1-15 (major). What the gate certificates do not cover, and whether the G7 and G8 certificates are current

**Where:** §6.3 (lines 163-193); `audit/gate/*.cert.json`; `GATE_TOOL.json`; `audit/gate/common.py:119-141`.

**Reason.**
- **Only the study file is hashed.**
  - A certificate stores `module_sha256` of the study file alone. `checks.py`, the twins, `plus_systems.py` and
    `tesaron/` are not hashed.
  - A code change is therefore noticed only if it changes the outcome counts when the certificate is verified again.
- **What the gate does not exercise:**
  - the PYTHONHASHSEED parts of G2 and G4 (the draft says so);
  - N4's mechanism in the real run, a set order that differs between processes. The gate's N4 draws an in-process rng
    order instead;
  - G7's baseline comparison (R1-1);
  - τ calibration, aggregation, seed derivation, world validity and the F controls;
  - T-1 on data shaped like the real data. The synthetic `plus` has 30 distinct continuous uncertainty values and a
    flat new_false (0.10 ± 0.01). Real data have at most 10 levels, duplicates across k and a jump between regimes
    (R1-2).
- **Unclear whether the G7 and G8 certificates are current.**
  - INSTRUCTIONS.md says the G7 and G8 certificates predate draft 3 and will be regenerated.
  - GATE_TOOL.json says they were regenerated after P3-1 to P3-3.
  - Their `module_sha256` matches the current `g7_study.py` and `g8_study.py`; they were created at 05:31Z and 05:33Z.
  - I could not decide which statement is current, and I did not rerun the gate.

**Fix.**
- Just before the freeze, run `certify all --verify` on the frozen tree. Record its output, and the SHA-256 of the
  files in `audit/` and `tesaron/`, in GATE_TOOL.json.
- Add a T-1 study whose `plus` and `minus` use metric arrays from development worlds: `plus` restricted to α ≥ 0.65,
  `minus` with NT applied.
- If G7c is adopted (R1-1), give it a study whose `minus` changes a baseline.

---

## Minor

### R1-16 (minor). Version labels disagree, and the freeze record cannot live in a frozen file

**Where:**
- PREREG lines 3 and 10-11: "DRAFT 3", but "Version: draft 2" and dates for drafts 1 and 2 only.
- `audit/README.md` line 5: "DRAFT 2".
- §9 (lines 252-256): "Frozen on / Manifest core hash / Signed off by: to be filled in".

**Reason.**
- The version labels disagree.
- The §9 fields sit in a file that is itself frozen. Filling them in after `freeze write` changes the file and breaks
  the manifest, and the runner then refuses to start.

**Fix.**
- Use "draft 3" everywhere.
- Move the freeze record (date, core hash, salt, sign-off) to a separate file outside the manifest, for example
  `prereg/FREEZE_RECORD.md`, and say so in §9.

### R1-17 (minor). Text and code differ in details of seeds, replacement and τ

**Where:** §7 (lines 206, 210); §6.2, N2 (line 149); `seeds.py:18`; `worldset.py:76-85`; `tau.py:18-21`.

**Reason.**
- The role `n2` is used in the code but not listed in §7.
- "Test world i" in N2 and in the perm seeds means the draw index, which counts rejected draws, not the index among
  valid worlds.
- A generator failure (RuntimeError) is a replacement reason that D5 does not list. Also, `except RuntimeError`
  swallows RecursionError and NotImplementedError raised by `encode`.
- `compute_taus` silently skips worlds with a None metric; D1 does not say so.

**Fix.**
- List `n2` among the roles in §7.
- Write "i is the draw index".
- Add "a world whose generator fails after max_attempts is replaced", and catch only a dedicated exception class for
  that case.
- Treat a calibration world with an undefined metric as invalid under D5, and replace it instead of skipping it.

### R1-18 (minor). Small gaps in individual checks

**Where:** `checks.py:78-82, 102` (G1), `checks.py:223-250` (G5); `per_world.py:17, 61-62` (G2); §3.2, G6 text (line 74).

**Reason.**
- **G1 (ii)** looks only at outlier entities, and an outlier with no D_derive rows is skipped silently. A twin that
  derives μ⁻ from μ⁺ only for normal entities would pass.
- **G5** compares the arrays of unit values without the atom keys, provenance or status.
- **G2:** the subprocess runs with PYTHONHASHSEED=1, but nothing makes the parent's seed differ. If the parent also
  runs with 1, the seed is not "different".
- **G6:** the text "every other fact has status HYPOTHESIS" is vacuous, because there are only three statuses. The
  code checks the meaningful condition: every fact outside the recomputed fixpoint is a HYPOTHESIS.
- **G5's claim is worded backwards.** "Pattern computation does not leak into validation data" should read
  "validation data do not leak into pattern computation".

**Fix.**
- G1 (ii): check the class atoms of all entities.
- G5: compare dicts that map each atom to (μ⁺, μ⁻, status, provenance).
- G2: set the parent's PYTHONHASHSEED explicitly, or compare two subprocesses with different seeds.
- Reword G6 and G5 as above.

### R1-19 (minor). The fixed wording leaves out the numbers that make a quantitative verdict readable

**Where:** §4 (lines 105-107); `aggregate.py:79-86`.

**Reason.**
- For G7, G8 and T-1, the FAILS sentence gives only the number of failing worlds, and the HOLDS sentence omits the
  Wilson bound.
- A FAILS with 27 of 30 worlds holding reads the same as one with 5 of 30.

**Fix.** For the quantitative tests, add: "… <n_holds> of <n_defined> defined worlds hold (Wilson lower bound <b>,
threshold 0.80); <n_undefined> undefined."

### R1-20 (minor). The draft does not address several protocol checklist items

**Where:** PROTOCOL §1.3 ("2 to 4 primary criteria"); the checklist items on model test or data replicate, input
dates, the "new inputs" condition and directional hypotheses.

**Reason.**
- There are nine confirmatory verdicts and no statement on multiplicity. The three quantitative tests each run at
  one-sided 5%.
- The items that do not apply are not written down.
- T-1 claims the absence of a trade-off. Generic factors, such as narrow feasible sets and duplicates across k, push
  it toward HOLDS (R1-2).

**Fix.**
- Name T-1, G7 and G8 as the primary tests, and call G1–G6 implementation checks.
- Add a sentence on multiplicity: there is no combined verdict; each quantitative test runs at 5%; the family-wise
  error over the three is up to about 14%.
- Write "not applicable (synthetic worlds)" for the input-dates and "new inputs" items.
- Label the run "model test on new worlds".

### R1-21 (minor). The twin diagnostic has no pre-registered reading

**Where:** §6.2 (lines 158-161).

**Reason.**
- The expected outcome is "FAILS", but nothing says what it means when a twin does not fail on a world.
- On 20 development worlds every real-run twin failed on 20 of 20, except two:
  - N7: 13 FAILS and 7 UNDEFINED;
  - NT: 17 FAILS and 3 UNDEFINED, on the same worlds where the fixed system is undefined.
- For N4, a score tie straddled the k₀ cut on 30 of 30 development worlds, so N4 can act on every world.

**Fix.** Add: "For each test, report the number of worlds where both the fixed system and its twin HOLD. If it is
above 0, qualify the HOLDS verdict: 'the detector did not separate on <n> worlds'."

### R1-22 (minor). The runner's freeze check relies on an external truth_gate that is not pinned

**Where:** `run_v02.py:54-60`.

**Reason.**
- `verify_freeze` imports `truth_gate.freeze` from `TRUTH_GATE_DIR`, or from a default path in the designer's
  workspace.
- It does not check the version at run time, while `certify.py` does check the tag.

**Fix.** Choose one:
- check that `truth_gate.__version__ == "0.5.1"`, and compare the SHA-256 of `truth_gate/freeze.py` with a value
  recorded in GATE_TOOL.json; or
- copy the short verifier into `audit/` so that it is frozen with the rest.

---

## Checklist of the protocol against the draft

| Item | State in draft 3 |
|---|---|
| Tautology question | Only partly answered. G1, G3 and G6 are also decided by construction (R1-6), and T-1's answer is wrong (R1-2). |
| Known and prospective parts separated | Yes, but the expected verdicts that follow from the pilot are missing (R1-10). |
| Criteria, verdict mapping, UNDEFINED | Written. The G7 claim does not match its check (R1-1). The NaN and equality rules are missing (R1-7, R1-8). |
| Interpretations with sensitivity arms | Present. T-1's structure and the outcome-related UNDEFINED worlds need arms (R1-2, R1-13). |
| A negative control that can make each criterion fail | Yes. The twins fail on (nearly) every development world. N7 is UNDEFINED on about a third (R1-21). |
| Fidelity check against an independent implementation | F2 yes. F1 no, F4 only partly, F3 not blind (R1-11). |
| The minus world changes the data the criterion reads | Yes in every certificate. For G7, only `hv_system` changes (R1-1, R1-15). |
| Tolerances above numerical resolution | No at exact equality (R1-8). |
| D4 clean | Reachability shown with twins on development worlds. |
| Nobody has seen the real result | Not demonstrable as designed (R1-3). |
| Manifest written, runner verifies it | The runner verifies; the manifest is not yet written; the §9 record cannot sit inside it (R1-16). |
| Run-to-run drift | Zero on one machine and one NumPy build only (R1-14). |
| Power of each confirmatory test | Given only for 30 defined worlds; wording inaccurate (R1-9). |
| Model test or data replicate | Not stated (R1-20). |
| Steps before the data enforced by the runner | Partly: τ is not verified, seeds are computable before the freeze, partial outputs are written before a stop (R1-3, R1-4, R1-12). |
| Input dates; "new inputs" condition | Not applicable; not written down (R1-20). |

## Overall judgment

The design is worth running once the two blocking findings and the integrity findings (R1-3, R1-4, R1-11, R1-12,
R1-14) are fixed. Its claims should then be stated more narrowly than draft 3 states them.

- **The machinery is strong.** The audit layer follows the text closely: the collect and judge pairs, the aggregation,
  the seed formula and D5 all match apart from small details. Every twin acts on (nearly) every development world, and
  the F2 and F4 controls agree to 1e-15.
- **Most of the content is already settled before the run.**
  - G1–G6 are regression checks that hold by construction.
  - G7 reduces to "the system's hypervolume is positive", because no baseline can score.
  - G8 is in practice a zero-tolerance test of whether abduction changes any decided encoded atom.
  - T-1 mainly measures whether the D1 bounds admit the 0.60 source.
  - Given the disclosed pilot, T-1 and G8 are expected to FAIL.
- **What remains to fix.** The draft should say all of this in its claims and its fixed wording. It should make seed
  derivation and the τ commitment verifiable. It should pre-register what happens after a stop, a crash or an F3
  disagreement. If the author wants T-1 to test a graded relation between uncertainty and new false conclusions, that
  is a design change, to be decided openly with the pilot disclosure in view.

---

## Appendix: commands run and results

All runs used `C:\Users\user\AppData\Local\Python\pythoncore-3.14-64\python.exe` (Python 3.14.2, NumPy 2.4.1). They
ran on the writable copy `out/scratch/repo`, with `TRUTH_GATE_DIR=<task>/truthgate` and `PYTHONDONTWRITEBYTECODE=1`.
My scripts are in `out/scratch/`. I did not run `audit/run_v02.py` without `--dev`, did not create `run/`, and did not
run `audit/gate/certify.py` or the gate.

1. **Unit tests:** `python -m unittest discover -s tests` (in the copy). Result: 192 tests, 1 error, as predicted:
   `test_checkout_matches_the_tag_and_is_recorded` raised "truthgate is not a git checkout".
   - **Note:** two tests start git through the code they test. `test_checkout_matches_the_tag_and_is_recorded` calls
     `certify.check_checkout()`, which runs `git -C <truthgate> rev-parse HEAD`. `test_test_mode_needs_a_committed_unmodified_tau`
     calls `run_v02.check_tau_committed`, which runs `git rev-parse --is-inside-work-tree`.
   - These read-only git calls ran in folders that are not git repositories, and they failed. I did not intend them,
     and I did not run the suite again.
   - The suite's dev end-to-end test ran `run_v02 calibrate/test --dev` (3 calibration and 2 test worlds) and wrote
     `out/scratch/repo/run_dev/`. I did not read its verdict files.
2. **Certificate summary:** `python -I out/scratch/cert_summary.py out/scratch/repo/audit/gate`.
   - All nine certificates are FALSIFIABLE, in full mode with tool 0.5.1 and NumPy 2.4.1.
   - Each body hash verifies, and each `module_sha256` matches its study file.
   - G1: `probe:noise` held on 1 of 100 samples.
   - G7: the minus has 42 of 100 UNDEFINED, and `changed_keys` is `['hv_system']`.
3. **Diagnostics part 1:** `python out/scratch/analyse_dev.py 30` (dev "world-test" mapping, 30 valid worlds).
   - **Draws:** 2 rejected, both `h_too_small`.
   - **Dev τ:** s = 0.80645, d = 0.019231 (= 1/52), t = 0.97468, b = 0.63158.
   - **k-invariance:** the largest |metric(α, k) − metric(α, 0)| for uncertainty, new_true and new_false is 0.0.
     Feasibility differs across k at some α on 8 worlds.
   - **Feasibility:** no feasible point on 3 worlds; default (0.7, 5) infeasible on 7.
   - **Feasible sets:** wherever a feasible point exists, the highest feasible α is 0.80. α ≤ 0.60 is feasible on a
     minority of worlds; I withhold the count because, with item 5, it would give T-1's pilot rate.
   - **Distinct feasible uncertainty values per world:** {0: 3, 1: 1, 2: 6, 3: 8, 4: 6, 5: 5, 7: 1}. The uncertainty
     span among feasible points has a median of 0.047 and a maximum of 0.338.
   - **Baselines:**
     - no baseline scored above 0 on any world;
     - feasible baseline points: echo at 77 (world, α) pairs, the others at none;
     - front hypervolume against the best single-α score: no difference on any world.
   - **Deviation denominators** (minimum to maximum): 18–36 at 0.95, 21–40 at 0.90, 23–43 at 0.85, 36–68 at 0.80,
     38–68 at 0.75, 39–70 at 0.70 and 0.65, 52–92 at 0.60 to 0.50.
   - **|I| and fidelity:** |I| ranges from 18 to 96; fidelity was never None.
   - **Abduction:**
     - G6 was never UNDEFINED;
     - there were 20–64 candidates at α₀;
     - a score tie straddled the k₀ cut on 30 of 30 worlds.
   - **|H|:** 14 to 101, median 27.
4. **Diagnostics part 2:** `python out/scratch/analyse_dev2.py 20 twins`.
   - **Constraints failing at k = 0:**
     - α ≥ 0.85: uncertainty > τ_b on 20 of 20 worlds;
     - α 0.65–0.80: each constraint fails on at most 2 worlds;
     - α = 0.60: fidelity < τ_s on 12, consistency < τ_t on 10, deviation > τ_d on 1.
   - **Verdict-B atoms outside I:** 0 at every α.
   - **Decided atoms outside K:** median 2 in 0.65–0.80 and 7 at ≤ 0.60.
   - **Inside 0.65–0.80**, the largest new_false rise toward lower uncertainty was 0.0000, on every world.
   - **Twins with the real-run mechanisms** (subprocesses on):
     - N1a, N1b, N2, N3, N4, N5, N6 and N8: FAILS on 20 of 20;
     - N7: 13 FAILS and 7 UNDEFINED;
     - NT: 17 FAILS and 3 UNDEFINED.
5. **Diagnostics part 3:** `python out/scratch/analyse_dev3.py 30`. On the worlds where α = 0.60 is feasible, new_false
   rose from 0.65 to 0.60 by a median of 0.154 (minimum 0.071, maximum 0.188).
6. **F controls on 20 development worlds:** a `-c` script running `audit.fidelity.run_controls` and
   `max_center_difference`. No disagreement; the largest F4 center difference was 1.33e-15.
7. **Wilson thresholds and power:** `python -I out/scratch/wilson_power.py`.
   - The minimum number of HOLDS worlds and P(HOLDS) for n = 16 to 30 are in R1-9.
   - n = 30 needs 28 (lower bound 0.8173; with 27 it is 0.7745), which confirms "28 of 30".
   - P(HOLDS | 0.706, n = 30) = 0.0026.
8. **Floating point at the tolerances:** a `-c` script over denominators 18 to 99.
   - 79 of the 194 differences of exactly 0.05 evaluate as > 0.05;
   - 34 of the 50 differences of exactly 0.02 evaluate as > 0.02;
   - example: `4/20 - 3/20 = 0.05000000000000002`.
