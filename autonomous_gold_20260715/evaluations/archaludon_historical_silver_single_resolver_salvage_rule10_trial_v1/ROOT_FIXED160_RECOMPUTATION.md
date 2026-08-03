# Root recomputation: Rule 10 fixed160

## Result

`DEFER-DORMANT`. Rule 10 is not integrated and its conditions are not widened.

## Frozen inputs

- Fixed160 spec SHA-256: `B647B547DCB377F156ED24B32AA0B77A0CDA7BB9618DDBE5FF7E11D006A02EE0`.
- Checked wrapper SHA-256: `0A2154D723D7DFDD9C9881219065E1EA36A8CE9110BBDBB6B9C17DD0BBC868AF`.
- Rule 5 baseline `main.py`: `D966E455E5110F9D5616195AEAAC8663E6A92F310DAFC4B7F79E4D37149A9C62`.
- Rule 10 candidate `main.py`: `2C9249F74CA37429DECEA4801E736E13085E50C19956BB0C75176B9D6759245A`.

## Independent root calculation

Root parsed both canonical `paired_results.csv` files and recomputed each win
as `result == tested seat` without trusting the stored win columns.

- Rows: 160.
- Unique `(panel, opponent, seat, seed)` keys: 160.
- Schedule: eight opponent/seat cells, each with games 0--19 and the exact
  consecutive seed sequence from its frozen seed base; deviations: zero.
- Stored versus recomputed win mismatches: zero.
- Rule 5 wins: 100/160.
- Rule 10 wins: 100/160.
- Paired gains/regressions/ties: 0/0/160.
- Baseline/candidate step mismatches: zero.
- Candidate/baseline trace-file SHA mismatches: zero across all 160 games.
- Summary rows across baseline A, duplicate baseline B, and candidate: 480.
- Start faults, action errors, and max-step hits: 0/0/0.
- Manifest entries: 24; nonzero exit codes: zero.
- Both runner reports: `valid=true`, duplicate mismatches zero, invalid reasons
  zero.

### Cells

| Opponent | Seat | Rule 5 | Rule 10 | Delta |
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

All 160 candidate traces are byte-identical to their Rule 5 baseline traces.
Unlike Rule 9, a Rule 10 entry necessarily changes the emitted public action
from the parent's registered ATTACK to a bound Full Metal Lab PLAY. Therefore
trace identity proves zero fixed160 Rule 10 starts and zero complete natural
FML-to-same-attack transactions.

Root separately reran the full replay shadow: 30,977 callbacks, zero starts,
completions, aborts, faults, or action differences. Combined natural activity
is zero. The frozen minimum of one complete non-fixture transaction fails, so
the controlling result is `DEFER-DORMANT`; fixed160 numerical parity cannot
substitute for mechanism coverage.

## Execution integrity

The evaluation runner executed the exact requested outer command with
`py -3.11 -B`, exited zero, and wrote to the frozen empty destination. Frozen
input hashes, inner seeded manifests, schedule, duplicate controls, and output
hashes validated. No execution-command discrepancy is present.

## Independent-audit agreement

The root counts agree with
`numerical_audits/archaludon_historical_silver_single_resolver_salvage_rule10_trial_v1/INDEPENDENT_NUMERICAL_AUDIT.md`
(SHA-256 `DCB908B411CCCAACA57F73D21636972284EF95254BBBBA5BAF7ED5E023549DA5`).
Both calculations independently find exact 100/160 parity, G/R/T 0/0/160,
all 160 candidate traces byte-identical, zero execution faults, and zero Rule
10 natural starts or completions. No discrepancy was repaired or suppressed.
