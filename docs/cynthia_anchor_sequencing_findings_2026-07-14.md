# Cynthia/Garchomp アンカー訂正と Buster 順序検証

## 結論

2026-07-14 の root 監査で、Cynthia v43/v44 の一次評価に使った
Archaludon 方策が、厳密には過去に 1022.4 へ到達した提出物そのものでは
ないことを確認した。一次評価で使っていたのは、その提出物へ後から
Archaludon mirror 用の Attach residual を追加した派生方策だった。

正しい提出アーカイブを展開し、同一 seed・両 seat・60 戦で再評価した結果、
v43/v44 の勝敗、手数、paired flip は旧評価と完全に一致した。このため
v43/v44 の棄却判断は維持する。ただし、今後の主アンカーは正しい提出物へ
固定する。

## 正しい historical-Silver アンカー

- Kaggle submission: `54495224`
- archive:
  `submission_archaludon_gtmidguard_lucariobev_crustledeckguard.tar.gz`
- archive SHA256:
  `69BC01010FA2963781E6CD18CBA4773E0372127763DBB7AAF5E2081E1A156809`
- extracted `main.py` SHA256:
  `F4B578453C9D953BE94885144DD50E05DBA4510DF3340BE27ADE07495896046E`
- extracted deck SHA256:
  `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`
- raw live evidence:
  `analysis_outputs/kaggle_live/submission_54495224_crustledeckguard/monitor_54495224_20260709_230625_episodes.csv`
- raw live CSV SHA256:
  `AAA64F1C433A96EBC6185C87FC9CC478D723B41C5940080A1B0EBF195A8E4256`

この CSV の episode `85028336` は、submission `54495224` の score が
`1000.2800774209175` から `1022.4096015934665` へ更新されたことを記録して
いる。最終 score がその後下がったことと、過去に Silver 水準へ到達した
ことは分けて扱う。

## 誤って historical-Silver と呼んでいた方策

- path:
  `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_archattach_ruleinline_20260710`
- `main.py` SHA256:
  `9F4A35D7CC2365AC2A9A5B1A684E4C66618FEF08E6DD0635D75EA49AF423313D`
- deck SHA256:
  `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`

デッキは同一だが、`main.py` には Archaludon mirror の turn `<=4` または
`7..10` で、上位4つの安全候補に含まれる Attach へ score spread の
`0.03` を加える residual が追加されている。したがって、同じデッキでも
同じ方策ではない。

## 訂正後の固定60戦

Immutable spec:

`analysis_outputs/cynthia_v43_v44_historical_silver_anchor_gate_20260714/SPEC.md`

共通条件:

- baseline: Cynthia v23
- opponent: 正しい submission `54495224` の展開物
- seed base: `203177313`
- games per seat: `30`
- max steps: `1000`
- baseline A/B duplicate control 必須

Root 再計算結果:

| Candidate | Baseline | Candidate | Gains | Losses | seat 0 | seat 1 |
|---|---:|---:|---:|---:|---:|---:|
| v43 Roserade breakpoint | 9/60 | 8/60 | 0 | 1 | 4->3 | 5->5 |
| v44 pre-Buster backup Attach | 9/60 | 8/60 | 2 | 3 | 4->2 | 5->6 |

両評価とも 60 unique schedule keys、180 raw summary rows、全6 process が
exit `0`、action error `0`、max-step `0`、duplicate mismatch `0` だった。
以前の派生アンカー評価と比較すると、seat、game、seed、result、win、steps
の core fields は v43/v44 とも `0/540` mismatch だった。

## v44 から得た一般化可能な知見

v44 は、非終端の Draconic Buster KO の直前に benched Garchomp line へ
Energy を付け、その後同じ turn に Buster することを狙った。5つの勝敗反転
局面では、意図した Attach-then-Buster がすべて実行された。しかし結果は
2 gain / 3 loss で、全局とも初回攻撃後の missed attack はなかった。

したがって、ここでの支配的な問題を「次の攻撃が止まること」だけで説明
するのは誤りである。Energy の置き先変更は、次の要素を同時に変える。

- gust される価値の高い控え
- Active KO 後の賞品交換経路
- 手札・山札の後続 search 順序
- backup を今すぐ完成させる価値と、未完成の1 Energyを晒す危険
- 同じ攻撃回数でも、どの attacker がどの target を取るか

単純な「Buster 前に必ず控えへ付ける」は、攻撃継続を増やさずに経路だけを
変え、双方向の勝敗反転を生む。turn、seat、seed、特定相手IDで閾値を追加
してこの5局へ合わせることは禁止する。

## 今後の証拠手順

1. 主アンカーには必ず正しい archive/source hash と Kaggle episode evidence
   を結び付ける。
2. デッキ一致と方策一致を分け、派生方策を historical result の本人として
   扱わない。
3. 仮説選定と最終採否は Sol Ultra が raw path を直接読んで行う。
4. 具体的なルール実装と定性的リプレイ整理は Sol xhigh が行う。
5. Luna low は固定コマンド実行と raw output 保存だけを担当し、数値や因果を
   解釈しない。
6. 次候補は 9/60 から実務的に大きく改善する機序を要求し、1勝程度の差を
   方策改善とは扱わない。

