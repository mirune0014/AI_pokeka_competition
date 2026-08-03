# v2 fix8 active-owner final amendment

## 変更理由

fix7は、発火前のowner判定とduplicate certificateを修正したが、
active V2 transactionのcallback冒頭ではcurrent-stateのduplicate ownerを
完全には検査していなかった。

fix8は仮説・発火条件・優先順位を変更せず、active callbackのowner gateだけを
初期発火前と同じ完全述語へ統一する。

## 凍結identity

- source:
  `alakazam_staged_20260729/versions/alakazam_newdeck_v2_continuity_fix8_h1_unique_attach`
- policy closure file count: `34`
- policy closure:
  `AB4F6FD57911BAE1D5CF9FAE2013298FC1744E401E52C65855BAB127A638FD57`
- planner:
  `12266E3311F878F99C6C6924274B22288912889E3F51B4B62DBDA8A1D35DB724`
- added fixture:
  `test_v2_fix8_active_owner_gate.py`
- fixture:
  `9B81CAE27051DD57CAE0CA1BAA8F2F0FC0F03F817728B68E6B138E61FC1DC93D`
- deck:
  `F598F5E578D0440C96DC0492EAECF2E19739B7A23225BE57114A724EF7D0FB94`

fix7との差はplannerの1箇所変更とfixture 1ファイルの追加だけである。

## 完全owner gate

active V2 callbackでは、duplicate replayまたはstage処理より前に次を検査する。

- v1 transaction
- core transaction
- parent latch owner
- current snapshot hashと一致するv1 duplicate cache
- current snapshot hashと一致するcore duplicate cache
- v1 trace ownerまたはfault/filter/terminal/duplicate tag
- current decision signatureと一致するparent generic duplicate
- current raw signature、transaction identity、stage、parent stateと一致する
  parent exact-prize duplicate

いずれかがactiveなら、
`NEW_V1_OWNER_DURING_V2`の不可逆faultとしてtransactionをclearする。

別hashまたは別rawの古いduplicate recordはblockしない。

## 検証

- root full tests: `192/192 PASS`
- changed files: planner 1、fixture 1
- compile: PASS
- deck: 60行、fix7とbyte-identical
- independent static review: `PASS`
- newly confirmed P1/P2: `0`

静的PASSはruntime発火・完了・強さを証明しない。

