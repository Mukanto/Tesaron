# Tesaron: implementation spec for v0.1

Status: draft, 2026-11-22. The main session (Claude) wrote the design; the author (Hazar Şimşek) made the decisions.
The Turkish design record is in the author's wiki (spec draft and decisions K1–K6, A-1–A-8). This file is the
authoritative implementation spec for v0.1.

**Rule for the implementer:** do not change a definition in this file. If something here is ambiguous, contradictory or
impossible, stop and report it instead of choosing.

## 0. Scope of v0.1

Build the core pipeline and its metrics, with unit tests and one smoke run:

```
world → observations → encoder (sampling, split, PCM) → meaning units → Belnap interface
      → decoder (two-channel Datalog + single-step abduction) → output → metrics → constrained Pareto + hypervolume
```

Also build the degenerate baselines (§10), so the criterion code can be checked.

**Not in v0.1:**
- the tests G1–G8 and their faulty twins;
- Truth_Gate certificates;
- pre-registration;
- calibration and test worlds.

Those come in v0.2. Seeds are restricted (§11).

## 1. Conventions

- **Python and dependencies:** Python ≥ 3.12 (developed on 3.14, run as `py`). numpy and the standard library only; no
  other runtime dependency.
- **Package layout:** package `tesaron/` with the subpackages `worlds`, `encoder`, `meaning`, `belnap`, `decoder` and
  `criterion`. In v0.1 the top-level directories `audit/` and `prereg/` held only a README placeholder; v0.2 fills
  them (revision S-8).
- **Determinism:**
  - Every random draw uses a `numpy.random.Generator(numpy.random.PCG64(seed))` that is passed explicitly. Never use
    the global numpy RNG, the `random` module, or `hash()` for ordering.
  - Any iteration over a set or dict that can affect output goes through `sorted()`.
- **Canonical serialization** (used for hashes): `json.dumps(obj, sort_keys=True, separators=(",", ":"),
  ensure_ascii=True)`, with every float rounded with `round(x, 12)` first and numpy types converted to Python types.
- **Atoms:** `Atom(pred: str, args: tuple[str, ...])`, ordered by `(pred, args)`.
  - Entities are `e00`…`e19`.
  - Classes are the unary predicates `c0`, `c1`, `c2`.
  - Relations are the binary predicates `r0`, `r1`, `r2`.
- **Vocabulary:** all class atoms `c_k(e)` (60), plus all relation atoms `r_a(x, y)` with x ≠ y (3 × 380 = 1140); 1200
  atoms in total. Atoms outside the vocabulary (for example `r(x, x)`) are discarded wherever they arise.
- **Enums:**
  - Channels: `POS` (evidence for) and `NEG` (evidence against).
  - Belnap values: `T`, `F`, `B`, `U`.
  - Epistemic status, from strongest to weakest: `OBSERVED` > `DERIVED` > `HYPOTHESIS`.
  - Computational status: `NOT_COMPUTED`, kept separate from the epistemic statuses. It is used only when the encoder
    does not converge.

## 2. Types: Membership and Probability

A membership degree is the degree to which something belongs to a set; it is not a probability. The types enforce this.

- **`Membership`:**
  - An immutable wrapper of a float in [0, 1]; a value outside that range raises `ValueError`.
  - Supports the comparisons `<`, `<=`, `>`, `>=` and `==` with another `Membership` and with a plain `int` or `float`
    (thresholds).
  - Supports the module functions `tconorm_max(*ms)` and `tnorm_min(*ms)`, and the property `.value`.
  - Arithmetic operators (`+ - * /`, unary `-`) are not defined and raise `TypeError`.
- **`Probability`:** the same shape, but a separate class. It is used only inside the world generator.
- **No mixing:** any operation or comparison between a `Membership` and a `Probability` raises `TypeError`.
- **Encoder APIs** check `isinstance(x, Membership)` for every degree they receive and raise `TypeError` otherwise.
- **The only conversion** is one explicit, documented function, `support_degrees_from_world(world) -> dict[str,
  Membership]`. Its docstring must say: "v0 modelling choice: the context's support degree for a source equals,
  numerically, the generator's probability that the source reports correctly; in the encoder it is a membership degree
  and is only combined with max".

## 3. World generator (`tesaron.worlds`)

`generate_world(seed: int, params: WorldParams = WorldParams()) -> World`. The output is fully determined by `seed`.

**Defaults** (the counts of entities, classes, rules and sources are author decision A-8; the number of relations and
everything else are Claude's defaults and may change only before the v0.2 freeze):

| Parameter | Default |
|---|---|
| n_entities, n_classes, n_relations, n_sources | 20, 3, 3, 3 |
| feature_dim | 2 |
| prototypes | class k at angle 2πk/3 on a circle of radius 3.0 (fixed, not random) |
| feature noise σ | 0.6 |
| rows_per_entity | 5 |
| n_outliers | 2 |
| n_overlaps | 2 |
| base_density | 0.04 |
| source reliabilities | (0.95, 0.80, 0.60), as `Probability` |
| q_true | 0.5 |
| q_false | 0.02 |
| max_attempts | 1000 |

**Entities and base classes:**
- Base classes are assigned round-robin (balanced) and then shuffled.
- Every entity has exactly one base class.
- The true mean of an entity depends on its group:
  - normal entities: the prototype of their base class;
  - outliers: radius 7.0, at a random angle;
  - overlaps: 40% of the way from the prototype of their base class toward a randomly chosen other prototype.
- Which entities are outliers and which are overlaps is drawn **stratified by base class** (revision S-1, §15):
  - Take a random permutation of the classes.
  - Assign the `n_outliers + n_overlaps` special slots round-robin over that class order; outliers come first, then
    overlaps.
  - For each slot, pick a random entity of that class that is not yet special.
  - With the defaults, the classes get 2, 1 and 1 special entities, so every class keeps at least 4 normal entities.

**Feature rows:** each feature row is the true mean plus N(0, σ²·I). There are `rows_per_entity` rows per entity, with
ids `f0000`, `f0001`, … in entity order.

**Base relation facts:** each ordered pair (x ≠ y) is, for each relation independently, a base fact with probability
`base_density`.

**Rules:** exactly 6 rules, one per template. The indices are drawn with the world RNG, with a ≠ b, b ≠ c where stated,
and i ≠ j where stated.

| id | Template |
|---|---|
| R1 | `c_j(Y) ← r_a(X, Y) ∧ c_i(X)` |
| R2 | `r_b(X, Y) ← r_a(X, Y) ∧ c_i(X)`, a ≠ b |
| R3 | `r_b(Y, X) ← r_a(X, Y)`, a ≠ b |
| R4 | `r_c(X, Z) ← r_a(X, Y) ∧ r_b(Y, Z)` |
| R5 | `¬r_a(X, Y) ← r_b(X, Y) ∧ c_i(X)`, a ≠ b |
| R6 | `¬c_j(X) ← c_i(X)`, i ≠ j |

**Truth:**
- The world's true atoms are the closure of the base class facts and base relation facts under the positive-head rules
  (the least model).
- Every vocabulary atom outside the closure is false.
- The truth is classical. Belnap values describe only the system's epistemic state, never the world.

**Acceptance:** a draw (rule indices and base facts) is accepted only if both conditions hold:
1. **Consistency:** no ground instance of R5 or R6 has a true body and a true head atom.
2. **Every rule fires at least once:** some ground instance has a true body, and for R5 and R6 the head atom is false.

Otherwise the generator draws again from the same RNG stream. After `max_attempts` failed draws it raises
`RuntimeError`. Feature rows are drawn after acceptance.

**Sources and report rows:**
- For each source and each true base relation fact, the fact is "considered" with probability `q_true`.
- For each false relation atom, it is considered with probability `q_false`.
- True relation atoms that are derived but not base are never considered.
- For each considered atom, the source reports the correct polarity with probability equal to its reliability, and the
  wrong polarity otherwise.
- A report row is `(row_id, source, atom, polarity)`, with ids `r0000`, … in deterministic order. Sources never report
  class atoms in v0.1.

**`World` holds:** the seed, the params, the entities, the base classes, the outlier ids, the overlap ids, the feature
rows, the base facts, the rules, the set of true atoms, the source reliabilities and the report rows.
`world.truth(atom) -> bool`.

## 4. Context (`tesaron.encoder.context`)

`Context` is a frozen dataclass holding the encoder's and decoder's parameters (the "awareness"):

| Field | Value |
|---|---|
| entities, vocabulary | from the world |
| prototypes | the world's fixed prototypes; used as PCM initial centers |
| eta | 2σ² for every class, where σ is the world's feature noise (0.72 with the defaults; revision S-2, §15) |
| m (fuzzifier) | 2.0 |
| max_iter, tol | 1000, 1e-6 (revision S-4, §15) |
| support | `support_degrees_from_world(world)` |
| rules | the world's rules (in v0.1 the decoder is given the true rules) |
| alpha | 0.7 (one threshold; author decision A-3) |
| k_abduction | 5 |
| sampling_ratio | 0.8 |
| derive_fraction | 0.7 |
| encoder_seed | an explicit int |
| epsilon_band | 0.05 |

## 5. Encoder (`tesaron.encoder`)

`encode(world, context) -> Encoding`. The steps:

1. **Selection.** Sort all rows (feature and report) by row id; N rows in total. With the encoder RNG, take the first
   `round(sampling_ratio·N)` rows of a permutation, then sort them by row id.
2. **Split.** Permute the selected rows again with the same RNG. The first `round(derive_fraction·n)` rows form
   `D_derive`, the rest form `D_validate`; both are sorted by row id.
3. **PCM (Krishnapuram and Keller 1993)** on the feature rows of `D_derive` only:
   - The initial centers are the prototypes.
   - Each iteration updates the typicalities and then the centers:
     - u_ik = 1 / (1 + (d²_ik / η_k)^(1/(m−1)));
     - c_k = Σ_i u_ik^m x_i / Σ_i u_ik^m.
   - The loop stops when the largest center shift falls below `tol`. If that has not happened after `max_iter`
     iterations, the encoder has not converged.
   - The fitted parameters are the final centers, the number of iterations, the converged flag and the degenerate
     flag.
   - **Degeneracy check (revision S-3, §15):** after the loop, the fit is degenerate if the smallest distance between
     two fitted centers is below 0.5 × the smallest distance between two prototypes. A degenerate fit is treated
     exactly like non-convergence: the class units get status `NOT_COMPUTED` and produce no facts. Coincident centers
     must never pass silently.
4. **Entity typicality.** For an entity with at least one feature row in `D_derive`, x̄_e is the mean of those rows and
   u_ek = 1 / (1 + (|x̄_e − c_k|² / η_k)^(1/(m−1))), as a `Membership`. The typicalities are **not** normalized.
5. **Meaning units:** `MeaningUnit(atom, mu_pos: Membership, mu_neg: Membership, provenance: tuple[row_id, ...],
   status)`.
   - **Class atom `c_k(e)`:**
     - mu_pos = u_ek and mu_neg = Membership(0.0).
     - The provenance is the entity's feature-row ids in `D_derive`.
     - The status is `OBSERVED`, or `NOT_COMPUTED` if PCM did not converge.
     - An entity with no feature row in `D_derive` gets no class units.
     - **Forbidden:** computing mu_neg from mu_pos (for example 1 − mu_pos). Low typicality is absence of evidence, not
       refutation. Put this as a comment at the code site.
   - **Relation atom** (only if it has at least one report in `D_derive`):
     - mu_pos = tconorm_max over the support degrees of its positive reports, or Membership(0.0) if there are none.
     - mu_neg is the same for its negative reports.
     - The provenance is the report row ids.
     - The status is `OBSERVED`.
6. **Validation units.** Build the same kind of units from `D_validate`, using the same fitted centers (no refit). They
   are used only by the descriptive metric `validation_agreement` (§8). Nothing fitted may depend on `D_validate`.

`Encoding` holds: the selected, derive and validate row ids; the fitted parameters; the units (keyed by atom, sorted);
and the validation units.

## 6. Belnap interface (`tesaron.belnap`)

`to_value(mu_pos, mu_neg, alpha)`: pos = (mu_pos ≥ alpha) and neg = (mu_neg ≥ alpha). Equality counts as ≥.

| pos | neg | value |
|---|---|---|
| yes | no | T |
| no | yes | F |
| yes | yes | B |
| no | no | U |

- **Initial facts:** `(POS, atom)` if pos and `(NEG, atom)` if neg, each with status `OBSERVED` and the unit's
  provenance. A unit with status `NOT_COMPUTED` produces no facts.
- **Encoded value:** `enc(a)` is the interface value of atom a, or `U` if a has no unit.
- **Boundary band (descriptive only):** a unit is on the boundary if |mu_pos − alpha| < epsilon_band or
  |mu_neg − alpha| < epsilon_band.

## 7. Decoder (`tesaron.decoder`)

### 7.1 Rules

- **`Literal(pred, args, channel)`:** an arg is either a variable (a string starting with an uppercase letter) or an
  entity constant.
- **`Rule(id, head: Literal, body: tuple[Literal, ...])`:**
  - **Safety:** every head variable must occur in the body; otherwise raise `ValueError`.
  - **Body literals:** a literal with channel `POS` means "a POS fact is present"; with channel `NEG` it means "a NEG
    fact is present". This is strong negation, never negation as failure.
  - **Head:** a head with channel `POS` adds a POS fact; with channel `NEG` it adds a NEG fact.
- **Belnap–Dunn connectives,** for evaluating compound queries; implement and test them even though v0.1 rules only use
  conjunctive bodies:

  | | pos | neg |
  |---|---|---|
  | ¬a | a.neg | a.pos |
  | a ∧ b | a.pos ∧ b.pos | a.neg ∨ b.neg |
  | a ∨ b | a.pos ∨ b.pos | a.neg ∧ b.neg |

### 7.2 Evaluation

- **Two functions:** `naive_eval(facts, rules, vocab)` and `seminaive_eval(facts, rules, vocab)`. Each returns the least
  fixpoint as a set of `(channel, atom)`. Derived atoms outside the vocabulary are discarded.
- **Equivalence:** the two results must be equal; this is checked by tests (§13).
- **Termination:** the fixpoint is reached within at most 2·|vocab| + 1 rounds. Assert this.
- **Contradiction:** POS and NEG facts for the same atom may coexist (the value is B). Nothing else follows from that;
  there is no explosion.
- **Derivation records:** for every derived fact, keep the first derivation found, as `(rule_id, premise facts)`. The
  search order is deterministic: rules sorted by id, then substitutions in sorted order. The input order of facts and
  rules must not change any result or record.

### 7.3 Two passes, statuses and abduction

1. **Pass 1:** deduction from the interface facts (status `OBSERVED`). New facts get status `DERIVED`. A fact that is
   both observed and derived keeps `OBSERVED`.
2. **Abduction** (single step, cap `k_abduction`; author decision A-4). Work over the pass-1 fixpoint F1.
   - **Candidates.** Take every rule and every ground substitution θ such that all of the following hold:
     - the head θ is in F1 with status `OBSERVED`;
     - exactly one body literal bθ is missing from F1, and all the other body literals are present;
     - bθ is fully ground (all its variables are bound by the head or by the present body literals);
     - the atom of bθ is in the vocabulary;
     - the atom of bθ has neither a POS nor a NEG fact in F1, i.e. its value is U.

     The candidate is then the missing literal as `(channel, atom)`. No existential guessing.
   - **Score:** the number of distinct `(rule_id, θ)` instances the candidate completes.
   - **Ranking:** score descending, then `(channel, pred, args)` ascending, with `POS` before `NEG` (revision S-9).
     Keep the top `k_abduction`. With k = 0
     there is no abduction.
3. **Pass 2:** add the kept candidates as facts with status `HYPOTHESIS` and deduce again from F1 plus the hypotheses.
   Facts that are new in pass 2 get status `HYPOTHESIS`. Pass-1 facts keep their status.

### 7.4 Output

For every vocabulary atom the decoder gives:
- the facts present per channel, each with its status and its provenance or derivation record;
- **`full(a)`:** the Belnap value from all facts;
- **`verdict(a)`:** the Belnap value from facts with status `OBSERVED` or `DERIVED` only. Hypotheses are descriptive
  (author decision A-6).

## 8. Metrics (`tesaron.criterion.metrics`)

W(a) ∈ {T, F} is the world truth. Several sets come first:

| Set | Definition | Depends on alpha? |
|---|---|---|
| E | atoms with a meaning unit from `D_derive` (any degrees) | no |
| I | atoms in E with enc(a) ≠ U | yes |
| H | atoms not in E that are entailed by the world rules from the W-values of E | no |
| K | E ∪ H | no |

H is computed with `seminaive_eval`, starting from POS a for every a in E with W(a) = T and NEG a for every a in E with
W(a) = F. H is every atom outside E that appears in that fixpoint, in either channel. Assert that the derived channel of
each H atom agrees with W, and assert that no H atom has both channels.

**H always uses the world's rules R\*, never the rules given to the decoder** (revision S-5, §15). In v0.1 the two are
the same, but in v0.2 a faulty twin may be given different rules, and the target set must not move with it.

| Metric | Definition | Role |
|---|---|---|
| fidelity | \|{a ∈ I : full(a) = W(a)}\| / \|I\|; None if I is empty | constraint ≥ τ_s |
| deviation | \|{a ∈ I : enc(a) ∈ {T, F} and full(a) ≠ enc(a)}\| / \|{a ∈ I : enc(a) ∈ {T, F}}\|; 0 if the denominator is 0 | constraint ≤ τ_d |
| consistency | 1 − \|{a ∈ K : full(a) = B}\| / \|K\| | constraint ≥ τ_t |
| uncertainty | \|{a ∈ K : verdict(a) = U}\| / \|K\| | constraint ≤ τ_b |
| new_true | \|{a ∈ H : verdict(a) = W(a)}\| / \|H\|; None if H is empty | Pareto axis y |
| new_false | \|{a ∉ I : verdict(a) ∈ {T, F} and verdict(a) ≠ W(a)}\| / \|{a ∉ I : verdict(a) ∈ {T, F}}\|; 0 if the denominator is 0 | Pareto axis x = 1 − new_false |

In these formulas B and U never equal W.

**Reading:**
- Expansion (new_true) is about atoms with no evidence at all.
- Deciding atoms that have weak evidence reduces uncertainty instead.
- Every decision on an atom the encoding did not assert can count as new_false.

**Descriptive outputs, not in any verdict:**
- **Hypotheses:** `hyp_count` is the number of atoms decided (T or F) in `full` but U in `verdict`. `hyp_correct` is how
  many of those match W.
- **`validation_agreement`:** take the atoms whose validation-unit interface value is T or F and whose verdict is T or
  F; this is the share where the two are equal (None if there are none).
- **`boundary_share`:** the share of meaning units on the boundary band.
- **Counts:** \|E\|, \|I\|, \|H\|, \|K\|.

## 9. Wisdom criterion (`tesaron.criterion.wisdom`)

- **Configurations:** a configuration is (alpha, k_abduction). The creativity grid in v0.1 is alpha ∈ {0.9, 0.8, 0.7,
  0.6, 0.5} × k ∈ {0, 5, 10}. The final grid is fixed in the v0.2 pre-registration.
- **Point:** each configuration on one world gives a point (x, y) = (1 − new_false, new_true).
- **Feasibility:** a point is feasible if fidelity ≥ τ_s, deviation ≤ τ_d, consistency ≥ τ_t and uncertainty ≤ τ_b.
  - A None in fidelity or new_true makes the point infeasible.
  - The τ values are parameters in v0.1; the rule that calibrates them is fixed in v0.2.
- **`pareto_front(points)`:**
  - The front is computed over the feasible points only.
  - p dominates q if p ≥ q in both coordinates and p > q in at least one.
  - The output order is deterministic: x descending, then y descending.
- **`hypervolume(front, ref=(0, 0))`:** the area of the union of the rectangles [0, x] × [0, y]. A single point gives
  x·y. The score of an infeasible point is 0.
- **`t1_world(points, delta)`** (author decision A-7; v0.1 implements only the function, it evaluates no hypothesis):
  - Over the feasible points of one world, consider every pair (p, q) with uncertainty(q) < uncertainty(p).
  - The world passes iff new_false(q) − new_false(p) ≤ delta for every such pair: where uncertainty is lower, new_false
    is not higher by more than delta.
  - The result is "undefined" if fewer than two feasible points have distinct uncertainty values.
  - delta is a parameter (default 0.05); its value is fixed in the v0.2 pre-registration.

## 10. Baselines (`tesaron.criterion.baselines`)

Each baseline returns an output in the same format as the decoder, so the metrics apply unchanged:

| Baseline | full and verdict |
|---|---|
| echo | enc(a) for every atom (no deduction, no abduction) |
| all_true | T for every atom |
| all_false | F for every atom |
| all_unknown | U for every atom |
| all_both | B for every atom |

In v0.1 the only checks on baselines are structural (§13). Any claim that the real system beats them is G7, which comes
in v0.2.

## 11. Seeds

- v0.1 code, tests and smoke runs use only seeds in the range 900000–900999, for both world and encoder seeds.
- The calibration and test seeds of v0.2 are derived from the freeze manifest's core hash and a salt that is drawn
  only after the freeze commit is public (PREREG v0.2 §7; revision S-8). They are therefore neither chosen nor seen in
  advance.

## 12. Smoke command

`py -m tesaron.smoke --world-seed 900001 --encoder-seed 900101 [--out FILE]` runs the full pipeline on one world over
the default grid.

It prints a JSON summary:
- the world statistics, \|E\|, \|I\|, \|H\| and \|K\| per alpha;
- every metric for every grid point;
- the feasibility of each point under the placeholder τ values (τ_s 0.8, τ_d 0.05, τ_t 0.9, τ_b 0.5);
- the front, the hypervolume and the baselines' metrics;
- the run time.

The placeholder τ values must be labelled `"placeholder, not frozen"` in the output. Nothing is written to disk unless
`--out` is given.

## 13. Tests

The tests use standard-library `unittest` and are run with `py -m unittest discover -s tests`. At least the following:

**Types:**
- Arithmetic on `Membership` and on `Probability` raises `TypeError`.
- Mixing the two raises `TypeError`.
- A value outside [0, 1] raises.
- `tconorm_max` is idempotent and `tnorm_min` is correct.
- The encoder rejects degrees that are not `Membership`.

**Class units:**
- mu_neg is 0 whatever mu_pos is.
- No code path derives mu_neg from mu_pos.

**PCM:**
- It converges on hand-made data.
- An outlier point gets a typicality sum below 0.5, so typicalities are not normalized.
- Initialization is at the prototypes.
- With max_iter = 1 and tol = 0 it does not converge, and the class units get status `NOT_COMPUTED` and produce no
  facts.
- Hand-made data whose centers coincide sets the degenerate flag. The class units then get `NOT_COMPUTED` and produce
  no facts.

**Encoder:**
- The same world, context and seed give an identical canonical hash.
- A different encoder seed gives a different selection.
- Replacing every feature value in `D_validate` with garbage leaves the fitted centers bit-identical.

**Belnap:**
- All four rows of the table.
- Equality with alpha counts as ≥.
- The Belnap–Dunn connectives.

**Datalog:**
- `seminaive_eval` equals `naive_eval` on at least 200 random small programs over both channels, including NEG body
  literals and NEG heads.
- Hand-made examples, including transitive closure.
- POS and NEG facts for the same atom give B without affecting unrelated facts.
- The safety check raises.
- The vocabulary filter discards out-of-vocabulary atoms.
- The termination bound holds.
- Shuffled input order of facts and rules gives the same fixpoint and the same derivation records.
- A subprocess test runs the smoke pipeline under three different `PYTHONHASHSEED` values and compares the canonical
  output hashes.

**Abduction:**
- A hand-made example with its expected candidate.
- The cap k is respected.
- The ranking is deterministic.
- Candidates are only U atoms.
- Pass-2 facts get status `HYPOTHESIS`.
- `verdict` ignores hypothesis facts.

**World:**
- Each seed gives a deterministic world.
- The acceptance conditions hold.
- There are no reflexive relation atoms.
- Classes are balanced.
- The counts of outliers and overlaps are correct.
- The special entities are stratified: no class has more than ⌈(n_outliers + n_overlaps) / n_classes⌉ special
  entities, checked over seeds 900000–900099.

**Metrics:**
- Tiny hand-made worlds with exact expected values for every metric.
- The H soundness assertion.
- Examples for the Pareto front and the hypervolume.
- `t1_world` examples, including the undefined case.

**Baselines:**
- The structural checks: echo has new_true = 0 and therefore hypervolume 0; all_unknown and all_both have fidelity 0
  and are infeasible.

## 14. Repository files

- `README.md`, `SPEC.md` (this file) and `pyproject.toml`.
- `tesaron/…` and `tests/…`.
- `audit/README.md` and `prereg/README.md`, each saying "v0.2".
- `.gitignore`.

The license is MIT (`LICENSE`), the author's decision of 2026-11-22. The implementer must not commit, push, add
dependencies or use seeds outside §11.

## 15. Revisions before any freeze

S-1–S-5 were found on development seeds (900000–900099) during the first smoke checks of v0.1; S-6–S-9 came from the
v0.2 pre-registration work. All were made before any calibration or test world existed and before any hypothesis was
evaluated. All of them are Claude's repairs
of Claude's own defaults; none of them touches an author decision.

| # | Change | Reason |
|---|---|---|
| S-1 | Special entities (outliers, overlaps) are drawn stratified by class (§3) | On seed 900003 all four special entities fell in class 1, leaving one normal entity. Its PCM center then drifted onto the neighbouring class's center. |
| S-2 | η changed from 7.0 to 2σ² = 0.72 (§4) | With η = 7 the typicality bandwidth is comparable to the prototype separation (typicality at the midpoint between two prototypes is 0.51). Fitted centers coincided in 20 of 20 development worlds; this is the known coincident-cluster failure of PCM. A first repair to η = 2.0 still left 5 of 100 worlds degenerate: a sparse class's center slid along its overlap entity onto a neighbour. The final value follows a rule, not a search: it is the expected value, in these worlds, of the Krishnapuram–Keller (1993) estimator of η with K = 1 (the average within-class squared distance of a row, 2σ² in two dimensions). It was chosen before its diagnostic was run. Result on seeds 900000–900099: 0 degenerate fits. Cost: weaker class evidence (median share of normal entities that are T for their own class at α = 0.7 falls from 0.94 to 0.69). |
| S-3 | A degeneracy check on the fitted centers (§5) | In those runs the converged flag was True while the centers coincided, so the failure was silent. |
| S-4 | max_iter changed from 100 to 1000 (§4) | With η = 0.72, 4 of 100 development fits did not converge within 100 iterations. With 1000 all four converged (in 109–142 iterations) to well-separated centers, and the result is the same with 10000. This is a computational budget only; tol is unchanged. |
| S-5 | H uses the world's rules, not the decoder's (§8) | A latent defect the main session found in code review: the metrics took H's rules from the context. |
| S-6 | `encode_from_rows(world, context, derive_ids, validate_ids)` was split out of `encode` (§5, steps 3–6); `encode` calls it after sampling and the split | Grounding test G3 (v0.2) re-encodes a changed D_derive. There is no behaviour change: the smoke output hash for 900001/900101 is unchanged (`0c8497d0…`), and all v0.1 tests pass. |
| S-7 | Exact companions for the metrics (`compute_metrics_exact`, `compute_metrics_for_exact`, which return the metrics and a dict of `Fraction` values); `compute_metrics` is now a thin wrapper. A dedicated `WorldGenerationError(RuntimeError)` is raised when the acceptance loop is exhausted. | Pre-registration v0.2, draft 4: exact comparisons (R1-8) and a dedicated replacement reason (R1-17). No float value changed; the smoke output hash is unchanged (`0c8497d0…`). |
| S-8 | §1 and §11 brought up to date for v0.2: `audit/` and `prereg/` are no longer placeholders, and the v0.2 seeds also use a salt drawn after the freeze commit is public (PREREG v0.2 §7) | Blind review 2 of the pre-registration (R2-8): the text was stale. No code changed. |
| S-9 | §7.3: the channel order in the ranking is stated (`POS` before `NEG`, the order of the `Channel` enum the code has used since v0.1) | The independent candidate enumerator of F1 (PREREG v0.2 §6.1) needed the order written down. No code changed. |
