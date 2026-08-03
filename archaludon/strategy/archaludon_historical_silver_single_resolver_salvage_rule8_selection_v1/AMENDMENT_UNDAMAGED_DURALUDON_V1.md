# Rule 8 Amendment: Undamaged Duraludon

This amendment controls the focused-fixture section of
`STRATEGY_SELECTION.md`. All other frozen requirements remain unchanged.

## Contradiction

The original negative-fixture line described an undamaged Duraludon as an
outcome tie. That is false under the frozen printed metadata:

- Hammer In (`223`) has 30 printed damage.
- Raging Hammer (`224`) has 80 printed damage plus 10 for each damage counter
  on Duraludon.

At zero damage counters, before identical target modifiers, the attacks are 30
versus 80. Therefore an otherwise fully certified undamaged-Duraludon state is
a positive strict-damage-dominance fixture, not a tie.

## Controlling fixture correction

- Remove `Zero-damage Duraludon where outcomes tie` from the negative fixtures.
- Add an undamaged Duraludon with both attacks legal and an unchanged target to
  the positive non-KO-damage fixtures; require `30 -> 80` before identical
  modifiers and a semantic override from `223` to `224`.
- Keep the fail-closed code path for any genuinely equal final public outcome,
  but do not invent an engine state or broaden the effect model merely to make
  a tie fixture. A controlled helper-level equal-result fixture may exercise
  that branch only if it uses the same exact comparison function.

No implementation may redefine final damage, suppress the printed 80 damage,
or weaken the exact metadata and Pareto gates to satisfy the original mistaken
fixture.
