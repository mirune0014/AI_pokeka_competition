# V2.1 実装・診断報告

## 変更範囲

- 受理済み Historical-Silver parent と deck は変更していない。
- 実験側だけに、`T1`--`T13` の一次 action transformation、複数付与可能な
  `C_*` public context tags、callback-indexを含む決定的 discovery/holdout/reserve
  split を追加した。
- calibration済みrootはmanifestのfamily keyで除外する。
- world bankは count-consistency と formal public-zone contract を分離し、
  必須zone/serial/logが無い診断worldを formal multiworld として扱わない。
- root-family集計、root-world集計、transformation別集計、固定seed bootstrap、
  機械的 gate report を追加した。
- T7用の `collect_energy_target_roots.py` は public MAIN callback、未attach、
  同一Energy serialの異なるin-play target 2つ、という条件だけを収集する。

## 固定親

- parent main SHA-256: `506E1A75062EE22BEE550C303C74D44A141EF6F8A6AD0DB6AEADBD9211085CB6`
- parent deck SHA-256: `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`
- `accepted_parent_unchanged: true`

## 機械検証

- `py_compile`: PASS
- V2.1 unit tests: 4/4 PASS
- public root extraction: discovery 32 / holdout 16 / reserve 8、全requested数を満たした。
- calibration除外family: 98
- fresh manifest SHA-256（全rows）: `09E3664EDFC5154DCE36A188318C85A937A8E8E017FEC17F085A16FB452745CD`
- fixed discovery run: 32 roots × 4 diagnostic worlds、root-world 128、branch 524
- ROOT_VALID: 128/128、action errors 0、invalid forced actions 0、world count failures 0
- formal world: 0/128（public zone mirrorが無いため fail-closed。診断worldの結果をformal evidenceに昇格していない）
- holdout: 未実行。候補ruleを同じholdoutで調整しないため、hypothesis contractと独立candidateの後に一度だけ実行する。

## Discoveryの診断値（採用判断ではない）

- world-row gains/regressions: 6/20
- root-family gains/regressions: 1/1、net 0
- transformation別では `T1_ATTACK_TO_DEVELOP` が 0/1、
  `T6_ATTACK_TO_DRAW` が 0/19、`T13_OTHER` が 6/0（いずれもworld-row）。
- root-level bootstrap（seed 0、2000 draws）のnet 5%点/中央値/95%点:
  `-2 / 0 / +2`
- opponent familyはmanifestに無いため、hypothesis eligibilityはfalse。
- 以上から、現時点でrule実装・採用・Kaggle提出は行っていない。

## T7 Energy target

- on-policy fresh 100 replay scan: eligible roots 197、distinct games 99、skipped 0。
- status: `ELIGIBLE_FOR_T7_DISCOVERY`
- roots SHA-256: `D783878C4652A4B1376A5DEDA0DD999C27840DB8536E3C0C33715F49AAA646C5`
- report SHA-256: `2305D07E413D5DF3D80D8BB2D39622F3995D274E559E5D3868F0D00E8B4D4104`
- 固定760 traceは既存保存物がthrowaway traceのみで、T7の全MAIN callback抽出には使えない。
  そのため fixed760 trace-preserving rerunは未実施として明記し、on-policy件数を固定760の代用にはしていない。

## 禁止事項の確認

この変更では、親agent/deck/final、RL、学習、Gold action模倣、replay-derived opponent
policy、holdout tuning、Kaggle package/submissionを行っていない。次の判断は、GPT PROが
fixed760 trace再実行を要求するか、また発見済みのどのtransformationをhypothesis contract
にするかを指定した後に進める。
