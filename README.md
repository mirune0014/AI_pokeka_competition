# AI Pokeka Competition

Kaggle `pokemon-tcg-ai-battle`向けの、決定論的ルールベースエージェントと
対戦検証のリポジトリです。

## 最初に見る場所

- 全体の配置と用途: [`docs/repository_layout.md`](docs/repository_layout.md)
- 使用技術と強化学習手法の初学者向けガイド: [`docs/ptcg_competition_technology_guide.md`](docs/ptcg_competition_technology_guide.md)
- 日付付きワークスペース名の恒久名への移行: [`docs/workspace_rename_20260804.md`](docs/workspace_rename_20260804.md)
- Archaludonの正式成果物: [`archaludon/WORKSPACE.md`](archaludon/WORKSPACE.md)
- Alakazamの段階開発: [`alakazam/README.md`](alakazam/README.md)
- 終了済みのRL・模倣学習実験: [`research/experiments/README.md`](research/experiments/README.md)
- 開発・評価ルール: [`AGENTS.md`](AGENTS.md)

## ルート構成

```text
archaludon/                 Archaludonの現行ワークスペース
alakazam/                   Alakazamの現行ワークスペース
archive/submissions/        旧提出物・固定回帰アンカー
opponents/                  対戦相手と独立ルールエージェント
infrastructure/             アプリ、ツール、外部エンジン、共有データ
research/                   終了済み実験、RL基盤、横断レポート
docs/                       配置・設計・移行記録
_local_generated/           Git管理外のログ、評価出力、配布物
```

ArchaludonとAlakazamは内部パスが長いため、Windowsのパス長問題を避けて
ルート直下に維持しています。それ以外の共通資産・研究・旧提出物・生成物は
用途別の親フォルダへ物理的に集約しています。

## 現在の基準成果物

- Archaludon: `archaludon/final/archaludon_historical_silver_single_resolver_salvage_v1/`
- Historical-Silver: `archaludon/baseline/historical_silver_archaludon_54495224/`
- Alakazam: `alakazam/`のREADMEと判断レポートを参照

`final/`は採用済み、`candidates/`と`versions/`は不採用・保留を含む候補です。
新しい名前や番号だけで強弱を判断しません。
