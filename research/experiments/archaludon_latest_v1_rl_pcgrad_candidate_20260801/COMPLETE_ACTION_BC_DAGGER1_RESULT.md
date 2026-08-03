# Complete-action BC DAgger round-one result

DAgger round one completed successfully but did not pass the gate for PPO.
`iteration004` remains the retained deterministic baseline, and none of the
three DAgger checkpoints is accepted as a deployment or PPO-reference model.

## Fixed evaluation

| Seed | Initial BC | DAgger 1 | Gain | Delta from iteration004 | Gate |
|---|---:|---:|---:|---:|---|
| `2026080211` | 241/320 (75.31%) | 244/320 (76.25%) | +0.94 pp | -5.31 pp | fail |
| `2026080212` | 229/320 (71.56%) | 247/320 (77.19%) | +5.63 pp | -4.38 pp | pass |
| `2026080213` | 248/320 (77.50%) | 254/320 (79.38%) | +1.88 pp | -2.19 pp | pass |

Pooled DAgger performance was 745/960 (77.60%), improving the initial BC
checkpoints by 2.81 percentage points while remaining 3.96 points below the
81.56% iteration004 baseline. Historical-Silver remained the clear floor at
51/120 (42.50%), 15 points below the baseline rate. All 960 raw schedule keys
were unique; action errors and max-step hits were zero.

## Locked validation

Teacher top-1 was 86.54%, 86.42%, and 87.33% across the three seeds. Optional
selection reached 91.44–92.71%, while multiple selection remained
74.81–75.24%. Illegal actions and representability fallbacks were zero. All
three seeds therefore missed the fixed 98% overall gate and the per-family
gate.

The one allowed DAgger round is exhausted. The fixed-evaluation drop of at
least five points did not reproduce across seeds, so the predeclared trigger
for a state/action-representation investigation is not met. PPO is still
blocked by the validation gate, and the learned branch stops here without
selecting the best seed.

Detailed values and source hashes are recorded in
[`COMPLETE_ACTION_BC_DAGGER1_RESULT.json`](COMPLETE_ACTION_BC_DAGGER1_RESULT.json).
