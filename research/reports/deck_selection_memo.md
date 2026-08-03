# デッキ選定前の対面・行動履歴解析メモ

## 判定

最小ルールベース実装で検証する暫定対象にはフーディンを選定する。

使用する完全一致デッキhashは `4414e8995e50c7a00d4b6aa7d9229f63c1dff5261643ec7cd86c4e329113ed69` とする。

この判定は開発対象の選定であり、完成エージェントの採用判定やKaggle投入許可ではない。

2026年7月28日の感度分析後の位置づけは、最終採用ではなく `SENSITIVE` な暫定候補である。大規模ルール実装には進まず、最小実装のローカルA/Bでデッキ選定自体を検証する。

追加結果は `reports/deck_selection_sensitivity.md`、集約明細は `reports/candidate_matchup_aggregation_sensitivity.csv`、未観測対面シナリオは `reports/candidate_meta_scenarios.csv` に保存した。

新規ルールベースエージェントの実装は本メモ作成時点では開始していない。

## 解析範囲と証跡

対象期間は2026年7月19日から7月25日までである。

各日の `avg_score` 上位50試合を選び、350試合、700席を解析した。

正規の席データは `analysis_outputs/rocket_preimplementation_meta_20260727/verified_top_band_7d/enriched_decks_7d.csv` である。

生成証跡は `analysis_outputs/rocket_preimplementation_meta_20260727/deck_selection_analysis/analysis_manifest.json` に保存した。

確定manifestのSHA-256は `a9bb4e75728e01ee1aed6adc0bd6b5a654c7312b044759565f003abcd4583d3b` である。

生成スクリプトのSHA-256は `2201f01ec584380746c10b8b8d78a25a27858ba77261a09b058628f46cd5b253` である。

manifest内の365入力と15出力は、存在、サイズ、SHA-256の再監査で不一致0件だった。

## 1. 読み込んだepisode数

読み込んだepisodeは350件である。

各episodeにplayer 0とplayer 1が1席ずつ存在し、合計700席だった。

同一の `(episode_id, player_index)` の重複は0件だった。

全700席のデッキは60枚で、deck hash欠損と未分類は0件だった。

## 2. 欠損episode数

欠損episode、JSON読み込み失敗、構造不正は0件だった。

詳細一覧は `reports/missing_or_invalid_episodes.csv` に保存した。

## 3. 行動履歴を復元できた割合

行動履歴は350件中350件で復元でき、coverageは100%だった。

抽出した64,676行の行動イベントは `analysis_outputs/rocket_preimplementation_meta_20260727/deck_selection_analysis/action_events_7d.csv` に保存した。

700席の状態特徴は `analysis_outputs/rocket_preimplementation_meta_20260727/deck_selection_analysis/seat_features_7d.csv` に保存した。

記録actionはlegal optionと選択枚数の範囲内だったが、fallbackとinvalid actionは完全記録の保証がないため `UNKNOWN` とした。

## 4. 先攻・後攻を判定できた割合

元JSONの `current.firstPlayer` から350件中350件の先攻・後攻を判定でき、coverageは100%だった。

player indexから先攻・後攻を推測した行は0件だった。

## 5. 対面別の試合数

主な物理対戦数は次のとおりだった。

| 対面 | 試合数 |
|---|---:|
| マーニー対マーニー | 104 |
| フーディン対マーニー | 62 |
| シロナ対マーニー | 56 |
| マーニー対ロケット団 | 54 |
| フーディン対シロナ | 39 |
| シロナ対ロケット団 | 6 |
| フーディン対フーディン | 5 |
| フーディン対ドラパルト | 5 |
| シロナ対お祭り音頭 | 5 |
| マーニー対ドラパルト | 3 |
| マーニー対ガルーラ／イワパレス | 3 |
| その他7組 | 8 |

同一hashミラー102試合は構成上の方向付き勝率を空欄にし、異なるhashミラー9試合はhash辞書順の一方向だけを残した。

## 6. チーム反復を抑えた場合の結果変化

率を算出できる43対面群のうち、team-pair-day等加重でraw率から変化した群は17群だった。

exact-deck-pair-day等加重でraw率から変化した群は15群だった。

最大絶対差はteam-pair-dayで26.67ポイント、exact-deck-pair-dayで30.00ポイントだった。

フーディン主流型対マーニー主流型はraw 42.86%からteam-pair-day 56.74%へ13.88ポイント上昇した。

フーディン主流型の全マーニー型に対するraw成績は29勝33敗の46.77%だったが、候補表のteam-pair-day等加重値は59.69%だった。

この方向反転は、実装対象を選ぶうえで最も重要な反対証拠である。

本判定はユーザーが事前確定したとおり、同一チームの連戦数ではなく集約unitを等加重する値を主に用いた。

## 7. 完全一致デッキ別の結果

low sampleではない主な完全一致型は次のとおりだった。

| アーキタイプ | hash先頭 | 試合 | team | 日 | raw | unit等加重 | メタ加重 | coverage |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| フーディン | `4414e899` | 116 | 2 | 6 | 55.17% | 65.56% | 60.84% | 77.55% |
| マーニー主流型 | `4194e1d8` | 354 | 8 | 7 | 53.67% | 52.91% | 50.83% | 100.00% |
| マーニー別型 | `41bdf9d5` | 32 | 3 | 3 | 46.88% | 36.67% | 36.89% | 91.84% |
| ロケット団主流型 | `2a450040` | 49 | 1 | 4 | 24.49% | 21.11% | 20.67% | 57.14% |

ガルーラ／イワパレスは4種類を観測したが、各型1試合から3試合、1team、1日だけだった。

ロケット団は5種類、フーディンは1種類、マーニーは3種類の完全一致60枚リストを観測した。

全型とカード差分は `reports/exact_deck_variants.csv`、`reports/deck_common_core.csv`、`reports/deck_variant_comparison.md` に保存した。

## 8. 勝者と敗者で差が大きかった初動

`opening_sequence_patterns.csv` の3,482行はすべてlow sampleであり、系列別勝率を選定根拠には使わない。

完全一致hash、対面、先後、フェーズを揃えた観測差分では、フーディン対マーニーの先攻でKadabraのカードID `742` を検索した割合が勝者側で38.16ポイント高かった。

同じ層で最初の攻撃時に次アタッカーが存在した割合は勝者側で37.28ポイント高かった。

同じ層でpassの観測割合は勝者側で31.14ポイント低かった。

これらは2teamに依存する観測相関であり、方策を模倣する教師ラベルではない。

## 9. 勝者と敗者で差が大きかった中盤判断

マーニーミラーでは、最初のサポートがLillie's DeterminationのカードID `1227` だった割合が勝者側で31.25ポイント高かった。

同じミラーのPRIZE_RACEでは1枚のサイド取得が記録された割合が勝者側で54.71ポイント高かった。

同じミラーではImpidimpのカードID `646` へのエネルギー装着が勝者側で44.16ポイント低かった層があった。

RECOVERYで手札1枚から3枚の割合が勝者側で37.47ポイント低かった層があった。

これらの差分は繰り返し観測された同一deck hashに依存し、因果効果とは呼ばない。

## 10. 各候補デッキの長所と弱点

フーディンは最大勢力マーニーへのunit等加重59.69%、メタ加重60.84%、観測済み主要対面のworst 50.00%、未攻撃ターン率31.28%が候補中で強かった。

フーディンはロケット団とガルーラ／イワパレスが未観測で、2team依存、次アタッカー準備率22.81%という構造的弱点がある。

マーニー主流型は8team、7日、354試合、主要対面coverage 100%、次アタッカー準備率73.86%、先攻52.87%と後攻54.44%の頑健性が長所だった。

マーニー主流型はフーディンへのunit等加重43.26%、シロナへの41.18%が弱く、ガルーラ／イワパレスへの25.00%は2unitだけで確証がない。

ロケット団主流型は初動失敗率26.53%と観測時間差0.0556秒相当が比較的良かったが、unit等加重21.11%、次アタッカー準備率2.08%が重大な弱点だった。

ロケット団主流型の49試合は1teamだけに依存しており、アーキタイプ一般へ外挿できない。

ガルーラ／イワパレスは構築差が大きく、各完全一致型が1試合から3試合しかないため選定不能だった。

## 11. 暫定開発対象

最小ルールベース版で検証する暫定候補はフーディンである。

合法性とエンジン確実性は観測済み60枚かつ未解決IDなしで、invalid action、例外、timeoutは完全観測ではなく `UNKNOWN` である。

対マーニーはraw 29勝33敗の46.77%、正規team-pair-day 9unit等加重59.69%、1試合unit除外48.17%、5試合以上unit52.04%だった。

フーディン側の1teamを順に除外すると39.58%から75.78%まで動き、集約方式のenvelopeも50%をまたぐため、基準3で決着したとは扱わない。

未観測対面だけを0%、25%、50%で補う主要メタ値は47.19%、52.80%、58.41%である。従来の60.84%は観測済み対面だけを再正規化したlegacy比較値で、全メタ推定値ではない。

したがって、フーディンを最終採用デッキとは確定せず、ハンドパワー連続攻撃保証に絞った最小実装を両席・同一seedで比較する。
## 12. 暫定検証対象の完全一致60枚リスト

検証対象hashは `4414e8995e50c7a00d4b6aa7d9229f63c1dff5261643ec7cd86c4e329113ed69` である。

| 枚数 | card_id | カード名 |
|---:|---:|---|
| 2 | 5 | Basic {P} Energy |
| 1 | 13 | Enriching Energy |
| 4 | 19 | Telepath Psychic Energy |
| 2 | 66 | Dudunsparce |
| 1 | 140 | Fezandipiti ex |
| 3 | 305 | Dunsparce |
| 1 | 343 | Shaymin |
| 4 | 741 | Abra |
| 4 | 742 | Kadabra |
| 4 | 743 | Alakazam |
| 3 | 1079 | Rare Candy |
| 4 | 1081 | Enhanced Hammer |
| 4 | 1086 | Buddy-Buddy Poffin |
| 1 | 1097 | Night Stretcher |
| 1 | 1129 | Sacred Ash |
| 4 | 1152 | Poké Pad |
| 3 | 1182 | Boss’s Orders |
| 1 | 1184 | Lana’s Aid |
| 3 | 1197 | Xerosic’s Machinations |
| 4 | 1225 | Hilda |
| 4 | 1231 | Dawn |
| 2 | 1266 | Nighttime Mine |

合計はポケモン19枚、トレーナーズ34枚、エネルギー7枚の60枚である。

同名カードは基本エネルギーを除いて4枚以下で、Enriching Energyは1枚だった。

## 13. ルールベースへ実装すべき主要判断

最初に検証する単一仮説は「Powerful Hand連続攻撃保証」とする。

現在の手札枚数からPowerful Handの確定ダメージを計算し、合法な即時KOがあれば最少の手札消費で実行する。

即時KOがなければ、AlakazamとPsychic Energyによる現在の攻撃経路を最優先する。

現在の攻撃が確定した後に、別のAbra系統と次のPsychic Energyを確保する。

Telepath Psychic Energyは、攻撃エネルギーと不足するAbra展開を同時に満たす対象へ付ける。

Hilda、Dawn、Buddy-Buddy Poffin、Poké Pad、Rare Candyは、現在と次の攻撃経路の不足部品を辞書式に埋める。

Boss’s Orders、Enhanced Hammer、Xerosic’s Machinations、Nighttime Mineは、確定KOの手札閾値や次攻撃経路を壊さない場合だけ使う。

Enriching Energy、Psychic Draw、Run Away Drawは、山札切れを避けつつ確定打点または攻撃継続を改善する場合だけ使う。

Sacred Ash、Night Stretcher、Lana’s Aidは、失った攻撃系統の再建を優先する。

この仮説は公開盤面とカード理論だけを使い、episodeの選択を模倣しない決定的ルールとして実装する。

## 14. データ不足で判断できない事項

フーディン対ロケット団とフーディン対ガルーラ／イワパレスの観測結果は存在しない。

フーディンの2team、6日、116席という観測が別チームの方策でも再現するかは判断できない。

フーディン対マーニーのraw 46.77%とunit等加重59.69%のどちらが将来対戦をよく表すかは判断できない。

fallbackとinvalid actionは完全記録が保証されず、未発生とは判断できない。

`remainingOverageTime` の差分はエージェント処理だけを測らないため、正確な推論時間とは判断できない。

opening系列は全行low sampleであり、特定の系列が強さの原因かは判断できない。

winner-loser差分は観測相関であり、特定行動を選べば勝率が上がるとは判断できない。

実装後の絶対強度、Silver Archaludon anchorとの比較、両席のseed頑健性はまだ評価していない。

## 実装後の評価ゲート

baseline、candidate、engine、相手、両席、seed、出力schema、全hashを実行前に固定する。

各相手について同一50 seed以上を両席で比較する。

invalid action、例外、timeout、max-stepはすべて0件を要求する。

マーニー主流型への絶対勝率55%以上と各席50%以上を要求する。

baseline比でマーニーに100戦当たり5勝以上の実用差を要求する。

シロナ、Silver Archaludon anchor、フーディンミラー、ロケット団、ガルーラ／イワパレスでは各席100戦当たり3勝を超える後退を認めない。

次アタッカー準備率を同一seed baseline比で10ポイント以上改善し、初攻撃ターンと未攻撃ターン率を悪化させない。

変更局面は全件確認し、任意行動が確定打点または次攻撃経路を壊す失敗を防いだかを判定する。

## 成果物

- `analysis_outputs/rocket_preimplementation_meta_20260727/verified_top_band_7d/enriched_decks_7d.csv`
- `reports/episode_analysis_validation.md`
- `reports/missing_or_invalid_episodes.csv`
- `reports/matchup_matrix.csv`
- `reports/opening_sequence_patterns.csv`
- `reports/winner_loser_action_diff.csv`
- `reports/exact_deck_variants.csv`
- `reports/deck_common_core.csv`
- `reports/deck_variant_comparison.md`
- `reports/candidate_deck_scorecard.csv`
- `analysis_outputs/rocket_preimplementation_meta_20260727/deck_selection_analysis/action_events_7d.csv`
- `analysis_outputs/rocket_preimplementation_meta_20260727/deck_selection_analysis/seat_features_7d.csv`
- `analysis_outputs/rocket_preimplementation_meta_20260727/deck_selection_analysis/analysis_manifest.json`
