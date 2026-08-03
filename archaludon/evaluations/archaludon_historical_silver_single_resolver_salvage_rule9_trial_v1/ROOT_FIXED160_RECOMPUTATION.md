# Root recomputation: Rule 9 fixed160

## Result

`DEFER-DORMANT`. Rule 9 is not integrated and its conditions are not widened.
The fixed schedule proves mechanical neutrality, but it does not prove the
required natural Gear-to-Boss completion.

## Frozen inputs

- Fixed160 spec SHA-256: `DC4F17D354374B3CA048CB1DEA3EDAAED1CBB9AAC7FE5063DD5956AB75CCDE4B`.
- Checked wrapper SHA-256: `0A2154D723D7DFDD9C9881219065E1EA36A8CE9110BBDBB6B9C17DD0BBC868AF`.
- Rule 5 baseline `main.py`: `D966E455E5110F9D5616195AEAAC8663E6A92F310DAFC4B7F79E4D37149A9C62`.
- Rule 9 candidate `main.py`: `FC2ACC8F1AA08AC32D85B20001E420D9D036853B117FF11539D985D99B7395D0`.

## Independent root calculation

Root parsed both canonical `paired_results.csv` files and recomputed each win
as `result == tested seat` without trusting the stored win columns.

- Rows: 160.
- Unique `(panel, opponent, seat, seed)` keys: 160.
- Schedule: eight opponent/seat cells, each with games 0--19 and the exact
  consecutive seed sequence from its frozen seed base; deviations: zero.
- Stored versus recomputed win mismatches: zero.
- Rule 5 wins: 100/160.
- Rule 9 wins: 100/160.
- Paired gains/regressions/ties: 0/0/160.
- Baseline/candidate step mismatches: zero.
- Candidate/baseline trace-file SHA mismatches: zero across all 160 games.
- Summary rows across baseline A, duplicate baseline B, and candidate: 480.
- Start faults, action errors, and max-step hits: 0/0/0.
- Manifest entries: 24; nonzero exit codes: zero.
- Both runner reports: `valid=true`, duplicate mismatches zero, invalid reasons
  zero.

### Cells

| Opponent | Seat | Rule 5 | Rule 9 | Delta |
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

The fixed runner did not persist Rule 9 owner-stage telemetry. That telemetry is
missing, not measured zero. In particular, Rule 9 deliberately returns the
same Gear action as Rule 5 at entry, so byte-identical traces cannot prove that
the entry gate never armed.

All 160 candidate traces are byte-identical to the Rule 5 traces. Therefore no
observable candidate-owned continuation changed a public action. The natural
replay shadow likewise covered 30,977 callbacks with zero Rule 9 differences,
but it also did not persist an internal entry counter. Neither evidence source
contains a provable complete non-fixture
`Gear -> reveal Boss -> play Boss -> select target -> same terminal attack`
transaction. The frozen adoption gate requires at least one such completion.
Its satisfaction is therefore **unproven**, and the controlling result is
`DEFER-DORMANT`; absence of telemetry is not converted into a claimed zero.

## Execution-command discrepancy

The execution operator was asked to invoke
`py -3.11 -B ...run_fixed160.py --execute` but used
`.venv-rl\Scripts\python.exe -B ...run_fixed160.py --execute`. Both resolve to
Python 3.11.6. The frozen spec, wrapper, candidate and baseline hashes remained
the requested values; all inner manifests, schedules and outputs validated.
The deviation is recorded rather than suppressed and does not invalidate the
mechanical comparison. It also does not repair the missing activity evidence.

## Independent-audit agreement

The root counts agree with
`numerical_audits/archaludon_historical_silver_single_resolver_salvage_rule9_trial_v1/INDEPENDENT_NUMERICAL_AUDIT.md`
(SHA-256 `CE316741F15BFC55F9B4810C97CBBD7D98371BEF4D6BEAAB80BE58C1626B7BE1`).
That audit scanned 8,881 candidate callbacks, found 236 ordinary Gear reveal
prompts and six physical same-turn Gear/Boss/switch/attack shapes, but found
zero shape satisfying the frozen all-remaining-Prize entry certificate. This
supports `0 proven complete natural transactions` while preserving the
distinction that unpersisted entry starts remain unknown. No discrepancy was
repaired or suppressed.
