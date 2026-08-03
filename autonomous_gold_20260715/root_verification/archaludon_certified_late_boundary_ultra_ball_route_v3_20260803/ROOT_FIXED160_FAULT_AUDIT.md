# Rule 3 v3 固定160戦・自然発火 fault 監査

## 結論

候補 SHA-256 `8D5CE37324D1EE966799EDA1CB8628D159E498F917BBFE58510273E7D7B8C645` は、固定160戦の勝敗・機械安全性では親と同値だったが、自然発火2件のうち1件で commit 後の `IRREVERSIBLE_FAULT` を起こした。したがって、この SHA は採用・固定760戦進行ともに不可であり、戦略仮説の棄却ではなく実装 fault として同一条件で修正・再実行する。

## 凍結入力

- 親 SHA-256: `4287A616E1611F5697964D9F4065978EED1CEA72CDB48C9F63F1430D69106C35`
- 候補 SHA-256: `8D5CE37324D1EE966799EDA1CB8628D159E498F917BBFE58510273E7D7B8C645`
- Deck SHA-256: `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`
- 固定160 overlay SHA-256: `3EECFE9398D55FEBB51EE2511C3400B182944DE9366A6FC1DCF38D780DAD61D8`
- root再計算スクリプト SHA-256: `45F7E65D7329284AD5C40E0B93722770CE0BEC44A3AC4E457268A38405608857`

## root再計算

| 指標 | 親 | 候補 | 差 |
| --- | ---: | ---: | ---: |
| 全160戦 | 100 | 100 | 0 |
| seat 0（80戦） | 47 | 47 | 0 |
| seat 1（80戦） | 53 | 53 | 0 |
| Historical-Silver（40戦） | 20 | 20 | 0 |
| Arch Peak（40戦） | 20 | 20 | 0 |
| Alakazam（40戦） | 29 | 29 | 0 |
| Marnie（40戦） | 31 | 31 | 0 |

- paired gains: 0
- paired regressions: 0
- paired ties: 160
- unique schedule keys: 160/160
- manifest command rows: 24、全 exit code 0
- game summary rows: 480、not-started 0、action error 0、max-step 0
- duplicate mismatch: 0
- policy first difference: 2件、両方ともHistorical-Silver mirror、各席1件

## 自然発火1: seat 1、正常完遂

- seed: `271828188`
- turn 17、parentはArchaludon exへの進化、candidateはUltra Ballへ変更。
- route: `ACTIVE_EX_FUEL_ROUTE`
- certificate: `R3_WIN_NOW`
- Ultra Ball costはArchaludon ex serial 69とCinderace serial 72。
- 検索、Active進化、Assemble Alloyで物理Metal serial 93/112を付与し、Metal Defenderまで完遂。
- completion: `rule3_completed:metal_defender_observed`
- fault/run_failed: 0
- 勝敗は親・候補とも勝ち。

## 自然発火2: seat 0、実装 fault

- seed: `271828198`
- turn 14、parentはNight Stretcher serial 28、candidateはUltra Ball serial 23へ変更。
- route: `ACTIVE_EX_FUEL_ROUTE`
- certificate: `R3_WIN_NOW`
- Ultra Ball costはCinderace serial 11/13。検索、Active進化、能力skipまでは正常。
- productive prefixとしてNight Stretcher 2回、Duraludon配置、別のDuraludonからArchaludon ex serial 9への進化を親どおり許可。
- その別進化のAssemble Alloyは、context 43の能力選択、context 22のMetal serial 62/60選択までは通過した。
- context 21では `effectCard=Archaludon ex serial 9` と `contextCard=Metal serial 62/60` が同時に現れる。現実装はeffectとcontextCardの全カードが進化元source ref `(190,9)`と一致することを要求したため、最初のEnergy target callbackで `prefix_unowned_effect_prompt` を誤検出した。
- fault latch後、合法な親行動でcontainmentし、次の安定MAINで解放。最終的にはMetal Defenderで勝ったが、`IRREVERSIBLE_FAULT=1`、`run_failed=1` なので完遂とは数えない。

この不具合は発火条件・certificate・route理論の誤りではなく、consultationが要求した「effectful non-route evolutionのexact source-bound continuation」を物理Energy callbackまで所有できていない実装不備である。

## 修正境界

新しい独立候補で次だけを修正する。

1. context 43を正確なArchaludon ex source refへ結合する。
2. context 22で親が選んだBasic Metalの物理 `(id, serial)` 集合をownerへ保存する。
3. context 21はeffect source一致に加え、contextCardがその保存集合に含まれる場合だけ親の合法・exact target actionを通す。
4. 同一prompt再送とoption順序変更は物理refで再結合する。
5. source不一致、未選択Energy、重複/曖昧serialは従来どおりfault containmentとする。
6. route列挙、ranking、cost reservation、certificate、safe-prefix allowlist、発火条件は変更しない。

## 証拠hash

- seat0 telemetry: `F0E7B7949FDAE234097746067171497AC635085CF5CF692236FF8BDE6E494BA9`
- seat0 trace: `391F945DFCD79A2822314B9124706871177E62553DAD62E271982F6CD6033243`
- seat0 summary: `C3169C383CD586A96BC738D6975818B51627EA01E6847B5814693FB4D3844022`
- seat1 telemetry: `2D2C104EB370183D1FB4E1061C0392A8D96428EE9D5AB4652D036140B5D48326`
- seat1 trace: `87A28756150A6F8FFA954C5DBEB0DDBCC91541E79451EF7503950DDA5E94A4D8`
- seat1 summary: `80030F727C69036AE27911E0916955B3ED9DB7130E993E34F30C0E1654EFE918`
- diagnostic wrapper: `26A0E51EE4A50ACAC047A74C9543FFF570A30DA998DB6E61C7739DB7E28FB43C`

## 判断

`REJECT_CURRENT_SHA_IMPLEMENTATION_FAULT / REPAIR_AND_RERUN_IDENTICAL_SCHEDULE`
