# リポジトリ物理配置の移行記録（2026-08-04）

## 目的

ルート直下に並んでいた旧提出物、対戦相手、ツール、外部資産、研究実験、
レポート、ログ、配布物を用途別の親フォルダへ集約する。

## 基準と保全方針

- 移行前基準commit: `3111ecf`
- ファイルの削除は行っていない。
- 過去のMarkdown、JSON証拠、凍結仕様、旧提出エージェントの本文は変更しない。
- 現行実行コードと設定に含まれるルート参照だけを新配置へ更新する。
- 移行前のパスとハッシュが必要な場合は、基準commitをcheckoutして確認する。

## 主な移動

| 移行前 | 移行後 |
|---|---|
| `submission_*/` | `archive/submissions/submission_*/` |
| `meta_agents/` | `opponents/meta_agents/` |
| `isolated_rule_agents/` | `opponents/isolated_rule_agents/` |
| `apps/`、`tools/`、`external/`、`data/`、`vendor/` | `infrastructure/`配下 |
| `experiments/`、`rl_ptcg/`、`reports/` | `research/`配下 |
| `deliverables/`、`logs/`、`metrics/`など | `_local_generated/`配下 |
| ルートの共通Pythonスクリプト | `infrastructure/scripts/` |
| ルートの圧縮ファイル | `_local_generated/source_archives/`または`_local_generated/share_packages/` |

`autonomous_gold_20260715/`と`alakazam_staged_20260729/`は、Windowsのパス長を
増やさないためルート直下に維持した。

## 生成物の扱い

`_local_generated/analysis_outputs/`の移動中にWindows側の長い処理が中断した
ため、残りは`_local_generated/analysis_outputs_remaining/`へ退避した。両方とも
Git管理外の再生成可能データであり、正式な証拠やソースの入口ではない。

## 検査

- `infrastructure/scripts/rewrite_repository_paths.py`: 実行コードと設定だけを移行
- `infrastructure/scripts/check_repository_paths.py`: 同じ範囲の旧ルート参照を検査
- `docs/repository_path_migration_report_initial.json`: 初回のパス・import移行と前後SHA-256
- `docs/repository_path_migration_report.json`: 最終補正パスの前後SHA-256
- `docs/repository_path_residual_report.json`: 残存参照の検査結果

過去証拠中の旧パスは意図的に残しているため、残存検査の対象外とする。
