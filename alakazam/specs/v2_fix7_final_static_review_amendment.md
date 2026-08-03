# v2 fix7 final static-review amendment

## 目的

fix7は、単一仮説
`V2_H1_UNIQUE_BENCH_ALAKAZAM_ATTACH_THEN_KO`を変更せず、
fix6の再監査で残った3件の安全境界だけを修正する。

仮説、適用条件、比較schedule、機構完全性閾値、採否閾値は
`v2_fix5_unique_bench_alakazam_attach_then_ko_contract.md`から変更しない。

## 修正前

- source:
  `alakazam_staged_20260729/versions/alakazam_newdeck_v2_continuity_fix6_h1_unique_attach`
- policy closure:
  `B7F7F65851B18EFCEE75299B2D115D3718968D654D15DF46C4AED14BC66E717F`
- planner:
  `4D2A9F1F16EDB3F1CF505E8996D9FE8C16B4C743BCF7F2329792C189EE097B05`

fix6の140試合smokeはbattle-runner上は完了したが、その後の静的再監査で
契約不適合が見つかった。

出力は
`metrics/smoke_v2_fix6_h1_unique_attach_seed202608550_rejected_static_review`
へ隔離し、正式比較へ使用しない。

## fix7で閉じる3件

1. post-attach attack delegateが
   `v1.UnrecoverableObservationFault`を送出しても、active V2 transactionを
   clearし、policy stateをrollbackし、不可逆fault traceを残す。
2. attach、Telepath child、attackのduplicate callbackでは、hashとlogsだけ
   でなく、各stageの完全certificateを再実行する。
3. KO完了callbackは、global `V2_TRANSACTION`をclearしてからfix5 v1へ
   1回だけ委譲する。

既に `_abort` がtransactionをclearした後の
`UnrecoverableObservationFault`は二重処理しない。

duplicateの意味的な順序変更はstable keyと完全certificateで受理する。

`select.deck=None`から空listへの変更、Telepath childへの余分なdeck card、
その他のstage certificate不一致は不可逆faultとする。

完了delegateが例外を送出した場合は、local transaction proofを使って
policy rollbackとfault traceを行う。

## 凍結identity

- source:
  `alakazam_staged_20260729/versions/alakazam_newdeck_v2_continuity_fix7_h1_unique_attach`
- policy closure file count: `34`
- policy closure:
  `D61C5A342020141BA0C558908070C83F27B714197B8A9E1E81AC2ADB9C576BEA`
- planner:
  `E414CE7705E804025D549297157B0F48C30F5F5E6FF98373A7F2FDCC890ADA85`
- added fixture:
  `test_v2_fix7_final_review.py`
- fixture:
  `F21EFA6335F272BE85AB7FF58A9796500BF3F877D78F1C9F6FB14E967981084C`
- deck:
  `F598F5E578D0440C96DC0492EAECF2E19739B7A23225BE57114A724EF7D0FB94`

fix6との差はplannerの変更とfixtureの追加だけである。

## 検証

seeded engineを`PYTHONPATH`へ設定したPython 3.11.6で、rootが
fix7 directoryの`test*.py`を全探索した。

- tests: `187/187 PASS`
- changed files: planner 1、fixture 1
- compile: PASS
- deck: 60行、fix6とbyte-identical

fixtureはBasic/Telepath固有例外、3種類のduplicateのexact・reorder・mutation、
完了delegate入口でのglobal owner消去、成功時exactly-once、
例外時rollback/faultを含む。

この結果は静的・fixture上の安全証明であり、実対戦における発火完全性、
勝率、連続攻撃改善を証明しない。

