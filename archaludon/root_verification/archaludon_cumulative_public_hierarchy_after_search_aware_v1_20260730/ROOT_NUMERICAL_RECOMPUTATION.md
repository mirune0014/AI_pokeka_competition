# Root fixed-760 numerical recomputation

Recomputed: 2026-07-30 04:02 JST

## Immutable raw inputs

- Combined physical-panel CSV SHA-256:
  `B58EBC8CF088B9B740651E8058478838D27EB1D0205A1E8CFB4C303276340BB4`
- Execution manifest SHA-256:
  `E28E458C456A7F1259C5781F2CD82C80B9DF2CDC5A1DEDCDE449ECC5A1BADFD4`
- Historical report SHA-256:
  `F54D80C469309306C2558E9F92F4ED26A8832BBEE4A906A827F0FCA22B96A48B`
- Adjacent report SHA-256:
  `50FBA74DFEAE3A5EEF8663235DB20707CF5E6910E3A42D12A23DA2428512413B`

The deterministic execution operator used the exact frozen command and exited
0 after 663.7 seconds. Both panel subprocess exit codes in the execution
manifest are 0.

## Root row and schedule checks

- Physical schema:
  `panel,opponent,seat,seed,baseline_win,candidate_win,baseline_result,candidate_result,baseline_steps,candidate_steps`
- Rows: 760.
- Unique `(panel, opponent, seat, seed)` keys: 760.
- Independently reconstructed expected keys from the frozen schedule: 760.
- Missing keys: 0.
- Extra keys: 0.
- Nonbinary win/result values: 0.
- Baseline seat-to-result consistency errors: 0.
- Candidate seat-to-result consistency errors: 0.
- Baseline steps at or above 1000: 0.
- Candidate steps at or above 1000: 0.
- Historical and adjacent checked reports: both `valid=true`,
  `invalid_reasons=[]`, and `duplicate_mismatch_count=0`.

The raw engine result convention is seat-dependent: for seat 0,
`win = 1 - result`; for seat 1, `win = result`. Applying that convention gives
zero consistency errors.

## Root win recomputation

| Cut | Games | Baseline | Candidate | Gains | Regressions |
|---|---:|---:|---:|---:|---:|
| Overall | 760 | 478 | 478 | 0 | 0 |
| Historical-Silver | 200 | 100 | 100 | 0 | 0 |
| Adjacent population | 560 | 378 | 378 | 0 | 0 |
| Seat 0 | 380 | 243 | 243 | 0 | 0 |
| Seat 1 | 380 | 235 | 235 | 0 | 0 |
| Alakazam Gold | 80 | 62 | 62 | 0 | 0 |
| Archaludon peak | 80 | 39 | 39 | 0 | 0 |
| Archaludon Shumpei | 80 | 40 | 40 | 0 | 0 |
| Cynthia v23 | 80 | 67 | 67 | 0 | 0 |
| Kangaskhan/Crustle | 80 | 28 | 28 | 0 | 0 |
| Marnie/Kazuki | 80 | 68 | 68 | 0 | 0 |
| Mega Lucario | 80 | 74 | 74 | 0 | 0 |

Every opponent-by-seat cell also matches the baseline exactly. Therefore the
cumulative candidate has zero parent-win/candidate-loss flips and preserves
the inherited `28/80` Kangaskhan/Crustle floor.

## Changed fixed traces

Outcomes and result values are identical on all 760 rows. Baseline and
candidate step counts differ on exactly four parent-win/candidate-win rows:

| Panel/opponent | Seat | Seed | Baseline steps | Candidate steps |
|---|---:|---:|---:|---:|
| Historical-Silver | 0 | 271828201 | 129 | 127 |
| Archaludon Shumpei | 1 | 271958328 | 126 | 130 |
| Mega Lucario | 0 | 271958329 | 76 | 94 |
| Mega Lucario | 1 | 271958318 | 85 | 95 |

These four trace differences require a separate qualitative certificate and
opportunity-cost audit. Outcome equality is not by itself proof that their
actions are good.

## Root numerical conclusion

The candidate passes the frozen destructive numerical floor:

- exact overall, panel, seat, opponent, and opponent-seat totals;
- zero paired regression;
- zero schedule, duplicate, result, missingness, or max-step fault.

The fixed-760 result demonstrates safety only. It demonstrates no strength
gain because paired gains and regressions are both zero.
