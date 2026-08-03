# 最新v1起点のResidual PPO

このディレクトリは、`submission_archaludon_general_visible_counterattack_ready_rotation_v1_20260731` を学習開始点とする、ローカル専用のPhase 0実装です。

旧RL実装のコードは参照、import、移植していません。

最新v1だけを教師、参照事前分布、保護時のフォールバックとして使います。

Historical-Silverは評価用の対照であり、教師や方策には使いません。

## 学習対象

RLが介入できるのは、次の条件をすべて満たすコールだけです。

- `SelectType.MAIN` かつ `SelectContext.MAIN`
- `minCount == maxCount == 1`
- 合法候補が2個以上
- 最新v1の最終判定が `rank17_exact_parent`
- 最新v1のルール所有者、適格ルール、retry、reset、rollback、例外、emergency、binding failureがない

条件を外れたコールでは、最新v1が返した行動をそのまま実行します。

最新v1のルールがトランザクションを所有している間も、RLは介入しません。

## 方策

全合法候補を残した参照分布に、ニューラルネットの残差を重ねます。

変換式は次のとおりです。

```text
p(a) ∝ q_latest(a) * exp(2 * tanh(clamp(r(a), -3, 3)))
```

`q_latest` は全候補に正の確率を持つため、元のルールベースが選ばなかった行動も学習できます。

状態ベクトルは104次元、行動ベクトルは102次元です。

現在のschemaは `encoder-v4`、`effect-features-v3`、`trajectory-v2`、`run-manifest-v2` です。

行動表現には意味的な行動IDと公開対象情報を含めるため、同じカードIDを異なるベンチ対象へ使う行動も区別できます。

カード効果を確定できない場合は `UNKNOWN` として記録し、合法候補から除外しません。

不明効果を推測して既知の0として扱うこともありません。

## 安全境界

教師の最終 `agent` は各コールでちょうど1回だけ呼び、その直後に累積テレメトリを全件drainします。

モデルがない場合、遅い場合、NaNを返した場合、スキーマが合わない場合、または選択が不正な場合は、同じコールで得た最新v1の行動へ戻ります。

学習時と配置時は同じ適格性判定と50msの推論上限を使います。

学習時だけ方策分布からサンプリングし、その実際の行動対数確率を保存します。

配置時は決定的argmaxを使います。

特徴抽出には公開観測だけを使います。

`search_begin_input`、相手手札の中身、サイドの中身、山札順、カードserial、engine search/clone APIは方策入力に使いません。

## 構成

- `archaludon_rl/frozen_sources.py`: 最新v1とchecked engineの固定receipt
- `teacher_adapter.py`: statefulな最新v1教師の隔離と1-call契約
- `public_state.py`: 公開情報だけの座席相対projection
- `semantic_action.py`: エンジン候補の意味的な同定
- `decision_contract.py`: 学習可能面と保護コールの境界
- `catalog.py`, `effect_features.py`: checked engine由来の静的情報と保守的な効果特徴
- `encoders.py`: 104次元状態、102次元行動の固定スキーマ
- `reference_policy.py`, `model.py`, `policy.py`: full-support residual actor-critic
- `trajectory.py`, `collector.py`: 終局単位のatomic trajectory、manifest、失敗台帳、A/B照合
- `collect_rollouts.py`: seeded checked engineによるon-policy収集
- `train_ppo.py`: 入力行再計算、GAE、PPO、anchor KL、更新後KL rollback
- `runtime_agent/`: ローカル配置用wrapperと最新v1の60枚デッキ

## 環境

PowerShellでリポジトリrootから実行します。

```powershell
$env:PYTHONPATH = (Resolve-Path experiments\archaludon_latest_v1_rl).Path
$env:PYTHONDONTWRITEBYTECODE = '1'
```

## テスト

```powershell
.venv-rl\Scripts\python.exe -B -m unittest discover -v `
  -s experiments\archaludon_latest_v1_rl\tests `
  -t experiments\archaludon_latest_v1_rl

.venv-rl\Scripts\python.exe -B -m compileall -q `
  experiments\archaludon_latest_v1_rl
```

## ゼロ残差チェックポイント

```powershell
@'
from pathlib import Path
from archaludon_rl.frozen_sources import checkpoint_source_hashes, verify_frozen_sources
from archaludon_rl.model import ResidualActorCritic, checkpoint_metadata, save_checkpoint

verify_frozen_sources()
output = Path("analysis_outputs/archaludon_latest_v1_rl/initial_zero.pt")
print(save_checkpoint(
    output,
    ResidualActorCritic(),
    checkpoint_metadata(
        source_hashes=checkpoint_source_hashes(),
        training={"stage": "zero_residual"},
    ),
))
'@ | .venv-rl\Scripts\python.exe -B -
```

## 対戦収集

収集は強さ評価ではありません。

両席、seed、engine、教師、チェックポイント、対戦相手のreceiptをrun manifestへ固定します。

収集先は空のディレクトリでなければなりません。

全episodeのatomic publish後に、相対パス、byte数、SHA-256、schedule、dataset SHA-256を含む最終manifestをcommit markerとして保存します。

`--duplicate-audit` を付けると、同じseedと同じ方策乱数でA/Bを再実行し、正規化した意思決定列が一致した局だけを公開します。

```powershell
.venv-rl\Scripts\python.exe -B -m archaludon_rl.collect_rollouts `
  --checkpoint analysis_outputs\archaludon_latest_v1_rl\initial_zero.pt `
  --opponent analysis_outputs\reference_agents\historical_silver_archaludon_54495224 `
  --output-dir analysis_outputs\archaludon_latest_v1_rl\rollouts_001 `
  --run-id rollouts_001 `
  --seed-base 731300000 `
  --episodes-per-seat 8 `
  --seat both `
  --max-steps 1000 `
  --timeout-seconds 0.05 `
  --duplicate-audit
```

## PPO更新

trainerは、保存値を信用せず、入力チェックポイントから残差、value、参照分布、最終分布、選択log probabilityを再計算します。

trainerは `--manifest` を唯一のdataset入口にします。

source、engine、checkpoint、schedule、episodeの完全ファイル集合、byte数、SHA-256、encoder、terminal遷移が一致しないdatasetは受理しません。

```powershell
.venv-rl\Scripts\python.exe -B -m archaludon_rl.train_ppo `
  --input-checkpoint analysis_outputs\archaludon_latest_v1_rl\initial_zero.pt `
  --manifest analysis_outputs\archaludon_latest_v1_rl\rollouts_001\run_manifest.json `
  --output-checkpoint analysis_outputs\archaludon_latest_v1_rl\ppo_001.pt `
  --epochs 4
```

## ローカル配置

```powershell
$env:ARCHALUDON_RL_CHECKPOINT = `
  (Resolve-Path analysis_outputs\archaludon_latest_v1_rl\ppo_001.pt).Path
```

この環境変数を設定しない場合、`runtime_agent` は最新v1と同じ行動を返します。

強さ比較には引き続き `tools/run_seeded_paired_suite.py` を使い、同一seed・両席で最新v1および対照集団と比較します。

## 現在の範囲

Phase 0は、収集とPPO更新を安全に開始できる土台までを対象とします。

小規模pilotの勝敗は強さの証拠ではありません。

リーグ構成、十分な試合数による評価、昇格判定、Kaggle用package、upload、submissionはこの実装には含めていません。

検証済みのreceiptとpilot結果は `IMPLEMENTATION_VERIFICATION.md` に記録しています。
