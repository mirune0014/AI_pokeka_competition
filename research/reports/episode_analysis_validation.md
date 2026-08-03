# Episode解析検証

## 対象

- 期間：2026-07-19 から 2026-07-25
- 選択：各日 `avg_score` 上位50試合
- 期待episode数：350
- 読み込み済みepisode数：350
- 期待席数：700
- 出力席数：700

## 完全性

| 検査 | 結果 |
|---|---:|
| episode種類数 | 350 |
| 2席でないepisode | 0 |
| 60枚でないデッキ | 0 |
| rewardが-1/+1でないepisode | 0 |
| 未分類 | 0 |
| deck_hash欠損 | 0 |
| opponent対応不一致 | 0 |
| episode-seat重複 | 0 |
| 元JSON欠損・読込失敗 | 0 |

## 行動履歴

- 行動履歴を復元できたepisode：350 / 350
- `current.firstPlayer`を確認できたepisode：350 / 350
- fallback：明示証拠がないため `UNKNOWN`
- invalid action：完全記録の保証がないため `UNKNOWN`
- 処理時間：同一席・同一ターン内の `remainingOverageTime` 差分だけを近似値として使用

## 集約定義

`raw_result_rate = (wins + 0.5 * draws) / raw_games`。

`team_pair_day` と `exact_deck_pair_day` は、各ユニット内のresult rateを計算し、ユニットを等加重平均する。

`descriptive_win_rate` は `episode_raw` ではraw result rate、集約単位ではunit-equal-weight result rateを格納する。

通常の二項信頼区間と有意差検定は使用しない。

## 行動・状態指標の操作的定義

- `recorded_action_valid=TRUE` は記録actionのoption indexと選択枚数がlegal actionの範囲内だったことだけを表し、fallbackやinvalid actionが不存在だったことは表さない。
- `forced_choice=TRUE` は `minCount..maxCount` の全選択数を展開し、意味上重複する候補を除いた完全actionが1通りだけだったことを表す。
- `opening_failure_rate` は最初の攻撃が自分の第2ターンまでに記録されなかった席の比率である。
- `second_attacker_ready` は最初の攻撃時点でベンチに攻撃可能な別ポケモンが存在したかを表す。
- `no_attack_turns` は席ごとに `TurnStart` で攻撃フラグを初期化し、`Attack` で立て、`TurnEnd` で未攻撃なら加算する状態追跡で算出する。
- 最初のサイド取得は `MoveCard(fromArea=6,toArea=2)` とvisualizer frameの双方から照合し、frame番号を保存する。
- 処理時間近似は連続するACTIVE観測で `current.yourIndex` が同じ席、かつglobal turnが同じ場合だけを `CONTIGUOUS_SAME_PLAYER_APPROX` とする。
- low sampleはraw gamesが5未満、unique team pairが3未満、または各集約unitが10未満のいずれかに加え、比較表では各群・各teamが2未満の場合にも付与する。
- single date、single team dominance、repeated exact deckはlow sampleとは別の依存性警告として保持する。

## 集約感度・シナリオ・次アタッカー距離

- candidate scorecard の正規 `team_pair_day` キーは `(date, team_id, opponent_team_id, deck_hash, opponent_deck_hash)` とし、matchup matrix と統一する。
- `candidate_matchup_aggregation_sensitivity.csv` はraw、正規unit等加重、単試合unit除外、5試合以上unit、exact-pair階層、date外側等加重、exact-pair外側等加重とleave-one-out範囲を併記する。
- `candidate_meta_scenarios.csv` の0/0.25/0.5/1およびworst-fillは仮定であり、母集団勝率の点推定ではない。observed-only再正規化値はlegacy比較値である。
- `second_attacker_ready` は `LEGACY_V1_ANY_BENCH_PRINTED_ATTACK_COST_READY` として再現確認用に残し、デッキ選定には使用しない。
- `next_attacker_action_distance` v1は最初の攻撃直前ACTIVE observationだけを使い、最初の攻撃カードと同じprinted card IDへ至る既知の場・手札からのBasic場出し、進化、Rare Candy、Energy装着の自己root actionを幅優先探索したmodel-scope値である。
- 将来ドロー、検索・回収・加速効果、相手干渉、KO昇格、retreat/switch、ターン待ちはv1の範囲外である。supported pathがない席はFalseや3へ丸めずUNKNOWNにする。
- 距離値は勝敗や最初の攻撃後の行動を参照しない。`first_attack_snapshot_hash` と証明pathをseat featuresへ保存する。
