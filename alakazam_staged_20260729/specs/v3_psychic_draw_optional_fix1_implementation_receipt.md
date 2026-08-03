# v3 サイコドロー任意化 fix1 実装記録

## 結果

合意した実装順序のうち、次の二項目を完了した。

1. episode `88844273` の四局面を公開観測 fixture として固定した。
2. ユンゲラー／フーディンのサイコドローを任意能力として扱う分岐を実装した。

進化後の確定 KO 優先は実装していない。step `148` の action は基準版と同じ `[7]` のままである。

## 成果物

- 候補:
  `alakazam_staged_20260729/versions/alakazam_newdeck_v3_psychic_draw_optional_fix1`
- fixture:
  `alakazam_staged_20260729/fixtures/episode_88844273_public_observations`
- 不変仕様:
  `alakazam_staged_20260729/specs/v3_psychic_draw_optional_fix1_immutable_spec.md`
- 実行環境追補:
  `alakazam_staged_20260729/specs/v3_psychic_draw_optional_fix1_execution_amendment.md`
- 最終 runner evidence:
  `alakazam_staged_20260729/evaluations/v3_psychic_draw_optional_fix1/runner_recheck_attempt_3`
- 表示名訂正後の fixture evidence:
  `alakazam_staged_20260729/evaluations/v3_psychic_draw_optional_fix1/fixture_recheck_attempt_4`

## 実装した判断

- 厳密に同定した自分のユンゲラー `742` またはフーディン `743` の `ACTIVATE` YES/NO prompt だけを対象にする。
- ユンゲラーは 2 枚、フーディンは 3 枚引くものとして、能力後に山札が 0 枚になる場合だけ、基準版の `YES` を `NO` へ変更する。
- 能力後に 1 枚以上残る場合、基準版が既に `NO` の場合、または prompt を一意に証明できない場合は基準 action を保存する。
- YES/NO option の順序には依存しない。
- v1 が所有する active／ready-bench の進化 transaction は、`NO` 後の手札・山札不変遷移を検証して攻撃判断へ接続できる。
- Psychic-readiness reservation などの継承 owner が存在しても、厳密な危険サイコドローは `NO` にできる。継承 owner と親の可変状態は保持する。
- `NO` 後の手札は集合一致ではなく serial 列の完全一致を要求する。

## 最終 identity

- frozen baseline policy closure:
  `5FFA8776CA95E16C7030C55B5682DE42BA21C06964C790A3D6312B60FBAA5009`
- frozen baseline planner:
  `80A9B0F88A04591D4174B21AFCC5C9019A4EFCEC02E8F9C2D1576DCFC0FC044B`
- candidate policy closure file count:
  `33`
- candidate policy closure:
  `7124EA621B02E58D9143149A33EAA79DB44E1AEF6D206560D17BA7146DF7D590`
- candidate planner:
  `4C6F246A256A7C6B327ECFCB81E507E0E1D9E62D8B99D28FAF444BF3AAEA1929`
- deck:
  `F598F5E578D0440C96DC0492EAECF2E19739B7A23225BE57114A724EF7D0FB94`
- replay:
  `9E749F259D90655BE4C17F1795C15D277132C02E0167310394216609B90A7EBF`

基準版、`deck.csv`、`_cumulative_parent.py`、`main.py`、`runtime/main.py` は変更していない。

## 固定 fixture

| step | 公開局面 | observation SHA-256 | 基準／候補 action |
|---:|---|---|---|
| 67 | 最初のフーディン KO 後の強制昇格 | `ADC9BA59F1FF48ED6D45C5908C372D076B09AEAF2B69D4FEEBB02BAC1F1B0D71` | `[0]` |
| 98 | ユンゲラーを含む後続選択の強制昇格 | `89A26FDA4AC9EB9D00C5A5A3C5DADA4B581D63301CC2A62B9185007B96E1EB67` | `[0]` |
| 121 | 後半の強制昇格 | `FFE554622B851635C93288FE8B6F9651177DC7BE0A42EDEED8352152B1488FA0` | `[4]` |
| 148 | エネルギー付きユンゲラーと手札フーディンがある MAIN | `CBD113C00820ABEE3A32EDAF740BB112D26CC651643AB7AC35EB7B9532B20FE3` | `[7]` |

各 fixture は replay の当該 agent observation と完全一致し、相手の手札は `None`、山札順・賞札内容などの非公開 episode 情報は含まない。

## 検証

- focused optional-draw suite:
  `9/9 OK`
- candidate full suite:
  `155/155 OK`
- fixture suite:
  `3/3 OK`
- changed Python compile:
  `OK`
- 四 fixture の基準／候補 action:
  全件完全一致
- 独立静的監査:
  P0–P2 の機能問題なし

最初の独立実行は `PYTHONPATH` 未指定により `cg` import で機械的に失敗した。この raw evidence は削除せず `runner_recheck` に保存した。環境を明示した attempt 2 は中間候補、最終候補は attempt 3、表示名訂正後の fixture は attempt 4 を正規証拠とする。

## 残る範囲

現行 v1 の所有進化ルートは、進化前に山札 4 枚以上を要求する。そのため、所有 transaction の `NO` 分岐は今回の通常対戦ではほぼ非発火であり、将来の「進化後の確定 KO 優先」で山札条件を分離するための安全基盤である。

本候補は実装・機構検証までであり、勝率改善、採用、Kaggle 提出を意味しない。
