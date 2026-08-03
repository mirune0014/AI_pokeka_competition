# Strategy selection — public opening role-complete turn plan v1

## Status

`PRE_EDIT_CENSUS_ONLY`

No source edit is authorized by this selection.

## Hypothesis

Treat mulligan, first/second choice, setup Active and Bench, and the first own
turn through its first attack as one public-state opening plan rather than as
independent score decisions.

The two candidate opening lanes are:

- `ACCELERATION_OPENING`: choose second; use Cinderace through
  Explosiveness; commit the minimum role-complete Duraludon Bench; attach;
  use Turbo Flare; and allocate only the exact useful Metal to one closest-to-
  payable successor.
- `EVOLUTION_TEMPO_OPENING`: choose first only when a fully visible
  Duraludon, evolution, and attachment route attacks one public round earlier
  without sacrificing a certified turn-one attack.

Unknown draws, hidden Prize contents, unresolved search, tied plans,
unsupported effects, or any live owner return the exact parent action.

## Hard ordering

1. Legal action, mandatory callback, and existing owner.
2. Correct mulligan or no-mulligan action.
3. Exact immediate attack or win.
4. Earliest payable attacker.
5. Surviving ready or closest-to-ready successor.
6. Minimum Bench and Energy commitment.
7. Hand/deck preservation and public live-out counts.

Legal outputs are semantic rebindings of current options only: `YES` or `NO`,
one legal setup Active, a legal setup-Bench subset, a current MAIN action, or a
legal Turbo Flare Energy/target callback selection.

## Pre-edit implement/stop gate

Implementation requires all of the following without threshold relaxation:

- exact 207 files, 209 target seats, and 25,880 parent calls;
- zero manifest mismatches, duplicate keys, or invalid parent actions;
- at least 80 exact opening-plan decisions over both seats and 40 replays;
- at least 24 predicted first-action differences over both seats and 16
  replays;
- differences in at least two of `IS_FIRST`, `SETUP_ACTIVE/BENCH`,
  `FIRST_MAIN`, and `TURBO_CALLBACK`, with at least six in each represented
  family;
- at least eight exact acceleration-opening controls and eight exact
  evolution-tempo directions;
- zero hidden-card-as-known, owner collision, semantic-copy noise, stale role,
  or incomplete callback case;
- every predicted difference inspected by root and classified `GOOD_CAUSAL`.

Any failed floor means `STOP__OPENING_PLAN_NOT_BROADLY_ACTIONABLE`.

## Regression risks

- choosing first while forfeiting Supporter or turn-one attack access;
- illegal mulligan handling or failed Explosiveness;
- overcommitting or underbuilding the setup Bench;
- scattering or overallocating Turbo Flare Energy;
- colliding with H3, PFC, CUM, PCRD, DPER, or PF Gear ownership.

This selection must first pass an engine-timing feasibility check. In
particular, any decision claimed to use the visible opening hand must prove
that the hand is actually observable at the callback where that decision is
emitted.
