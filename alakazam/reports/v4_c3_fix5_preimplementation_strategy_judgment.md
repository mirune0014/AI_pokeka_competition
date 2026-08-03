# v4 C3 FIX5 pre-implementation strategy judgment

Date: 2026-07-30

## Judgment

Inherit C2 FIX4B and implement one isolated C3 hypothesis:

> At a normal MAIN prompt with exactly one own Active and no Bench, when the
> complete parent policy is about to `ATTACK` or `END`, play exactly one
> independently useful, low-cost Basic first only when a supported public
> damage envelope certifies that the same threatening attacker can still KO
> the current Active after both the parent line and the candidate line, the
> parent line would leave no Pokémon in play, and the candidate preserves the
> parent's exact tactical outcome.

C1 Poffin fix3 is rejected and must not be inherited.

## Parent

- Candidate parent:
  `versions/alakazam_newdeck_v4_next_attacker_distance_shadow_fix4b`
- Parent closure:
  `29084BC13CB74236ABE557B57A9E633A8F9E88FA83FF22D131C835293E987157`
- Inherited action behavior:
  exactly B0
- C2 audit:
  `reports/v4_c2_fix4b_union_sol_ultra_audit.md`
- C2 result:
  PASS

## Enabled decision point

The only enabled action change is:

```text
normal MAIN
Bench count = 0
parent action = ATTACK or END
→ play one certified Basic
→ verify Hand-to-Bench movement
→ re-enter the complete parent policy once
→ semantically rebind the same attack or END
```

Do not alter:

- supporter, search, or draw actions;
- Run Away;
- forced promotion;
- Trading Places or another switch child;
- wall selection.

## Exact projected-state interpretation

`PARENT_POST_STATE` and `CANDIDATE_POST_STATE` are separate projections.

The phrase “threat remains certified in both” means:

- the same public opposing attacker remains able to KO the same current own
  Active in both projected states;
- the parent projection has Bench 0 and therefore exposes immediate board-out;
- the candidate projection has the selected surviving Basic on Bench and
  therefore prevents that immediate board-out.

If the parent attack may remove, switch, disable, or otherwise alter the
threat and that continuation cannot be projected exactly, retain the parent
action.

## Initial supported scope

Opponent damage support begins with the frozen Fighting family:

- Pokémon `673`–`678`;
- attacks `976`–`983`;
- exact static metadata, cost, formula, weakness/resistance, status, and
  continuity checks;
- Premium Power Pro `1141`, with four-copy physical-serial stacking.

A generic fixed-damage attack may be analyzed only when its entire formula,
cost, modifiers, post-attack effect, and continuation are exact. Dynamic
damage, copied attacks, coin results, unresolved bench damage, counter
placement, or unsupported effects are `UNKNOWN`.

Own post-action projection initially supports:

- Super Psy Bolt `1071`;
- Powerful Hand `1072`, including the exact `-20` hand-scaling effect of
  playing one Basic;
- `END` with no unresolved parent transaction.

## Basic ranking

Every candidate must actually prevent board-out and preserve attack legality,
terminal win, last-prize win, exact current KO, and prize exchange.

Rank:

1. a candidate that prevents board-out;
2. one that preserves the exact parent tactical outcome;
3. Abra `741` when it improves certified next-attacker distance;
4. Shaymin `343` for its independently supported Bench value;
5. Dunsparce `305` when it creates the missing draw/wall line;
6. lower prize and resource liability;
7. canonical semantic option key.

For a cap-only threat, “any Basic” is insufficient. The Basic must have one of
the independent values above.

## Premium Power Pro

Track physical serials for the exact game and turn.

```text
C_t = distinct valid current-turn Play(1141, serial)
U_t = distinct publicly unavailable 1141 serials
additional_max = max(0, 4 - |C_t union U_t|)
current floor boost = 30 * |C_t|
current supported cap boost =
  30 * (|C_t| + additional_max)
future supported cap boost =
  30 * max(0, 4 - |U_future|)
```

A direct discard without `Play` adds no floor. Duplicate callbacks add no
copy. Recovery removes the serial from `U`. Ambiguous game boundary, turn,
serial, zone, recovery, or accumulator lifetime makes the affected result
`UNKNOWN` and retains the parent action.

For episode `88843743`, the supported Solrock envelope is floor 100 and cap
160 at the relevant later attack, not cap 100.

## Fixed episode behavior

For `88843743`:

- keep Run Away at observation 22;
- keep forced Kadabra promotion at observation 23;
- keep Hilda at observation 24;
- at observation 27, play Shaymin `343/serial 81`;
- after exact transaction verification, make the same attack `1071`.

No episode ID, opponent label, seed, later action, hidden card, or game result
may be a production trigger.

## Fail closed

Retain the parent action on:

- raw/parsed disagreement;
- duplicate or missing owner/serial/zone identity;
- unsupported attack, effect, weakness/resistance, status, or modifier;
- ambiguous public ledger boundary or Power Pro multiplicity;
- a parent/candidate post-state that cannot be projected independently;
- an attack that changes the threat without an exact continuation;
- a non-unique Basic semantic option;
- inability to rebind the same attack after Basic placement;
- loss of terminal win, last-prize win, exact KO, attack legality, or supported
  prize exchange;
- current v1, integrated, C3, or other owner transaction;
- transaction verification failure or stale callback.

Unsupported action changes must remain zero.

## Required focused verification

Implement all fixtures in the frozen C3 specification, the Power Pro
amendment, and the strategy-binding amendment, including:

- floor and cap-only board-out;
- `KO -> non-KO` rejection after the `-20` Powerful Hand change;
- threat removed by the parent attack;
- Power Pro stacks of one, two, and four;
- direct discard, duplicate callback, recovery, and ambiguous boundaries;
- supporter-first behavior;
- duplicate and reordered options;
- transaction rollback and full-policy re-entry;
- the four `88843743` observations.

Run candidate full regression and parent full regression before simulation.

## Evaluation

Strength comparison uses the immutable 7-opponent, both-seat, 5-seed-base,
10-game-per-cell panel: 700 paired games.

Adopt only if all frozen C3 gates pass:

- candidate wins at least the B0 absolute floor of 452;
- positive overall paired delta;
- Historical Silver at least `+3/100`;
- both Silver seats nonnegative;
- at least two of five Silver seed blocks positive;
- adjacent six opponents at least `-2/600`;
- every opponent at least `-2/100`;
- every opponent-seat at least `-2/50`;
- required one-sided paired lower bounds;
- mechanism reach and raw-integrity gates.

Otherwise reject the action change. A separately validated pure
damage/continuity analyzer may still be inherited by C4 with the C3 action
gate disabled.
