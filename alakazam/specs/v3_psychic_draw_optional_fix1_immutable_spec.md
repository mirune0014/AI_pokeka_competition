# v3 サイコドロー任意化 fix1 不変仕様

## 目的

ユーザーと合意した実装順序のうち、次の二項目だけを実装する。

1. episode `88844273` の指定四局面を、非公開情報を含まない固定 fixture にする。
2. ユンゲラー／フーディンのサイコドローを任意能力として扱い、能力を使うことで次の通常ドローを残せない場合は `NO` を選べるようにする。

進化後の確定 KO 優先、ポフィン、壁判定、次アタッカー距離、公開最大打点、ベンチ 0 回避は本候補の対象外とする。

## 固定入力

- 基準実装:
  `alakazam_staged_20260729/versions/alakazam_newdeck_v1_package_runtime_certified_fix5`
- 基準実装 source closure SHA-256:
  `5FFA8776CA95E16C7030C55B5682DE42BA21C06964C790A3D6312B60FBAA5009`
- 基準 planner SHA-256:
  `80A9B0F88A04591D4174B21AFCC5C9019A4EFCEC02E8F9C2D1576DCFC0FC044B`
- replay:
  `C:/Users/amuam/Downloads/88844273.json`
- replay SHA-256:
  `9E749F259D90655BE4C17F1795C15D277132C02E0167310394216609B90A7EBF`
- 対象 agent index:
  `1`
- Python:
  `C:/Users/amuam/project/AI_pokeka_competition/.venv-rl/Scripts/python.exe`
- engine:
  `analysis_outputs/cynthia_v9_vs_v11_poffin_role_selection_20260713/seeded_engine`
- engine tree SHA-256:
  `466638706BD5C6915E25D1B3CB9E3D966390FBC263F4ED3153108E29C0194FFF`

## 出力

- 候補:
  `alakazam_staged_20260729/versions/alakazam_newdeck_v3_psychic_draw_optional_fix1`
- fixture:
  `alakazam_staged_20260729/fixtures/episode_88844273_public_observations`
- 検証ログ:
  `alakazam_staged_20260729/evaluations/v3_psychic_draw_optional_fix1`

基準実装は一切変更しない。

## 四局面 fixture

各 fixture は replay の当該 step に含まれる agent index `1` の `observation` だけを保存する。相手の手札、山札順、サイド内容など、agent に非公開の episode 情報を混入させない。

各 JSON は少なくとも次のメタデータを持つ。

- `episode_id`
- `source_replay_sha256`
- `agent_index`
- `source_step_index`
- `semantic_label`
- `expected_baseline_action`
- `observation_sha256`
- `observation`

対象局面は次の四つとする。

| source step | 意味 | 基準 action |
|---:|---|---|
| 67 | 最初のフーディン気絶後の強制昇格 | `[0]` |
| 98 | ユンゲラーを昇格させれば次の進化攻撃へ接続できる強制昇格 | `[0]` |
| 121 | 後半の強制昇格 | `[4]` |
| 148 | エネルギー付きユンゲラーと手札フーディンがある自分の MAIN | `[7]` |

action は observation が保存された step の次 step に記録された agent index `1` の action と対応させる。抽出時にこの一つ先の対応関係を検証する。

## 任意サイコドロー規則

対象は `SelectContext.ACTIVATE` における、厳密に同定できた自分のユンゲラーまたはフーディンのサイコドロー YES/NO prompt だけとする。

- ユンゲラーは 2 枚、フーディンは 3 枚引くものとして計算する。
- `projected_deck = deck_count - min(deck_count, draw_count)` とする。
- 基準実装が `YES` を選ぶ局面で `projected_deck < 1` なら `NO` を選ぶ。
- `projected_deck >= 1` なら基準 action を完全に保存する。
- 基準実装が既に `NO` なら変更しない。
- prompt、option、context card、所有者、場の serial、カード ID、選択数を一意に確認できない場合は基準 action へフォールバックする。
- YES/NO の option 順序には依存しない。
- prize count を deck count から差し引かない。

任意化により `NO` を選んだ後も、既存の進化→能力→攻撃 transaction を fault にせず、手札・山札が変わらない遷移を検証して後続の攻撃判断へ進める。

## 明示的な非変更条件

- 四つの replay fixture はサイコドロー ACTIVATE prompt ではないため、候補 action は基準 action と完全一致しなければならない。
- step `148` の進化優先順位は本候補では変えない。ここを変えるのは次の「進化後の確定 KO 優先」候補である。
- `_cumulative_parent.py` の進化候補生成、既存デッキリスト、攻撃評価、ベンチ展開、ポフィン、壁判断を変更しない。
- 学習器、行動模倣、replay action の一般化は導入しない。

## 必須テスト

1. 基準版の既存 unittest を候補コピー上ですべて実行する。
2. 四 fixture の JSON schema、source hash、observation hash、公開観測限定を検証する。
3. 四 fixture で基準 action と候補 action が一致することを検証する。
4. ユンゲラーとフーディンについて、境界値を検証する。
   - 能力後に deck が 1 枚残る: 基準 `YES` を保存。
   - 能力後に deck が 0 枚になる: `NO`。
5. YES/NO option の順序入れ替え、重複 option、欠落 option、誤った context card、相手所有 card、場に存在しない serial、未知 card ID を検証する。
6. 既存の active route と ready-bench route の transaction が、`YES` と `NO` の両方で fault なく完了することを検証する。
7. 必須ドローやサイコドロー以外の ACTIVATE prompt に一切発火しないことを検証する。

## 合格条件

- 必須テストが全件成功する。
- 四 fixture で基準・候補 action が完全一致する。
- 任意化の発火は、厳密なサイコドロー prompt かつ能力後の deck が 0 枚になる場合だけである。
- malformed/unknown prompt は例外や first-legal への逸脱を起こさず、基準 action を保存する。
- 基準実装と replay 原本の hash が不変である。

本検証は規則の意味と transaction 安全性を確認するもので、勝率比較または採用判定ではない。
