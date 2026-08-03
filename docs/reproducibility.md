# 再現環境の復元

## Windowsでの取得

固定した戦略証跡には長いパスが含まれるため、Windowsではcloneまたはcheckoutの前に長いパスを有効にする。

```powershell
git config --global core.longpaths true
```

`alakazam`と`archaludon`は、記録済みSHA-256を維持するため改行を正規化しない。これらのディレクトリに`git add --renormalize`を実行しない。

## ネイティブ対戦runtime

各候補に重複する4個のネイティブライブラリはGit管理外であり、追跡済みの基準runtimeから復元する。

```powershell
py -3.11 tools/hydrate_candidate_native_runtime.py
```

特定候補だけを復元する場合は候補名を渡す。`--check`を付けると書き込まずにSHA-256を検証する。

```powershell
py -3.11 tools/hydrate_candidate_native_runtime.py --check archaludon_certified_late_boundary_ultra_ball_route_v3_repair1
```

## Git管理するもの

- 方策ソース、テスト、固定評価契約、判断記録、再生成スクリプト
- 各候補の`deck.csv`。60枚構成そのものが実験入力なので追跡する
- 固定局面fixtureと、再生成に必要な小さな入力JSON

ビルド成果物、キャッシュ、提出アーカイブ、対戦ログ、巨大な集計表、評価runnerの出力は`.gitignore`対象とし、隣接する固定契約とスクリプトから再生成する。
