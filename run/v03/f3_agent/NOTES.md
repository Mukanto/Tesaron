# F3 notes

No unclear point turned out to matter for these inputs, and nothing anomalous came up. All files were written. Code:
`out/code/f3.py` (standard library only; run as `python f3.py <task folder>`).

## Checks that passed

- All 40 calibration worlds have the four τ metrics defined at "0.7|0", and |H| >= 10 in every world.
- H: the brute-force closure (every assignment of entities to the rule variables, repeated to a fixpoint) gives the same
  result as a join-based naive closure in all 90 worlds. The SPEC §8 assertions hold in every world: each H atom's
  derived channel agrees with W, and no H atom has both channels.
- Step 1 cross-check (scratch only, not an output): the pass-1 closure of my encoded values under the input rules equals
  the input's `full` and `verdict` at all 540 k = 0 configurations (50 x 10 test, 40 calibration).
- uncertainty, new_true, new_false, n_q, validation_agreement and boundary_share come out the same at every k for a
  given alpha, as PREREG §3.1 says they should.

## Conventions for cases that did not arise

None of these cases occurs in the inputs, so none of them affects an output.
- consistency and uncertainty would be written null if K were empty, and boundary_share null if a world had no units.
- G7a: if the oracle had no feasible point, I would write UNDEFINED even if a baseline scored > 0 ("UNDEFINED iff the
  oracle has no feasible point"). If the oracle were feasible but never scored > 0 and no baseline scored, I would write
  FAILS ("FAILS otherwise"). Neither case occurs.

## Pareto front

Points with identical (x, y) do not dominate each other under the stated definition, so all of them stay on the front,
ordered by alpha ascending and then k ascending. Since x and y do not depend on k, this happens whenever an alpha is
feasible at more than one k (40 of the 50 test worlds).
