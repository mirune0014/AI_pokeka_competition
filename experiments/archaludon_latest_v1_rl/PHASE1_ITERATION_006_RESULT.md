# Phase 1 Iteration 006 結果

## 結論

Iteration 006 の2段階actor-only更新で生成したcheckpointは `REJECT` とする。

このcheckpointはruntime smoke、対戦、継続学習、配備、Kaggle提出に使用せず、調査証跡としてのみ保持する。

開始点はIteration 004のcheckpointへ戻す。

ただし、この判定は2回更新したcheckpointの棄却であり、RL方針の棄却ではない。

上流層へ勾配が届いた後の更新は1回だけであり、対戦も実行していないため、学習量や対戦性能を判定できる実験ではない。

## 固定した入力と成果物

- 初期checkpoint: `24D8A4EACD9D7B699D327D3F2436F4DA21AC79433038E6FA96F9AE0E50F8FB04`
- manifest: `30BF22BE56E73E8790A40135DD78080217FFAB7598D9646887FD8742D0FCF393`
- dataset: `3D714FC248B597ADD412B1D9B4BAD60DDF6BDEB3DFA652264D763D7A843AC41B`
- execution spec: `5258FEEC0A418C00EE711D27A8DDA183F2D5EF4F805AAA8BC0CDF39E23B96ED3`
- prepare receipt file/self: `1DE8718F771BBBDB08712666EA1BFBFA52B34260EC76178B5D0B59C232B14B52` / `B2758162F79F6CDF892576DF963ED375FBA372F0919FE226A69510907BC3E385`
- 固定advantage: `B7F77DEBE545FDD5B7767C909E185904A52F161B6253D821950E6FDE6A79E53B`
- 固定behavior log-probability: `BF402ED36ECD78905597F562E8987927C2D74FD5AEE390F1D1E1426CE3D1DA98`
- rejected checkpoint: `C1F9B0D4CEAFD0B481F9E1C517F5B56A2490DF9AF2EEA1DD8B8E5412596FA12B`
- rejected receipt file/self: `FF97079BB4CD071A3548A830AC516FE2E30FC70CCCF09EBFC57F1605421A950B` / `9F61AC21FABF231FB3B4D5BF37BC1BB0CCFBFF0F15A5342708F91AB8D29019C0`
- `REJECTED` marker: `2AE8550E0FF1B1BABC68826FEE42CBB3C2FDE7AF3C5CB6C7D3D89CB5E28E29CD`

出力集合は `candidate.pt`、`rejected_receipt.json`、`REJECTED` の3件だけで、`ACCEPTED` は存在しない。

## 実行と独立監査

凍結した830行をmanifest順の1バッチとして、CPU 1スレッド、同一Adamで正確に2回更新した。

第1段階はゼロ初期化された `residual_head.2` のweightとbiasだけを更新した。

第2段階はactor 10 tensorを更新し、value head 4 tensorはbyte-exactに固定した。

ゲーム対戦は実行していない。

独立したSol-Ultra数値監査は、初期checkpointとraw 830行からGAE、float32正規化、同一Adamの2更新を再構成した。

全830行の固定入力、Stage 1とStage 2の全確率と価値、loss、勾配、最終model、optimizer、metadataはreceiptと最大誤差0、不一致0だった。

したがって、観測した挙動は実装や保存の不整合ではなく、今回固定した更新設計の挙動である。

## 全体ゲート

| 段階 | aligned / anti / neutral | alignment score | lower median | mean KL | max KL | max TV |
|---|---:|---:|---:|---:|---:|---:|
| Stage 1 | 432 / 389 / 9 | 0.0518072289 | 1.4305115e-6 | 1.4808520e-7 | 5.6303856e-7 | 2.2455724e-4 |
| Stage 2 | 438 / 390 / 2 | 0.0578313253 | 2.3245811e-6 | 2.1998113e-7 | 9.8715842e-7 | 4.5905448e-4 |

両段階とも全830行で一意argmaxを持ち、非有限値は0件で、KLとTVの安全ゲートを通過した。

Stage 2のalignment scoreとlower medianはStage 1から僅かに改善した。

しかし、変化量は実用的な文脈分離を示す大きさではない。

## 行動群ごとの方向

| 行動群 | 正例数 | 負例数 | Stage 2正例median | Stage 2負例median | 失敗側 |
|---|---:|---:|---:|---:|---|
| PLAY | 216 | 201 | -2.2947788e-5 | 1.6808510e-5 | 正例 |
| ATTACH | 83 | 47 | 3.2365322e-5 | -3.2365322e-5 | 負例 |
| EVOLVE | 40 | 29 | 2.0086765e-5 | -3.6358833e-5 | 負例 |
| RETREAT | 17 | 5 | -2.1615997e-5 | 6.1511993e-5 | 正例 |
| ATTACK | 99 | 34 | 1.4525652e-4 | -1.2910366e-4 | 負例 |
| END | 22 | 36 | -3.0279160e-5 | 1.7972663e-5 | 正例 |

Stage 1で失敗した6つの極性群はStage 2でも同じ向きに失敗し、絶対値がおおむね拡大した。

すなわち、PLAY、RETREAT、ENDは正負にかかわらず下がり、ATTACH、EVOLVE、ATTACKは正負にかかわらず上がる傾向だった。

## END方向ゲート

4件の明示的な負例はすべて、END確率低下、教師行動確率上昇、教師の一意argmax維持を満たした。

正のnormalized advantageを持つ正当END 20件は、20件すべてでEND確率が低下した。

その変化範囲は `-2.0116568e-4` から `-7.6293945e-6` だった。

Raw advantageが正の正当END 31件のlower medianは `-3.1590462e-5` だった。

正当END 43件の教師一意argmaxは43件すべてで維持した。

## 勾配と価値出力

Stage 2の全勾配ノルムは `0.0334388688` だった。

`residual_head.2.weight` の勾配ノルムは `0.03343869`、action encoderは約 `8.0e-5`、`residual_head.0` は約 `7.45e-5`、state encoderは約 `6.6e-7` だった。

最終出力層の更新が支配的であり、第2段階は新しい文脈差を作るよりも、第1段階で生じた行動群ごとの偏りを増幅したと解釈する。

価値MSEは `0.2677978385` から `0.2678684072` へ僅かに悪化した。

Value head自体は不変なので、これは共有state encoderの変化による価値出力ドリフトであり、critic学習ではない。

## 採否

最終失敗は27件で、receiptと独立再計算が完全一致した。

- Stage 2の行動群median失敗: 6件
- 正のnormalized advantageを持つEND増加失敗: 20件
- 正のraw advantageを持つEND lower median失敗: 1件

Parameter、optimizer、固定入力、anchor係数、value契約、checkpoint再読込、全体KLとTV、Stage 2改善ゲートは通過した。

Offline方向ゲートを通過していないため、runtime smokeと対戦は行わない。

## 次の単一仮説

Iteration 007は、最終出力層を1回だけ開通させた後に固定し、非線形な状態と行動の相互作用層だけを成熟させる。

Iteration 004から再開し、Stage 1で `residual_head.2` だけを1回更新する。

Stage 2では `residual_head.2` を固定し、`residual_head.0` だけを32回更新する。

両encoderとvalue headは固定するため、価値出力と価値MSEは初期checkpointから完全不変でなければならない。

Stage 2の更新1、2、4、8、16、32で診断を保存し、更新32だけを最終候補とする。

更新32まで安全ゲートを守って実行し、途中の方向ゲート失敗だけを理由に早期棄却しない。

この試験でも同じ行動群の極性が残る場合は、更新回数の追加を止め、公開状態と合法行動の表現が相反するadvantageを識別できるかをread-onlyで監査する。
