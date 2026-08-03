# v3 進化後確定KO優先 fix2 実行追補

## attempt 1 の保存

`runner_recheck_attempt_1`では、最初のfocused commandを起動するPowerShell wrapperがコマンド本体の実行前に失敗した。

- `focused_candidate_stdout.txt`: 0 bytes
- `focused_candidate_stderr.txt`: 0 bytes
- 両ファイルのSHA-256:
  `E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855`
- unittestは未起動。
- 後続3コマンドは未実行。
- `execution_manifest.json`は生成されていない。

この試行を削除、上書き、またはテスト失敗として扱わない。機械的なrunner失敗のraw evidenceとしてそのまま残す。

## attempt 2

新しい出力先を使用する。

`alakazam_staged_20260729/evaluations/v3_exact_evolution_ko_fix2/runner_recheck_attempt_2`

凍結identity、テスト対象、期待件数、Python、engine、合格条件は元の実行仕様から変更しない。

PowerShellの共通wrapperを使わず、各unittest commandを個別のプロセスとして起動する。環境変数は各プロセスの直前に固定する。

```text
PYTHONPATH=C:/Users/amuam/project/AI_pokeka_competition/analysis_outputs/cynthia_v9_vs_v11_poffin_role_selection_20260713/seeded_engine
PYTHONDONTWRITEBYTECODE=1
```

実行順:

1. 候補cwdでfocused 11件。
2. 候補cwdでfull 166件。
3. 親cwdでfull 155件。
4. workspace rootで変更2ファイルを組み込み`compile()`。

各commandのstdout/stderrは最初から別ファイルへ直接redirectする。各command終了後にexit codeを取得し、最後に`execution_manifest.json`を作る。

attempt 2でもrunner自体が起動できない場合は、同じdirectoryへ再試行せずrootへ返す。

## attempt 2 の保存

attempt 2では、unittest commandそのものは正しかったが、stdout/stderrのredirect先が候補cwdからの相対パスとして解釈された。このため`Out-File`が`DirectoryNotFoundException`となり、Python processは起動されなかった。

誤って候補ディレクトリ内に作られたtreeは、ファイルが0件であることと、解決済み絶対パスが候補ディレクトリ内に収まることをrootが確認してから削除した。source file、test file、fixture、正規evaluationには変更がない。

attempt 2もテスト結果には使用しない。

## attempt 3

新しい出力先を使用する。

`C:/Users/amuam/project/AI_pokeka_competition/alakazam_staged_20260729/evaluations/v3_exact_evolution_ko_fix2/runner_recheck_attempt_3`

実行前に、上記の解決済み絶対パスを`New-Item -ItemType Directory -Force -LiteralPath`へ直接渡す。各stdout/stderr pathも、上記directoryと固定ファイル名を`Join-Path`した絶対パスを使う。

unittest processは`System.Diagnostics.ProcessStartInfo`で直接起動してもよい。その場合は次を固定する。

- `FileName`: 凍結Pythonの絶対パス。
- `WorkingDirectory`: 各候補または親の絶対パス。
- `UseShellExecute = false`。
- `RedirectStandardOutput = true`。
- `RedirectStandardError = true`。
- environmentに凍結`PYTHONPATH`と`PYTHONDONTWRITEBYTECODE=1`。

実行順、引数、期待件数、compile対象、manifest schemaは元仕様から変更しない。
