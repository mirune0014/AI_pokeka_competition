# H5 strategy selection: inherited-Attack non-ex 120 KO

Selected mechanism:

`H5_INHERITED_ATTACK_NONEX_120_KO`

This is a direct child of exact historical-Silver:

- `main.py` SHA-256:
  `F4B578453C9D953BE94885144DD50E05DBA4510DF3340BE27ADE07495896046E`;
- `deck.csv` SHA-256:
  `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`.

H1 through H4 remain absent siblings.

## Verified evidence

- primary replay `87996118` SHA-256:
  `EF7699BAFDDEE7D247F25BC591CD55D2AEB7D2D8B0110E7A9FC3F62D68AE2977`;
- equal-KO control `88602602` SHA-256:
  `CF945C489ABEA48E10518D60045E679972422EAAEE68E220A07921542E7C8420`.

At `87996118:96`, after the parent completes Pokégear and Bench setup:

- Active `169#64` is a full-HP one-Prize Duraludon with three Basic Metal;
- opposing Active `743#26` is a one-Prize Alakazam at 90 HP;
- `840#92` can legally evolve the exact Active;
- inherited Raging Hammer `224` deals 80 and does not KO;
- Coated Attack `1212` deals 120 and deterministically KOs.

At `88602602:118`, the parent instead has a legal equal-KO Boss route. It
Bosses `742#83`, then Raging Hammer already KOs the 80-HP one-Prizer. This is
an equal-KO control and must not trigger H5.

The `88724889` Boss/Riolu idea guarantees an immediate Prize but not its
claimed successor-removal outcome because future switching and rebuilding
depend on unknown access. Energy reservation, Bench survival, and non-KO
continuity improve resources or board value without certifying an immediate
Prize. H5 therefore has the cleanest remaining public certificate.

## Scope and precedence

At an ordinary MAIN callback:

1. Compute exact historical-Silver's inherited semantic action first.
2. It must be Attack `224` with the current Active.
3. Current Active must be Duraludon `169`, already eligible to evolve, with
   exactly three attached Basic Metal `8`.
4. A legal non-ex Archaludon `840` evolution option must target that exact
   Active.
5. Both `169` and `840` must yield one Prize.
6. Opposing Active must yield exactly one Prize.
7. The H5 KO must be nonterminal; exact terminal routes retain precedence.
8. Effective inherited Raging Hammer damage, including all public modifiers,
   must be strictly below the opposing Active's current HP.
9. Effective Coated Attack `1212` damage must deterministically reach that HP.
10. Coated Attack must remain legal without attachment, retreat, Ability,
    Supporter, search, draw, chance, or hidden information.
11. No currently legal deterministic route without `840` may take an equal or
    greater number of Prizes. Check direct attacks, alternate legal
    evolution-to-attack routes, and legal Boss-to-attack routes.
12. Exact parent Ogerpon/endgame non-ex exceptions remain above H5.
13. Any uncertain predicate fails closed.

Precedence:

1. forced callbacks, legality, and exact terminal win;
2. existing deterministic equal/higher-Prize conversion;
3. existing parent non-ex exceptions;
4. H5 transaction;
5. exact historical-Silver.

H5 intercepts only when exact historical-Silver is already about to use
Raging Hammer. It must not preempt Pokégear or Bench actions at
`87996118:93/95`.

## Transaction

Snapshot:

`(seat, turn, Prize counts, Active id/serial/HP/Energy serials, 840 serial, opposing Active id/serial/HP/Prize value, inherited attack id/damage, Coated damage, public modifiers)`.

Stages:

1. `ARMED`: select stored `840` evolution onto the stored Active.
2. `EVOLVED`: advance only after the public state confirms that exact
   evolution and retained Energy.
3. Revalidate target serial, HP, attack legality, damage, Prize value, and
   terminal/higher-Prize vetoes.
4. `ATTACK_READY`: select only Coated Attack `1212`.
5. `DONE`: clear after confirmed attack, turn end, terminal result, or reset.

A returned action never advances state. Repeated callbacks return the same
semantic action.

For duplicate `840` cards, choose lowest card serial and then lowest legal
option position. Duplicate semantic options use the lowest legal position.

Before evolution confirmation, a mismatch clears H5 and delegates unchanged
to the parent. After evolution, rollback cannot undo the card: clear and
delegate from the actual evolved state if the opposing Active changes, Energy
changes, Coated Attack disappears, damage ceases to KO, or an unexpected
callback occurs.

Reset on deck request, new game, result, seat/turn change, confirmed attack,
or exception. Never retain transaction state across games or turns.

## Required positive

`87996118:96` is the primary first difference:

- parent: Raging Hammer `224`;
- H5: evolve `840#92 -> 169#64`;
- after public confirmation, H5 uses Coated Attack `1212`;
- Coated Attack deterministically KOs `743#26` at 90 HP.

## Required negatives

- `88602602:118` remains parent-identical on Boss.
- `88602602:120` remains parent-identical because inherited Raging Hammer
  already KOs `742#83`.
- inherited parent action is not Attack `224`;
- Raging Hammer already KOs;
- Coated Attack does not KO;
- target is multi-Prize or the route is terminal;
- Active has other than exactly three Basic Metal;
- `840` is absent, illegal, or targets another Pokémon;
- an equal/higher-Prize direct, Boss, or alternate-evolution KO exists;
- the route needs attachment, retreat, search, draw, Ability, or chance;
- Ogerpon/endgame parent exceptions apply;
- H1/H2/H3/H4 certificate states;
- evidence states `88584180`, `88660007`, `88507294`, `88247531`, and
  `88724889`.

## Forbidden generalizations

Do not add:

- generic non-ex preference;
- Alakazam, opponent, HP-90, episode, seed, or option-index rules;
- threat forecasting or Boss arbitration;
- Energy reservation, promotion preservation, or Bench-damage planning;
- two-hit-KO scoring;
- Coated defensive-effect forecasting;
- replay action imitation;
- any H1 through H4 stack.

## Verification and adoption gates

Focused exact engine:

- reconstruct `87996118:96` and complete the evolve-to-Coated KO;
- prove `88602602:118/120` remains parent-identical;
- test both seats, serial and option permutations, duplicate `840`, repeated
  callbacks, every rollback/reset, resistance/immunity/modifier changes, and
  illegal-attack variants;
- require zero invalid actions, exceptions, stale state, or max-step hits.

Shadow:

- shadow the complete frozen replay corpus;
- require 100% trigger-external equality;
- Root inspects every natural trigger;
- every first difference must be inherited Raging Hammer versus certified
  `840` evolution;
- every continuation must match the intended Coated-KO mechanism.

Fixed evaluation:

- run the immutable 200-game historical-Silver anchor plus 560-game adjacent
  population, identical seeds and both seats;
- require exact schedule/key equality, zero duplicates, action errors,
  exceptions, and max-step hits;
- require no primary-anchor, seat, panel, opponent-seat cell, or adjacent
  population regression;
- a single tiny paired gain is insufficient;
- promotion requires repeated mechanism-aligned candidate-only wins on at
  least two independent seeds, including positive primary-anchor movement;
- zero natural triggers or fixed `478/760` neutrality means
  contract-correct/no-strength and inactive, not promoted.

Live:

- permit a separate direct-parent live probe only after all local strength
  gates pass;
- attribute results only where H5 changes the correct-seat action;
- parent-identical games provide no H5 strength evidence;
- formal-parent promotion requires repeated public H5 triggers, no causal
  losses, no destructive faults, both-seat safety, and at least one
  mechanism-confirmed match conversion.

Any causal parent-win/candidate-loss flip, equal-KO trigger, mechanism
mismatch, action fault, or max-step hit rejects the candidate.

If H5 produces no repeated outcome movement, reject promotion without
widening it. The next discriminating sibling should test attack-completing
Energy reservation separately.
