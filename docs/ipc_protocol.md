# IPC プロトコル

## 方式

プロトコルバージョンは1です。

親子間はmultiprocessing.Connection.send_bytes()とrecv_bytes(maxlength)を使います。

stdoutとstderrを通信路にせず、ワーカーでは破棄先へ隔離します。

各フレームは最大1 MiBの厳密なUTF-8 JSONオブジェクトです。

pickleされたアプリケーションオブジェクト、NaN、Infinity、重複キー、未知トップレベルキー、未知メッセージ種別を拒否します。

## 共通エンベロープ

~~~json
{
  "protocol_version": 1,
  "message_id": "message-uuid",
  "message_type": "decision.submit",
  "match_id": "match-uuid",
  "request_id": "request-uuid-or-null",
  "state_revision": 14,
  "step_id": 14,
  "payload": {}
}
~~~

8フィールドを常に持ち、値が該当しないメタデータはnullです。

message_idは接続内で一意とし、重複を拒否します。

request_id、state_revision、step_idは安全な入れ子DTOから共通欄へ昇格します。

親と子は方向ごとの許可メッセージ集合を指定し、不明なmessage_typeを拒否します。

## 親から子

| message_type | 用途 |
|---|---|
| match.start | 再検証済み絶対パス、人間席、デッキ、原本SHA、リプレイ先、上限を渡します。 |
| decision.submit | 現在request ID、revision、順序付きopaque token配列を渡します。 |
| match.forfeit | 人間の放棄を要求します。 |
| worker.shutdown | 終了または取消しを要求します。 |
| deck.validate | 使い捨てワーカーで人間デッキを検証します。 |

## 子から親

| message_type | 用途 |
|---|---|
| worker.ready | ワーカー起動を通知します。 |
| match.started | エンジン初期化と提出物識別子を通知します。 |
| state.update | HumanViewStateと公開ログ増分だけを通知します。 |
| decision.required | 安全なDecisionRequestを通知します。 |
| decision.accepted | 1回限りの選択受付を通知します。 |
| phase.changed | 状態機械フェーズを通知します。 |
| replay.sealed | 確定パス、外部SHA、complete状態を通知します。 |
| match.finished | 分類済み結果を通知します。 |
| error | 固定コード、例外型名、安全な日本語要約だけを通知します。 |
| deck.validated | 構成、既知ID、エンジン受理、表示用デッキ一覧を通知します。 |

専用Heartbeatは実装せず、phase.changedの到着時刻と子プロセス生存状態からスーパーバイザが期限を監視します。

## DecisionRequest

~~~json
{
  "request_id": "uuid",
  "state_revision": 14,
  "select_type": "yes_no",
  "context": "context_41",
  "prompt": "先攻を選びますか？",
  "min_count": 1,
  "max_count": 1,
  "ordered": true,
  "options": [
    {
      "token": "opaque",
      "kind": "yes",
      "label": "はい",
      "detail": "識別番号 1",
      "target_token": null
    }
  ]
}
~~~

生option、エンジンインデックス、serial、reprはIPCへ出しません。

子プロセスはmatch ID、request ID、revision、所属token、個数、重複、順序、処理済み状態を再検証してからlist[int]へ復元します。

送信受付までGUIの要求を保持し、二重クリックやEnter連打を無効化します。

## 切断

終端結果受信後、子がPipeを閉じてからプロセス終了するまでの短いWindows競合は正常EOFとして扱います。

終端結果がない状態での切断だけをipc_disconnectedとして分類します。
