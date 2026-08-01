## Material Passport

- Origin Skill: experiment-agent
- Origin Mode: run
- Origin Date: 2026-08-02
- Verification Status: VERIFIED
- Version Label: exp_result_v1

# Independent Behavior Cloning actor 最小実験

3 seedのBC学習と各320試合を完了した。本結果は最終不採用として固定し、3 checkpointはいずれも将来のPPO referenceに使用しない。追加rollout・PPO・PCGrad・報酬変更・actor表現変更は実施していない。

## Offline validation

| seed | validation top-1 | cross-entropy | entropy | locked 212一致 | 非合法 | fallback |
|---:|---:|---:|---:|---:|---:|---:|
| 2026080201 | 238/347 (68.59%) | 2.4234 | 0.3923 | 137/212 | 0 | 0 |
| 2026080202 | 244/347 (70.32%) | 2.1759 | 0.4154 | 144/212 | 0 | 0 |
| 2026080203 | 232/347 (66.86%) | 2.5219 | 0.4388 | 131/212 | 0 | 0 |

seed平均はtop-1 `68.59%`、population SD `1.41%`。

| option_type（主要family） | seed1 | seed2 | seed3 | 3 seed平均 |
|---:|---:|---:|---:|---:|
| 1 | 100.00% | 100.00% | 100.00% | 100.00% |
| 3 | 70.53% | 66.32% | 69.47% | 68.77% |
| 7 | 69.05% | 70.63% | 68.25% | 69.31% |
| 8 | 48.28% | 58.62% | 51.72% | 52.87% |
| 9 | 52.63% | 47.37% | 42.11% | 47.37% |
| 13 | 67.65% | 79.41% | 64.71% | 70.59% |

## 固定320試合

| seed | 勝率 | iteration004差 | 席0 | 席1 | fallback | 行動エラー |
|---:|---:|---:|---:|---:|---:|---:|
| 2026080201 | 169/320 (52.81%) | -28.75 pp | 56.25% | 49.38% | 3254/17879 (18.20%) | 0 |
| 2026080202 | 163/320 (50.94%) | -30.63 pp | 46.88% | 55.00% | 2997/17013 (17.62%) | 0 |
| 2026080203 | 157/320 (49.06%) | -32.50 pp | 48.75% | 49.38% | 3230/17792 (18.15%) | 0 |

| 相手 | iteration004 | seed1 | seed2 | seed3 |
|---|---:|---:|---:|---:|
| alakazam_public | 82.50% | 57.50% | 67.50% | 60.00% |
| alakazam_rmy_live | 90.00% | 45.00% | 55.00% | 50.00% |
| dragapult_live | 85.00% | 75.00% | 77.50% | 60.00% |
| historical_silver | 57.50% | 15.00% | 15.00% | 10.00% |
| marnie_kazuki_live | 85.00% | 50.00% | 47.50% | 50.00% |
| mega_lucario_public | 97.50% | 75.00% | 70.00% | 67.50% |
| ogerpon_cornerstone_public | 67.50% | 42.50% | 20.00% | 37.50% |
| starmie_public | 87.50% | 62.50% | 55.00% | 57.50% |

## 判定

- validation 98%、主要family 95%、runtime fallback 0、固定320の非破綻を満たさず、3つのBC checkpointはPPO用referenceとして採用しない。この判断を最終結果として固定する。
- 確定している阻害要因はactorの行動表現不足である。live fallbackの約99%が、現actorでは表現できないoptional/multiple selection cardinalityだった。
- train top-1 98.4～98.7%とepisode-held-out validation 66.9～70.3%の差は確認されたが、この差だけでは、データ量・coverage不足、state表現不足、train/validation/deployment間の分布シフトのどれが主因かは確定しない。
- 同形式の単一選択rolloutを増やしても確定済みの表現不足は解消しない。次はstate encoderを変えず、完全合法行動候補を1候補としてscoreするaction出力方式だけを検証する。
- PPO、追加学習、追加対戦には進まない。
