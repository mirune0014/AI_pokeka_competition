# 最終fixed760 root再計算

Date: 2026-08-03 JST

## 凍結入力

- spec:
  `autonomous_gold_20260715/evaluation_specs/archaludon_historical_silver_single_resolver_salvage_v1/fixed760_spec.json`
- spec SHA-256:
  `49B89DDAEDF6745A7ADD203602DA457BDDE912B2B7F4F18FAA3C2955780BC75D`
- Historical-Silver `main.py`:
  `F4B578453C9D953BE94885144DD50E05DBA4510DF3340BE27ADE07495896046E`
- candidate `main.py`:
  `D966E455E5110F9D5616195AEAAC8663E6A92F310DAFC4B7F79E4D37149A9C62`
- shared deck:
  `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`
- raw tree SHA-256:
  `F3B7393D88DFC4026404AC5D8AC32AD629739A2C0960E642C5634859E7853168`

## 実行・schedule確認

- physical paired rows: 760。
- unique `(panel, opponent, seat, seed)`: 760。
- missing / extra / duplicate keys: `0 / 0 / 0`。
- manifest: 48行、全exit 0。
- baseline A / baseline B / candidate summary: 各760行。
- baseline A/B summary・decision count・byte trace: `760/760`一致。
- start fault、action error、exception evidence、max-step: すべて0。
- `result == scheduled seat`から再計算したwin flagとCSVの不一致: 0。

physical CSVには`panel`列がない。checked runnerがpanelごとに別directoryへ
出力するため、そのdirectory名を構造上のpanel値として結合した。この補完で
specの760キーと完全一致する。これは数値やscheduleの曖昧性ではないが、literal
CSV schemaとしては独立監査に記録した。

## 結果

| Scope | Games | Silver | Candidate | G/R/T | Delta |
| --- | ---: | ---: | ---: | ---: | ---: |
| 全体 | 760 | 478 | 480 | 4/2/754 | +2 |
| Silver mirror | 200 | 100 | 100 | 0/0/200 | 0 |
| 隣接population | 560 | 378 | 380 | 4/2/554 | +2 |
| seat 0 | 380 | 243 | 245 | 2/0/378 | +2 |
| seat 1 | 380 | 235 | 235 | 2/2/376 | 0 |

Opponent別は次のとおり。

| Opponent | Silver | Candidate | Delta |
| --- | ---: | ---: | ---: |
| arch_peak | 39/80 | 39/80 | 0 |
| arch_shumpei | 40/80 | 39/80 | -1 |
| alakazam_capbloo_gold | 62/80 | 62/80 | 0 |
| marnie_kazuki_live | 68/80 | 68/80 | 0 |
| mega_lucario_public | 74/80 | 74/80 | 0 |
| kang_crustle | 28/80 | 31/80 | +3 |
| cynthia_v23 | 67/80 | 67/80 | 0 |

paired 95% CIは`[-0.3697,+0.8960] pp`、seed-cluster感度CIは
`[-0.2691,+0.7954] pp`、exact McNemarは`p=0.6875`。`+2`は強化の
統計的証明ではない。

## 全first-difference分類

baselineとcandidateでbyte traceが異なる145キーをrootが全件走査した。

- Rule 1 exactly-one Duraludon setup: 128。
- Rule 4 pre-Lillie exact materialization: 14。
- Rule 5 direct exact current win: 3。
- 未分類: 0。

勝敗discordantは6キー。

| Opponent / seat / game / seed | Direction | First rule |
| --- | --- | --- |
| kang / 0 / 12 / 271958325 | gain | Rule 4 |
| kang / 0 / 26 / 271958339 | gain | Rule 1 |
| kang / 1 / 20 / 271958333 | gain | Rule 4 |
| kang / 1 / 32 / 271958345 | gain | Rule 1 |
| arch_shumpei / 1 / 32 / 271958345 | regression | Rule 1 |
| kang / 1 / 0 / 271958313 | regression | Rule 1 |

Rule 5の3差分はすべて同じ勝利を早い確定攻撃へ変換し、勝敗discordantでは
なかった。Rule 4は勝敗discordantで`2 gain / 0 regression`。Rule 1は
`2 gain / 2 regression`。

## Gate再計算

- candidate `480 >= 478`: PASS。
- gains `4 >= 2` regressions: PASS。
- 各席の悪化上限2: PASS（`+2`, `0`）。
- mirror `100 >= 98`: PASS。
- 各隣接相手の悪化上限5: PASS（worst `-1`）。
- execution/duplicate gates: PASS。
- base retention gate before qualitative judgment: **PASS**。
- strengthened `candidate >= 486`: **FAIL**。
- strengthened両席非悪化: PASS。
- strengthened conjunction: **FAIL**。

## 独立監査との照合

独立Sol-Ultra数値監査
`autonomous_gold_20260715/numerical_audits/archaludon_historical_silver_single_resolver_salvage_v1/INDEPENDENT_FIXED760_AUDIT.md`
（SHA-256
`556D3408315D614D5279EA64970AFA1A9793133761F6DF66DCC4B0CDAFFF4000`）
は、760キー、全勝数、G/R/T、全席・相手bucket、fault、duplicate、CI、base
PASS、strengthened FAILについてroot再計算と一致した。

数値上の結論は「Historical-Silverを壊していない」である。「強化した」とは
判定しない。最終採否は6 discordantの定性監査を含むSol-Ultra最終判定に委ねる。
