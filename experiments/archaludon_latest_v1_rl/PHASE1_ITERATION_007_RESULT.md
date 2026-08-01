# Phase 1 Iteration 007 結果

## 結論

Iteration 007で生成したcheckpointは `REJECT` とする。

このcheckpointはruntime smoke、対戦、継続学習、配備、Kaggle提出に使用せず、調査証跡としてのみ保持する。

開始点はIteration 004のcheckpointを維持する。

ただし、この判定は「小規模学習で対戦性能が改善しなかった」という判定ではない。

対戦は0件であり、勝率やゲーム上の強さは測定していない。

棄却したのは、固定した830局面と固定targetに対して、凍結したencoder上の相互作用層を32回更新すれば正負の方向を分離できる、という今回のcheckpoint生成仮説である。

## 固定した入力と成果物

- 初期checkpoint: `24D8A4EACD9D7B699D327D3F2436F4DA21AC79433038E6FA96F9AE0E50F8FB04`
- manifest: `30BF22BE56E73E8790A40135DD78080217FFAB7598D9646887FD8742D0FCF393`
- dataset: `3D714FC248B597ADD412B1D9B4BAD60DDF6BDEB3DFA652264D763D7A843AC41B`
- execution spec: `9CDA1C0B8A7BF5E542C23061349505C5AC80119595060B968BD002B7D06CD1CF`
- prepare receipt file/self: `7E8F6238ECEE6444C98D041A12A2478EA6FEAD110A73AA224D071AEC5316F08F` / `B4CA02474685E13A492E82D727AC929E7DEDCD03B15047A8962BF59C71AC6AFE`
- 固定advantage: `B7F77DEBE545FDD5B7767C909E185904A52F161B6253D821950E6FDE6A79E53B`
- 固定behavior log-probability: `BF402ED36ECD78905597F562E8987927C2D74FD5AEE390F1D1E1426CE3D1DA98`
- rejected checkpoint: `5547AFD90CF039390CDA8E70E3DA5868C12B0277AA670636573F7BC0FE7715B3`
- rejected receipt file/self: `C2AF5C7BCA142296CAF1407F3FFA498A4FD2E4F71FB7C9E6B68C5D2C2AC0B796` / `07E8D544F5544779A5488C9072238317FDE238E7BCEE13EE69E9A87B2EBBFC3D`
- `REJECTED` marker: `6EC4E19250DA5B2C635327CB89FFA160FDD6A517034FB50B76B36F224A43E00E`

出力集合は `candidate.pt`、`rejected_receipt.json`、`REJECTED` の3件だけで、`ACCEPTED` は存在しない。

Iteration 006のrejected checkpointは読み込んでいない。

## 実行内容

凍結した830行をmanifest順の1バッチとして、CPU 1スレッド、同一Adamで実行した。

Stage 1では最終readoutの `residual_head.2.{weight,bias}` だけを1回更新した。

Stage 2ではreadout、両encoder、value headを固定し、相互作用層の `residual_head.0.{weight,bias}` だけを32回更新した。

Stage 2の更新1、2、4、8、16、32で完全診断を保存した。

実行時間は約54秒で、ゲーム対戦は実行していない。

## 安全性と再現性

全33更新で非有限値は0件だった。

最悪値はmean KL `1.7524377209e-7`、1行最大KL `8.6689323085e-7`、最大TV `3.1407363713e-4` で、すべて安全上限を十分下回った。

保存した全診断で830行すべてが一意argmaxを維持した。

変更されたtensorは許可した `residual_head.0` と `residual_head.2` のweight、biasだけだった。

両encoderとvalue headはbyte-exactに不変で、全830行のvalueもbyte-exactに不変だった。

保存checkpointの再読込結果は終端診断の全830行と一致した。

独立したSol-Ultra数値監査とroot再計算は、主要な行数、符号、median、安全指標、hash、保存checkpoint再生について不一致0だった。

## 方向分離の結果

| 段階 | aligned / anti / neutral | alignment score | lower median |
|---|---:|---:|---:|
| Stage 1 | 432 / 389 / 9 | 0.0518072289 | 1.4305115e-6 |
| Stage 2更新32 | 430 / 395 / 5 | 0.0421686747 | 2.1411106e-6 |

Stage 2の勾配は更新1から32まで非ゼロで、全勾配ノルムは約 `7.45e-5` から `7.41e-5` だった。

したがって、更新が停止していたわけではない。

一方、Stage 1で失敗した6群は、更新16と更新32の両方でStage 1より悪化した。

| 失敗群 | Stage 1 median | 更新16 median | 更新32 median |
|---|---:|---:|---:|
| PLAY positive | -1.13845e-5 | -1.23978e-5 | -1.37091e-5 |
| ATTACH negative | -1.56760e-5 | -1.96695e-5 | -2.37823e-5 |
| EVOLVE negative | -1.74642e-5 | -2.16961e-5 | -2.72989e-5 |
| RETREAT positive | -1.03898e-5 | -1.41235e-5 | -1.78069e-5 |
| ATTACK negative | -6.26445e-5 | -7.86185e-5 | -9.41753e-5 |
| END positive | -1.48416e-5 | -2.04444e-5 | -2.66433e-5 |

これは「あと数回だけ同じ更新を続ければ通る」という挙動ではなく、今回の固定表現と固定targetの組合せでは逆方向が強まったことを示す。

## END方向ゲート

4件の負のEND controlと43件のteacher-END argmax controlはすべて通過した。

正のnormalized advantageを持つEND 20件は、20件すべてでEND確率を増加できなかった。

正のraw advantageを持つENDのlower medianは `-2.5272369385e-5` だった。

## 採否

最終blockerは47件だった。

- 行動群方向: 6件
- 旧失敗群の中間・終端改善条件: 18件
- 全体方向: 2件
- 正のEND増加: 20件
- 正のraw END median: 1件

安全性、有限性、parameter変更範囲、value固定、保存checkpoint再生は通過した。

しかし、意図した正負の方向分離を満たさないため、このcheckpointを対戦へ進めない。

これは計算量を節約するための早期打切りではなく、事前に固定したオフライン受入条件に基づく判定である。

## この結果から言えないこと

対戦を行っていないため、Iteration 004より勝率が低いとは言えない。

830行は識別可能性を調べる固定probeであり、十分な自己対戦学習量ではない。

今回の結果だけでRL全体、別の状態表現、別のcredit assignment、追加rollout、自己対戦を棄却することはできない。

## 次の段階

同じoptimizer更新を延長する前に、830行を読み取り専用で監査する。

監査では、公開状態、合法行動集合、選択行動、encoder出力が相反するtargetを区別できるかを調べる。

あわせて、GAEとMonte Carlo returnの符号差、価値推定、過去2行動の不足、trajectory間の重み偏り、群別勾配の競合を分解する。

この監査でも学習、optimizer生成、対戦は行わない。

原因を固定した後に、表現、時間情報、credit assignment、samplingのうち一つだけを次の改善仮説として選ぶ。
