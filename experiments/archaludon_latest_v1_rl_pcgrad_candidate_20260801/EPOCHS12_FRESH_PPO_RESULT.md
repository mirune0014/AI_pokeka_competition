# Fresh PPO 12 epoch更新結果

## 結論

fresh 32試合に対するepoch数だけを4から12へ増やした。64個の未使用matched keyで、
最新v1開始点は49勝15敗、12 epoch直前は50勝14敗、12 epoch後は51勝13敗だった。
paired差は開始点比で2改善・0悪化、直前比で1改善・0悪化である。

事前に固定した「両anchorに対するpositive net、runtime正常、duplicate一致、
Historical Silver非悪化」という継続gateは機械的には通過した。したがって、次の
fresh PPO更新にも12 epochを使うことは支持する。ただし直前比は1試合だけで、argmax
変更も0である。これは学習継続の根拠であり、checkpoint昇格やKaggle提出の根拠ではない。

現在のRL学習継続checkpointは
`27B57A8CE0A9A7862651732C850294E5ED48930563994CF3DE1320A40F7D0302`
とする。最新v1 zero-residual開始点と更新直前checkpointは巻き戻しanchorとして残す。

## 学習

- 入力checkpoint: `D376294BFB405224185828A6BAB1EAE8D17D57972B0A55CE922A700D10AAB5D4`
- fresh rollout seed: `731200705`, `731200706`
- rollout: 32試合、22勝10敗、PPO対象748行、正常終了32/32、エラー0
- rollout manifest: `AF9B1D29B873A9DB09EB5111F310927E077A5DC4EC3C972738814ED4A3C6BC7B`
- dataset: `41559FF57AB24F3CE7C8859F3470753D6990E52B6BDD94F357B95770AF8D0AFC`
- 変更した設定: `epochs=12`のみ
- 維持した設定: learning rate `3e-4`、clip `0.2`、value係数`0.5`、
  entropy係数`0.01`、anchor KL、teacher margin、相手population

最終epochのratio範囲は`0.915903–1.162099`で、PPO clip範囲`0.8–1.2`内だった。
anchor KLは`2.128180e-4`でtarget `0.02`の約1/94、early stopとrollbackは0である。
4 epoch更新より方策を強く動かしつつ、既存の安全条件内に収まった。

## seed 760/761 panel

| arm | checkpoint | 勝敗 | seat 0 | seat 1 | clean / errors / max-step |
|---|---:|---:|---:|---:|---:|
| zero | `24D8A4EA…FB04` | 22勝10敗 | 12勝4敗 | 10勝6敗 | 32 / 0 / 0 |
| pre | `D376294B…B5D4` | 23勝9敗 | 13勝3敗 | 10勝6敗 | 32 / 0 / 0 |
| post | `27B57A8C…D0302` | 24勝8敗 | 13勝3敗 | 11勝5敗 | 32 / 0 / 0 |

zero→postは2改善・0悪化、pre→postは1改善・0悪化だった。pre→postの改善は
`marnie_kazuki_live / seat 1 / seed 731200761`である。postのduplicate controlは
32 key、1,907 decisionの勝敗、decision数、エンコード済みstate/action/effect、mask、
action order、最終行動、最終確率、next-state hashが完全一致した。

### 方策変化

| 比較 | aligned PPO行 | 平均TV | 中央TV | 最大TV | argmax変更 | sampled action変更 | trace変更 |
|---|---:|---:|---:|---:|---:|---:|---:|
| zero→post | 791 | 0.003106 | 0.002555 | 0.020364 | 0 | 6 | 6/32 |
| pre→post | 773 | 0.002060 | 0.001664 | 0.014110 | 0 | 7 | 7/32 |

4 epochを2巡した前回比較はpre→postの平均TVが`0.001021`、sampled action変更1件
だった。12 epochは実行方策を以前より明確に動かしたが、teacherを上回るargmaxはまだ
生じていない。

## seed 750/751 confirmation

既存のzeroと`D376…`のログを再利用し、新しいpostだけ32試合追加した。三者とも
27勝5敗で、paired勝敗変化は0だった。postのduplicateも完全一致し、runtime異常は0で
ある。このpanelでは改善を再現しなかったが、悪化も再現しなかった。

## 64 matched keyの合算

| arm | 全体 | seat 0 | seat 1 | Historical Silver |
|---|---:|---:|---:|---:|
| zero | 49勝15敗 | 27勝5敗 | 22勝10敗 | 3勝5敗 |
| pre | 50勝14敗 | 28勝4敗 | 22勝10敗 | 3勝5敗 |
| post | 51勝13敗 | 28勝4敗 | 23勝9敗 | 3勝5敗 |

postの上積みはseat 1とMarnie bucketにある。一方、主要anchorであるHistorical Silverは
3勝5敗で三者同一であり、改善していない。直前比`+1/64 = +1.5625` percentage point、
開始点比`+2/64 = +3.125` pointに留まるため、統計的に確立した強化とは扱わない。

独立監査の保守的なpaired 95%区間は、直前比で`[-6.60, +9.56]` point、開始点比で
`[-6.35, +12.10]` pointだった。exact McNemar p値はそれぞれ`1.0`と`0.5`で、どちらも
0を十分に含む。64 key全体のpre→postでは1,547 aligned PPO確率ベクトルが変化し、
平均TV `0.002093`、最大TV `0.014110`、sampled action変更8件、trace変更8/64、
argmax変更0だった。

## 改善したMarnie戦の診断

preとpostはdecision 46まで同じだった。最初の分岐はturn 7、decision 47で、同じ
公開盤面と8選択肢から次をsampleした箇所である。

- pre: option 3、手札のブリジュラスexをベンチのジュラルドンへ進化
- post: option 4、スパイクタウンジムの能力を使用
- rule teacher: option 5、相手activeへの攻撃（確率はpre `0.922906`、post `0.929573`）

両方とも約1%のfull-support探索行動で、postでも能力使用の絶対確率は
`0.011102`から`0.010406`へ下がっている。したがって、この1勝を「能力使用が強いと
学習した」証拠にはできない。固定乱数`0.0416167`が、分布変化後に別のCDF区間へ入った
sampling-boundary crossingである。

post側のスパイクタウンジム能力は対象となるマリィのポケモンが自分のdeckにないため、
盤面や手札を増やさずdeckをshuffleしただけで、その後は両方とも攻撃した。ただしpreは
基本鋼Energyがdiscardに0枚の時点で先に進化したため、後のアッセンブルアロイで加速
できなかった。postはretreatで鋼Energyがdiscardへ落ちたturn 9まで進化を遅らせ、
アッセンブルアロイで2枚、続いてかえんエールで3枚を供給し、終盤に3体の3-Energy
ブリジュラスexを形成した。preはready 2体、1-Energy 1体、未進化1体だった。

この攻撃継続差は勝利へ寄与した可能性があるが、postの行動確率は上がっておらず、無効
能力によるshuffleで後続drawも変わっている。単一リプレイでは「進化を遅らせる方策を
RLが学んだ」とは結論しない。

## 判断

- `epochs=4`の盲目的反復: 停止
- `epochs=12`でfresh batchを継続: 採用
- `27B57…`を強いagentとして昇格: 不採用
- RL全体: 継続

次は別seedのfresh 32試合を1バッチ収集して、同じ12 epochをもう一度だけ適用する。
他の係数やteacher marginは同時に変えない。その後の評価では、64 keyのpaired netだけで
なくHistorical Silverの非悪化と、複数の独立した勝敗改善または意味のあるargmax変化を
要求する。これが出なければepoch数をさらに増やさず、actor/critic共有表現かteacher
marginを一項目ずつ見直す。

## 独立数値監査

Sol Ultraの再計算は、両panelの全hash/receipt、schedule、candidate-relative勝敗、
duplicate control、paired差、subgroup、方策TVを独立に検証し、手元集計と一致した。
判定は「事前に固定した継続gateは機械的PASS。ただし効果は1件・2件のfavorable flipに
依存し、区間は0を含み、Historical Silverも弱いのでCAUTION」である。

- seed 760比較仕様: `FBFE990E1B4C2EB3FD2179B2F674B7EF9E032B117EF46D1AC075BE49488D1E54`
- seed 750確認仕様: `7557CB0CB1630080A8610E0FEBFB1BF987CAC314479139A9A4E8E52F7E2C401B`
- 監査計算JSON: `AA62EF8347045B95E4D407449D8F4333E02141FB6592615274480AA9816A4D1C`
- 再計算script: `6AB6621495B94556ECA5035F5AE9D6046AD2876340481A6A12F6D8633121C2DF`
- 監査report: `75B01415CA94D8D7A89D0EF574EB1D9D3CB68AAF91A87DBAC19FE286831A9C2F`
