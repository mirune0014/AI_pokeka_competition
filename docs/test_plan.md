# テスト計画と受入記録

## テスト階層

コア単体テストは Python 標準の `unittest` で実行します。

エンジン統合テストは、固定提出物と自己管理ローカルエージェントを環境変数で明示した場合に実行します。

QML スモークテストは `offscreen` とソフトウェアレンダラーを使用し、4 画面の生成、キーボード導線、DPI 別レイアウトを確認します。

Windows 配布テストは、PyInstaller の one-folder 成果物から spawn ワーカー、ローカル IPC、固定照合またはローカル登録、リプレイ封印を確認します。

## 2026-08-02 の実行環境

- Windows `10.0.26200` 上で実行しました。
- Python は `3.11.6`、64 bit です。
- PySide6 は `6.10.1` です。
- PyInstaller は `6.21.0` です。
- 固定提出物は submission 55155015 の信頼済み 12 ファイルと一致する展開済みアーカイブです。
- ローカル統合対象は `archaludon_public_exact_same_active_attack_dominance_v1` の 12 ファイルアーカイブです。

## 自動テスト結果

次の環境変数を設定し、実エンジンと長時間統合テストを含めて実行します。

~~~powershell
$env:PYTHONPATH = (Resolve-Path apps\ptcg_desktop\src)
$env:PTCG_SUBMISSION_ARTIFACT = (Resolve-Path autonomous_gold_20260715\packages\archaludon_practice_first_terminal_and_role_commitment_v1_validationfix2_clean_20260801_1455\extracted_verification)
$env:PTCG_RUN_LONG_INTEGRATION = '1'
$env:PTCG_LOCAL_AGENT_ARTIFACT = (Resolve-Path autonomous_gold_20260715\packages\archaludon_public_exact_same_active_attack_dominance_v1_clean_20260801_2352\submission_archaludon_public_exact_same_active_attack_dominance_v1_20260801.tar.gz)
$env:PTCG_LOCAL_HUMAN_DECK = (Resolve-Path autonomous_gold_20260715\packages\archaludon_public_exact_same_active_attack_dominance_v1_clean_20260801_2352\stage\deck.csv)
apps\ptcg_desktop\.venv\Scripts\python.exe -m compileall -q apps\ptcg_desktop\src\ptcg_desktop apps\ptcg_desktop\tests
apps\ptcg_desktop\.venv\Scripts\python.exe -m unittest discover -s apps\ptcg_desktop\tests -v
~~~

エージェント選択表示の修正後は 95 件成功、失敗 0、スキップ 0、実行時間 18.981 秒でした。

主要な実証内容は次のとおりです。

- 正しい 12 ファイルの照合、1 バイト変更、追加ファイル、古いステージングの安全な清掃を確認しました。
- ローカル登録が `main.py` を実行しないこと、アーカイブと展開フォルダーの内容指紋一致、改変検出、mtime 非依存、提出 ID 偽装拒否、安全でないアーカイブ拒否を確認しました。
- `.tar.gz`、`.tgz`、`.gz` をファイル選択画面の対象に含め、日本語パスを欠落なく受け渡すことを確認しました。
- 圧縮ファイル用ボタンと展開済みフォルダー用ボタンを区別し、フォルダー選択画面にはファイルが表示されないことを画面内で説明しました。
- 固定マニフェストと異なる実候補を `local_registered` として登録し、両座席の互換性確認と開始可能状態を確認しました。
- 同じ実候補を両座席で起動し、ローカル ID、submission ID の null、使用した 12 ファイルのハッシュが結果と封印済みリプレイへ保存されることを確認しました。
- 日本語と空白を含むパス、60 枚、59 枚、未知 ID、壊れた列、非正整数、UTF-8 異常を確認しました。
- 人間が Player 0 と Player 1 の双方で、実エンジンの通常終局まで到達することを確認しました。
- 両座席のデッキを使い捨てプロセスでエンジン受理確認しました。
- Player 1 の放棄、Player 0 の最大ステップ、AI 思考中の放棄を実プロセスで確認しました。
- HumanView、IPC の UTF-8 JSON バイト列、公開ログへ秘密カナリアが混入しないことを確認しました。
- 終局後の FullReplayFrame に同じ秘密カナリアが残ることを確認しました。
- `minCount=0`、順序維持、重複、二重送信、古い revision、不正 AI 行動、未知型のフェイルクローズを確認しました。
- QML の 4 画面生成、盤面、結果、リプレイのダミー状態描画、警告 0 件を確認しました。
- 大型カードプレビュー、数値 HP、エネルギー表示、両プレイヤーのトラッシュと内容ポップアップを確認しました。
- 日本語カード名とワザ名の変換、完全画像と縮小画像の使い分け、画像フォルダー直指定時の親カタログ探索を確認しました。
- AI 行動の描画前待機と描画後待機の分割、日本語の直前行動表示、既定 1,000 ms への設定移行を確認しました。
- 裏向きサイドを `サイド1` 形式で表示し、カード ID、対象カード ID、area、index を DTO へ含めないことを確認しました。
- 合法手番号と盤面カード番号の対応、選択済みカードの金色表示、150% と 200% でのキーボード操作を確認しました。
- エネルギー付与の組み合わせ表示、二段階ガイド、日本語化後の付け先名とエネルギー個数の保持を確認しました。
- 初期、各選択後、終局フレームの往復読込、画像非同梱、未知 ZIP メンバーと改変フレームの拒否を確認しました。
- `cg.visualize_data()` 互換フレームの封入、単一JSONへの自動書出し、旧リプレイからの互換再構成を確認しました。
- 結果画面からJSON、保存先、ローカル補助ページを安全に開けることと、補助ページが明示確認まで外部送信しないことを確認しました。
- プロセス停止直後でも、終了後処理とリプレイ検証が終わるまで結果を公開しない回帰テストを確認しました。

## 高 DPI とキーボードの実測

次のコマンドを倍率ごとに実行します。

~~~powershell
apps\ptcg_desktop\.venv\Scripts\python.exe apps\ptcg_desktop\tests\qml_interaction_probe.py --scale 1.5
apps\ptcg_desktop\.venv\Scripts\python.exe apps\ptcg_desktop\tests\qml_interaction_probe.py --scale 2.0
~~~

150% では device pixel ratio 1.5、論理 viewport 853×480、QML 警告 0 件でした。

200% では device pixel ratio 2.0、論理 viewport 640×360、QML 警告 0 件でした。

両倍率でキーボード選択が 1 回だけ送信され、スクロール範囲 1240×820 を確認しました。

番号対応の検査を含むダミー局面でのローカル操作応答は 150% で 2.522 ms、200% で 1.486 ms でした。

これは offscreen の自動試験であり、物理モニター上の目視受入を代替しません。

## one-folder 配布物の実測

エージェント選択表示の修正版は `apps\ptcg_desktop\dist_viewer_v5\PTCGHumanClient` です。

自己管理ローカル候補を使った frozen 自己試験では、Player 0 と Player 1 がともに終了コード 0、`completed=true`、`replay_available=true` でした。

自己試験は 6 回の `battle_select` で意図的に打ち切るため、結果分類は両座席とも `system_error / max_steps` です。

通常終局そのものは、ソース環境の実エンジン統合テストで両座席を確認しています。

配布物へ submission の `main.py`、`deck.csv`、`cg.dll`、カード画像、QtWebEngine、QtWebSockets、QtWebView、QtWebChannel、QtNetwork QML プラグインが混入していないことを確認しました。Qt Quick の必須依存である `QtNetwork.pyd` は同梱します。

修正版 EXE の SHA-256 は `1A184ABB62AD03D80081AD10AF0CCFDC0C1FF8D700EBAFA0F57EC6725722FD8D` です。

## オフライン実測

対戦、リプレイ保存、アプリ内リプレイ閲覧は外向き通信を必要とせず、GUI のアイドル起動時にアプリ自身が通信を開始しないことを確認しました。

公式ビューワー連携だけは例外で、同梱するローカル補助ページに外部送信先を明記しています。

補助ページはJSONを選択しただけでは送信せず、利用者が確認ボタンを押した場合に既定ブラウザーから `ptcgvis.heroz.jp` へPOSTします。

最新 one-folder GUI は、一意な起動完了マーカーで終了コード 0、`qml_loaded=true`、ルート1件、準備画面、QML警告0件を確認しました。通常GUIをさらに5秒起動し、対象 PID の TCP エンドポイント0件、UDPエンドポイント0件を確認しました。

Qt Quick の内部依存として `QtNetwork.pyd`、`Qt6Network.dll`、`Qt6QmlNetwork.dll` は残りますが、QtNetwork QMLプラグインは除外し、アプリからネットワークAPIを呼びません。

Windows Defender Firewall で通信を遮断した状態の、照合から通常終局、リプレイ閲覧までの手動通し試験は未実施です。

## 10 件の最重要受入結果

### 1. エージェント同一性：合格

固定提出物について、正しい 12 ファイル、1 バイト変更、追加ファイルを自動試験しました。

ローカルエージェントについて、全ファイルの指紋登録、変更検出、提出 ID 偽装拒否、ステージング後の再照合を自動試験しました。

`artifact_manifest_id` と使用ファイルの SHA-256 は結果とリプレイ manifest に保存されます。

### 2. デッキと Windows パス：合格

日本語、空白、非 ASCII を含むパスと、規定の拒否ケースを自動試験しました。

### 3. 座席と先攻／後攻：合格

両座席の通常終局、独立した座席と先攻情報、上下固定の QML 描画を自動試験しました。

### 4. 秘密情報非混入：条件付き合格

HumanView、IPC バイト列、公開ログ、FullReplayFrame のカナリア試験は合格です。

ワーカーの stdout と stderr は破棄されます。

QML 境界は許可リスト検証済み DTO だけを受け取りますが、入れ子まで QObject 化した完全型付き ViewModel ではなく、`QVariantMap` と `QVariantList` を使用しています。

### 5. AI ターン中の人間選択：条件付き合格

AI が選択者の局面でも固定人間席の手札を投影する単体試験は合格です。

実提出物との通常対戦で、AI のカード効果により人間へ選択権が移る特定局面を固定再現する試験は未実施です。

### 6. 選択意味論：条件付き合格

現在コードで扱う DTO、0 件、単一、複数、順序、Yes/No、対象カード、添付、サイド匿名化、合法手番号、未知型の安全側停止を単体試験しました。

すべての enum を実エンジン上で意図的に発生させる網羅試験は未実施です。

### 7. 二重送信と古い局面：合格

二重送信、古い revision、処理済み要求、重複トークン、順序維持を自動試験しました。

### 8. 障害隔離：未完

失敗分類、最大ステップ、放棄中断、終了直後の IPC 競合、リプレイ欠損の単体または統合試験は合格です。

agent 例外、agent 無限ループ、不正戻り値、worker 強制終了、IPC 切断、`cg.dll` 異常、子孫プロセス生成を実際に注入し、GUI 生存と次戦開始まで確認する一括試験は未実施です。

### 9. リプレイ完全性：条件付き合格

初期、各 `battle_select` 後、終局の保存、`steps + 1` 件数不変条件、ハッシュ鎖、封印 ZIP、終端結果整合、前後移動、終局後ゲート、エンジン非再実行を自動試験しました。

公式ビューワー互換JSONの封入と自動書出し、旧形式からの再構成、外部送信前の明示確認も自動試験しました。

長局でのフレーム容量、ピークメモリ、圧縮後サイズ、保存時間、読込時間、移動時間の容量スパイクは未実施です。

### 10. 高 DPI、キーボード、オフライン：条件付き合格

150% と 200% の offscreen 操作、画面内へ収める初期サイズ、キーボード送信、100 ms 目標、GUI の無通信アイドル起動は合格です。

物理 1280×720 モニター上の目視、ファイアウォール遮断下の通常対戦通し試験は未実施です。

## 完了判定

実用的な MVP 本体と one-folder 配布物は成立しています。

ただし、ユーザー定義の厳密な完了条件では、完全型付き QML ViewModel、障害注入一括試験、長局リプレイ容量スパイク、物理モニターとファイアウォール遮断下の手動通し試験が残っています。

したがって、現時点の総合判定は「受入残件あり」であり、「全条件を満たした MVP 完了」とは記録しません。
