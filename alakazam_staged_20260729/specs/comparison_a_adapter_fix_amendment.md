# 比較Aの評価adapter修正と全パネル再実行

## 結論

比較Aの初回分割実行は、`202608500_direct_frozen`だけが同じ位置で3回停止したため、事前契約どおり全体をBLOCKEDとした。

停止原因はv0方策ではなく、複数のstaged Alakazam adapterを同じPython processで、2試合以上連続してロードしたときの`sys.path`順序であった。

評価adapterだけを修正し、方策source、deck、opponent、seed、seat、max steps、checked runnerは変更せず、全35パネルを新しい出力先へ最初から再実行する。

## 保存した失敗証拠

初回分割実行のledgerは`alakazam_staged_20260729/evaluations/comparison_a_panels/execution_ledger.jsonl`である。

ledgerのSHA-256は`26FB9ED56D5D2BD03B17D04B22D92F9EA6A494A54D8E30098AC71FD44489F76F`である。

seed base `202608500`の通常6対面は、attempt 1で各20 paired rows、6 manifest rows、duplicate mismatch 0、`report.valid=true`となった。

`202608500_direct_frozen`はattempt 1から3まで同じcandidate childでexit code `1`となり、各attemptは10 paired rows、3 manifest rows、`report.valid=false`で停止した。

この部分結果は比較Aの勝率へ使用しない。

## 再現した例外

v0をseat 0、凍結版をseat 1として、seed base `202608500`を2試合連続で実行すると、1試合目は完了し、2試合目のagent loadで次の例外となった。

```text
AttributeError: module '_cumulative_parent' has no attribute 'V0_GENERIC_HOLD'
```

tracebackは`alakazam_staged_20260729/diagnostics/direct_frozen_seed500_batch2/console.txt`へ保存した。

同ファイルのSHA-256は`9CD19E67AD7F7FB76453C24FBECBBD57D5284BA29D8A0FC2B70D57D9D77F469C`である。

1試合目の終了時、凍結版adapterが凍結版source directoryを`sys.path`先頭へ残していた。

2試合目にv0 adapterは既存のv0 pathを先頭へ移動せず、凍結版の`_cumulative_parent.py`をv0 sourceから参照した。

したがって、これはゲーム間のmodule path分離不全であり、v0のカード処理や選択actionが起こした例外ではない。

## adapterの修正

両adapterは、ロードのたびに自分のtarget pathを`sys.path`先頭へ移動する。

両adapterは、方策callbackの間だけ自分のtarget pathとworking directoryを有効にし、callback後に直前の状態へ戻す。

方策module、関数引数、返却action、deck、reason、transaction stateは変更しない。

| adapter | 修正後SHA-256 |
| --- | --- |
| `eval_adapters/alakazam_800_frozen/main.py` | `B99DE98C53E777332B5F21036E1F634A2BBD9FD1BD22C3049F9467A953F1E8A2` |
| `eval_adapters/alakazam_newdeck_v0_port/main.py` | `C38C357D28CB4E8401815220E385B5542B385B7AB2984719E30DBAF9503CC2AC` |

修正後、同じ2試合を同じseedで再実行し、両方がexit code `0`、action error `0`、max-step hit `false`で完了した。

修正後summaryのSHA-256は`B83530A228F4608CA19EF6E1EAF0A257799D209B963E0DAD94F22432ADA6721D`である。

修正後consoleのSHA-256は`0FD553FBA46DEDE66603E5DCAC2BC2CE9A0A81290EF3116F713F93589C6F1057`である。

## 再実行契約

新しい出力rootは`alakazam_staged_20260729/evaluations/comparison_a_panels_adapterfix_v2`とする。

対象は5 seed basesと7 opponentsの直積35パネルである。

各パネルは同じchecked `tools/run_seeded_paired_suite.py`を使い、games per seat `10`、両seat、max steps `1000`で実行する。

各パネルは20 paired rows、6 manifest rows、`report.valid=true`、duplicate mismatch `0`を満たす必要がある。

失敗時は同一commandを最大3 attemptまで再実行し、すべてのattemptを保存する。

各パネルの最初のvalid attemptだけを採用する。

全35パネルがvalidでなければ、比較Aは再びBLOCKEDとする。

旧出力rootの6 valid panelsも再利用しない。

新しい35パネルだけから700 paired rowsを組み立て、旧失敗結果や診断smokeを勝率へ混入させない。

## 不変条件

凍結版とv0のpolicy closure hashは変更しない。

比較Aのopponent path、opponent hash、seed、seat、games、max stepsは、`comparison_a_immutable_spec.md`から変更しない。

勝率の正本はchecked runnerのraw paired rowsであり、adapter診断の単独試合は構造検証にだけ使う。
