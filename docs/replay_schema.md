# .ptcgmatch リプレイスキーマ

## 形式

.ptcgmatchはZIP形式のリプレイスキーマバージョン1コンテナーです。

カード画像を保存せず、カードIDだけを保存します。

読取時にエンジン、`cg.dll`、登録した `main.py` を実行しません。

## ZIPメンバー

| メンバー | 内容 |
|---|---|
| manifest.json | バージョン、識別、結果、完全性、内部メンバー検証情報です。 |
| artifact.json | 区分、submission ID または null、manifest ID、使用した全ファイルの SHA-256 です。 |
| settings.json | 人間席、原本デッキSHA、上限、表示待ち、開始時刻です。 |
| decks.json | 両デッキのカードIDと正規化SHA-256です。 |
| frames.jsonl | 初期状態と各battle_select受理後のFullReplayFrameです。 |
| public_log.jsonl | revision付き公開ログです。 |
| result.json | 勝者、分類、理由、座席、先攻、ターン数、選択回数です。 |
| diagnostics.json | 時刻、所要時間、最終フェーズ、ステップ数、complete状態です。 |

## manifest.json

manifestは次を持ちます。

- replay_schema_version
- protocol_version
- human_view_schema_version
- app_version
- match_id
- submission_id
- artifact_manifest_id
- used_file_hashes
- human_deck_original_sha256
- human_deck_normalized_sha256
- human_seat
- first_player
- human_went_first
- started_at_utc
- finished_at_utc
- winner_seat
- result_category
- termination_reason
- frame_count
- complete
- last_frame_hash
- members
- content_sha256

読取器はバージョン、必須キー、メンバー集合、個別サイズ、合計展開サイズ、個別SHA、内容SHA、フレームチェーンを検証します。

固定提出物では `submission_id` に `55155015` を保存します。

自己管理ローカルエージェントでは `submission_id` を null とし、`artifact_manifest_id` に内容指紋由来の `local-...` ID を保存します。

## FullReplayFrame

ワーカーはvisualize_data()の戻り値をそのまま保存せず、許可済みの独立FullReplayFrameへ型検査付きで変換します。

各フレームはschema_version、frame_index、revision、captured_after、payload、previous_hash、frame_hashを持ちます。

payload.currentは両者の盤面、手札、山札順、サイド内容、一時公開領域、選択者、先攻、結果を持ちます。

payload.selectとpayload.logsも専用フィールド集合だけへ正規化します。

## ステップと終局

初期battle_start後に最初のフレームを保存します。

成功した各battle_selectの直後にrevisionを増やし、フレームと最終HumanView／公開ログを更新します。

各battle_selectは履歴を厳密に1件だけ増やす必要があり、complete=trueで封印する場合はframe_countがsteps+1でなければ失敗します。

エンジン終局状態を受け取った場合は、その終局フレームを先に保存した後で結果を確定します。

## 封印と公開条件

一時ZIPへ全メンバーを書き、flushとfsync後に同一ボリューム上のos.replace()で正式名へ変更します。

ワーカーは封印成功後にreplay.sealedとmatch.finishedを送ります。

両通知の間でワーカーが終了した場合、親は完全検証済みリプレイ内のresult.jsonを終端結果として復元します。

通知済み結果とresult.jsonが一致しない場合は、リプレイ検証失敗として完全情報を公開しません。

親は子プロセス終了を確認した後、外部ファイルSHAとZIP内部を再検証します。

completeがtrueでない場合、または外部・内部検証に失敗した場合、完全情報表示を有効にしません。

捕捉可能な異常は不完全リプレイとして封印できても、レビュー画面では完全情報リプレイとして公開しません。
