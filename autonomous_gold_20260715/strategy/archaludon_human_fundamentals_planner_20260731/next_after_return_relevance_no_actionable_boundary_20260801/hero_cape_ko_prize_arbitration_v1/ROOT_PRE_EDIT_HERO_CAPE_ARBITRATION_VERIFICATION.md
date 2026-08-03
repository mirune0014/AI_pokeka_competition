# Root verification — parent-initiated Hero's Cape arbitration v1

## Decision

`STOP__PARENT_CAPE_NOT_ONE_BROAD_ACTIONABLE_BOUNDARY`

Do not create, package, or submit a source candidate from this contract. The
pre-edit census does not pass its immutable implementation gate.

## Frozen evidence

- Parent `main.py`: `558EE5DB29E001428B0D59813613FABEE8E15B96E422746C104BDFAB4DC22DB6`
- Parent `deck.csv`: `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`
- Source manifest: `90A512D5C9AE5EAD8DF92F370C32716959EC0929F9465451E7BB0926DBEB5A68`
- Strategy contract: `C973A81410538E176CEA41FEDB53A9D03D117255CBB67576B25C82D7A1E244B9`
- Census runner: `C7A0E150E2CCF6F17EECA76108577F4EA5E863CBBED353B551E84524838823B8`
- Execution specification: `81DA814E2284A4A04932A96C8B02A6F1A14E5C402947FFCDF47206A347DCADD7`
- Callback rows: `DE4554312ADBDF177DEABEBFB6956D1E946814770EAD31A024DE72519D97533A`
- Target-world rows: `9BFC462EE352EA8E672C13D0F969BD1F0F19AA579A723E5B5911867FA474A68F`
- Raw summary: `E5A713193D7BACCF197C8EC7066923853C4CEE7FFAAF44A1A74779BE18EE597A`
- Independent Sol-Ultra numerical audit:
  `B5DB1A71189775638D437E9D8691F61CDEC197E68D91001A9738D8691C6549E7`

The deterministic execution completed with exit code zero. It replayed 207
files, 209 target seats, and 25,880 selectable target callbacks. The raw
runner reported 25,880 unique snapshot keys, zero invalid parent actions, and
zero manifest mismatches. It emitted 119 parent-Cape callback rows and 415
counterfactual world rows.

## Root recomputation

Root independently grouped callback rows by `(replay, seat, turn)` in frozen
CSV order. The required `independent` column was omitted from the CSV, but the
first activation-bearing parent-Cape callback is unambiguous for all 116 turn
keys in this dataset.

| Measure | Recomputed | Required |
|---|---:|---:|
| Independent parent-Cape turns | 116 | diagnostic |
| Scope-correct clear turns with a legal attack | 103 | 40 |
| Complete earliest-independent comparisons | 13 | 40 |
| Classifiable and emittable turns | 13 | 20 |
| Predicted first-action differences | 13 | 12 |
| `RETARGET_CAPE` | 0 | 3 and both seats |
| `VETO_TO_ATTACK` | 13 | 3 and both seats |
| Survival / Prize / continuity boundaries | 0 | 3 |
| Finish / no-purpose conservation labels | 13 | 3 |

The 13 predicted changes span 13 replays and both seats: five seat-0 turns and
eight seat-1 turns. Each historical replay confirms that the parent attached
the physical Cape to its selected target. All 13 comparisons first differ at
`POST_ACTION_THEN_POST_REPLY_RESOURCES`; none first differs at exact win,
terminal-loss avoidance, current Prize/KO, public return survival/continuity,
or ready-backup conversion.

The independent evaluator further checked all 31 attack-now versus Cape-world
dominance comparisons underneath those 13 turns. Every comparison is driven
by the resource ledger preferring Hero's Cape `HAND_READY` to
`ATTACHED_AND_RECOVERABLE`; two also mark the attached Cape certainly lost.
This is real conservation ordering, but it is not evidence that Cape changes a
KO, Prize, or attack-continuity boundary.

## Audit limitations

- The raw summary counts 113 owner-clear Cape turns, but ten have no legal
  attack and are outside this contract's attack-versus-Cape scope. The
  scope-correct count is 103; the natural-support gate still passes.
- The callback CSV omits the contract-required earliest-independent flag.
- The imported helper was not hash-bound by the frozen runner/specification.
  Its observed SHA-256 is
  `3441E6DFA25140E9C70CABB58E9F36CF3DF76FCD25B3B36311590FA83CF9EF8B`.
- The runner cannot assign an `APPROVE_PARENT_CAPE` survival boundary because
  it compares the winning parent plan with itself. It also labels every
  retarget as survival/Prize/continuity without checking which comparator
  layer changed. These defects cannot manufacture the missing 27 complete
  comparisons or the missing retarget direction in the frozen rows.
- The helper's owner/error accounting is narrower than the parent's complete
  owner set. Any correction can only remove nominal support; it cannot turn
  this failed gate into a pass.

## Conclusion

Hero's Cape is common enough to matter, and delaying a no-purpose attachment
is a plausible one-direction resource rule. This particular broad arbitration
hypothesis is nevertheless rejected: exact actionability is too sparse, it has
no retarget evidence, and it never demonstrates the promised KO, Prize, or
continuity mechanism. Preserve the evidence as a future narrow conservation
lead; do not weaken the fixed gate or edit source from it.
