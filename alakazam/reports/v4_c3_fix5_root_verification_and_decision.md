# v4 C3 公開最大打点・ベンチ0回避 fix5 root検証・採否

日付: 2026-07-30

## 結論

`alakazam_newdeck_v4_public_survival_bench0_fix5` のベンチ0回避による
**行動変更は不採用**とする。

一方、`planner_public_damage_continuity.py` のpureな公開打点・攻撃継続
解析器は、C3の行動gate、transaction、outer wrapperを一切呼ばない条件で、
C4の行動非変更shadowへ限定継承する。

C4のaction parentは、採用済みC2
`alakazam_newdeck_v4_next_attacker_distance_shadow_fix4b`へ固定する。

```text
C2 closure
29084BC13CB74236ABE557B57A9E633A8F9E88FA83FF22D131C835293E987157
```

## Rootによるpaired再計算

| 項目 | 親版 | 候補 | 差 |
| --- | ---: | ---: | ---: |
| 全体 | 452/700 | 452/700 | 0 |
| Marnie | 69/100 | 69/100 | 0 |
| Cynthia | 73/100 | 73/100 | 0 |
| Alakazam mirror | 81/100 | 81/100 | 0 |
| Rocket proxy | 38/100 | 38/100 | 0 |
| Kangaskhan/Crustle | 71/100 | 71/100 | 0 |
| Historical Silver | 56/100 | 56/100 | 0 |
| Direct frozen | 64/100 | 64/100 | 0 |

gain/loss/tieは`0/0/700`。全700 schedule keyで勝敗とstepが一致した。

## 採用ゲート

| ゲート | 結果 |
| --- | --- |
| 候補勝数 `>=452/700` | PASS: 452 |
| overall paired deltaが正 | FAIL: 0 |
| Historical Silver `>=+3/100` | FAIL: 0 |
| Silver両seat非負 | PASS: 0/0 |
| Silver正block `>=2/5` | FAIL: 0/5 |
| 隣接6対面 `>=-2/600` | PASS: 0 |
| 各対面・各対面seat floor | PASS |
| paired lower-bound | PASS |
| raw完全性 | PASS |
| mechanism reach | FAIL: supported state 0 |

絶対勝数が境界値を保ったことや、悪化がなかったことは、正の改善と機構到達を
要求するゲートを代替しない。

## Metric raw検証

受理した4 suiteは合計90 block、900 game。

- complete block/game: `90/90`, `900/900`
- nonzero exit、timeout、action error、max-step、invalid result: すべて0
- `CALL_START/CALL_END`: `55,514/55,514`
- duplicate/unmatched callback: 0
- action value/type/order/object identity fault: 0
- transaction、metric/wrapper exception、structural invalid: 0
- supported threat/action origin state: 0

したがって、解析器のraw integrityはPASSだが、ベンチ0回避actionのreachは
`INSUFFICIENT_EVIDENCE`である。

## 凍結証拠

- paired raw:
  `evaluations/v4_c3_public_survival_bench0_fix5_combined_attempt1/combined_paired_results.csv`
- paired raw SHA-256:
  `50AC17BD9DABE801D22D86F84765536E2CCC58EA535F528DAF6FE43F4262B851`
- root paired audit:
  `root_independent_paired_audit.json`
- root paired audit SHA-256:
  `99D376DD46257B5A5A2BC15A1F9220EA6AE57FB0BAC7BA838D330A82015A1812`
- root metric audit:
  `root_independent_metric_audit.json`
- root metric audit SHA-256:
  `3F0AC1FB99E8A8E813CD611EB782F574039D7C3BC461B9B527DD2C46CA0F5F89`
- independent numerical audit:
  `reports/v4_c3_fix5_sol_ultra_independent_numeric_audit.md`
- independent audit SHA-256:
  `E702797781AB2ED3EBC75F16F1110CD725E8CBE444E329E3E6F6E106AC05485C`
- final strategy judgment:
  `reports/v4_c3_fix5_final_strategy_judgment.md`
- strategy judgment SHA-256:
  `0B8ADAFDC2F093A97DFDCB6EA137E5372CB618B9C94327C5B475F1A9B349435E`
- execution path/retry amendment:
  `specs/v4_c3_fix5_formal_execution_path_retry_amendment.md`
- path/retry amendment SHA-256:
  `7614294084EC942EAD38BC72E5AC4037983F81B63F12290AF61B641DA8C52428`

## C4への継承境界

継承可:

- `premium_power_pro_envelope`
- `opponent_damage_rows`
- SUPPORTEDなfloor/cap/continuity
- C2 distance/importanceの読み取り

継承禁止:

- `planner_public_survival_bench0.py`
- C3 action proposalの実行
- C3 transaction、ledger、duplicate/rebind
- C3 outer `agent`
- C3のproposed/applied actionを次の行動へ利用すること

C4は全callbackでC2 parent actionの同一objectを返す。
