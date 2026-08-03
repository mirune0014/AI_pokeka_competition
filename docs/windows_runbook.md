# Windows 開発・実行ランブック

## 前提

Windows 11 x64、CPython 3.11 x64、PowerShell 7またはWindows PowerShell 5.1を使います。

アプリ専用仮想環境は apps\ptcg_desktop\.venv とし、研究用環境を変更しません。

## 開発環境

~~~powershell
py -3.11 -m venv apps\ptcg_desktop\.venv
apps\ptcg_desktop\.venv\Scripts\python.exe -m pip install --upgrade pip
apps\ptcg_desktop\.venv\Scripts\python.exe -m pip install -e "apps\ptcg_desktop[build]"
~~~

## 単体・QMLテスト

~~~powershell
$env:PYTHONPATH = (Resolve-Path apps\ptcg_desktop\src)
apps\ptcg_desktop\.venv\Scripts\python.exe -m unittest discover -s apps\ptcg_desktop\tests -v
~~~

## 実提出物の統合テスト

~~~powershell
$env:PYTHONPATH = (Resolve-Path apps\ptcg_desktop\src)
$env:PTCG_SUBMISSION_ARTIFACT = (Resolve-Path autonomous_gold_20260715\packages\archaludon_practice_first_terminal_and_role_commitment_v1_validationfix2_clean_20260801_1455\extracted_verification)
apps\ptcg_desktop\.venv\Scripts\python.exe -m unittest apps.ptcg_desktop.tests.test_engine_integration -v
$env:PTCG_RUN_LONG_INTEGRATION = "1"
apps\ptcg_desktop\.venv\Scripts\python.exe -m unittest apps.ptcg_desktop.tests.test_engine_full_match -v
~~~

長局試験はPlayer 0とPlayer 1の両方を正常終局まで自動操作します。

## 高DPI・キーボードプローブ

~~~powershell
$env:PYTHONPATH = (Resolve-Path apps\ptcg_desktop\src)
$env:QT_QPA_PLATFORM = "offscreen"
$env:QT_QUICK_BACKEND = "software"

$env:QT_SCALE_FACTOR = "1.5"
apps\ptcg_desktop\.venv\Scripts\python.exe apps\ptcg_desktop\tests\qml_interaction_probe.py --scale 1.5

$env:QT_SCALE_FACTOR = "2.0"
apps\ptcg_desktop\.venv\Scripts\python.exe apps\ptcg_desktop\tests\qml_interaction_probe.py --scale 2.0
~~~

プローブは物理1280×720相当の論理ビューポート、縦横スクロール、F6、Space、Ctrl+Enter、一回送信、100ms未満のローカル反応を検査します。

## GUI起動

~~~powershell
$env:PYTHONPATH = (Resolve-Path apps\ptcg_desktop\src)
apps\ptcg_desktop\.venv\Scripts\python.exe -m ptcg_desktop.launcher
~~~

初回は Kaggle 互換ローカルエージェントの `.tar.gz` または実行ルート、人間デッキ CSV、任意の日本語カード画像フォルダー、リプレイ先を選びます。

圧縮されたエージェントは「tar.gzファイル…」を選びます。

「展開済みフォルダー…」はディレクトリ専用であり、`.tar.gz` を含むファイルは表示しません。

ローカルエージェントの実行ルートには `main.py`、`deck.csv`、`cg/` が必要です。

選択だけではコードを実行しません。

「この内容を登録して互換性を確認」を押すと、指紋登録後に使い捨て子プロセスで `main.py` と `cg.dll` をロードします。

この子プロセスは OS サンドボックスではないため、自分で管理しているパッケージだけを選びます。

画像は <card-id>.jpg、<card-id>.png、cards_jp\<card-id>.* などのローカル候補だけから解決します。

このリポジトリでは、`tools\ptcg_japanese_visualizer_extension` を選ぶと、日本語名称カタログ、完全画像、盤面用縮小画像をまとめて使用できます。

## 対戦画面の操作

カードへカーソルを合わせると、右側のカードプレビューへ大きな日本語画像を表示します。

ポケモンの現在 HP と最大 HP、ついているエネルギー枚数、ポケモンのどうぐはカード上の表示で確認します。

各プレイヤーのトラッシュへカーソルを合わせるかクリックすると、内容一覧が開きます。

AI の直前行動は右側の行動欄へ日本語で表示します。

AI 行動の表示時間は対戦準備画面で 400 ms から 10,000 ms の範囲に設定でき、既定値は 1,000 ms です。

合法手のカード名とワザ名は、日本語カタログに対応項目がある場合に日本語で表示します。

サイド取得では、一覧に `サイド1`、`サイド2` のように表示します。

この番号はサイドの物理位置ではなく、現在表示されている候補の順番です。

ポケモンや手札を対象とする選択では、一覧番号と同じ番号を盤面カードの左上へ表示します。

選択したカードは金色の枠と半透明色に変わり、左上へチェック記号を表示します。

エネルギー付与の一覧は「つけるカード → ポケモン」と表示します。

カード効果がカード選択と付け先選択を分けて要求する場合は、`① つけるカードを選ぶ → ② つけるポケモンを選ぶ` の現在段階を表示します。

## JSON履歴を開く

対戦が終了すると、同じ名前の `.ptcgmatch` と `.visualizer.json` をリプレイ保存フォルダーへ保存します。

`.ptcgmatch` はアプリ用の改ざん検査付きZIPであり、内部にもJSONとJSON Linesを保持します。

`.visualizer.json` は `cg.visualize_data()` 互換の単一JSON配列であり、テキストエディター、JSON解析ツール、対応する対戦ビューワーから開けます。

結果画面の「JSONファイルを開く」は、WindowsでJSONに関連付けられたアプリを起動します。

「保存先を開く」は、`.ptcgmatch` と `.visualizer.json` があるフォルダーをエクスプローラーで開きます。

「公式ビューワーで見る」はローカル補助ページを開きます。

補助ページで `.visualizer.json` を選び、「外部の公式ビューワーへ送って表示」を押すと、JSONを `ptcgvis.heroz.jp` へPOSTします。

ファイルを選んだだけでは外部へ送信しません。

公式ビューワー用JSONには双方の手札、山札順、サイド内容が含まれるため、共有してよい対戦だけを使用してください。

## エージェントの指紋確認

自己管理ローカルエージェントは、次のコマンドでコードを import せずに内容指紋を確認できます。

~~~powershell
$env:PYTHONPATH = (Resolve-Path apps\ptcg_desktop\src)
apps\ptcg_desktop\.venv\Scripts\python.exe -m ptcg_desktop.cli inspect-local --artifact "C:\path with space\my-agent.tar.gz"
~~~

固定 submission 55155015 との一致だけを調べる場合は、次のコマンドを使います。

~~~powershell
apps\ptcg_desktop\.venv\Scripts\python.exe -m ptcg_desktop.cli verify --artifact "C:\path with space\submission.tar.gz"
~~~

固定照合が成功した場合だけ `Verified Submission` と表示します。

それ以外の互換パッケージは、明示的な登録後に `自己管理ローカルエージェント` と表示します。

ローカル登録は安全性審査ではありません。

## one-folderビルド

実行中の `PTCGHumanClient.exe` がある場合は、配布フォルダーを更新できないため先に終了します。

~~~powershell
apps\ptcg_desktop\.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean --distpath apps\ptcg_desktop\dist --workpath apps\ptcg_desktop\build apps\ptcg_desktop\packaging\PTCGDesktop.spec
~~~

通常の成果物は `apps\ptcg_desktop\dist\PTCGHumanClient` です。

2026-08-03 のエージェント選択表示修正版は、旧実行ファイルによるフォルダーロックを避けて `apps\ptcg_desktop\dist_viewer_v5\PTCGHumanClient` に出力しました。

提出物、cg.dll、カード画像、リプレイを成果物へ含めません。

specは汎用QtQml探索が拾うQtWebEngine、QtWebSockets、QtWebView、QtWebChannel、QtNetwork QMLプラグインを配布物から除外します。QtQml／QtQuickが起動時に必要とするQtNetwork.pydは同梱します。

Qt Quick内部依存のQtNetwork.pyd、Qt6Network.dll、Qt6QmlNetwork.dllは残りますが、対戦機能とアプリ内リプレイ機能はHTTP、WebSocket、待受、外向き画像取得を呼びません。

公式ビューワーへの送信は、結果画面からローカル補助ページを開き、利用者がJSONを選んで確認ボタンを押した場合だけ既定ブラウザーが実行します。

## frozen自己試験

~~~powershell
$artifact = (Resolve-Path autonomous_gold_20260715\packages\archaludon_practice_first_terminal_and_role_commitment_v1_validationfix2_clean_20260801_1455\extracted_verification)
$exe = (Resolve-Path apps\ptcg_desktop\dist_viewer_v5\PTCGHumanClient\PTCGHumanClient.exe)
$runId = [guid]::NewGuid().ToString('N')
foreach ($seat in 0, 1) {
    $output = Join-Path $env:TEMP "ptcg-$runId-seat$seat.json"
    $process = Start-Process -FilePath $exe -ArgumentList @('--self-test', $artifact, '--self-test-output', $output, '--self-test-seat', [string]$seat) -PassThru -Wait -WindowStyle Hidden
    Get-Content -LiteralPath $output -Raw -Encoding utf8
    "seat=$seat exit=$($process.ExitCode)"
}
~~~

## frozen GUI起動試験

プロセス生存だけでは例外ダイアログを正常起動と誤認するため、必ず一意な完了マーカーと終了コードを確認します。

~~~powershell
$exe = (Resolve-Path apps\ptcg_desktop\dist_viewer_v5\PTCGHumanClient\PTCGHumanClient.exe)
$runId = [guid]::NewGuid().ToString('N')
$output = Join-Path $env:TEMP "ptcg-gui-smoke-$runId.json"
$process = Start-Process -FilePath $exe -ArgumentList @('--gui-smoke-output', $output) -PassThru -Wait -WindowStyle Hidden
Get-Content -LiteralPath $output -Raw -Encoding utf8
"exit=$($process.ExitCode)"
~~~

成功条件は、終了コード0、qml_loaded=true、root_countが1以上、screen=setup、warningsが空であることです。

## 保存先

設定は `%LOCALAPPDATA%\PTCGHumanClient\settings.json` です。

選択パスは保存しますが、登録マニフェストと互換性確認結果は次回起動へ持ち越しません。

一時ステージングは %LOCALAPPDATA%\PTCGHumanClient\staging です。

診断ログは %LOCALAPPDATA%\PTCGHumanClient\logs です。

既定リプレイ先は %USERPROFILE%\Documents\PTCG Human Client\Replays で、画面から変更できます。

アプリ用リプレイは `match-<UUID>.ptcgmatch`、公式ビューワー用JSONは `match-<UUID>.visualizer.json` です。

診断ログへ生観測、AI手札、山札順、サイド内容を書きません。

診断ログと異なり、`.ptcgmatch` と `.visualizer.json` は試合後レビュー用の完全情報を含みます。

## クラッシュ後の回復

次回起動時に、staging直下にある24時間超の通常ディレクトリだけを削除します。

シンボリックリンク、ジャンクション相当の外部解決パス、stagingルート自体、直下でないパスは削除しません。

即時手動清掃が必要な場合は、アプリと全PTCGHumanClient.exeが終了したことを確認してから、対象の個別match IDディレクトリだけを削除します。

.tmpリプレイとcomplete:falseリプレイは完全情報表示へ使いません。

## オフライン実測

アプリの外向き通信をWindows Defender Firewallでブロックした状態で、照合、対戦、リプレイを実行します。

対象PIDの待受を Get-NetTCPConnection -OwningProcess <PID> -State Listen で確認します。

このネットワーク実測は端末環境依存の手動受入項目です。
