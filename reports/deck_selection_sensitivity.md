# デッキ選定感度分析

対象はフーディン exact hash `4414e8995e50c7a00d4b6aa7d9229f63c1dff5261643ec7cd86c4e329113ed69` である。
公開Daily Topの選択標本に対する記述的な感度分析であり、母集団勝率の推定ではない。

## フーディン対マーニーの集約感度

| 集約方法 | 対象試合 | unit数 | 結果率 | leave-one-team範囲 | 最大unit試合比率 |
|---|---:|---:|---:|---:|---:|
| `EPISODE_RAW` | 62 | 62 | 46.77% | 37.50%–63.64% | 1.61% |
| `TEAM_PAIR_DAY_EQUAL` | 62 | 9 | 59.69% | 39.58%–75.78% | 38.71% |
| `TEAM_PAIR_DAY_EXCLUDE_SINGLE_GAME_UNITS` | 60 | 7 | 48.17% | 39.58%–59.63% | 40.00% |
| `TEAM_PAIR_DAY_MIN_5_GAMES` | 56 | 6 | 52.04% | 44.44%–59.63% | 42.86% |
| `EXACT_PAIR_DAY_EPISODE_WITHIN` | 62 | 6 | 57.23% | 39.58%–70.83% | 38.71% |
| `EXACT_PAIR_DAY_TEAM_PAIR_WITHIN` | 62 | 6 | 59.20% | 39.58%–75.28% | 38.71% |
| `DATE_OUTER_EQUAL` | 62 | 6 | 59.20% | 39.58%–75.28% | 38.71% |
| `EXACT_PAIR_OUTER_EQUAL` | 62 | 2 | 67.67% | 39.58%–75.00% | 90.32% |

`TEAM_PAIR_DAY_EQUAL` の正規キーは `(date, team_id, opponent_team_id, deck_hash, opponent_deck_hash)` である。
集約方式またはleave-one-outで50%の上下が変わる場合、対マーニー優位は `SENSITIVE` と扱う。

## 未観測・low-sample主要対面のシナリオ

| シナリオ | 仮定値 | 結果 | 解釈 |
|---|---:|---:|---|
| `UNOBSERVED_ONLY_AS_0` | 0.00% | 47.19% | ASSUMPTION_NOT_POINT_ESTIMATE |
| `UNOBSERVED_ONLY_AS_0_25` | 25.00% | 52.80% | ASSUMPTION_NOT_POINT_ESTIMATE |
| `UNOBSERVED_ONLY_AS_0_50` | 50.00% | 58.41% | ASSUMPTION_NOT_POINT_ESTIMATE |
| `OBSERVED_ONLY_RENORMALIZED_LEGACY` | - | 60.84% | OBSERVED_CELLS_ONLY_RENORMALIZED_NOT_FULL_META_ESTIMATE |
| `UNCERTAIN_AS_0` | 0.00% | 36.98% | ASSUMPTION_NOT_POINT_ESTIMATE |
| `UNCERTAIN_AS_0_50` | 50.00% | 58.41% | ASSUMPTION_NOT_POINT_ESTIMATE |
| `UNCERTAIN_AS_1` | 100.00% | 79.84% | ASSUMPTION_NOT_POINT_ESTIMATE |
| `OBSERVED_WORST_FILL` | 59.69% | 62.56% | ASSUMPTION_NOT_POINT_ESTIMATE |

観測済み主要対面weightは 77.55%、未観測weightは 22.45% である。
観測済みだけを再正規化した値は、全メタ推定値ではなくlegacy比較値としてのみ残す。

## 次アタッカー距離

- legacy即時準備率: 22.81%
- v1距離点値coverage: 45.61%
- 構造下限coverage: 95.61%
- 構造下限中央値: 1.00000000
- 既知手札経路上限coverage: 45.61%
- 既知手札経路上限中央値: 1.00000000
- 距離0率（既知分母）: 11.54%
- 距離1以下率（既知分母）: 59.62%
- 距離2以下率（既知分母）: 100.00%
- 距離中央値（既知分母）: 1.00000000

v1距離は最初の攻撃直前observationだけを使い、場出し・進化・Rare Candy・手張りの既知手札経路を数える。
将来ドロー、検索・回収・加速効果、相手干渉、KO昇格、交代、ターン待ちはモデル外であり、経路が証明できない席は数値へ丸めずUNKNOWNにする。

## 判定

フーディンは最小実装で検証する暫定候補として維持する。
ただし、集約方式・チーム除外・未観測対面仮定に敏感なため、最終採用デッキとは確定しない。
150～300ルールの大規模化には進まず、ローカル両席同一seed比較を先に行う。
