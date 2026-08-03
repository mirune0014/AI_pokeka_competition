# Fresh PPO追加学習（更新4・5）結果

## 結論

新規32試合から4 epoch更新する処理を2巡追加したが、未使用seedの
matched比較では追加学習前後とも27勝5敗で、勝敗が変わった対戦は0件だった。
したがって、今回の`32試合 + 4 epoch`をそのまま反復する構成には、まだ継続を
支持する性能改善の証拠がない。

一方で、32/32試合が正常終了し、行動エラーと最大手数到達は0だった。方策確率も
有限かつ小さく動いているため、RL自体を棄却する結果ではない。更新5のcheckpointは
昇格候補ではなく、次の学習実験用の巻き戻し可能なwarm startとして保持する。

次は他の係数を同時に変更せず、fresh 32試合に対する全バッチ更新回数だけを
4 epochから12 epochへ増やす。現在のKLはtargetから大きく離れており、4 epochでは
1バッチあたりAdam stepが4回しかないためである。

## 追加した学習

| 更新 | 入力checkpoint | 新規試合 | 学習行 | 学習時勝敗 | manifest | 出力checkpoint |
|---|---:|---:|---:|---:|---:|---:|
| 4 | `F8758778…0912E` | 32 | 714 | 18勝14敗 | `DEAA41C7…E1C9` | `F4474D3B…32ED` |
| 5 | `F4474D3B…32ED` | 32 | 844 | 26勝6敗 | `03E72B10…25A4` | `D376294B…B5D4` |

学習データ自身の勝敗は性能評価には使用していない。両収集とも全試合が正常終了し、
行動エラー0、最大手数到達0だった。

更新4の最終epochはanchor KL `3.370567e-5`、ratio範囲
`0.982330–1.016245`だった。更新5はanchor KL `3.425968e-5`、ratio範囲
`0.982068–1.014563`だった。いずれもearly stopとrollbackは発生していない。

## 未使用seedでのmatched比較

比較仕様は
`specs/more_training_seed750_comparison_20260801.json`に固定した。
8相手、両seat、seed `731200750`と`731200751`の32対戦を各armで実行した。

| arm | checkpoint | 勝敗 | seat 0 | seat 1 | 正常終了 | エラー / max-step |
|---|---:|---:|---:|---:|---:|---:|
| 最新v1開始点（zero residual） | `24D8A4EA…FB04` | 27勝5敗 | 15勝1敗 | 12勝4敗 | 32/32 | 0 / 0 |
| 追加学習前 | `F8758778…0912E` | 27勝5敗 | 15勝1敗 | 12勝4敗 | 32/32 | 0 / 0 |
| 追加学習後 | `D376294B…B5D4` | 27勝5敗 | 15勝1敗 | 12勝4敗 | 32/32 | 0 / 0 |

32個の`(opponent, seat, seed)` keyは完全一致した。zero→post、pre→postの
どちらも、改善0件、悪化0件、net 0だった。相手別・seat別の勝敗も三者で同一である。
McNemarの両側p値は1で、改善は確立していない。全差分が0の観測標本を再標本化した
paired bootstrap区間も0に退化するが、これは母集団での同等性を証明するものではない。
0/32件のdiscordanceに対する片側95% Clopper-Pearson上限から置いた保守的な
感度区間は`[-8.94, +8.94]` percentage pointである。

相手・seat別では`alakazam_rmy_live / seat 1`がzero、pre、postのすべてで
0勝2敗だった。2試合だけの記述的floorだが、今回の更新がこの弱点を変えていないことは
確認できる。

### 方策の変化

エンコード済みstate、action、effect、action orderが一致するPPO局面だけを比較した。

| 比較 | 対応局面 | 平均TV | 中央TV | 最大TV | argmax変更 | sampled action変更 |
|---|---:|---:|---:|---:|---:|---:|
| zero→pre | 779 | 0.0016323 | 0.0014845 | 0.0070509 | 0 | 0 |
| zero→post | 772 | 0.0013552 | 0.0011393 | 0.0058366 | 0 | 1 |
| pre→post | 772 | 0.0010213 | 0.0007882 | 0.0047973 | 0 | 1 |

pre→postで行動列が変わったのは
`starmie_public / seat 1 / seed 731200751`の1試合だけだった。decision 47で
sampled actionが`3`から`4`へ変わったが、両方とも勝利した。argmax方策は全対応局面で
変化していない。

## 再現性control

post armを同じcheckpoint、相手、seat、seedで32試合再実行した。32 key、全勝敗、
試合ごとのdecision数、1,577 decisionのエンコード済みstate/action/effect、action
order、最終行動、最終確率が完全一致した。

`raw_observation_sha256`だけは337 decisionで不一致だったが、policy入力とその出力は
byte-equivalentだった。初回の手元集計はこのrun依存hashまでalignment条件に含めたため
672局面と過少集計した。再現性controlで原因を確認後、policyが実際に読むエンコード入力
の完全一致へ修正して772局面を再集計し、独立監査値と一致した。672局面の旧集計値は
採用しない。

## 更新が弱かった理由

このtrainerはminibatchを使わず、各epochで全学習行を平均してAdamを1 stepだけ進める。
今回増えたのは合計8 stepである。PPOのclip範囲は`0.8–1.2`、anchor KL targetは
`0.02`だが、実測KLは約`3.4e-5`に留まった。安全制約に当たって更新が止まったのではなく、
方策を変える量そのものが小さい。

更新5の844行を使った手元の初期勾配再計算では、policy勾配L2は`0.020885`、係数適用後の
value勾配L2は`0.129161`だった。共有`state_encoder`に限るとpolicyは`1.979e-5`、
valueは`0.079391`で、cosineは`-0.118`だった。共有表現をcriticが強く動かす点は今後の
監視事項だが、次の実験では原因を分離するため構造・value係数・entropy係数を同時に
変更しない。

## 次の一変更

`D376294B…B5D4`から別seedのfresh 32試合を収集し、`--epochs 12`で更新する。
learning rate `3e-4`、PPO clip、value係数、entropy係数、anchor KL、teacher margin、
相手populationは維持する。更新後は未使用の同一seedで更新前後を比較する。

この実験でもKLとratioが十分小さいままargmax・行動・勝敗が動かない場合は、単純な
epoch追加を止め、actor/critic共有state encoderかteacher marginの設計を一項目ずつ
見直す。

## 独立数値監査

Sol Ultraによる独立再集計は、手元の勝敗、paired差、TV、argmax、再現性controlと
一致した。比較仕様SHA-256は
`70B2CDAE9DA8CC8F0BFFA233E9849409186F52618932F3326C4B00AED9574766`、
監査計算JSONは
`24B491AEDA148828B923ABF4E8DB72FFA0D2E160D5D93F152F9E272A16261445`、
再計算scriptは
`267942C45C111A748EEAA95281773AC5FD7BDD9D8CC1CB32E6FA7FD7F7C22E8D`である。

監査判定も「同じ`32試合 + 4 epoch`構成の継続はunsupported、ただしRLの棄却ではない」
で一致した。この比較は探索的であり、checkpoint昇格やKaggle提出の根拠には使用しない。
