# F3 notes

Code: `out/code/f3.py` (recomputation), `out/code/check_outputs.py` (structural check of the outputs against
OUTPUT_SCHEMA.json; 0 errors). Diagnostics: `scratch/diagnostics.json`.

Conventions and observations where the text left room, or where a check was made:

1. **boundary_share, float comparison.** I computed `abs(mu - alpha) < epsilon_band` in IEEE double arithmetic, with
   mu, alpha and epsilon_band as parsed from the input. This gives the same result as an exact comparison of the double
   values. A decimal reading of the printed numbers gives a different result in one kind of case: relation units with
   mu = 0.6 at alpha 0.55, mu = 0.8 at alpha 0.85 and mu = 0.95 at alpha 0.9. As doubles the difference is just below
   0.05, so these units count as on the boundary. As decimals it is exactly 0.05, so they would not count. This affects
   `boundary_share` at alpha 0.55, 0.85 and 0.9 in every world, and no other metric. No outcome uses `boundary_share`.
2. **enc ties.** In every world many relation units have mu exactly equal to an alpha of the grid (0.95, 0.8 and 0.6,
   the source support degrees). Equality counts as >= (SPEC section 6), which is what I did.
3. **G8 anchor.** I used the instructions' definition of a hypothesis: full not U and verdict U at (alpha0, k = 10).
   SPEC's `hyp_count` uses full in {T, F}. The counts differ by one in 3 worlds (461088552, 682198850, 990879660),
   but both are > 0 in all 30 worlds, so the anchor is met either way.
4. **G7a.** I applied the order the instructions give: UNDEFINED iff the oracle has no feasible point, HOLDS as stated,
   FAILS otherwise. The oracle had a feasible point with a positive score in every world, and no baseline scored > 0 at
   any alpha, so the order made no difference.
5. **Null cases not covered by SPEC.** I would have written consistency and uncertainty as null for an empty K, and
   boundary_share as null for a world with no units. Neither case occurs. There are no NOT_COMPUTED units or validation
   units in the inputs, so E is the full set of unit atoms.
6. **Checks.** Every atom in true_atoms, units, validation_units, full and verdict is in the vocabulary. The H
   assertions hold in every world: each H atom has one channel, and that channel agrees with W. A second closure
   algorithm, which extends substitutions by joins, gives the same H in all 30 worlds. In every world, verdict at
   (alpha, 5) and (alpha, 10) equals verdict at (alpha, 0), as PREREG section 3.1 says it should.
