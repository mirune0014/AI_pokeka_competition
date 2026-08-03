# Phase 1 iteration 004 結果

## 結論

温度 `0.65` の全合法行動サポート方策による固定データセットは、別仕様で実行する保守的なPPO pilotの入力として採用する。

今回採用したのはデータセットだけである。
学習済みcheckpoint、強さの改善、実戦投入、パッケージ化、Kaggle提出は承認していない。
このiterationではPPOを実行していない。

## 実装と開始点

- teacher、prior、fallback: exact latest-v1 Archaludon
- 挙動方策:

```text
z_i  = log(w_i) + 2 * tanh(clamp(r_i, -3, 3))
mu_i = 0.98 * softmax(z_i / 0.65) + 0.02 / K
```

- teacherの重み: `exp(3)`
- その他の合法行動の重み: `1`
- 保護局面: latest-v1をそのまま実行し、サンプリングせずPPO対象外
- 挙動方策receipt SHA-256: `11049A88FB535D7496A2B3C9F7A1A48DB71FD20EFAD3EA39FD9E35CD79819F22`
- isolated candidate snapshot SHA-256: `2B4E0795439843A69ED78EA3EA1567C791271EFEFBF2E4662940CB93F2E5F1BB`
- 最終テスト: 87件すべて成功

開始checkpointは次である。

`analysis_outputs/archaludon_latest_v1_rl_phase1_iteration_004_temperature065_checkpoint_deterministic_20260731/initial_zero_temperature065.pt`

SHA-256は `24D8A4EACD9D7B699D327D3F2436F4DA21AC79433038E6FA96F9AE0E50F8FB04` である。
重みは旧ゼロ残差checkpointと同一で、対戦数とPPO stepはいずれも0である。

最初のcheckpoint変換では、`torch.save` の一時ファイル名がzip内部名へ入るため、同じpayloadでも保存先によってbyte hashが変わる問題が判明した。
その実行は失敗として保存し、対戦やPPOを開始する前に停止した。
修正後は `io.BytesIO` へ直列化してからatomic replaceし、別process・別保存先でもbyte-identicalになることを確認した。

## 固定収集

- 対戦相手: 8種
- 席: 両席
- seed: `731200401`、`731200402`
- 保持episode: 32
- A/B duplicate auditを含むnative対戦: 64
- 実行時間: 約58.6秒
- device: CPU
- Torch intra-op / inter-op thread: `1 / 1`
- GPU: 不使用
- サブPC: 不使用

大量CPU対戦へ移る通知条件である2000対戦または約1 CPU時間には達していない。

固定manifestは次である。

`analysis_outputs/archaludon_latest_v1_rl_phase1_iteration_004_temperature065_single_thread_20260731/rollouts/run_manifest.json`

- manifest SHA-256: `30BF22BE56E73E8790A40135DD78080217FFAB7598D9646887FD8742D0FCF393`
- dataset SHA-256: `3D714FC248B597ADD412B1D9B4BAD60DDF6BDEB3DFA652264D763D7A843AC41B`
- schedule SHA-256: `2DB8B8F875998C5EF52AD3456C84FF64CCB7817EBF34AB03021DFA32FA7D43FB`
- 97-file uppercase snapshot: `8093E5366749879FC732A3DAB31A923A35332F2E2BF2C24E51BCE72690B6B572`
- runnerが使用したlowercase preimage snapshot: `76F109DEED24B440CB95BD3C958E0CD35E3A732B496357768891B67A83C16943`

最後の2つは各ファイルhashの大文字・小文字規約だけが異なる。
97ファイルの内容と個別hashは同一で、両規約を再計算して期待値と一致した。

## 数値結果

- 23勝9敗0分
- 勝率: 71.875%
- 勝率Wilson 95%区間: 54.63%から84.44%
- PPO対象行: 830
- teacherと異なる探索行動: 74
- 探索逸脱率: 8.9157%
- 探索逸脱率Wilson 95%区間: 7.16%から11.05%
- seat 0: 10勝6敗、37/377行が逸脱
- seat 1: 13勝3敗、37/453行が逸脱

同じ相手・席・seedの決定論的latest-v1は27勝だった。
対応差は改善0、悪化4、不変28で、勝数差は `-4` である。
これは探索コストの観測であり、強さが改善した証拠ではない。

全相手で少なくとも1勝し、両席・全相手で探索逸脱が発生した。
最低成績は `alakazam_rmy_live` の1勝3敗で、seat 0は0勝2敗だった。
この値は診断上の注意点だが、事前固定した不合格条件ではない。

## 完全性監査

次はすべて0だった。

- model failure
- model timeout
- action error
- max-step hit
- exception
- A/B trace、勝敗、stepの不一致
- runtime receipt不一致
- behavior receipt不一致
- protected行のPPO混入
- protected行のteacher逸脱
- ゼロ残差時のneural argmaxとteacherの不一致
- zero-divergence episodeと決定論的controlの勝敗・step不一致

checked no-game manifest validatorも32 episodeを受理した。

root独立再計算は次に保存した。

- `evaluation/root_verify_collection.py`: `398C3285DDFEF22028E67EB4582BC043531AD850ECB21C6A13CBF416C3CF27BE`
- `evaluation/root_verification.json`: `3574D033403F16EAC389FF0C928AEED89D14245637982A21C044FF004320EB29`

Sol-Ultra独立再計算は次に保存した。

- `evaluation/sol_ultra_recompute.py`: `30A5B227246698131588F827F05EE5A44ECF9DD099A85A5C25C9C6FBAD4487D4`
- `evaluation/sol_ultra_evaluation.json`: `8BF7002B2728317228A40E3652DEB0166E3C6E3A4DE1A38DB92D6F7225DCF8E8`
- `evaluation/SOL_ULTRA_EVALUATION.md`: `715953B3177645DD30201F91544CDEDDDA28D7FB771AE1A09D190D669D5BCB91`

submission-criticalな数値に不一致はなかった。

## 4悪化局の診断

4局とも、ゼロ残差、`neural_shadow_action == teacher_action` の状態で、低確率探索がセットアップ行動ではなく `END` を1回だけ選んだものだった。

| 相手 | 席・seed | decision | teacher | 探索行動 | 診断 |
|---|---|---:|---|---|---|
| alakazam_public | seat 0・731200402 | 6 | ジュラルドンをPLAY | END | ベンチ0のまま初動を終了し、次のagent decision前に敗北 |
| alakazam_rmy_live | seat 0・731200402 | 6 | ジュラルドンをPLAY | END | 同じ初動形で、次のagent decision前に敗北 |
| starmie_public | seat 0・731200402 | 6 | ポケパッドをPLAY | END | ジュラルドンも合法だったがセットアップを打ち切り、次のdecision前に敗北 |
| ogerpon_cornerstone_public | seat 1・731200402 | 3 | ハイパーボールをPLAY | END | 初動が1ターン遅れ、ジュラルドンとbackup形成が遅延した可能性が高い |

最初の3局は「ベンチ0で使えるセットアップ行動があるのにターンを終える」という同じ失敗群である。
Ogerpon戦も同じ行動型だが、敗北までの因果全体はcontrol traceがないため、強い仮説に留める。

これらはルール外行動まで含めた探索が実際に機能し、悪い行動へ負の終端報酬を付けた例である。
teacher行動の模倣labelとしては扱わない。

## 最終戦略判定

判定は `ACCEPT — dataset only` である。

学習前に手書きのEND禁止、mask、行動種別penalty、失敗episodeの複製、replay固有ルールを追加しない。
それらを追加すると、今回得られた反例を消し、正しくENDすべき局面まで狭める危険がある。

検証する仮説は次である。

> ベンチ形成が不十分で合法なセットアップPLAYがある局面の早すぎるENDに負の報酬を与えると、PPOはENDの相対確率を下げる。一方、latest-v1 priorとKL制約により正しいENDは維持できる。

## 次のPPO pilot契約

次のiterationでは、別のimmutable specと専用driverを作成してから実行する。
現在のCLIはepochs以外を上書きできないため、そのまま使用しない。

- input checkpoint: `24D8A4EACD9D7B699D327D3F2436F4DA21AC79433038E6FA96F9AE0E50F8FB04`
- manifest: `30BF22BE56E73E8790A40135DD78080217FFAB7598D9646887FD8742D0FCF393`
- dataset: `3D714FC248B597ADD412B1D9B4BAD60DDF6BDEB3DFA652264D763D7A843AC41B`
- 対象: manifest順の830行のみ
- shuffle、minibatch、replay混合: なし
- epoch: 1
- optimizer step: 1
- optimizer: fresh Adam、`betas=(0.9, 0.999)`、`eps=1e-8`、`weight_decay=0`、`amsgrad=false`
- `gamma=0.99`
- `gae_lambda=0.95`
- `clip_ratio=0.10`
- `value_coef=0.50`
- `entropy_coef=0.0`
- `learning_rate=1e-4`
- `gradient_clip=0.25`
- `anchor_kl_target=5e-4`
- `anchor_kl_initial_coef=0.10`
- `anchor_kl_hard_stop=2e-3`

学習前に、4つの早すぎるEND局面と、正しくENDする対照43局面のprobe receiptを固定する。
4つの負例では、学習後にEND確率が減り、teacher/setup PLAY確率が増え、setup PLAYが一意のargmaxであり続けることを要求する。
正しいEND対照では一意のargmaxを全件維持し、正のadvantageを持つ局面を不当に弱めないことを要求する。

次の場合は同じiteration内で再試行せず、出力checkpointを棄却する。

- input hash、830行、probe、action orderの不一致
- optimizerがfreshでない、またはstep数が1でない
- 非有限のvalue、gradient、parameter
- mean anchor KLが `0.002` を超える
- いずれかのrow KLが `0.01` を超える
- いずれかのrow total variation shiftが `0.02` を超える
- protected行、checkpoint provenance、runtime smokeの違反
- 4負例または43の正しいEND対照のprobe gate違反

PPO後も、fresh seed・両席・同一scheduleのpaired評価と、root再計算、Sol-Ultra数値監査、再度の戦略判定を通すまで強さを主張しない。

## このiterationで実行していないこと

- PPO学習
- 学習済みcheckpointの作成
- 大量CPU対戦
- GPU学習
- パッケージ作成
- Kaggle Notebook、Discussion、submissionへの書き込み
