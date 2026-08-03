# Root pre-edit feasibility — public opening plan v1

## Decision

`STOP__OPENING_PLAN_NOT_BROADLY_ACTIONABLE`

Do not build the full opening-world census and do not edit source from the
combined hypothesis. Its first/second lane requires information that is not
available when the engine asks for the decision.

## Exact inputs checked

- Formal parent `main.py`:
  `558EE5DB29E001428B0D59813613FABEE8E15B96E422746C104BDFAB4DC22DB6`
- Formal parent `deck.csv`:
  `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`
- Source manifest:
  `90A512D5C9AE5EAD8DF92F370C32716959EC0929F9465451E7BB0926DBEB5A68`
- Corpus: 207 replay files, 209 target seats, 25,880 selectable target
  callbacks, zero replay-hash mismatches.

Root scanned every target-seat selectable observation and grouped the opening
contexts by replay, seat, step, context, and snapshot hash.

| Context | Callback rows | Replays | Unique `(replay, seat, turn)` | Seats |
|---|---:|---:|---:|---|
| `IS_FIRST` | 168 | 108 | 108 | seat 0 only |
| `MULLIGAN` | 113 | 82 | 82 | both |
| `SETUP_ACTIVE_POKEMON` | 1,017 | 207 | 209 | both |
| `SETUP_BENCH_POKEMON` | 473 | 71 | 71 | both |

All 168 `IS_FIRST` callbacks have exactly:

- `turn == 0`;
- `handCount == 0`;
- an empty visible hand;
- two generic `YES/NO` options;
- no visible Duraludon, evolution, Energy, Cinderace, or other role evidence.

The opening seven-card hand first becomes visible at the later `MULLIGAN`
callback. It cannot retroactively inform the already emitted first/second
choice. The `IS_FIRST` target callback also exists only for seat 0 in this
corpus, so the contract's both-seat direction requirement cannot be met at
that family.

## Consequence

The required eight exact `EVOLUTION_TEMPO_OPENING` directions cannot be
certified from public state. A rule that chooses first because a visible
Duraludon/evolution/attachment line exists would either read future hidden
information or reconstruct replay history as an action label, both forbidden.

The existing parent always chooses second. With no public hand at
`IS_FIRST`, a different legal rule can only be a deck-level fixed preference,
not the selected bidirectional opening-plan comparison. Therefore the fixed
gate is already impossible before producing expensive counterfactual worlds.

## Preserved next lead

The failure is caused by combining pre-deal first/second choice with post-deal
setup and first-turn planning. It does not show that post-deal opening play is
complete. A successor may evaluate only the visible-hand stages—mulligan,
setup Active/Bench, first MAIN, and Turbo Flare callbacks—while treating the
parent's second-player choice as fixed input. Such a successor needs a new
frozen hypothesis and cannot silently drop the failed evolution-tempo gate.
