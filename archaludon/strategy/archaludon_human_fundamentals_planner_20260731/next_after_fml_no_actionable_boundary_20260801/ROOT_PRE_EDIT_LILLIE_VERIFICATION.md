# Root verification — pre-edit Lillie actionability census

## Frozen evidence

- Parent `main.py`:
  `558EE5DB29E001428B0D59813613FABEE8E15B96E422746C104BDFAB4DC22DB6`
- Deck:
  `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`
- Source manifest:
  `90A512D5C9AE5EAD8DF92F370C32716959EC0929F9465451E7BB0926DBEB5A68`
- Strategy contract:
  `B77AAB1F5033E4827CA31B338388E49AB7E3A23C0ABB2E6385CA93C23FED2797`
- Census runner:
  `EFBD7B11D2C3D61454AAABB3FA4AF3989F68943EE99BFEED1D35EA5D30D08DED`
- Opportunity CSV:
  `42AEBFFF013023C3C90567FD1A69D6EF1BE224B3C377B2BFDFD7E8E74411B73C`
- Runner summary:
  `847E96B39EBFF6B8202B489B0552CA2B84727FE5B0D3E7310CDDED537055781E`
- Independent Sol-Ultra audit:
  `EFE1A2F1468326CEE077D89D054321312213A06AC222F13D39787C0E77587F57`

## Integrity

Root independently confirmed:

- 207 manifest entries and 209 target seats;
- exactly 25,880 parent calls in the frozen summary;
- zero invalid parent actions, manifest mismatches, or duplicate row keys;
- exactly 256 historical Lillie PLAY turns, 153 replays, both seats;
- 1,889 opportunity rows and exact admitted Lillie metadata;
- the exact hand/deck transform on every row.

## Deduplicated result

Root's PowerShell recomputation from the raw CSV agrees with the independent
audit:

| Direction/scope | Unique turns | Replays | Seats |
|---|---:|---:|---|
| Strict-purpose union | 408 | 167 | 0, 1 |
| Actionable | 346 | 157 | 0, 1 |
| Predicted first difference | 346 | 157 | 0, 1 |
| PLAY_LILLIE | 346 | 157 | 0, 1 |
| APPROVE_PARENT_LILLIE | 171 | 125 | 0, 1 |
| HOLD_LILLIE | 0 | 0 | none |

All 691 actionable callback rows have a current unique Lillie role, a complete
queue, no live-owner collision, and no rejection.  They use exact hand-count
or deck-count change only; none assumes a particular hidden draw.

The raw 1,889 callbacks collapse to 646 independent `(replay, seat, turn)`
keys.  Therefore raw callback volume is not used as evidence.  In particular,
691 PLAY callbacks collapse to 346 PLAY turns.

## Decision

`STOP_BEFORE_IMPLEMENTATION__NO_HOLD_BOUNDARY`

The frozen gate requires at least three PLAY and three HOLD turns, each in both
seats, plus at least two protected HOLD roles.  The census has 346 PLAY turns
but exactly zero HOLD turns and zero protected HOLD roles.  The missing
qualitative `GOOD_CAUSAL` audit is irrelevant once these non-relaxable numeric
gates fail.

Do not implement, package, evaluate, or submit this Lillie hypothesis.  A
one-direction rule that broadly plays Lillie would lack natural evidence that
it preserves completed attack, Boss, attachment/evolution, recovery, and
backup lines.  Lowering the gate after seeing the result is forbidden.
