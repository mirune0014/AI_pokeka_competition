# 障害と勝敗の分類

## 結果モデル

結果は `normal`、`technical_forfeit`、`human_forfeit`、`system_error` のいずれかです。

`normal` ではエンジンの `current.result` に従い、Player 0、Player 1、引き分けを決定します。

`technical_forfeit` では AI 側の責任と特定できる障害として人間を勝者とします。

`human_forfeit` では人間が明示的に放棄した通常結果として AI 席を勝者とします。

`system_error` では勝者を設定しません。

## 分類表

| 原因 | 分類 | 勝者 |
|---|---|---|
| `agent(obs)` の例外 | `technical_forfeit` | 人間 |
| AI 思考フェーズのタイムアウト | `technical_forfeit` | 人間 |
| AI が `list[int]` 以外を返す | `technical_forfeit` | 人間 |
| AI が選択数、重複、範囲に違反する | `technical_forfeit` | 人間 |
| AI の選択に対する `battle_select` の拒否 | `technical_forfeit` | 人間 |
| 人間の明示的な放棄 | `human_forfeit` | AI |
| GUI 例外 | `system_error` | なし |
| IPC 破損、切断、スキーマ違反 | `system_error` | なし |
| `cg.dll` ネイティブクラッシュ | `system_error` | なし |
| `battle_start`、人間選択、終了処理中のエンジン例外 | `system_error` | なし |
| 最大ステップ到達 | `system_error` | なし |
| 封印またはリプレイ単独障害 | `system_error` | なし |
| ワーカー強制終了で直前フェーズが AI 思考と特定できる | `technical_forfeit` | 人間 |
| ワーカー強制終了の責任主体を特定できない | `system_error` | なし |

## タイムアウト

スーパーバイザは最後に受信した `phase.changed` を保持し、フェーズごとに別の期限を適用します。

`AGENT_THINKING` だけを AI タイムアウトとし、`ENGINE_PROCESSING`、`STARTING`、`FINISHING` の期限超過は `system_error` とします。

人間の思考時間はゲーム内タイムアウトとしては制限しません。

## 回復

異常時は新しい `battle_select` を実行せず、協調的終了を短時間待ってから Job Object 単位で強制終了します。

次の対戦は前のワーカー、パイプ、ステージング領域、エンジンのグローバル状態を再利用せず開始します。
