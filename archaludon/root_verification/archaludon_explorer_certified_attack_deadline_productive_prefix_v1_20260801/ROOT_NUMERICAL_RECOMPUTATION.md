# Explorer attack deadline conservative release v1 — Root numerical recomputation

## 結論

Root は runner 集計と独立 Sol-Ultra 数値監査の文章を集計根拠として使わず、二つの `paired_results.csv`、48 manifest rows、2,280 summary rows、baseline duplicate tracesから再計算した。

Root の再計算は独立監査と一致した。

候補は fixed760 上で direct parent の勝敗を完全に維持した。

候補は45勝で同じ勝利を短く確定したが、勝敗を改善したゲームは0だった。

したがって、これは安全な挙動改善と対面floor保持の証拠であり、強度向上の証拠ではない。

## 凍結入力

- spec SHA-256: `22CBACA72FCD23D0909C205D8EF05FF3E8630998F687A2A054AAE937EC0E492F`
- direct parent SHA-256: `558EE5DB29E001428B0D59813613FABEE8E15B96E422746C104BDFAB4DC22DB6`
- candidate SHA-256: `E19A2CBF2C0F9626D8530263CB13750568F8C7B9739F4A3E9E43B9EDF4B44669`
- deck SHA-256: `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`
- historical-Silver opponent `main.py`: `F4B578453C9D953BE94885144DD50E05DBA4510DF3340BE27ADE07495896046E`
- historical-Silver opponent `deck.csv`: `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`
- historical paired CSV SHA-256: `6B2F26D9E2ACD9DCD2FE4D0B24DF99465F0473BDF912F1805247A1647AE41B63`
- adjacent paired CSV SHA-256: `8C120673577452D6906DBE0793763FECC1465AB6D42FC15028FE233E49A4F8B7`

## Schedule と実行完全性

- logical paired rows: 760
- unique `(panel, opponent, seat, seed)` keys: 760
- historical-Silver rows: 200
- adjacent population rows: 560
- manifest commands: 48
- nonzero manifest exits: 0
- summary rows: 2,280
- start failures: 0
- action errors: 0
- max-step hits: 0
- missing results: 0
- baseline duplicate semantic summaries: 760/760
- baseline duplicate byte-identical traces: 760/760

物理CSVには `panel` 列がない。

Root は immutable spec の出力partition `historical_silver` と `adjacent_population` から論理 `panel` を補った。

partitionは各CSVにつき一意であり、schedule keyに曖昧さはない。

specは historical-Silver opponent の期待hashを明示していなかった。

Root は実行後に既知の exact historical-Silver hashと一致することを確認したが、この点は実行前preflightに含まれなかったprovenance limitationとして残す。

## 勝敗再計算

| Bucket | Parent | Candidate | Gain | Regression | Tie |
|---|---:|---:|---:|---:|---:|
| All | 476/760 | 476/760 | 0 | 0 | 760 |
| Historical-Silver | 100/200 | 100/200 | 0 | 0 | 200 |
| Adjacent population | 376/560 | 376/560 | 0 | 0 | 560 |

全16個の `(panel, opponent, seat)` cellでdeltaは0だった。

| Opponent | Seat 0 parent = candidate | Seat 1 parent = candidate |
|---|---:|---:|
| historical_silver | 57/100 | 43/100 |
| arch_peak | 20/40 | 19/40 |
| arch_shumpei | 19/40 | 22/40 |
| alakazam_capbloo_gold | 32/40 | 29/40 |
| marnie_kazuki_live | 33/40 | 35/40 |
| mega_lucario_public | 37/40 | 37/40 |
| kang_crustle | 14/40 | 13/40 |
| cynthia_v23 | 32/40 | 34/40 |

最弱floorは `kang_crustle` だった。

seat 0は35.0%、seat 1は32.5%であり、この候補はその既存弱点を悪化させていないが、解決もしていない。

## 挙動差分

760ゲーム中45ゲームで `baseline_steps != candidate_steps` だった。

- candidate shorter: 45
- candidate longer: 0
- minimum step delta: -13
- maximum nonzero step delta: -1
- total step delta: -116
- activated games that both policies won: 45/45
- activated games with a result change: 0/45

独立監査は45件すべてで最初のtrace差分がtested policy自身のactionであることを確認した。

したがって、これは相手の後続差分から生じた見かけ上の短縮ではない。

ただし45件はすべて親も勝っていたため、fixed760からは勝率改善を主張できない。

## Gate 判定

| Gate | Observed | Result |
|---|---:|---|
| unique schedule keys 760 | 760 | PASS |
| duplicate semantic summaries 760 | 760 | PASS |
| duplicate byte traces 760 | 760 | PASS |
| execution faults 0 | 0 | PASS |
| start faults 0 | 0 | PASS |
| action errors 0 | 0 | PASS |
| exceptions/nonzero exits 0 | 0 | PASS |
| max-step hits 0 | 0 | PASS |
| regressing cells 0 | 0 | PASS |

## 独立監査との照合

独立監査:

- `autonomous_gold_20260715/numerical_audits/archaludon_explorer_certified_attack_deadline_productive_prefix_v1_20260801/REPORT.md`
- SHA-256: `8933C96C848B9EC0E4F14B00E648E72BE7E716FB3F3B4DAF6C46BC3E1488D454`

Root再計算と独立監査のsubmission-critical numberに不一致はなかった。

## Root の数値判定

fixed760 retention gateはPASSとする。

候補は全対面・両席でparent結果を維持し、発火時には既勝利を短く確定した。

候補を「fixed760で強くなった」とは記録しない。

最終採否は、実装目的である終局勝利の即時確定、非終局の親復帰、安全なtransaction、および未解決floorをまとめてSol-Ultra strategy judgeへ渡す。
