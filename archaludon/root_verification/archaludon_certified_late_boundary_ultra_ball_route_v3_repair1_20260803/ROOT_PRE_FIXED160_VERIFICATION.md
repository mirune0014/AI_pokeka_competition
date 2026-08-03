# Rule 3 v3 repair1 固定160戦前 root 検証

## 凍結対象

- 候補: `archaludon_certified_late_boundary_ultra_ball_route_v3_repair1`
- 候補 `main.py` SHA-256: `3D95357E75E0B00CB679C1A31F6612AD1FA0EF44914E8ECA8C272CE9220027C3`
- Deck SHA-256: `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`
- 固定160戦の比較親: `archaludon_historical_silver_single_resolver_salvage_rule3_repair_v2`
- 比較親 `main.py` SHA-256: `4287A616E1611F5697964D9F4065978EED1CEA72CDB48C9F63F1430D69106C35`
- 修正元v3 SHA-256: `8D5CE37324D1EE966799EDA1CB8628D159E498F917BBFE58510273E7D7B8C645`

## 修正理由

修正元v3の固定160戦は160/160 unique key、親・候補100勝、gains/regressions 0/0、action error・max-step・duplicate mismatch 0だった。しかし自然発火2件のうちseat 0 seed `271828198`で、productive prefix中の別Archaludon ex進化が生成したAssemble AlloyのEnergy target callbackを所有できず、`prefix_unowned_effect_prompt`の`IRREVERSIBLE_FAULT`を1件記録した。

このため修正元SHAは不採用とし、発火条件・route列挙・certificate・cost ranking・safe-prefix allowlistを変えず、次の有限chainだけを修正した。

```text
Archaludon exの別進化
-> ACTIVATE context 43
-> ATTACH_TO context 22で選択Metalのphysical refを保存
-> ATTACH_FROM context 21を選択Metalごとに所有
-> 全physical receipt確認
-> MAINでcertificate再検証
```

## 差分監査

- 修正元v3とrepair1は各13 non-cache files。
- 異なるのは`main.py`だけ。
- source diff: 226 insertions / 5 deletions。
- 追加は上記有限chain、physical receipt、同一prompt再送時のsemantic-set rebindに限定。
- `agent`はtop-levelに1個、`_resolve`は1個、`_parent.agent`静的呼出しは1個、最終callableは`agent`。
- Rule 3のroute列挙、発火分類、certificate、reservation、cost ranking、Rule 1/4/5には差分なし。

## root再実行

### fixture

- 既存Rule 3 v3: `238/238 PASS`
- 修正chain: `74/74 PASS`
- 継承Rule 1/4/5: `28/28 PASS`
- compile/import: PASS
- legal deck: 60枚、Basic Metal 12枚、Hero's Cape 1枚
- candidate/implementation cache: 0

主な修正fixtureは両席、Metal 0/1/2枚、2つのtarget callback、能力NO、同一prompt再送、option順序反転、effect source不一致、未選択Metal、Energy/target serial重複を含む。

### 自然seedのexact-engine再現

| seed / seat | starts | completions | faults | run_failed | action errors |
| --- | ---: | ---: | ---: | ---: | ---: |
| 271828198 / seat 0 | 1 | 1 | 0 | 0 | 0 |
| 271828188 / seat 1 | 1 | 1 | 0 | 0 | 0 |

seat 0はAssemble Alloyの決定1回、Metal集合選択1回、physical target callback 2回を所有してから、元の`R3_WIN_NOW` Metal Defenderまで完遂した。seat 1の既存完遂も維持した。

root再現証拠:

- seat0 telemetry SHA-256: `DD9896772E1B060CEC45BFF48F1E9D98423088A108A78555EAA3FCA0CA7F6975`
- seat0 trace SHA-256: `391F945DFCD79A2822314B9124706871177E62553DAD62E271982F6CD6033243`
- seat0 summary SHA-256: `CD3B7EAC14483B44120AB3F3531E6CC7D6FF5A099C261847A88DBFA14696D7FD`
- seat1 telemetry SHA-256: `2D2C104EB370183D1FB4E1061C0392A8D96428EE9D5AB4652D036140B5D48326`
- seat1 trace SHA-256: `87A28756150A6F8FFA954C5DBEB0DDBCC91541E79451EF7503950DDA5E94A4D8`
- seat1 summary SHA-256: `92C8DBF0B20EC671FD91CD184E5A0C558A183E4602DE87EAC5FBF2F34F94A192`

### worker evidenceのroot照合

旧repair seed `610832404`、`610832554`、`610833354`も各start 1 / completion 1 / fault 0 / run_failed 0 / action error 0。これらは既存route回帰の補助証拠であり、自然頻度や強さの数値には含めない。

## 固定160戦へ進む条件

同じ比較親、同じ4対戦相手、同じseed、両席、同じchecked runnerを使用し、修正元v3の出力を上書きしない新規destinationで再実行する。

必須確認:

1. 160 unique keysと完全なschedule equality。
2. action error、start fault、max-step、duplicate mismatch 0。
3. 自然first differenceが親非Ultra -> Rule 3 Ultraであること。
4. 両席の親非Ultra transaction completion、fault/run_failed 0。
5. paired gains >= regressions、各seat/opponent cellで親から3勝以上悪化しないこと。
6. 明確に有害なfirst difference 0。

## 判断

`PASS_TO_IDENTICAL_FIXED160_RERUN`
