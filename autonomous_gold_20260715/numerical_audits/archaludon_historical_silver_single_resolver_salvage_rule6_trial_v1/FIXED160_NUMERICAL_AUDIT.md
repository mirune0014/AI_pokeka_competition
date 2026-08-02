# Rule 6 fixed160 independent numerical audit

## Verdict

**REJECT: the frozen coverage gate fails.** All execution, duplicate-control, schedule, and numerical-retention checks pass, but Rule 6 has one natural shadow start and **zero completed ready or whiff transactions** across shadow plus fixed160. The strategy therefore classifies this as an incomplete natural implementation, not `DEFER-DORMANT`. Rule 5 remains the accepted parent.

The fixed160 result itself is exactly neutral: baseline Rule 5 **100-60 (62.50%)**, candidate Rule 6 **100-60 (62.50%)**, delta **0/160 = 0.00 percentage points**, with paired gains/regressions/ties **0/0/160**. This is compatibility evidence, not evidence of improved strength.

## Independent recomputation

The tested policy-to-player mapping was audited explicitly:

- seat 0: tested policy is agent A / player 0; win iff `result == 0`;
- seat 1: tested policy is agent B / player 1; win iff `result == 1`.

Both paired CSVs were parsed independently. All 160 stored `baseline_win` and `candidate_win` values equal the seat-specific recomputation. The contextual key `(panel, opponent, seat, seed)` has 160 rows and 160 unique keys, exactly equals the immutable schedule, and every row satisfies `seed = seed_base + game`.

| Opponent | Seat / policy player | N | Baseline W-L | Candidate W-L | Candidate rate | Delta | G/R/T |
|---|---:|---:|---:|---:|---:|---:|---:|
| historical_silver | 0 | 20 | 11-9 | 11-9 | 55.0% | 0.0 pp | 0/0/20 |
| historical_silver | 1 | 20 | 9-11 | 9-11 | 45.0% | 0.0 pp | 0/0/20 |
| alakazam_capbloo_gold | 0 | 20 | 16-4 | 16-4 | 80.0% | 0.0 pp | 0/0/20 |
| alakazam_capbloo_gold | 1 | 20 | 13-7 | 13-7 | 65.0% | 0.0 pp | 0/0/20 |
| arch_peak | 0 | 20 | 6-14 | 6-14 | **30.0%** | 0.0 pp | 0/0/20 |
| arch_peak | 1 | 20 | 14-6 | 14-6 | 70.0% | 0.0 pp | 0/0/20 |
| marnie_kazuki_live | 0 | 20 | 14-6 | 14-6 | 70.0% | 0.0 pp | 0/0/20 |
| marnie_kazuki_live | 1 | 20 | 17-3 | 17-3 | 85.0% | 0.0 pp | 0/0/20 |

Panel rates are baseline=candidate **20/40 (50.00%)** against Historical Silver and **80/120 (66.67%)** against the adjacent population. Seat rates are baseline=candidate **47/80 (58.75%)** as player 0 and **53/80 (66.25%)** as player 1. Candidate-minus-baseline delta is zero for both seats and every scheduled seed.

The aggregate hides a severe inherited floor: `arch_peak`, player 0 is **6/20 (30%)**, versus **14/20 (70%)** in player 1. Historical Silver player 1 is also below 50% at **9/20 (45%)**. These floors recur identically in Rule 5 and Rule 6; Rule 6 neither repairs nor worsens them. There is only one approved seed base per panel, so between-seed-base robustness is not estimable.

The observed practical paired effect is **0.00 pp**. Exact McNemar `p=1.0`; no statistically or practically meaningful improvement is observed. The 160 candidate traces are byte-identical to their paired Rule 5 traces, so fixed160 contains no observable policy action change.

## Runner health and duplicate control

- 24 manifest runs; all used `.venv-rl\Scripts\python.exe`, `run_local_battle.py`, and `--engine-seed`; exit faults 0.
- Start faults 0; action errors 0; invalid results 0; max-step hits 0.
- Baseline duplicate control on every opponent/seat/seed: non-trace summary equality **160/160**, result equality **160/160**, decision-count equality **160/160**, byte-trace equality **160/160**.
- Candidate versus baseline: result equality **160/160**, decision-count equality **160/160**, byte-trace equality **160/160**.
- Both runner reports have `valid=true`, empty invalid reasons, zero duplicate mismatches, and aggregates matching the independent recomputation.

## Coverage gate

Frozen shadow evidence (`shadow_summary.json` and its single difference row):

- natural starts: **1**;
- attributable action differences: **1**, solely `POKE_PAD_DURALUDON_TARGET`;
- ready completions: **0**;
- whiff emissions/completions: **0/0**;
- owned counterfactual fail-close: **1** (`rule6_target_movement_failed`), which is neither a ready completion nor a whiff completion;
- invalid actions, exceptions, and candidate faults: **0**.

Fixed160 adds zero Rule 6 action differences, serialized transaction markers, ready completions, or whiffs. Combined coverage is therefore one natural start and zero completed-or-whiff transactions.

| Acceptance check | Observed | Result |
|---|---:|---:|
| Exact 160-key immutable schedule | 160/160 | PASS |
| Duplicate result/decision/byte-trace equality | 160/160 | PASS |
| Execution/start/action/max-step faults | 0 | PASS |
| Paired gains at least regressions | 0 >= 0 | PASS |
| No opponent/seat cell at least 3 wins below parent | worst delta 0 | PASS |
| `minimum_natural_starts=1` | 1 | PASS |
| `minimum_completed_or_whiff_transactions=1` | **0** | **FAIL** |
| Dormant condition (`combined starts == 0`) | false | Not applicable |

Because a natural start exists but neither completion route is observed, the frozen strategy requires **REJECT incomplete implementation**. Numerical neutrality cannot override that explicit coverage failure.

## Frozen identities and raw outputs

- Overlay spec: `autonomous_gold_20260715/evaluation_specs/archaludon_historical_silver_single_resolver_salvage_rule6_trial_v1/fixed160_spec.json`, SHA-256 `4BE2C65E3F28D403664769E50C0F1078BCC4A1BBAD134222ACDBA60AC24BD3BF`.
- Schedule base SHA-256 `E2B8986663A43A7F6F52888E487F39B8D059CDCDDF441A3E87D8C093DF15274C`.
- Baseline Rule 5 `main.py` SHA-256 `D966E455E5110F9D5616195AEAAC8663E6A92F310DAFC4B7F79E4D37149A9C62`.
- Candidate Rule 6 `main.py` SHA-256 `02180DB5EA65356FA85301D7978EF088725FCA241B84EE68B29E102B77655164`.
- Shared deck SHA-256 `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`.
- Parent-frozen raw root: `autonomous_gold_20260715/evaluations/archaludon_historical_silver_single_resolver_salvage_rule6_trial_v1/fixed160_raw`; supplied runner-tree digest `393A162DE440DB52CE5E8A29C0B2AE9B5576A409F771722C6335B99CE49A4C66`.
- `historical_silver/paired_results.csv`: `79110266032FF39C63EE3142E72FE228DBC82DF5BBE3BFDB397D8E20FF3FBA22`; `report.json`: `37706612165C1E2D80C3485C70D0AC571CF6F7148EA79C96B342390A376B7315`.
- `adjacent_population/paired_results.csv`: `F6B2596699ABB1CE767EF35B39A38A75DB4F2229DCED2132F8BFE4D9A6CA771E`; `report.json`: `AF692679EE949E2D6B72A3EE1283361A1F6A1A5C7A1DFEB16FF6F7D639BBCCE4`.
- Shadow summary SHA-256 `63EBFE999FD8918C67A45DE2401CC53224EAFFE0A8C2520E081ABC74AFE87ADA`; shadow differences SHA-256 `55AB30EA634CD9A3359A19B523AEB5278F6966D5E8A72167630EB45C55B9F8FF`.

## Reproducibility and assumptions

Recalculation is: parse both `paired_results.csv` files; derive each policy win as `int(result) == int(seat)`; attach `panel` from the containing raw subdirectory; assert the exact schedule-key set and seed formula; group by panel/opponent/seat; and classify each pair as gain, regression, or tie. Duplicate controls are reconstructed from manifest-linked `baseline_a` and `baseline_b` summaries, using `steps` as the decision count and excluding only the run-specific `trace` pathname before summary equality; corresponding trace files are compared by binary SHA-256.

Assumptions: the parent-supplied runner-tree digest is the immutable whole-tree identity, while the audit independently hashes the decision-critical CSV/report/shadow files; fixed160 coverage is limited to observable raw action/marker evidence and the frozen coverage counters, with no unlogged internal action inferred; the one malformed source replay listed by the shadow artifact is an excluded corpus input, not a fixed160 execution fault. No simulation, matrix expansion, source edit, raw-output edit, or external write was performed.
