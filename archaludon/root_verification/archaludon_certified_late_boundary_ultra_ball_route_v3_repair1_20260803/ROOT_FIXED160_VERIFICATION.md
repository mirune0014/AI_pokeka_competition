# Rule 3 v3 repair1 fixed160 root verification

## Decision

`DEFER_FOR_FROZEN_NATURAL_COVERAGE_EXTENSION`.

The repaired candidate is mechanically safe on the frozen fixed160 schedule,
but it is not yet eligible for fixed760. Equality is retention evidence only;
it is not evidence that the agent is stronger than its exact Rule 3 v2 parent.

## Frozen inputs

- Parent `main.py`: `4287A616E1611F5697964D9F4065978EED1CEA72CDB48C9F63F1430D69106C35`
- Candidate `main.py`: `3D95357E75E0B00CB679C1A31F6612AD1FA0EF44914E8ECA8C272CE9220027C3`
- Deck: `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`
- Overlay spec: `7C8BF76AAAF1909F4DD364DBD7184062F5DC29AC0968B6414EA3E1CD61A3A96F`
- User consultation: `CF70347E14337DD38648306BDAEB3D352008ECCA5CB408789D01C32CA2CA8B27`

## Root recomputation

- Unique schedule keys: `160/160`; missing, duplicate, and extra keys: `0`.
- Parent wins: `100/160`; candidate wins: `100/160`.
- Paired gains / regressions / ties: `0 / 0 / 160`.
- Seat 0: `47/80` versus `47/80`; seat 1: `53/80` versus `53/80`.
- Historical-Silver: `20/40` each.
- Arch Peak: `20/40` each.
- Alakazam: `29/40` each.
- Marnie: `31/40` each.
- Nonzero exits, action errors, exceptions, start faults, max-step hits, and
  duplicate mismatches: all `0`.
- Duplicate summary and trace controls: `160/160`.

The independent numerical audit reproduced these values. Its report SHA-256 is
`8098FEBDEBEA9519795B12261330058D75D586E6531A3CF055A246818A5472D1`.

## Natural mechanism evidence

Two natural first differences occurred, one in each seat. Both were
`ACTIVE_EX_FUEL_ROUTE` with `R3_WIN_NOW`, completed successfully, and had no
irreversible fault.

1. Historical-Silver, seat 0, seed `271828198`, turn 14:
   parent `PLAY Night Stretcher 1097/28`; candidate `PLAY Ultra Ball 1121/23`.
2. Historical-Silver, seat 1, seed `271828188`, turn 17:
   parent `EVOLVE Archaludon ex 190/67`; candidate `PLAY Ultra Ball 1121/80`.

Both games were wins under both policies. These are concrete tactical
realizations of the exact current-turn win certificate, but not paired outcome
gains.

The earlier seat-0 committed fault was an implementation defect in the
unrelated Assemble Alloy effect chain. Repair1 now owns the exact
`ACTIVATE -> ATTACH_TO -> ATTACH_FROM xN -> MAIN` chain; the same natural seed
completes with zero fault after repair.

## Open gates

- Natural starts are `2`, below the immutable minimum `4`.
- Neither first difference was a parent `ATTACK` or `END` action.
- No natural `TURBO_DURALUDON_ROUTE` start or completion occurred.

The Active-ex subfamily is therefore retained as provisionally validated.
The combined candidate is not promoted while the Turbo and late-boundary
coverage gates remain open.

## Next frozen check

Run a separate coverage-only extension without changing candidate, parent,
deck, engine, runner, or max steps:

- opponents in fixed order: Historical-Silver, Arch Peak, Alakazam, Marnie;
- new seeds `314159265..314159304`;
- both seats;
- maximum `320` unique keys;
- no extension win-rate interpretation as strength evidence.

Success requires cumulative fixed160 plus extension evidence to contain at
least four natural starts, a completed Active-ex route, a completed Turbo
route, an `ATTACK/END -> Ultra Ball` first difference, parent-non-Ultra
completion in both seats, 100% committed completion, zero mechanical faults,
the promised certificate in the post-transaction state, and no clearly
harmful first difference. Exhausting the cap without those observations keeps
the candidate deferred and blocks fixed760.

The physical paired CSVs omit a literal `panel` field. The immutable containing
directory reconstructs it uniquely, so numerical equality is verified, but a
future extension manifest must carry the panel label explicitly.
