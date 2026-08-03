# Rule 3 v3 implementation-boundary corrections

Status: CONTROLLING IMPLEMENTATION BOUNDARY
Date: 2026-08-03 JST

This amendment records root-verified differences between the GPT Pro design
skeleton and the existing executable source. It narrows implementation side
effects without narrowing any Rule 3 certificate or route.

## Physical references

The engine `Option` does not store a target serial directly. A saved semantic
reference must include seat, source area, card ID, card serial, option type,
attack ID where relevant, and target area/serial resolved through
`_parent.option_target()`. `CardRef(card_id, serial)` alone is not a sufficient
binding or duplicate key.

## Rule-local combat proof

The existing global combat registry does not contain Cinderace/Turbo Flare.
Do not add Turbo Flare to that global registry because doing so can change
existing terminal, Rule 4, or Rule 5 behavior. Implement a Rule3-local exact
metadata and same-attack certificate for Turbo Flare.

## Exact existing priority

The owner-free MAIN priority remains:

```text
direct exact current terminal
-> Rule 4 Lillie materialization
-> Rule 5 exact higher-Prize Boss
-> Rule 3 v3
-> Historical-Silver
```

Rule 3 `WIN_NOW` may override a parent draw only after existing higher-priority
materialization and Boss rules decline. Do not reorder or modify Rule 4/5.

## Route-specific state

- `ACTIVE_EX_FUEL_ROUTE` stores the pre-existing hand Archaludon ex physical
  ref separately from the optional Ultra Ball search result. The old
  searched-target-is-evolution-target invariant must not be reused.
- `TURBO_DURALUDON_ROUTE` stores the initial Bench physical serial set and
  proves that the searched Duraludon is the one added. The old `Bench == 0`
  before and `Bench == 1` after receipts must not be reused.
- Parent-selected Ultra Ball costs are not authoritative after a v3 override.
  Rebind only the cost pair certified before commit.

## Rule 5 handoff

The existing source has no owner-safe Rule3-to-Rule5 handoff. Do not clear the
Rule 3 owner temporarily to call the existing mutating Rule 5 starter. If the
required prefix supersession is implemented, use a pure availability/plan
probe followed by one explicit atomic owner conversion. Owner-free Rule 5 must
remain byte-for-byte behaviorally equivalent.

## Post-commit fault

The existing `_r3_abort` immediately clears an irreversible owner and is not
valid for v3. V3 must retain a fault-latched owner, emit only legal containment,
and record the run as failed until a declared stable release point.

