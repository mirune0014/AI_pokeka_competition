# repair1 fixed160 independent numerical audit

Material Passport: `academic-research-suite/experiment-agent`, mode `validate`, 2026-08-03, verification status `ANALYZED`.
Completed outputs were audited without rerunning or expanding simulation.

## Verdict

The frozen-160 safety/non-regression checks pass, but the immutable acceptance set does not: natural starts are `2`, below the required `4`.
The two seats each have one start, so the per-seat minimum passes.
All 160 paired outcomes are equal; this supports safety on this schedule only and supplies no evidence that the candidate is stronger.

## Fixed-160 recomputation

For seat 0, the tested policy is agent A/player 0 and wins exactly when `result == 0`.
For seat 1, it is agent B/player 1 and wins exactly when `result == 1`.
The same mapping was applied separately to baseline, duplicate baseline, and candidate rows.

- Schedule key `(panel, opponent, seat, seed)`: expected `160`, independently reconstructed `160`; duplicates, missing keys, and extra keys are all `0`.
- Baseline A, baseline B, and candidate each have exactly `160` unique schedule keys and exact schedule equality.
- Baseline: `100-60` (`62.5%`); candidate: `100-60` (`62.5%`); delta `0/160` (`0.0 pp`).
- Paired gains/regressions/ties: `0 / 0 / 160`; every scheduled seed has the same winner.
- With zero discordant outcomes, the exact two-sided 95% upper bound on any discordance probability is `2.279%`; the corresponding conservative signed paired-delta interval is `[-2.279, +2.279] pp`.
- Result mismatches are `0`, but one step-count mismatch remains: historical Silver, seat 0, seed `271828198`, baseline `106` versus candidate `108` steps.

| Opponent | Seat | Baseline | Candidate | Delta |
|---|---:|---:|---:|---:|
| alakazam_capbloo_gold | 0 | 16/20 (80%) | 16/20 (80%) | 0 |
| alakazam_capbloo_gold | 1 | 13/20 (65%) | 13/20 (65%) | 0 |
| arch_peak | 0 | 6/20 (30%) | 6/20 (30%) | 0 |
| arch_peak | 1 | 14/20 (70%) | 14/20 (70%) | 0 |
| marnie_kazuki_live | 0 | 14/20 (70%) | 14/20 (70%) | 0 |
| marnie_kazuki_live | 1 | 17/20 (85%) | 17/20 (85%) | 0 |
| historical_silver | 0 | 11/20 (55%) | 11/20 (55%) | 0 |
| historical_silver | 1 | 9/20 (45%) | 9/20 (45%) | 0 |

Seat totals are `47/80` (seat 0) and `53/80` (seat 1) for both policies.
Opponent totals are `29/40`, `20/40`, `31/40`, and `20/40` in the table's opponent order.
The recurring absolute floor hidden by the aggregate is arch_peak seat 0 at `6/20` (`30%`); equality does not repair that floor.

## Mechanical and duplicate controls

Action-error rows and total action errors, max-step hits, exceptions, start faults, nonzero exits, invalid results, command faults, and summary seed/count faults are all `0`.
The identical-policy baseline control matches `160/160` on runner result/step fields, `160/160` on full summary content apart from trace path, and `160/160` on trace SHA-256.
Runner-report, cell-summary, and physical-paired-CSV numeric disagreements are all `0`.

The physical paired CSVs omit the required literal `panel` column.
The containing immutable panel directory uniquely restores it, so numerical schedule equality is established, but the literal output-schema contract is not fully satisfied.

## Natural telemetry coverage

A start is counted only when the selected source is `CERTIFIED_LATE_BOUNDARY_ULTRA_BALL_ROUTE_V3`, `owner_before` is null, and `owner_after.stage` is `ULTRA_PLAY_EMITTED`.
A completion is a later row with `rule3_completed == true`.

| Seat / seed | Starts | Completions | Route | Certificate | Fault rows |
|---|---:|---:|---|---|---:|
| 0 / 271828198 | 1 | 1 | ACTIVE_EX_FUEL_ROUTE | R3_WIN_NOW | 0 |
| 1 / 271828188 | 1 | 1 | ACTIVE_EX_FUEL_ROUTE | R3_WIN_NOW | 0 |

Both starts use parent boundary `DEFER_AND_REEVALUATE`, reach completion, and preserve the parent search at completion.
Across both telemetry files, `irreversible_abort_fault`, `rule3_fault_latched`, and `rule3_run_failed` produce `0` fault-flagged rows.

## Immutable checks

| Check | Observed / required | Status |
|---|---|---|
| Unique schedule keys | 160 / 160 | PASS |
| Duplicate summaries | 160 / 160 | PASS |
| Duplicate byte-trace hashes | 160 / 160 | PASS |
| Execution/start/action/exception/max-step faults | all 0 / 0 | PASS |
| Paired gains at least regressions | 0 >= 0 | PASS |
| Maximum regression per seat or opponent | 0 / at most 2 wins | PASS |
| Natural starts per seat | seat 0: 1; seat 1: 1 / at least 1 | PASS |
| Natural starts total | 2 / at least 4 | **FAIL** |

Therefore the numerical safety gate passes, the strength verdict is neutral/insufficient, and the full immutable acceptance set fails.

## Input provenance

Raw root: `autonomous_gold_20260715/evaluations/archaludon_certified_late_boundary_ultra_ball_route_v3_repair1/fixed160_raw`.

- historical Silver: `paired_results.csv` `1117F92F98A668D9DF22CE829BCB3D075E56E524DE3A96CD2BE68E676A5BFCF8`; `manifest.jsonl` `510C4E606DDA0B0991F5344F92C6E7CE3A35FFA176258E7185DB81DCB4092D47`; `report.json` `37706612165C1E2D80C3485C70D0AC571CF6F7148EA79C96B342390A376B7315`; `cell_summary.csv` `BD30AEA1526B09FAE2147F5DE0D072AB56BCC0546E2B6485E5A938090F89A1F4`.
- adjacent population: `paired_results.csv` `F6B2596699ABB1CE767EF35B39A38A75DB4F2229DCED2132F8BFE4D9A6CA771E`; `manifest.jsonl` `0E2A7445A8F1DD684B46A29A39A4EB1A257CE80589144FB0B68FA630B9BEB194`; `report.json` `AF692679EE949E2D6B72A3EE1283361A1F6A1A5C7A1DFEB16FF6F7D639BBCCE4`; `cell_summary.csv` `BAF347F4C437B5028B053CC2601A2562DCCBD4EEC053E225505EB42258B0E96C`.
- telemetry: seat 0 `DD9896772E1B060CEC45BFF48F1E9D98423088A108A78555EAA3FCA0CA7F6975`; seat 1 `2D2C104EB370183D1FB4E1061C0392A8D96428EE9D5AB4652D036140B5D48326`; two-row first-difference CSV `9AB61CCF578D3E5DCF7EC1E273DD7D934D492B6F022C3812AA9FB72A201CF83D`.
- overlay spec `7C8BF76AAAF1909F4DD364DBD7184062F5DC29AC0968B6414EA3E1CD61A3A96F`; base schedule spec `E2B8986663A43A7F6F52888E487F39B8D059CDCDDF441A3E87D8C093DF15274C`.
- baseline `main.py` `4287A616E1611F5697964D9F4065978EED1CEA72CDB48C9F63F1430D69106C35`; candidate `main.py` `3D95357E75E0B00CB679C1A31F6612AD1FA0EF44914E8ECA8C272CE9220027C3`.

Primary rates were recomputed from manifest-linked raw rows; supplied aggregates were used only for disagreement checks.
The statistical fallacy scan covered all `11/11` patterns; no reversal or causal/strength claim is made, and inference is explicitly limited to the frozen opponent/seat/seed schedule.
