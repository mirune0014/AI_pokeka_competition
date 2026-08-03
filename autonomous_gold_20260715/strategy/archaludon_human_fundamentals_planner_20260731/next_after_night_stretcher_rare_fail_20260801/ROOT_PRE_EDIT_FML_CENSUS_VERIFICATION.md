# Root verification — pre-edit Full Metal Lab opportunity census

## Frozen inputs and outputs

- Parent source:
  `558EE5DB29E001428B0D59813613FABEE8E15B96E422746C104BDFAB4DC22DB6`
- Deck:
  `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`
- Source manifest:
  `90A512D5C9AE5EAD8DF92F370C32716959EC0929F9465451E7BB0926DBEB5A68`
- Census runner:
  `CF5A23E89468B681B3C24EC27C11A543D233F8F45C4F598E4B6B2D339CD24B9E`
- Raw opportunity rows:
  `7742839C705B224C2945B62210141F8B717784A69E88C0A8DD9442D65A098923`
- Runner summary:
  `7057AC7D368030173D7C2EB2A9E2FD6E7A8D57EB15A4972C5E6EDDF43598C754`

## Root-recomputed totals

The runner called the exact parent once on each of 25,880 target-seat
callbacks.  All 207 replay hashes matched the manifest; all 209 target seats
were processed; invalid parent actions were zero.

The historical-log control reproduced exactly:

- 172 natural FML PLAY turns;
- 141 replay files;
- both seats.

The pre-action opportunity table contains 803 rows over:

- 252 unique FML-option turns;
- 158 replay files;
- both seats.

Rejection/exact breakdown:

| Classification | Rows |
|---|---:|
| No actual legal ATTACK option | 301 |
| KEEP plan unavailable | 217 |
| KEEP return graph not exact | 188 |
| Exact KEEP and PLAY_FML pair | 97 |

The 97 exact pairs cover only 28 unique turns in 24 replay files, both seats.
Root independently grouped their first hard comparison direction:

- `EQUAL`: 97
- `PLAY_FML`: 0
- `KEEP`: 0
- `INCOMPARABLE`: 0 among exact pairs

## Factual implication

The census passes replay/seat reconstruction and proves substantial raw FML
exposure.  It does **not** show an actionable symmetric-combat boundary under
the frozen same-attacker/same-target/same-attack contract.  Exact opportunities
fall below the contemplated 40-turn full-shadow classification floor, and none
of the exact pairs supplies a natural PLAY or HOLD/VETO direction.

No candidate source was edited.  Sol-Ultra strategy judgment controls whether
this pre-edit result falsifies implementation and which broader rule is next.

## Sol-Ultra strategy judgment and root decision

`FALSIFIED__NO_ACTIONABLE_BOUNDARY__RARE_NARROW`

The proposed Full Metal Lab replacement is stopped before implementation.
The exact 28-turn coverage is below the frozen 40-turn gate, and every one of
the 97 exact comparisons is equal under the selected hard hierarchy.  The
required natural PLAY/HOLD directions, later action differences, and 3+3
direction floor are therefore structurally unreachable without changing the
hypothesis after seeing the evidence.

Root decision: do not spawn a source writer, do not run fixed760, do not
package, and do not submit this rule.  Full Metal Lab remains an identified
semantic gap in the broader TODO, but this exact same-attack comparison is not
a credible next implementation.
