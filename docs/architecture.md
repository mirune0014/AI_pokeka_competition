# PTCG Human Client アーキテクチャ

## 構成

アプリは、Qt GUI親プロセス、対戦スーパーバイザ、1対戦限定のspawn子プロセス、封印済みリプレイで構成します。

GUI親プロセスは4画面、設定、ローカルカードカタログ、安全化済み状態ストア、リプレイ読取器を持ちます。

GUI親プロセスは `cg.dll`、選択した `main.py`、生観測、AI観測、ライブ完全情報を import または保持しません。

互換性確認用または対戦用の子プロセスだけが、再検証済みステージングからエンジンとローカルエージェントをロードします。

子プロセスはエンジンのグローバル状態、生の合法手インデックス対応、完全情報フレームを所有します。

QMLへ公開するライブ状態はHumanViewStateとDecisionRequestの許可リストDTOに限定します。

現実装ではAppControllerの読取専用Qtプロパティを介してDTOを渡しますが、入れ子を個別のQObject型へ分解した完全型付きViewModelではなく、スキーマ検証済みQVariantMap／QVariantListです。

この差分は安全境界を越える生JSON公開ではありませんが、要件上の残課題として扱います。

## 対戦フロー

~~~mermaid
flowchart LR
    A["SetupScreen"] --> B["パッケージ選択と内容指紋登録"]
    B --> C["ステージング再検査と両座席の互換性確認"]
    C --> D["対戦専用ステージング"]
    D --> E["spawn worker + Job Object"]
    E --> F["battle_start"]
    F --> G{"current.yourIndex"}
    G -->|"人間"| H["DecisionRequest"]
    H --> I["opaque tokenを順序付き送信"]
    I --> J["battle_select 1回"]
    G -->|"AI"| K["登録済みagent(obs)"]
    K --> L["戻り値を現在合法手で再検証"]
    L --> J
    J --> M["HumanView / 公開ログ / replay frame"]
    M --> G
    G -->|"current.result"| N["replay封印"]
    N --> O["worker終了確認"]
    O --> P["Result / Replay"]
~~~

## 状態機械

対戦状態はPREPARING、STARTING、WAITING_FOR_HUMAN、AGENT_THINKING、ENGINE_PROCESSING、FINISHING、FINISHED、REPLAY_SEALED、ABORTEDのいずれかです。

各局面でcurrent.yourIndexを再評価し、ターンプレイヤーから選択者を推測しません。

Player 0／Player 1、先攻プレイヤー、現在ターンのプレイヤー、現在の選択者を別フィールドで扱います。

終局したcurrent.resultは、遅れて届いた放棄要求より先に確定します。

AI思考前後と局面境界で放棄・停止要求を確認し、AI思考中の放棄後に次のbattle_selectを実行しません。

## ステージングと終了管理

ステージャーは `%LOCALAPPDATA%\PTCGHumanClient\staging\<match-id>` に専用コピーを作り、コピー後に登録済みの全ファイルを再照合します。

人間デッキは同一の読取バイト列からCSV解析と原本SHA-256を作るため、解析内容と記録ハッシュが分離しません。

ローカルマニフェストは GUI 親プロセスからスーパーバイザを経てワーカーへ渡し、各段階が同じファイル集合を照合します。

固定提出物と一致する場合だけ固定マニフェスト ID と submission ID を使い、それ以外の結果とリプレイにはローカル内容指紋から作った ID を保存します。

起動後の子プロセスと子孫はWindows Job ObjectのKILL_ON_JOB_CLOSEへ所属させます。

Pipe、spawn、Job割当、初期送信の途中失敗でも、プロセス、ハンドル、ステージングを回収します。

24時間を超えた直下ステージング残骸は次回起動時に安全な親パス検査後だけ削除します。

## リプレイと再現性

対象cg.dllはシード付き対戦APIを公開していません。

「同じ設定で再戦」は新しい乱数系列になり得るため、同一対戦の再現を意味しません。

リプレイはエンジンや提出エージェントを再実行せず、ワーカーが保存したバージョン付きスナップショットだけを読みます。
