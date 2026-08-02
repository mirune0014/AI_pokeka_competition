# Rule 2 固定160戦 root再計算

## Identity

- fixed160 spec: `7EF9D7F5074EC6ADD7DE04A78D2B521792B5DDD9E3815A00E0394B4DEA642036`
- baseline Rule 1: `153D8461FB66927DB9731CBE614B71FF5398B8EAE8980AE0BB4D46ADD0E8792A`
- Rule 2 trial: `D2BC5FCC82A5A507B7C5CC9FEDAAC4ED6EA0BE1622EBE99EFC74B6E6A926FC62`
- raw tree: `8D3C52ADF49F2D36DCE2E3D50033E75306C981B7915443DE413FB598024F1F29`

## Root recomputation

- rows / unique keys: 160 / 160
- baseline wins: 100
- candidate wins: 100
- paired gains / regressions / ties: 0 / 0 / 160
- seat 0: 47 / 47
- seat 1: 53 / 53
- Historical-Silver: 20 / 20
- Arch Peak: 20 / 20
- Alakazam: 29 / 29
- Marnie: 31 / 31
- duplicate-control trace mismatches: 0 / 160
- baseline/candidate trace differences: 0 / 160
- start/action/max-step faults: 0

## Dormancy decision

Replay shadow 4,262 callbacksと固定160戦の双方でRule 2 first differenceは0。したがって自然発火は0である。

要件の「自然発火が一度もない規則は条件を広げず、実装記録を残すが最終候補に統合しない」を適用する。独立監査が同じ事実を確認した場合、Rule 2 trialは`DEFER-DORMANT`とし、受理親はRule 1のまま維持する。
