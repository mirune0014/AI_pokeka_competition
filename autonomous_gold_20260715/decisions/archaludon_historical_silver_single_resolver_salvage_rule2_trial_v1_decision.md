# Rule 2 採否決定

## Decision

`DEFER-DORMANT` — 実装記録は残すが、受理親へ統合しない。条件も広げない。

## Evidence

- 親Rule 1: `153D8461FB66927DB9731CBE614B71FF5398B8EAE8980AE0BB4D46ADD0E8792A`
- Rule 2 trial: `D2BC5FCC82A5A507B7C5CC9FEDAAC4ED6EA0BE1622EBE99EFC74B6E6A926FC62`
- focused: 9/9 PASS
- replay shadow: 4,262 callback、差分0
- fixed160: 親100、候補100、G/R/T 0/0/160
- baseline/candidate traces: 160/160 byte-identical
- 実行fault: 0
- 合計自然発火: 0

root再計算、独立Sol-Ultra数値監査、最終Sol-Ultra判定は一致した。

## Consequence

Rule 2は有害とは判定しない。ただし未発火コードを統合すると未検証分岐と複雑性だけを持ち込むため、凍結要件に従い不統合とする。

次のRule 3は、Rule 2 trialではなく受理済みRule 1を直接の親とする。
