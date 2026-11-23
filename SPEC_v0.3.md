# Tesaron: spec amendments for v0.3

**Status: FROZEN** with `prereg/PREREG_v0.3.md`, by the manifest `prereg/v03/FREEZE_v0.3.json`; see `prereg/v03/FREEZE_RECORD.md`.
- `SPEC.md`, as frozen in v0.2, stays the authoritative implementation spec for everything this file does not name.
  It is not edited.
- The test machinery of v0.3 (τ at k = 0, the Q-40 rule, T-1 at k = 0, G8 descriptive, 50 test worlds) belongs to the
  pre-registration, `prereg/PREREG_v0.3.md`, not to this file.

**Rule for the implementer:** as in `SPEC.md`. Do not change a definition. If something is ambiguous, contradictory or
impossible, stop and report it.

## S-10. The v0.3 reference worlds

v0.3 worlds come from the unchanged generator `generate_world(seed, params)` (SPEC §3). They are called with these
parameters (`audit/v03/worlds.py`, `v03_world_params(seed)`):

| Parameter | v0.2 | v0.3 | Decided by |
|---|---|---|---|
| n_sources | 3 | 8 | the author (changes A-8), on the designer's proposal; approved 2026-11-23 |
| source reliabilities | (0.95, 0.80, 0.60) | drawn per world from U(0.55, 0.97) and rounded to 3 decimals, in draw order for sources `s0`–`s7` | the author: continuous reliabilities (AQ1); the range was proposed by the designer and approved 2026-11-23 |
| q_true | 0.5 | 0.1875 | proposed by the designer, approved by the author 2026-11-23: keeps v0.2's expected number of reports per true base fact (3 × 0.5 = 8 × 0.1875) |
| q_false | 0.02 | 0.0075 | the same rule (3 × 0.02 = 8 × 0.0075); approved 2026-11-23 |
| overlap_fraction | 0.4 | 0.8 | the author (A4, "overlap entities, fraction 0.8"), from design study S1b |
| prototype_radius | 3.0 | 3.0 (unchanged) | design study S1 |

Every other parameter keeps its SPEC §3 value.

**The reliability stream.** The reliabilities of the world with seed `s` are
`np.random.Generator(np.random.PCG64(np.random.SeedSequence([s, 0x7E5A03]))).uniform(0.55, 0.97, size=8)`, each value
rounded with `round(float(x), 3)`. This stream is separate from the generator's own RNG, so drawing the reliabilities
does not shift the world draw (classes, rules, base facts, features). The context's support degrees still equal the
reliabilities (`support_degrees_from_world`, SPEC §4).

**Overlap entities.** With fraction 0.8, the true mean of each of the two overlap entities lies 80% of the way from the
prototype of its base class to the partner prototype (SPEC §3). Its features therefore look mostly like the partner
class. Its weak typicality for the partner class can make a world-false class atom T at low α. Its own class atom is
usually U, because the encoder never derives μ⁻ from μ⁺ (SPEC §5). Nothing in the encoder, the interface or the decoder
changes.

**Why these values** (design quantities on development seeds 930000–930099, encoder seed + 10000; no decoder run):
- **S1, a smaller prototype radius** (`prereg/v03/WORLD_STUDY.json`). It chose no radius. As the radius falls, PCM fits
  become degenerate (S-3) before world-false T class atoms become common:
  - at radius 2.0, 90 of 100 worlds are valid, and 8% of them have a world-false T class atom at α = 0.50;
  - at radius 1.5, 83 of 100 fits are degenerate;
  - below that, all fits are degenerate.
- **S1b, overlap entities moved** (`prereg/v03/OVERLAP_STUDY.json`, the same three criteria written before the run).
  The smallest fraction that meets them is 0.8:
  - 99 of 100 worlds are valid;
  - G1 (i) and (iii) hold on every valid world;
  - the share of worlds with at least one world-false T class atom is 0.18 at α 0.80, 0.31 at 0.70, 0.40 at 0.60 and
    0.54 at 0.50;
  - 2.2–4.0% of T class atoms are world-false (α 0.80–0.50).

**What v0.3 changes in the meaning of the worlds:**
- **Class evidence can be wrong.** In v0.2 it never was.
- **Relation evidence enters at up to 8 α levels per world,** at the world's own reliabilities, instead of at 0.95, 0.80
  and 0.60 in every world. Lowering α therefore admits sources one at a time.

## S-11. No other change to the system

The encoder, the Belnap interface, the decoder, the metrics (SPEC §8), the criterion (SPEC §9) and the baselines
(SPEC §10) are unchanged. `tesaron/` is not modified.
