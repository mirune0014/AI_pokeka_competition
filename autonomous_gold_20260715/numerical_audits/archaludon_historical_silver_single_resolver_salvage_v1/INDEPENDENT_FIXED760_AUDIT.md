# Historical-Silver single-resolver salvage v1: independent fixed760 numerical audit

Audit date: 2026-08-03 JST  
Scope: completed raw outputs only; no battle, replay rollout, source edit, deck edit, schedule expansion, or raw-output write was performed.

## Decision

The completed evaluation is deterministic and numerically valid under the explicit structural-panel assumption below. All supplied **base acceptance gates pass**. The independently recomputed result is:

- baseline: **478-282, 62.8947%**;
- candidate: **480-280, 63.1579%**;
- paired change: **G/R/T = 4/2/754**, net **+2 wins / 760 = +0.2632 percentage point**.

The **strengthened gate fails** because `480 < 486`, although both seats are nonworse. This is a tiny positive schedule delta, not evidence of a statistically or practically meaningful strength improvement: only 6/760 pairs are discordant, the exact paired McNemar test gives `p = 0.6875`, and both paired uncertainty intervals below include zero. Recommendation: **PASS the supplied base checks; FAIL strengthened/promotion-as-stronger**.

There is one contract caveat. Neither physical `paired_results.csv` contains a literal `panel` column. The containing directories unambiguously encode it, and adding that structural value yields the exact 760-key schedule. If `required_output_schema` means that `panel` must physically occur as a CSV column, the schema requirement itself fails even though the schedule and every numerical gate pass.

## Frozen inputs and execution identity

Specification:

- `autonomous_gold_20260715/evaluation_specs/archaludon_historical_silver_single_resolver_salvage_v1/fixed760_spec.json`
- expected and actual SHA-256: `49B89DDAEDF6745A7ADD203602DA457BDDE912B2B7F4F18FAA3C2955780BC75D`

Critical policies:

| item | path | independently observed SHA-256 | match |
|---|---|---:|---:|
| baseline `main.py` | `analysis_outputs/reference_agents/historical_silver_archaludon_54495224/main.py` | `F4B578453C9D953BE94885144DD50E05DBA4510DF3340BE27ADE07495896046E` | yes |
| baseline `deck.csv` | `analysis_outputs/reference_agents/historical_silver_archaludon_54495224/deck.csv` | `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A` | yes |
| candidate `main.py` | `autonomous_gold_20260715/final/archaludon_historical_silver_single_resolver_salvage_v1/main.py` | `D966E455E5110F9D5616195AEAAC8663E6A92F310DAFC4B7F79E4D37149A9C62` | yes |
| candidate `deck.csv` | `autonomous_gold_20260715/final/archaludon_historical_silver_single_resolver_salvage_v1/deck.csv` | `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A` | yes |

All 34 file hashes declared by the spec for strategy/freeze documents, baseline/candidate, three runners, seven opponents and the 11 engine files matched. The independently recomputed canonical 11-file engine hash is `466638706BD5C6915E25D1B3CB9E3D966390FBC263F4ED3153108E29C0194FFF`, also matching the spec.

All 48 manifest commands used `.venv-rl\Scripts\python.exe`, `tools\run_local_battle.py`, the specified seeded engine, `--engine-seed`, `--max-steps 1000`, the correct seed base, game count, paths and seat-dependent agent/deck mapping. All 48 exited zero.

## Player mapping and duplicate prerequisite

`run_local_battle.py` records the winning **player index**. This audit therefore used:

- policy in seat 0 = agent A / player 0; policy win iff `result == 0`;
- policy in seat 1 = agent B / player 1; policy win iff `result == 1`.

No player-0 win counter was reused for seat-1 rows. The summary field `your_index` was not used to score the scheduled policy.

An identical-policy control was checked before interpreting seat deltas. For `(historical_silver, historical_silver, seat 0, seed 271828182)`, baseline A and B both had `result=0`, `steps=136`, `turn=16`; their trace SHA-256 values were both `A26BC3E3A1AFF6C65BC179CDFB3BB51D070A59177F06AD8F719F11E05668CCFE`.

Across the complete schedule:

- runner duplicate fields `(seed,result,steps,turn,action_errors,hit_max_steps)`: **760/760 exact**;
- complete summary objects after removing only the necessarily different trace pathname: **760/760 exact**;
- decision count (`steps`): **760/760 exact**;
- baseline A/B trace bytes: **760/760 exact**.

Any nonzero difference would invalidate the full evaluation. Observed differences were zero.

## Completeness and exact schedule

Raw root: `autonomous_gold_20260715/evaluations/archaludon_historical_silver_single_resolver_salvage_v1/fixed760_raw_20260803`

| check | independently observed |
|---|---:|
| physical paired rows | 760 |
| unique `(panel,opponent,seat,seed)` keys after structural panel annotation | 760 |
| expected keys | 760 |
| duplicate / missing / extra keys | 0 / 0 / 0 |
| manifest rows / nonzero exits | 48 / 0 |
| baseline A / baseline B / candidate summary rows | 760 / 760 / 760 |
| preserved traces | 2,280 |
| start faults | 0 |
| action errors | 0 |
| invalid results outside `{0,1}` | 0 |
| max-step hits or `steps >= 1000` | 0 |
| missing traces or trace-line-count != `steps` | 0 |
| execution exceptions evidenced by nonzero exit or incomplete rows | 0 |

The exact schedule was 200 mirror rows (`271828182..271828281`, two seats) and 560 adjacent rows (seven opponents, `271958313..271958352`, two seats). Values independently rebuilt from the summaries matched every physical paired CSV field, all 16 `cell_summary.csv` rows, and both runner reports. Runner aggregates were only cross-checks, not the source of the counts reported here.

## Independent outcome recomputation

For each schedule key, `baseline_win = int(baseline_a.result == seat)` and `candidate_win = int(candidate.result == seat)`. A gain is `(0,1)`, a regression is `(1,0)`, and all other pairs are ties.

| scope | N | baseline W-L / rate | candidate W-L / rate | G/R/T | delta |
|---|---:|---:|---:|---:|---:|
| all | 760 | 478-282 / 62.8947% | 480-280 / 63.1579% | 4/2/754 | +2 / +0.2632 pp |
| historical-silver mirror | 200 | 100-100 / 50.0000% | 100-100 / 50.0000% | 0/0/200 | 0 |
| adjacent population | 560 | 378-182 / 67.5000% | 380-180 / 67.8571% | 4/2/554 | +2 / +0.3571 pp |

### Paired uncertainty and practical size

Let `d_i = candidate_win_i - baseline_win_i` for the 760 matched schedule keys.

- Mean paired effect: `mean(d) = 2/760 = +0.2632 pp`.
- Paired-difference standard error: `0.3224 pp`; 95% t interval (`df=759`): **[-0.3697, +0.8960] pp**.
- Because adjacent seeds are reused across 14 opponent/seat rows and mirror seeds across two seat rows, a stratified engine-seed cluster sensitivity calculation retained the panel weights. Its 95% t interval (`df=39`, the mirror stratum has zero variance) is **[-0.2691, +0.7954] pp**.
- Exact conditional McNemar/binomial test on the six discordant pairs: `G=4`, `R=2`, two-sided **p=0.6875**. The candidate-direction share is 4/6; its exact 95% interval is 22.28%-95.67%.
- Only **6/760 = 0.7895%** of paired outcomes changed. The net practical effect is two games and the strengthened threshold is missed by six wins.

Thus the positive point estimate is compatible with no improvement and with a small regression or small improvement. It must not be interpreted as strength from aggregate sign alone.

## Seat and seed sensitivity

| seat | N | baseline wins / rate | candidate wins / rate | G/R/T | delta |
|---:|---:|---:|---:|---:|---:|
| 0 (agent A/player 0) | 380 | 243 / 63.9474% | 245 / 64.4737% | 2/0/378 | +2 / +0.5263 pp |
| 1 (agent B/player 1) | 380 | 235 / 61.8421% | 235 / 61.8421% | 2/2/376 | 0 |

Within the mirror, both policies were 58/100 in seat 0 and 42/100 in seat 1. That 16-win seat split is shared exactly by baseline and candidate; it is not candidate uplift. Within the adjacent panel, seat 0 was 185 -> 187 and seat 1 was 193 -> 193.

All six discordances occurred in the adjacent panel:

| seed | opponent | seat | baseline result -> candidate result | paired class |
|---:|---|---:|---:|---:|
| 271958313 | kang_crustle | 1 | 1 -> 0 | regression |
| 271958325 | kang_crustle | 0 | 1 -> 0 | gain |
| 271958333 | kang_crustle | 1 | 0 -> 1 | gain |
| 271958339 | kang_crustle | 0 | 1 -> 0 | gain |
| 271958345 | arch_shumpei | 1 | 1 -> 0 | regression |
| 271958345 | kang_crustle | 1 | 0 -> 1 | gain |

The mirror had no discordance across 100 engine seeds. In the adjacent panel, five of 40 seeds carried at least one discordance; seed `271958345` had one gain and one regression and therefore net zero. Cluster net deltas were `+1` for three seeds, `-1` for one, and `0` for 36. There is only one seed base per panel, so cross-seed-base robustness cannot be established from this matrix.

## Opponent buckets and absolute floors

| opponent | N | baseline wins / rate | candidate wins / rate | G/R/T | delta |
|---|---:|---:|---:|---:|---:|
| historical_silver | 200 | 100 / 50.00% | 100 / 50.00% | 0/0/200 | 0 |
| arch_peak | 80 | 39 / 48.75% | 39 / 48.75% | 0/0/80 | 0 |
| arch_shumpei | 80 | 40 / 50.00% | 39 / 48.75% | 0/1/79 | -1 / -1.25 pp |
| alakazam_capbloo_gold | 80 | 62 / 77.50% | 62 / 77.50% | 0/0/80 | 0 |
| marnie_kazuki_live | 80 | 68 / 85.00% | 68 / 85.00% | 0/0/80 | 0 |
| mega_lucario_public | 80 | 74 / 92.50% | 74 / 92.50% | 0/0/80 | 0 |
| kang_crustle | 80 | 28 / 35.00% | 31 / 38.75% | 4/1/75 | +3 / +3.75 pp |
| cynthia_v23 | 80 | 67 / 83.75% | 67 / 83.75% | 0/0/80 | 0 |

The 63.16% aggregate hides a recurring severe `kang_crustle` floor: candidate 17/40 (42.5%) in seat 0 and 14/40 (35.0%) in seat 1, only 31/80 overall despite the local +3. The candidate also remains below 50% against `arch_peak` (48.75%) and `arch_shumpei` (48.75%); `arch_shumpei` seat 0 is 17/40 (42.5%). High rates against `mega_lucario_public`, `marnie_kazuki_live`, and `cynthia_v23` conceal these floors in the aggregate.

### Every panel/opponent/seat cell

| panel | opponent | seat | N | baseline wins/rate | candidate wins/rate | G/R | delta |
|---|---|---:|---:|---:|---:|---:|---:|
| historical_silver | historical_silver | 0 | 100 | 58 / 58.0% | 58 / 58.0% | 0/0 | 0 |
| historical_silver | historical_silver | 1 | 100 | 42 / 42.0% | 42 / 42.0% | 0/0 | 0 |
| adjacent_population | arch_peak | 0 | 40 | 19 / 47.5% | 19 / 47.5% | 0/0 | 0 |
| adjacent_population | arch_peak | 1 | 40 | 20 / 50.0% | 20 / 50.0% | 0/0 | 0 |
| adjacent_population | arch_shumpei | 0 | 40 | 17 / 42.5% | 17 / 42.5% | 0/0 | 0 |
| adjacent_population | arch_shumpei | 1 | 40 | 23 / 57.5% | 22 / 55.0% | 0/1 | -1 |
| adjacent_population | alakazam_capbloo_gold | 0 | 40 | 32 / 80.0% | 32 / 80.0% | 0/0 | 0 |
| adjacent_population | alakazam_capbloo_gold | 1 | 40 | 30 / 75.0% | 30 / 75.0% | 0/0 | 0 |
| adjacent_population | marnie_kazuki_live | 0 | 40 | 32 / 80.0% | 32 / 80.0% | 0/0 | 0 |
| adjacent_population | marnie_kazuki_live | 1 | 40 | 36 / 90.0% | 36 / 90.0% | 0/0 | 0 |
| adjacent_population | mega_lucario_public | 0 | 40 | 37 / 92.5% | 37 / 92.5% | 0/0 | 0 |
| adjacent_population | mega_lucario_public | 1 | 40 | 37 / 92.5% | 37 / 92.5% | 0/0 | 0 |
| adjacent_population | kang_crustle | 0 | 40 | 15 / 37.5% | 17 / 42.5% | 2/0 | +2 |
| adjacent_population | kang_crustle | 1 | 40 | 13 / 32.5% | 14 / 35.0% | 2/1 | +1 |
| adjacent_population | cynthia_v23 | 0 | 40 | 33 / 82.5% | 33 / 82.5% | 0/0 | 0 |
| adjacent_population | cynthia_v23 | 1 | 40 | 34 / 85.0% | 34 / 85.0% | 0/0 | 0 |

## Acceptance checks

| supplied check | observed | result |
|---|---:|---:|
| unique schedule keys = 760 | 760; exact set equality | PASS |
| duplicate summary matches = 760 | 760/760 | PASS |
| duplicate byte-trace matches = 760 | 760/760 | PASS |
| execution faults = 0 | 0 | PASS |
| start faults = 0 | 0 | PASS |
| action errors = 0 | 0 | PASS |
| exceptions = 0 | 0 by exits and row completeness | PASS |
| max-step hits = 0 | 0 | PASS |
| candidate wins >= 478 | 480 | PASS |
| gains >= regressions | 4 >= 2 | PASS |
| each seat no worse than baseline -2 | seat 0: +2; seat 1: 0 | PASS |
| mirror candidate wins >= 98/200 | 100/200 | PASS |
| each adjacent opponent no worse than baseline -5/80 | worst is -1 (`arch_shumpei`) | PASS |
| strengthened candidate wins >= 486 | 480 | **FAIL** |
| strengthened both seats nonworse | +2 and 0 | PASS |

Base-gate result: **PASS**. Strengthened conjunction: **FAIL**.

## Raw artifacts and hashes

| artifact | SHA-256 |
|---|---:|
| `historical_silver/paired_results.csv` | `66DBF667348F8EA054C03C4B264025D0283DB46F7E59080F0C722FB30447CAC0` |
| `historical_silver/manifest.jsonl` | `504594BF10FBC1E280E1FB336D70FECCD4C7C4642821B6FAE523D4A6AFD6EA8D` |
| `historical_silver/report.json` | `F54D80C469309306C2558E9F92F4ED26A8832BBEE4A906A827F0FCA22B96A48B` |
| `historical_silver/cell_summary.csv` | `929029669FD47D2DCA71072B4B7AE40851061C1D2F009F59BEE86542F77EA377` |
| `adjacent_population/paired_results.csv` | `963C518C154730973B936672ABD1612F422B475C81CCB996E83E6BCF7763AC9E` |
| `adjacent_population/manifest.jsonl` | `A4C169D7A7736CD00243E23D0AF20394D10F2BC2406A73D1E24F20CCF48B344E` |
| `adjacent_population/report.json` | `33D4BF3C0DE8540973AB9E10255A734F208CCB40A740168778B136444920924F` |
| `adjacent_population/cell_summary.csv` | `E431B461AB132BF719061B128AE6DF2992F44FB0C6E41194D531439AFC9D75E8` |

For compactly anchoring the preserved sets, a tree digest was computed as SHA-256 over sorted records `relative_path + NUL + lowercase(file_sha256) + LF`:

| set | files | bytes | tree SHA-256 |
|---|---:|---:|---:|
| historical summaries | 6 | 885,417 | `25F91A871010A4F71E026ACCE8E103E1E26821CDC048711C3AB21D9C5EA9226D` |
| historical traces | 600 | 118,955,396 | `2064934B08CD331F8DEDBC296E8F9B19F99C06B2D20072440C18A845B8C28BB6` |
| adjacent summaries | 42 | 2,548,067 | `2E22A773F42C28D1B1EBE3C95872AF58F970BC893B88C7B68BA8904BAB9A2052` |
| adjacent traces | 1,680 | 295,647,753 | `4451608263D8346F272EBDD3705D1962843BA200BEF18264AD102A6523BF4393` |
| complete raw root | 2,336 | 418,166,905 | `F3B7393D88DFC4026404AC5D8AC32AD629739A2C0960E642C5634859E7853168` |

## Reproducible calculation and assumptions

1. Read the immutable spec and both manifests; require exactly the specified cell/role commands, exit zero, `--engine-seed`, frozen paths and row counts.
2. Read baseline A, baseline B and candidate JSONL summaries for each manifest cell. Require `started=true`, `result in {0,1}`, `action_errors=0`, `hit_max_steps=false`, `steps<1000`, and one trace whose line count equals `steps`.
3. Require baseline A/B equality on the checked runner fields and exact trace bytes for every game. Use baseline A only after this control passes.
4. Construct the expected spec key set and the physical key set, adding `panel` from the containing panel directory. Require exact set equality and no duplicate physical row.
5. Recompute both wins from `result == scheduled seat`; never consume the CSV win columns for the primary count. Cross-check all CSV fields and runner summaries only afterward.
6. Compute G/R/T from matched keys, aggregate within the immutable buckets only, and form paired and seed-cluster uncertainty from `d_i in {-1,0,1}`.

Assumptions and limits:

- The containing directory is the authoritative `panel` value because the physical CSV omits the column; the consequence of requiring a literal column is stated in the decision.
- Current frozen file hashes plus exact manifest command paths establish policy/engine identity. The manifests themselves do not embed source hashes.
- A successful process with the exact expected row count is treated as no execution exception because successful summary rows have no separate `exception` field.
- With all results in `{0,1}`, losses are `N-wins`; there are no draws in these raw outputs.
- Uncertainty intervals model comparable future seeded schedules. The completed schedule itself is deterministic, and only one seed base per panel was approved.
- No inference is made outside the two approved panels or beyond these seven adjacent opponents.
