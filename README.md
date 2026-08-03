# AI Pokeka Competition

Kaggle `pokemon-tcg-ai-battle`向けの、決定論的ルールベースエージェントと
対戦検証のリポジトリです。

## 最初に見る場所

- 全体の配置と用途: [`docs/repository_layout.md`](docs/repository_layout.md)
- Archaludonの正式成果物: [`autonomous_gold_20260715/WORKSPACE.md`](autonomous_gold_20260715/WORKSPACE.md)
- Alakazamの段階開発: [`alakazam_staged_20260729/README.md`](alakazam_staged_20260729/README.md)
- RL・模倣学習の終了済み実験: [`experiments/README.md`](experiments/README.md)
- 開発・評価ルール: [`AGENTS.md`](AGENTS.md)

## 現在の基準成果物

### Archaludon

Historical-Silverを親にした単一resolver再基盤化版が、現在の正式な
決定論的成果物です。

```text
autonomous_gold_20260715/final/
  archaludon_historical_silver_single_resolver_salvage_v1/
```

### Alakazam

Alakazamは独立した段階開発ワークスペースにあります。正式なC2系統と
後続の試験候補は、次の索引から確認します。

```text
alakazam_staged_20260729/
```

## 重要な区別

- `final/`は採用済みの正式成果物です。
- `candidates/`と`versions/`は試験候補を含み、最新名が最強とは限りません。
- `evaluations/`、`live/`、`analysis_outputs/`などの大容量フォルダは
  再生成可能なローカル出力を含みます。
- ルート直下の`submission_*`は古い提出・回帰検証用アンカーです。
  既存の評価契約がそのパスを参照するため、移動しません。
- `rl_ptcg/`と`experiments/archaludon_latest_v1_rl*`は終了済み研究記録です。
  現在の実装方針には使用しません。
