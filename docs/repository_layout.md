# リポジトリ配置ガイド

この文書を、成果物を探すときの唯一の入口とします。

## 1. 現行エージェント

| 対象 | 状態 | 入口 |
|---|---|---|
| Archaludon | 正式な決定論的再基盤化版 | `autonomous_gold_20260715/final/archaludon_historical_silver_single_resolver_salvage_v1/` |
| Historical-Silver | Archaludonの強度基準 | `autonomous_gold_20260715/baseline/historical_silver_archaludon_54495224/` |
| Alakazam | 段階開発・C2系統が正式基準 | `alakazam_staged_20260729/` |

「新しいフォルダ名」ではなく、各ワークスペースの`README.md`、
`CHECKPOINT.md`、最終判断レポートを採否の根拠にします。

## 2. Archaludonワークスペース

`autonomous_gold_20260715/`は、2026-07-15以降の決定論的改善ループです。

| フォルダ | 用途 |
|---|---|
| `baseline/` | Historical-Silverなど変更しない基準 |
| `final/` | 採用済みの正式成果物 |
| `candidates/` | 採用・不採用・保留を含む候補ソース |
| `strategy/` | ルール要件と実装前判断 |
| `evaluation_specs/` | 再現用の固定対戦契約 |
| `numerical_audits/` | 数値の独立再計算結果 |
| `root_verification/` | rootによる破綻・差分確認 |
| `decisions/`、`judgments/` | 採否記録 |
| `evaluations/`、`live/` | 大容量のローカル実行結果・公開対戦履歴 |

`evaluations/`や`live/`は証拠ですが、通常の入口ではありません。まず
`final/`と`WORKSPACE.md`を見て、必要な場合だけ対応する評価記録へ進みます。

## 3. Alakazamワークスペース

`alakazam_staged_20260729/`にソース、要件、fixture、評価adapter、判断レポートを
集約しています。

| フォルダ | 用途 |
|---|---|
| `versions/` | 段階ごとの候補ソース |
| `reports/` | 採否と最終判断 |
| `specs/` | 比較契約・要件・実装記録 |
| `fixtures/` | 既知局面の再現入力 |
| `eval_adapters/` | 固定評価用entrypoint |
| `evaluations/`、`metrics/`、`submissions/` | 再生成可能なローカル出力 |

正式なC2系統と後続候補の関係は、
`alakazam_staged_20260729/README.md`を参照します。

## 4. RL・模倣学習アーカイブ

以下は現在の実装候補ではなく、失敗を含む研究記録です。

- `rl_ptcg/`: 初期の残差方策実験基盤
- `experiments/archaludon_latest_v1_rl*/`: PPO、BC、DAggerなどの比較
- `analysis_outputs/`: Git管理外の大容量生成結果

PPOは有効な行動差を作れず、BCとDAggerはHistorical-Silverを含む固定比較で
ルールベース基準を下回ったため、現在は停止しています。

## 5. 共通資産

| フォルダ | 用途 |
|---|---|
| `meta_agents/` | 対戦相手・メタ検証用の完全エージェント群 |
| `isolated_rule_agents/` | 独立ルール候補と回帰相手 |
| `tools/` | 実行、可視化、評価、パッケージ補助 |
| `external/` | 外部エンジンなどの参照物 |
| `apps/` | 対戦履歴・盤面確認用アプリ |
| `data/` | 共有入力と取得データの索引 |
| `docs/` | 横断的な設計・分析文書 |

## 6. 旧提出フォルダ

ルート直下の`submission_*`は、古い提出物または固定回帰アンカーです。
一部の固定評価JSONと検証スクリプトが現在も正確な相対パスを参照しています。

そのため、これらは見た目を整える目的では移動しません。新しい開発の親として
直接選ばず、対応する評価契約から参照するときだけ使用します。

## 7. 新規成果物の配置規則

- Archaludonの新候補は`autonomous_gold_20260715/candidates/`へ置きます。
- Alakazamの新候補は`alakazam_staged_20260729/versions/`へ置きます。
- 固定評価契約と結果を同じフォルダへ混在させません。
- 採用済みだけを`final/`または正式基準として明記します。
- RL、BC、DAggerを再開する場合は、現行ルールベース成果物と別の
  `experiments/`配下に置きます。
- 再生成可能なログ、trace、パッケージはGit管理対象にしません。
