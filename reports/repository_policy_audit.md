# Repository policy and RL-contamination audit

## 判定

新規ロケット団ミュウツーex／ワナイダー方策は、完全に分離したディレクトリで
手書きの決定論的ルールだけを実装する。`rl_ptcg/`、学習済み重み、残差ランカー、
模倣ラベル、replay 由来の相手方策 proxy は、実行時にもソース作成時にも使わない。

Historical-Silver の `cg/` 型定義と合法手 API、汎用ローカル対戦 runner は再利用可能。
ただしパスとハッシュを明示し、暗黙の既定値に依存しない。

## 監査範囲

以下を検索・確認した。

- RL 状態表現、カード特徴量、action mask、候補手 filter
- 行動番号と合法手の変換
- reward shaping、trajectory、checkpoint
- learned logit、方策・価値モデル、ranker、推論時 argmax
- belief/search expert、replay action、Gold action
- fallback と乱数
- RL 導入時の engine wrapper と共通 tool の既定値
- Historical-Silver と後発 archive の差分

## 新規方策で利用してよい部品

| 部品 | 利用範囲 | 条件 |
|---|---|---|
| exact baseline の `cg/api.py` | observation、enum、option、card metadata の型 | ハッシュを manifest と照合 |
| exact baseline の `cg/game.py`、`cg/sim.py`、`cg/utils.py` | engine の標準 interface | candidate に同一 bundle をコピーする場合だけ |
| engine が返す合法 option | 実行時の唯一の legality authority | index を返す前に範囲と一致を再検証 |
| `tools/run_seeded_paired_suite.py` | baseline/candidate の同一 seed 比較 | engine、agent、output をすべて明示 |
| `tools/run_local_battle.py` | trace と first-divergence 再現 | engine seed、seat、seed を固定 |
| baseline の通常 scoring/tie の考え方 | 既知の安全規則を人手で移植する際の参照 | RL 混入版からはコピーしない |
| `rl_ptcg/canonical_actions.py`、`public_state.py` | offline trace の比較・重複排除だけ | runtime の legality/scoring には使わない |

## 利用しない部品

次は全て禁止する。

- `rl_ptcg/residual_policy.py`
- `rl_ptcg/policy_value.py`
- `rl_ptcg/search_expert.py`
- `rl_ptcg/sparse_expert.py`
- `rl_ptcg/belief.py`
- `rl_ptcg/gold_prompt_ranker.py`
- `rl_ptcg/gold_prompt_policy.py`
- `rl_ptcg/encoding.py` を runtime feature encoder として使うこと
- reward、trajectory、checkpoint、replay action label
- Torch、NumPy 等を使う learned inference
- `meta_agents/alakazam_gold_bootstrap_nohistory_seed0` などの learned hybrid
- `analysis_outputs/.../seeded_engine` を提出物へ同梱すること

## 確認した残存影響

### 1. 「ruleinline」という名前だけでは純ルールを保証しない

`submission_archaludon_gtmidguard_lucariobev_crustledeckguard_archattach_ruleinline_20260710/main.py`
には `RL mirror attach` という RL 由来の補正が残る。モデルファイルがなくても
方策ロジックが RL 由来であれば不採用とする。

### 2. seeded-RL は版によって埋め込み方が違う

v1〜v3 は residual code と JSON weight を読み、v4〜v5 は runtime と weight を
`main.py` へ埋め込む。ファイル名・拡張子だけの検査では検出できない。

### 3. generic tool の既定 engine は exact anchor ではない

`tools/ptcg_common.py` の既定値は `submission_archaludon` を指す。
このディレクトリには変更済み wrapper がある。さらに一度 import 済みの `cg` は、
後から `sys.path` を変えても module cache から置換されない。

対策は、評価 subprocess ごとに engine path を明示し、開始直後に tree/hash receipt を
出力することである。

### 4. exact baseline の fallback は完全決定論的ではない

正常経路は得点と option index で決定論的だが、最外周例外時に `random.sample` を使う。
基準自体は変更しない。新規候補では、legal option の再検証後、
`win > prevent_loss > attack > end_turn > lowest_index` の固定順で fail-closed する。

### 5. deck path が CWD に影響される

exact baseline は CWD の `deck.csv` を先に見る。候補は `__file__` から解決し、
60 個の整数 ID、hash、engine validation を満たさなければ起動を失敗させる。

### 6. cross-game mutable state

baseline の一部 global は deck selection 時に reset される。候補では public observation
から毎回 state を再構築し、ゲームをまたぐ学習・belief・履歴依存を持たせない。

## 分離案

確認後の候補配置は
`isolated_rule_agents/rocket_mewtwo_spidops_v1/` とする。候補は以下を満たす。

1. baseline、既存 agent、`rl_ptcg/` を変更しない。
2. 実行時 import allowlist を標準ライブラリと候補内 `cg` に限定する。
3. `ObservationNormalizer` 以降の各層は public observation だけを入力にする。
4. 全ルールに evidence、test、reason code を付ける。
5. tie-break と fallback は固定順で、乱数を使わない。
6. package scan で `rl_ptcg`、model、weight、checkpoint、Torch/NumPy、
   residual/search/belief/replay import を拒否する。
7. candidate の `cg` hash が許可された runtime と一致することを検証する。

## 既存基準へ影響を与えずに修正する方法

今回の事前段階では agent code を作らない。カードプール問題が解消し、
ユーザー確認を得た後に、新規ディレクトリだけへ段階的に実装する。
Historical-Silver の nondeterministic fallback や deck path の問題は、
候補側の adapter でだけ修正する。既存 baseline の「改善」を名目にした直接編集は禁止する。

## 検査

`canonical_actions/public_state/encoding/residual` の既存 focused test は 23/23 pass した。
これは機構が再現可能であることの確認にすぎず、RL 部品の採用許可ではない。

実装開始時には、package 禁止物 scan、import graph、乱数利用 scan、engine hash、
baseline hash、合法手範囲、同一入力同一出力を CI gate にする。
