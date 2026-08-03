# v2 fix6 owner / snapshot review amendment

## 目的

この文書は、単一仮説
`V2_H1_UNIQUE_BENCH_ALAKAZAM_ATTACH_THEN_KO`を変更せず、
fix5候補の独立静的レビューで見つかった所有権・重複callback・例外境界の
欠陥だけを修正したfix6を凍結する。

元の仮説・発火条件・採否閾値は
`v2_fix5_unique_bench_alakazam_attach_then_ko_contract.md`を正本とする。

## 修正前候補

- source:
  `alakazam_staged_20260729/versions/alakazam_newdeck_v2_continuity_fix5_h1_unique_attach`
- policy closure:
  `816BC9CE5ECF1A11A40C481EF04E7CF4A7FA685B901E3EC3347D288823A3BB55`
- planner:
  `52F721BA11ABBE6303A476FDE0250EDF086A20E1361839C630D1865AA6178524`

fix5の140試合smokeは静的レビュー中に停止した。

途中出力は
`metrics/smoke_v2_fix5_h1_unique_attach_seed202608550_rejected_partial_owner_review`
へ隔離し、正式比較・勝率・行動指標へ使用しない。

## 独立レビューで確認した欠陥

1. v1 call後にcurrent-stateのv1/core/parent duplicate ownerが成立しても、
   v2が横取りできた。
2. attach開始時のsnapshot hashがrollback前のstateを表し、
   同一callback再送時に保持stateと一致しなかった。
3. attack dispatch後のsnapshot hashがv1 call前のstateを表し、
   同一callback再送時に保持stateと一致しなかった。
4. Telepath Psychic Energyのempty child `[]`を返した後、
   同じchild callbackを再送する経路がなかった。
5. attack delegateがowner stateを書き込んだ後に不一致となった場合、
   未実行actionに属するv1/core/parent stateが残った。
6. post-attach処理と完了後委譲に例外境界がなく、
   pending transactionまたはtrace欠落を残し得た。

## fix6の修正境界

- source:
  `alakazam_staged_20260729/versions/alakazam_newdeck_v2_continuity_fix6_h1_unique_attach`
- policy closure file count: `34`
- policy closure:
  `B7F7F65851B18EFCEE75299B2D115D3718968D654D15DF46C4AED14BC66E717F`
- changed planner:
  `planner_v2_h1_unique_attach.py`
- planner SHA-256:
  `4D2A9F1F16EDB3F1CF505E8996D9FE8C16B4C743BCF7F2329792C189EE097B05`
- added fixture:
  `test_v2_fix6_review_findings.py`
- fixture SHA-256:
  `53D3A507F089C0CF830D49ECFE8D3B61A450A68C090C413B1F02D9366D100933`
- deck SHA-256:
  `F598F5E578D0440C96DC0492EAECF2E19739B7A23225BE57114A724EF7D0FB94`

fix5との差は上記plannerの変更とfixtureの追加だけである。

v1 planner、既存v2 fixture、deck、runtime、親方策は変更しない。

## 所有権とrollback

発火前のv1 callは1回だけである。

call前とcall後について、v1 transaction、core transaction、parent owner、
v1/core duplicate cacheを検査する。

parent duplicateは、次のcurrent-state完全一致だけをownerとする。

- `_last_decision_signature`が現在のdecision signatureと一致し、
  `_last_decision_action`が存在する。
- `_exact_prize_lane_duplicate_action`が現在のraw signatureと
  parent stateに対してactionを返す。

古いrecordが存在するだけではdeferしない。

v2が発火する場合はcall前stateへrollbackし、rollback後にsnapshotを
再計算してtransactionへ保存する。

v2が発火しない場合は、v1が返したaction objectとcall後の
v1/core/parent stateをそのまま保持する。

attack delegateのaction、owner、snapshot、Powerful Hand証明が不一致の
場合は、delegate call前stateへrollbackしてから不可逆faultとして閉じる。

成功時だけcall後stateを保持し、そのstateで再計算したsnapshot hashを
attack duplicate certificateへ保存する。

## 重複callbackと例外

- attach MAINの再送はstable option keyで同じattachへ再束縛する。
- Telepath empty childの再送は完全なchild certificateを再検証して`[]`を返す。
- attack MAINの再送はstable option keyで同じPowerful Handへ再束縛する。
- mutationされた再送は不可逆faultとして閉じる。
- post-attach helper、attack delegate、完了後delegateの例外では、
  V2 transactionをclearし、証明可能な合法fault actionと
  `irreversible_abort_fault=true`を記録する。

## 検証

seeded engineを`PYTHONPATH`へ設定したPython 3.11.6で、rootが
fix6 directoryの`test*.py`を全探索した。

- tests: `176/176 PASS`
- planner/fixture compile: PASS
- fix5との差分: planner 1件の変更、fixture 1件の追加
- deck: 60行、fix5とbyte-identical

この結果はfixture上の安全証明であり、実対戦での発火数・完了数・強さを
証明しない。

