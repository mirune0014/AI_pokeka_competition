# リポジトリ配置ガイド

この文書を、成果物を探すときの入口とします。

## 1. 現行ワークスペース

| 対象 | 状態 | 入口 |
|---|---|---|
| Archaludon | 正式な決定論的再基盤化版 | `archaludon/final/archaludon_historical_silver_single_resolver_salvage_v1/` |
| Historical-Silver | Archaludonの強度基準 | `archaludon/baseline/historical_silver_archaludon_54495224/` |
| Alakazam | 段階開発・C2系統が正式基準 | `alakazam/` |

ArchaludonとAlakazamは内部の相対パスが長いため、Windowsのパス長問題を
避けてルート直下に維持します。両者の採否は、各ワークスペースのREADME、
CHECKPOINT、最終判断レポートで確認します。

## 2. 用途別の物理配置

```text
archive/
  submissions/             旧提出物・固定回帰アンカー
opponents/
  meta_agents/             メタ検証用の完全エージェント
  isolated_rule_agents/    独立ルール候補と回帰相手
infrastructure/
  apps/                    対戦履歴・盤面確認アプリ
  tools/                   実行、評価、可視化、パッケージ補助
  scripts/                 ルート共通の補助スクリプト
  external/                外部エンジンなどの参照物
  data/                    共有入力と取得データ
  vendor/                  外部依存物
research/
  experiments/             終了済みRL・BC・DAgger実験
  rl_ptcg/                 学習実験基盤
  reports/                 横断分析レポート
_local_generated/          Git管理外の再生成可能な出力
```

旧ルート直下の`submission_*`、`meta_agents`、`isolated_rule_agents`、
`apps`、`tools`、`external`、`data`、`experiments`、`rl_ptcg`、`reports`、
`deliverables`、`logs`などは、上記の親フォルダへ実際に移動済みです。

## 3. Archaludon

`archaludon/`は決定論的改善ループの本体です。

| フォルダ | 用途 |
|---|---|
| `baseline/` | Historical-Silverなど変更しない基準 |
| `final/` | 採用済みの正式成果物 |
| `candidates/` | 採用・不採用・保留を含む候補 |
| `strategy/` | ルール要件と実装前判断 |
| `evaluation_specs/` | 再現用の固定対戦契約 |
| `numerical_audits/`、`root_verification/` | 数値と挙動の検証記録 |
| `decisions/`、`judgments/` | 採否記録 |

通常は`final/`と`WORKSPACE.md`から入り、必要な場合だけ評価記録へ進みます。

## 4. Alakazam

`alakazam/`内で完結します。

| フォルダ | 用途 |
|---|---|
| `versions/` | 段階ごとの候補ソース |
| `reports/` | 採否と最終判断 |
| `specs/` | 比較契約・要件・実装記録 |
| `fixtures/` | 既知局面の再現入力 |
| `eval_adapters/` | 固定評価用entrypoint |
| `evaluations/`、`metrics/`、`submissions/` | 再生成可能なローカル出力 |

## 5. 研究アーカイブ

`research/rl_ptcg/`と`research/experiments/archaludon_latest_v1_rl*/`は、
PPO、BC、DAggerなどの終了済み研究記録です。現在の決定論的実装方針には
使用しませんが、失敗の再現と比較のため追跡します。

## 6. 生成物

`_local_generated/`はGit管理外です。ログ、評価出力、Notebook出力、配布用
圧縮ファイルなど、ソースから再生成できるものを置きます。整理前にルートへ
あった圧縮ファイルも、この配下へ退避しており削除していません。

## 7. 再現性

最初の物理整理の基準はcommit `3111ecf`、日付付きワークスペース名を恒久名へ
移した基準はcommit `0f22d49`です。過去のMarkdown、JSON証拠、凍結仕様、
旧提出エージェントの本文は書き換えていません。古い記録中の旧パスは当時の
配置を示すものとして残り、基準commitをcheckoutすればそのまま再現できます。

現行の実行コードと設定だけを新パスへ移行しています。詳細は
`docs/repository_layout_migration_20260804.md`と
`docs/workspace_rename_20260804.md`を参照してください。

## 8. 新規成果物の配置規則

- Archaludon候補は`archaludon/candidates/`へ置く。
- Alakazam候補は`alakazam/versions/`へ置く。
- 共通ツールやアプリは`infrastructure/`へ置く。
- 学習・探索実験は`research/experiments/`へ置く。
- 旧提出物は`archive/submissions/`へ置く。
- 再生成可能なログ、trace、評価出力、圧縮ファイルは`_local_generated/`へ置く。
