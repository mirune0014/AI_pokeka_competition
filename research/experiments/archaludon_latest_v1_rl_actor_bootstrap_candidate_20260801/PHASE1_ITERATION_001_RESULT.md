# Phase 1 iteration 001の実行記録

## 対象

この反復は、学習済みpilot checkpointから少量のon-policy収集と1 epochのPPO更新を続けても、安全契約が維持されるかを確認するために実行しました。

勝率差の測定やcheckpointの昇格には使用しません。

固定specは `specs/phase1_iteration_001.json` です。

specのSHA-256は `F7CEC4AE038CB8E9FC2B7CBB77FDE7D1C0F39621DCAFABB5E288E035AE667DBD` です。

## 固定した入力

- behavior checkpoint：`ppo_v2_pilot_001.pt`
- behavior checkpoint SHA-256：`9C7FDD69FC5409DFE6BED401032E5890E392705EB26135307415781D1AA03204`
- 対戦相手：Historical-Silver Archaludon
- seat：`0`、`1`
- seed：`731200201`、`731200202`
- duplicate replica：各episodeにつき2
- native game：8局
- PPO epoch：1
- device：CPU

## 収集結果

収集は11.370秒で終了しました。

最終manifestは `analysis_outputs/archaludon_latest_v1_rl_phase1_iteration_001_20260731/rollouts/run_manifest.json` です。

manifestのSHA-256は `1A42B2BDBAA4B2EDB4756F9A7297C41F8692B13258915F59AC81D726413DA8F4` です。

datasetのSHA-256は `3755A767B3DFC5EE1CEF296790491355D48EE17334DF1AAEE0D153B9180F1437` です。

rootと独立監査は、schedule、collection spec、dataset、全episode receiptをraw fileから再計算し、保存値との一致を確認しました。

4 episodeはすべてclean terminalでした。

action error、max-step hit、exception、duplicate mismatch、failure ledger entryはいずれも0でした。

113 decisionsに対し、teacher callとtelemetry rowはともに113でした。

PPO対象は58行、保護対象は55行でした。

37件の行動差はすべてPPO対象のfree MAIN `rank17_exact_parent`で発生しました。

保護対象55行では、全行で `ppo_eligible == false` かつ `final_action == teacher_action` でした。

seat 1、seed `731200201`のA/B間では、4 decisionのraw observation hashが異なりました。

公開projection、合法行動identity、teacher action、final action、PPO判定、終局結果は一致しているため、現在のcanonical duplicate契約には違反しません。

## PPO更新結果

PPO更新は58行を使い、CPUで1 epochだけ実行しました。

実行時間は3.713秒でした。

出力checkpointは `analysis_outputs/archaludon_latest_v1_rl_phase1_iteration_001_20260731/ppo_phase1_iteration_001.pt` です。

checkpointのSHA-256は `44E80A6E316CF6754C6BAF812DBD40C03BA9D3281F4FF779532DE77A6D239EC2` です。

更新後anchor KLは `1.517059786237951e-06` でした。

rootの独立再計算は保存値と完全一致しました。

KL hard stopは `0.10` であり、early stopとrollbackは発生しませんでした。

modelとoptimizerの全浮動小数点値はfiniteでした。

収集した58状態では、更新前後の決定的argmaxはすべてteacher actionと一致しました。

更新前後でargmaxが変わった行は0で、最大絶対logit変化は `0.0026025772094726562` でした。

したがって、この1 epochはlogitを更新しましたが、確認対象の配置行動はまだ変更していません。

## 両席runtime smoke

学習後checkpointを環境変数から明示的に読み込み、fresh seed `731200204`で両席を実行しました。

rootの事前確認では、`ResidualActorCritic`が読み込まれ、checkpoint hash、deployment mode、timeout `0.05`が一致しました。

checked paired runnerは11.217秒で終了しました。

6 commandのexit codeはすべて0でした。

action error、max-step hit、duplicate mismatchはいずれも0で、reportは `valid: true` でした。

reportのSHA-256は `D4179F753DCD199B1A4EF3D404F038CB6B25A8CF59FE1A319ED7CD5FD7782EE2` です。

2局の勝敗一致はruntime safetyだけを確認するものであり、強さの根拠には使用しません。

## seedの扱い

seed `731200201`は、以前のzero-checkpoint構造parity検証で使用済みでした。

behavior checkpointの学習データには含まれていないため、今回のon-policy安全性確認は無効になりません。

ただし、`731200201`をfresh holdoutや独立した強さ評価には使用しません。

seed `731200202`は今回の収集前には未使用で、runtime smokeの`731200204`も実行前には未使用でした。

## 判定

Phase 1 iteration 001の安全性、来歴、KL、両席runtimeの受け入れ条件はPASSです。

この判定は、`ppo_phase1_iteration_001.pt`が最新v1より強いことを意味しません。

今回のnative gameは8局であり、サブPCへ移す規模には達していません。

2,000 native gamesまたは推定CPU時間1時間を超える計画を立てる前に、ユーザーへサブPC利用を案内します。
