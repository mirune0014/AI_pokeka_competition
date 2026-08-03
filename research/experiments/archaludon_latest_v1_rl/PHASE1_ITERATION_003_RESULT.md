# Phase 1 iteration 003 結果

## 結論

単一スレッド実行契約と証跡検証基盤は採用した。
一方、今回の収集データはPPO学習に使用しない。

全32局の確率的方策は12勝20敗で、開始条件の19勝に届かなかった。
同じ相手・席・seedの決定論的latest-v1は27勝であり、対応比較は改善0、悪化15、変化なし17だった。
したがって、PPO checkpointは作成していない。

## 実行範囲

- 対戦相手: 8種
- 席: 両席
- seed: `731200401`、`731200402`
- 保持局: 32
- A/B duplicate auditを含むnative実行: 64
- 実行時間: 56.967秒
- GPU: 不使用
- サブPC: 不使用

大量CPU対戦への移行条件には達していない。

## 実行・証跡の判定

実行面のゲートはすべて通過した。

- model failure: 0
- model timeout: 0
- action error: 0
- max-step hit: 0
- exception: 0
- duplicate mismatch: 0
- protected decisionのPPO混入・方策逸脱: 0
- ゼロ残差時のteacher argmax逸脱: 0
- 最終manifest: complete

最終manifestは
`analysis_outputs/archaludon_latest_v1_rl_phase1_iteration_003_margin3_single_thread_20260731/rollouts/run_manifest.json`
で、SHA-256は
`60CEE4928E50A12D26636A86B6784896D3345E09A84D0FE345568C522944A588`
である。

rollout snapshotのSHA-256は
`19973E5D16F788958633E859596018882DA779806AC3BAC56129D9E214DA678D`
である。

## 数値結果

- 勝敗: 12勝20敗0分
- 勝率: 37.5%
- 勝率Wilson 95%区間: 22.93%〜54.75%
- PPO対象行: 834
- teacherと異なるサンプル行: 193
- 逸脱率: 23.14%
- 逸脱率Wilson 95%区間: 20.41%〜26.12%
- 席0: 5勝11敗、逸脱率24.30%
- 席1: 7勝9敗、逸脱率22.27%
- 決定論的latest-v1: 27勝5敗
- 対応勝敗差: `-15`

全相手・両席で探索自体は発生したが、強さの下限だけが不合格だった。
今回の検証はteacher margin 3と無温度の逐次categorical samplingを組み合わせて評価したため、margin 3単独の失敗とは断定しない。
観測された15件の悪化と改善0件は、1局中に積み重なる方策逸脱が主因である可能性と整合するが、これは因果確定ではない。

root再計算は
`analysis_outputs/archaludon_latest_v1_rl_phase1_iteration_003_margin3_single_thread_20260731/root_verification.json`
に保存した。
SHA-256は
`A2CF69A9278D81A4CBE16D3B63D94ED7989D97AE09C545A7F64F5F1607678BDE`
である。

Sol Ultraによる独立再計算は
`analysis_outputs/archaludon_latest_v1_rl_phase1_iteration_003_margin3_single_thread_20260731/evaluation/SOL_ULTRA_EVALUATION.md`
に保存した。
root再計算との数値不一致はない。

## 採用した実装

次の実行・証跡基盤だけをactive treeへ統合した。

- Torch import前の環境検証
- Torch intra-op / inter-opの1スレッド固定と観測値検証
- 同一process内600回の推論preflight
- 構造化されたfailure / timeout記録
- runtime receipt、dataset、episode、A/B audit、trainer間の推移的hash拘束
- 完了manifestだけを受理するvalidator

active treeの単体テストは74件すべて成功し、今回manifestのno-game validatorも成功した。
収集データとPPO方策は採用していない。

## 次の一手

次反復では、次の全行動サポート付き温度方策を1案だけ実装候補とする。

```text
z_i  = log(w_i) + 2 * tanh(clamp(r_i, -3, 3))
mu_i = 0.98 * softmax(z / 0.65)_i + 0.02 / K
```

teacherの重みを `exp(3)`、それ以外を `1` とする。
保護局面は従来どおりlatest-v1をそのまま実行する。

834行を使ったゲームなしの校正では、予測逸脱率は全体6.53%だった。
全16相手・席セルは5.33%〜7.36%に収まり、実データで観測した2〜21択の全行動は許容残差の範囲で一意argmaxになれることを確認した。
校正結果は
`analysis_outputs/archaludon_latest_v1_rl_phase1_iteration_003_margin3_single_thread_20260731/temperature_065_offline_calibration.json`
に保存した。

次反復の固定計画は
`specs/phase1_iteration_004_temperature_sharpened_behavior_plan.json`
である。
実装とテスト後に同じ32キーを1回だけ評価し、19勝未満、席ごとの対照比悪化が4超、いずれかの相手に0勝、または整合性違反があればPPOを開始せず終了する。
