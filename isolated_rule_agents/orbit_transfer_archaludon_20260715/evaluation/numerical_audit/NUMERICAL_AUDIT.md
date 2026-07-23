# Numerical audit of the frozen Orbit-transfer comparison

## Scope and receipts

This audit covers only paired numerical evidence. It does not interpret
first-divergence semantics and does not make the final adoption decision.

All six frozen inputs match the SHA256 receipts in `EVALUATION_SPEC.md`:

| panel | paired CSV | runner report | manifest |
|---|---|---|---|
| historical Silver | `00233D11...9472C1E` | `F54D80C4...B96A48B` | `CB1246BB...FF4684C` |
| adjacent population | `B859124E...11F974` | `6F35113E...309E80` | `3D8FCF20...CAED72` |

The checked repository tool was run with a 50-game block size for the
historical panel and a 40-game block size for the population panel. A separate
stdlib-only recomputation read every paired row, manifest row, and summary
JSONL row. The reproducible commands are:

```powershell
python tools/audit_paired_results.py isolated_rule_agents/orbit_transfer_archaludon_20260715/evaluation/historical_silver/paired_results.csv --runner-report isolated_rule_agents/orbit_transfer_archaludon_20260715/evaluation/historical_silver/report.json --block-size 50 --out isolated_rule_agents/orbit_transfer_archaludon_20260715/evaluation/numerical_audit/historical_checked_tool.json
python tools/audit_paired_results.py isolated_rule_agents/orbit_transfer_archaludon_20260715/evaluation/adjacent_population/paired_results.csv --runner-report isolated_rule_agents/orbit_transfer_archaludon_20260715/evaluation/adjacent_population/report.json --block-size 40 --out isolated_rule_agents/orbit_transfer_archaludon_20260715/evaluation/numerical_audit/population_checked_tool.json
python isolated_rule_agents/orbit_transfer_archaludon_20260715/evaluation/numerical_audit/independent_recompute.py
```

## Paired outcomes

| panel | rows | baseline wins | candidate wins | gain | loss | outcome ties | McNemar exact p |
|---|---:|---:|---:|---:|---:|---:|---:|
| historical Silver | 200 | 100 | 100 | 0 | 0 | 200 | 1.0 |
| adjacent population | 480 | 317 | 317 | 0 | 0 | 480 | 1.0 |
| combined | 680 | 417 | 417 | 0 | 0 | 680 | 1.0 |

Seat totals are unchanged: historical seat 0 is 58/100 and seat 1 is 42/100;
population seat 0 is 154/240 and seat 1 is 163/240. Population opponent totals
are also unchanged: `arch_peak` 39/80, `arch_shumpei` 40/80, `cynthia_v23`
67/80, `kang_v23` 28/80, `marnie_kazuki` 70/80, and `marnie_tonakai`
73/80. Every one of the four historical 50-game blocks and twelve population
40-game blocks has delta wins 0, gains 0, and losses 0.

There are no discordant outcomes, so the exact McNemar test has no directional
evidence and returns p=1.0. Under independent paired seeds, the exact one-sided
95% upper bound on the probability of any unobserved outcome discordance is
1.49% for 200 rows, 0.62% for 480 rows, and 0.44% for the pooled 680 rows. This
does not establish a strength increase or population equivalence.

## Step differences by outcome, opponent, and seat

All 206 differing pairs are `both_win`, all have fewer candidate steps, and
none has more candidate steps. Every `both_loss` pair has equal steps.

| outcome | opponent | seat | differing | candidate fewer | candidate more | steps saved |
|---|---|---:|---:|---:|---:|---:|
| both_win | historical_silver | 0 | 29 | 29 | 0 | 115 |
| both_win | historical_silver | 1 | 19 | 19 | 0 | 80 |
| both_win | arch_peak | 0 | 4 | 4 | 0 | 13 |
| both_win | arch_peak | 1 | 7 | 7 | 0 | 24 |
| both_win | arch_shumpei | 0 | 15 | 15 | 0 | 68 |
| both_win | arch_shumpei | 1 | 12 | 12 | 0 | 41 |
| both_win | cynthia_v23 | 0 | 22 | 22 | 0 | 87 |
| both_win | cynthia_v23 | 1 | 17 | 17 | 0 | 57 |
| both_win | kang_v23 | 0 | 1 | 1 | 0 | 2 |
| both_win | kang_v23 | 1 | 2 | 2 | 0 | 4 |
| both_win | marnie_kazuki | 0 | 21 | 21 | 0 | 82 |
| both_win | marnie_kazuki | 1 | 25 | 25 | 0 | 84 |
| both_win | marnie_tonakai | 0 | 18 | 18 | 0 | 69 |
| both_win | marnie_tonakai | 1 | 14 | 14 | 0 | 47 |
| **total** |  |  | **206** | **206** | **0** | **773** |

## Schedule and execution controls

| check | historical Silver | adjacent population |
|---|---:|---:|
| paired rows / expected | 200 / 200 | 480 / 480 |
| unique `(seed_base, opponent, seat, seed)` keys | 200 | 480 |
| missing / extra / duplicate keys | 0 / 0 / 0 | 0 / 0 / 0 |
| manifest rows, all exit code 0 | 6 | 36 |
| summary rows / expected | 600 / 600 | 1440 / 1440 |
| command-contract issues | 0 | 0 |
| action errors | 0 | 0 |
| max-step hits | 0 | 0 |
| duplicate-control mismatches | 0 | 0 |

Both runner reports are valid, their aggregates match the independent
recomputation, all game/seed relations and win fields are exact, and the paired
CSV schema is exact. The checked tool's generic `block_direction` flag is
`false` because it requires positive block deltas; this is not an execution or
data-validity failure.

## Frozen numerical gate

The numerical portion of the strength-improvement gate **does not have the
required candidate gain**: baseline-loss/candidate-win flips are 0. It also has
zero baseline-win/candidate-loss flips. Numerically, the artifact is
outcome-identical on this schedule with shorter completed wins, not an observed
strength improvement.
