## Material Passport

- Origin Skill: experiment-agent
- Origin Mode: run
- Origin Date: 2026-08-01
- Verification Status: ROOT_VERIFIED
- Version Label: exp_result_v1

# PPO epoch一括比較結果

個別試合・個別局面・行動確率の追加解析は行っていない。

## 条件集計

| 条件 | 試合 | 総勝率 | baselineとのpaired差 | 平均ターン | 行動エラー | 最大手数到達 | 重大異常行動率 |
|---|---:|---:|---:|---:|---:|---:|---:|
| iteration004 | 320 | 81.56% | 0.00% | 12.363 | 0 | 0 | 0.00% |
| 4 epoch | 960 | 81.56% | 0.00% | 12.363 | 0 | 0 | 0.00% |
| 12 epoch | 960 | 81.56% | 0.00% | 12.363 | 0 | 0 | 0.00% |
| 24 epoch | 960 | 81.56% | 0.00% | 12.363 | 0 | 0 | 0.00% |

## 学習seed別checkpoint

| checkpoint | epoch | 学習seed | 総勝率 | paired差 | 平均ターン | 行動エラー | 最大手数到達 | 重大異常行動率 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| e04_r1 | 4 | 731201100 | 81.56% | 0.00% | 12.363 | 0 | 0 | 0.00% |
| e04_r2 | 4 | 731201200 | 81.56% | 0.00% | 12.363 | 0 | 0 | 0.00% |
| e04_r3 | 4 | 731201300 | 81.56% | 0.00% | 12.363 | 0 | 0 | 0.00% |
| e12_r1 | 12 | 731201100 | 81.56% | 0.00% | 12.363 | 0 | 0 | 0.00% |
| e12_r2 | 12 | 731201200 | 81.56% | 0.00% | 12.363 | 0 | 0 | 0.00% |
| e12_r3 | 12 | 731201300 | 81.56% | 0.00% | 12.363 | 0 | 0 | 0.00% |
| e24_r1 | 24 | 731201100 | 81.56% | 0.00% | 12.363 | 0 | 0 | 0.00% |
| e24_r2 | 24 | 731201200 | 81.56% | 0.00% | 12.363 | 0 | 0 | 0.00% |
| e24_r3 | 24 | 731201300 | 81.56% | 0.00% | 12.363 | 0 | 0 | 0.00% |

## 相手別勝率

| 条件 | 相手 | 試合 | 勝率 |
|---|---|---:|---:|
| iteration004 | alakazam_public | 40 | 82.50% |
| iteration004 | alakazam_rmy_live | 40 | 90.00% |
| iteration004 | dragapult_live | 40 | 85.00% |
| iteration004 | historical_silver | 40 | 57.50% |
| iteration004 | marnie_kazuki_live | 40 | 85.00% |
| iteration004 | mega_lucario_public | 40 | 97.50% |
| iteration004 | ogerpon_cornerstone_public | 40 | 67.50% |
| iteration004 | starmie_public | 40 | 87.50% |
| 4 epoch | alakazam_public | 120 | 82.50% |
| 4 epoch | alakazam_rmy_live | 120 | 90.00% |
| 4 epoch | dragapult_live | 120 | 85.00% |
| 4 epoch | historical_silver | 120 | 57.50% |
| 4 epoch | marnie_kazuki_live | 120 | 85.00% |
| 4 epoch | mega_lucario_public | 120 | 97.50% |
| 4 epoch | ogerpon_cornerstone_public | 120 | 67.50% |
| 4 epoch | starmie_public | 120 | 87.50% |
| 12 epoch | alakazam_public | 120 | 82.50% |
| 12 epoch | alakazam_rmy_live | 120 | 90.00% |
| 12 epoch | dragapult_live | 120 | 85.00% |
| 12 epoch | historical_silver | 120 | 57.50% |
| 12 epoch | marnie_kazuki_live | 120 | 85.00% |
| 12 epoch | mega_lucario_public | 120 | 97.50% |
| 12 epoch | ogerpon_cornerstone_public | 120 | 67.50% |
| 12 epoch | starmie_public | 120 | 87.50% |
| 24 epoch | alakazam_public | 120 | 82.50% |
| 24 epoch | alakazam_rmy_live | 120 | 90.00% |
| 24 epoch | dragapult_live | 120 | 85.00% |
| 24 epoch | historical_silver | 120 | 57.50% |
| 24 epoch | marnie_kazuki_live | 120 | 85.00% |
| 24 epoch | mega_lucario_public | 120 | 97.50% |
| 24 epoch | ogerpon_cornerstone_public | 120 | 67.50% |
| 24 epoch | starmie_public | 120 | 87.50% |

## 席順別勝率

| 条件 | 席順 | 試合 | 勝率 |
|---|---:|---:|---:|
| iteration004 | 0 | 160 | 82.50% |
| iteration004 | 1 | 160 | 80.62% |
| 4 epoch | 0 | 480 | 82.50% |
| 4 epoch | 1 | 480 | 80.62% |
| 12 epoch | 0 | 480 | 82.50% |
| 12 epoch | 1 | 480 | 80.62% |
| 24 epoch | 0 | 480 | 82.50% |
| 24 epoch | 1 | 480 | 80.62% |
