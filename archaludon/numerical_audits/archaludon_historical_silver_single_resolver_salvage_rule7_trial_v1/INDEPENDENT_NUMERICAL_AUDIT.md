# Rule 7 fixed160 independent numerical audit

## Recommendation

**FAIL the frozen fixed160 numerical stage gates.** This is not a final rule-adoption judgment. Execution, immutable-schedule, duplicate-control, and observable Rule 7 mechanism gates pass, but the candidate has only **3 paired gains versus 5 regressions**, and player 1 falls **3 wins** below Rule 5, exceeding the allowed per-seat/opponent regression of 2.

Rule 5 finishes **100-60 (62.50%)** and Rule 7 **98-62 (61.25%)**. The paired effect is **-2/160 = -1.25 percentage points**. The exact McNemar two-sided value is `p=0.7265625`; the primary stratified paired seed-cluster empirical-bootstrap 95% interval is **[-7,+3] wins**, or **[-4.375,+1.875] pp**. The interval includes zero, while the observed effect is negative; there is no statistically or practically meaningful improvement.

## Independent reconstruction

Policy-to-player mapping was audited from all 24 manifest commands and independently applied to every raw result:

- seat 0: tested policy is agent A / player 0; win iff `result == 0`;
- seat 1: tested policy is agent B / player 1; win iff `result == 1`.

The contextual key `(panel, opponent, seat, seed)` has exactly **160 rows and 160 unique keys**. Baseline and candidate key sets exactly equal each other and the immutable schedule; every seed is `seed_base + game`. All 160 stored baseline/candidate win flags agree with seat-specific recomputation from `result`.

| Panel / opponent | Seat / player | N | Rule 5 W-L | Rule 7 W-L | Rule 7 rate | Delta | G/R/T |
|---|---:|---:|---:|---:|---:|---:|---:|
| historical_silver / historical_silver | 0 | 20 | 11-9 | 11-9 | 55% | 0 | 0/0/20 |
| historical_silver / historical_silver | 1 | 20 | 9-11 | 8-12 | **40%** | -1 | 1/2/17 |
| adjacent_population / arch_peak | 0 | 20 | 6-14 | 8-12 | **40%** | +2 | 2/0/18 |
| adjacent_population / arch_peak | 1 | 20 | 14-6 | 12-8 | 60% | -2 | 0/2/18 |
| adjacent_population / alakazam_capbloo_gold | 0 | 20 | 16-4 | 15-5 | 75% | -1 | 0/1/19 |
| adjacent_population / alakazam_capbloo_gold | 1 | 20 | 13-7 | 13-7 | 65% | 0 | 0/0/20 |
| adjacent_population / marnie_kazuki_live | 0 | 20 | 14-6 | 14-6 | 70% | 0 | 0/0/20 |
| adjacent_population / marnie_kazuki_live | 1 | 20 | 17-3 | 17-3 | 85% | 0 | 0/0/20 |

Panel totals are Historical Silver **20/40 -> 19/40** (`50.00% -> 47.50%`, -1) and adjacent population **80/120 -> 79/120** (`66.67% -> 65.83%`, -1). Opponent totals are Historical Silver `20 -> 19`, Alakazam `29 -> 28`, Arch Peak `20 -> 20`, and Marnie `31 -> 31`.

Seat totals expose the failed retention gate: player 0 improves **47/80 -> 48/80** (`+1`), while player 1 regresses **53/80 -> 50/80** (`-3`; one gain/four regressions). The aggregate also hides two severe 40% floors: Arch Peak player 0 improves from 30% but remains only **8/20**, while Historical Silver player 1 falls from 45% to **8/20**. Arch Peak player 1 separately falls from 70% to 60%.

Seed sensitivity is concentrated but unfavorable in both panels. Each panel has one approved seed base and 20 shared engine-seed clusters. Historical Silver has positive/zero/negative cluster counts `1/17/2` at seeds `271828182:+1`, `271828183:-1`, `271828191:-1`; adjacent population is also `1/17/2` at `271958316:+1`, `271958314:-1`, `271958317:-1`. Seed `271958329` contains one Arch Peak gain and one regression that cancel at cluster level. Between-seed-base robustness is not estimable.

## Runner health, duplicate control, and mechanism coverage

- 24 subprocess runs; every command uses `.venv-rl\Scripts\python.exe`, `run_local_battle.py`, the frozen seeded engine, and `--engine-seed`.
- Across all 480 baseline-A, baseline-B, and candidate game rows: exit failures `0`, start faults `0`, action errors `0`, populated exception fields `0`, invalid results `0`, and max-step hits `0`.
- Identical-policy baseline-A/baseline-B control on every seat/bucket/seed: runner six-field tuple, non-trace summary, result, decision count, and byte trace all match **160/160**. This control is audited before interpreting seat deltas.
- Candidate versus Rule 5: result equality `152/160`, decision-count equality `141/160`, byte-trace equality `127/160`.
- The retained flattened traces conservatively prove at least **87 Rule 7 starts**: 79 nonempty transactions plus 8 exact zero selections. All **79/79** nonempty transactions have an immediate next engine state showing one added Basic Metal per target callback, exact-three primary readiness, allocation cap three, at most one backup, and no third recipient. Thus fixed160 observable final emissions are at least **79**. Seventeen other candidate-side Turbo callbacks are left delegated/unattributed rather than inferred to be Rule 7 starts.

The Rule 7 overlay checks therefore pass: natural starts `87 >= 1`, externally verified final emissions `79 >= 1`, external next-state verification `79/79`, and the zero-start dormancy condition is false. The raw runner omitted `--trace-options`, so physical serial tie-breaking, internal owner/proposal labels, status, and stadium fields are not claimed observable from these retained traces.

## Acceptance checks

| Check | Observed | Result |
|---|---:|---:|
| Frozen hashes and seeded commands | exact | PASS |
| Unique immutable keys and exact schedule equality | 160/160 | PASS |
| Duplicate non-trace summary / result / decisions / byte trace | 160/160 each | PASS |
| Exit / start / action / exception / max-step faults | 0 | PASS |
| Minimum observable natural starts | 87 >= 1 | PASS |
| Minimum externally verified final emissions | 79 >= 1 | PASS |
| Paired gains at least regressions | **3 < 5** | **FAIL** |
| Maximum 2-win regression per seat or opponent | **player 1 = -3** | **FAIL** |

## Discordant outcome ledger

All paths below are relative to raw root `autonomous_gold_20260715/evaluations/archaludon_historical_silver_single_resolver_salvage_rule7_trial_v1/fixed160_raw`. `B/C` are baseline/candidate `result`; they are winning player indices. `Steps` are baseline/candidate decision counts.

| Key `(panel, opponent, seat, seed)` | Direction | B/C | Steps | Baseline trace | Candidate trace |
|---|---:|---:|---:|---|---|
| adjacent_population, alakazam_capbloo_gold, 0, 271958317 | regression | 0/1 | 115/167 | `adjacent_population/throwaway_traces/0006_271958313_alakazam_capbloo_gold_p0_baseline_a/game_0004.jsonl` | `adjacent_population/throwaway_traces/0008_271958313_alakazam_capbloo_gold_p0_candidate/game_0004.jsonl` |
| adjacent_population, arch_peak, 0, 271958316 | gain | 1/0 | 142/165 | `adjacent_population/throwaway_traces/0000_271958313_arch_peak_p0_baseline_a/game_0003.jsonl` | `adjacent_population/throwaway_traces/0002_271958313_arch_peak_p0_candidate/game_0003.jsonl` |
| adjacent_population, arch_peak, 0, 271958329 | gain | 1/0 | 160/165 | `adjacent_population/throwaway_traces/0000_271958313_arch_peak_p0_baseline_a/game_0016.jsonl` | `adjacent_population/throwaway_traces/0002_271958313_arch_peak_p0_candidate/game_0016.jsonl` |
| adjacent_population, arch_peak, 1, 271958314 | regression | 1/0 | 135/131 | `adjacent_population/throwaway_traces/0003_271958313_arch_peak_p1_baseline_a/game_0001.jsonl` | `adjacent_population/throwaway_traces/0005_271958313_arch_peak_p1_candidate/game_0001.jsonl` |
| adjacent_population, arch_peak, 1, 271958329 | regression | 1/0 | 160/145 | `adjacent_population/throwaway_traces/0003_271958313_arch_peak_p1_baseline_a/game_0016.jsonl` | `adjacent_population/throwaway_traces/0005_271958313_arch_peak_p1_candidate/game_0016.jsonl` |
| historical_silver, historical_silver, 1, 271828182 | gain | 0/1 | 136/129 | `historical_silver/throwaway_traces/0003_271828182_historical_silver_p1_baseline_a/game_0000.jsonl` | `historical_silver/throwaway_traces/0005_271828182_historical_silver_p1_candidate/game_0000.jsonl` |
| historical_silver, historical_silver, 1, 271828183 | regression | 1/0 | 85/132 | `historical_silver/throwaway_traces/0003_271828182_historical_silver_p1_baseline_a/game_0001.jsonl` | `historical_silver/throwaway_traces/0005_271828182_historical_silver_p1_candidate/game_0001.jsonl` |
| historical_silver, historical_silver, 1, 271828191 | regression | 1/0 | 152/147 | `historical_silver/throwaway_traces/0003_271828182_historical_silver_p1_baseline_a/game_0009.jsonl` | `historical_silver/throwaway_traces/0005_271828182_historical_silver_p1_candidate/game_0009.jsonl` |

## Frozen identities, raw hashes, and reproducibility

- Overlay spec: `autonomous_gold_20260715/evaluation_specs/archaludon_historical_silver_single_resolver_salvage_rule7_trial_v1/fixed160_spec.json`, SHA-256 `3B60AE8008D6ED8977B9703AFD070F99618E13E9AB521AA6B52E241F2F28245E`.
- Schedule base: `autonomous_gold_20260715/evaluation_specs/archaludon_historical_silver_single_resolver_salvage_v1_rule1/fixed160_spec.json`, SHA-256 `E2B8986663A43A7F6F52888E487F39B8D059CDCDDF441A3E87D8C093DF15274C`.
- Rule 5 `main.py`: SHA-256 `D966E455E5110F9D5616195AEAAC8663E6A92F310DAFC4B7F79E4D37149A9C62`.
- Rule 7 `main.py`: SHA-256 `9C2D5935364C0940967D48D85E2690EC386569143CD922186A31C716C5391BC1`.
- Shared deck: SHA-256 `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`.
- Raw tree: 512 files, portable ledger SHA-256 `E1CD954384236C5FB119799A03B45B3C93A3E6010597FC00868EE8F68264E700`, defined as SHA-256 of sorted UTF-8 `relative/path<TAB>bytes<TAB>file_sha256<LF>` rows.
- `historical_silver/paired_results.csv`: `E020E22D717C815020186E30AD7DA1B5718BF62551944ABBB4EEA6F66B709567`; `manifest.jsonl`: `C0DACE327CF1CA122692CE9F0027027A580A3B7945F04A37468A5028DAEAD378`; `report.json`: `8414DE19B0AD66E27914AB3377D83448854AEDA4EAFAC544EB2358492062E9C2`.
- `adjacent_population/paired_results.csv`: `EEC61025F3EA87952A9EAA12B3FD4B4B60DFDD8324CD6304FA19DECF82259CA2`; `manifest.jsonl`: `A5D6DE4A9BE53A94FD0F20FBBE2CB20121824CD066A92D201B70816E61737483`; `report.json`: `2EF29FF6B255A5CD401AFF733C35A34691E32F97ADD007665862D39C4DA13C45`.

Reproduce the calculation without writing runner outputs:

```powershell
.venv-rl\Scripts\python.exe -B autonomous_gold_20260715\numerical_audits\archaludon_historical_silver_single_resolver_salvage_rule7_trial_v1\audit_fixed160.py
```

Assumptions: panel identity comes from each containing raw subdirectory because `paired_results.csv` omits a panel column; the mechanism count is a conservative externally verified lower bound, not an inference from unlogged internal telemetry; and the paired interval is conditional on the frozen opponent/seed design. No simulation, matrix expansion, implementation edit, deck edit, schedule edit, raw-output edit, or external write was performed.
