# Root recomputation: Rule 8 fixed160

## Result

`DEFER-DORMANT`. Rule 8 is not integrated and its conditions are not widened.

## Independent root calculation

Root parsed both canonical `paired_results.csv` files and recomputed each win
as `result == tested seat` without trusting the stored win columns.

- Rows: 160.
- Unique `(panel, opponent, seat, seed)` keys: 160.
- Expected schedule: eight opponent/seat cells, each with exactly the frozen 20
  consecutive seeds; missing/unexpected cells or seeds: zero.
- Stored versus recomputed win mismatches: zero.
- Rule 5 wins: 100/160.
- Rule 8 wins: 100/160.
- Paired gains/regressions/ties: 0/0/160.
- Baseline/candidate step mismatches: zero.
- Candidate/baseline trace-file SHA mismatches: zero across all 160 games.
- Both runner reports: `valid=true`, duplicate mismatches zero, invalid reasons
  zero.

### Cells

| Opponent | Seat | Rule 5 | Rule 8 | Delta |
|---|---:|---:|---:|---:|
| historical_silver | 0 | 11/20 | 11/20 | 0 |
| historical_silver | 1 | 9/20 | 9/20 | 0 |
| arch_peak | 0 | 6/20 | 6/20 | 0 |
| arch_peak | 1 | 14/20 | 14/20 | 0 |
| alakazam_capbloo_gold | 0 | 16/20 | 16/20 | 0 |
| alakazam_capbloo_gold | 1 | 13/20 | 13/20 | 0 |
| marnie_kazuki_live | 0 | 14/20 | 14/20 | 0 |
| marnie_kazuki_live | 1 | 17/20 | 17/20 | 0 |

Seat totals are 47/80 for seat 0 and 53/80 for seat 1 for both policies.

## Activity gate

The checked runner did not persist a dedicated Rule 8 internal telemetry field;
that field is missing rather than a directly measured zero. However, all 160
candidate traces are byte-identical to their Rule 5 baseline traces. Under the
frozen source and contract, every Rule 8 start necessarily changes the emitted
action from attack `223` to attack `224`. Therefore fixed160 has zero observable
Rule 8 starts.

Root separately reran the full replay shadow: 30,977 callbacks, zero Rule 8
starts, and zero differences. The combined natural-start count is zero, so the
minimum-start gate fails and `dormant_if_shadow_plus_fixed160_starts == 0`
controls the decision.

## Independent-audit agreement

The root counts agree with
`numerical_audits/archaludon_historical_silver_single_resolver_salvage_rule8_trial_v1/INDEPENDENT_NUMERICAL_AUDIT.md`
(SHA-256 `71A6D30E58BE79A244F6700C6DCCC38D788FADCA2C079EB2E9DDE59AD43C875F`).
No discrepancy was repaired or suppressed.
