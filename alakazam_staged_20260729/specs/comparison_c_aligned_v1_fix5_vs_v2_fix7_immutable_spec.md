# Comparison C aligned v1 fix5 vs v2 fix7 immutable specification

## 目的

同じdeck、opponent、seed、seatで、fix5 v1と単一continuity仮説fix7 v2を
比較する。

このscheduleは比較A・Bと同じ`202608500..202608549`を使い、
全version同一seedの診断要件を満たす。

未使用seedのholdoutを実行する場合も、本結果とpoolしない。

## baseline

- source:
  `alakazam_staged_20260729/versions/alakazam_newdeck_v1_package_runtime_certified_fix5`
- closure:
  `5FFA8776CA95E16C7030C55B5682DE42BA21C06964C790A3D6312B60FBAA5009`
- planner:
  `80A9B0F88A04591D4174B21AFCC5C9019A4EFCEC02E8F9C2D1576DCFC0FC044B`
- adapter:
  `alakazam_staged_20260729/eval_adapters/alakazam_newdeck_v1_package_runtime_certified_fix5`
- adapter `main.py`:
  `426F1BBB71583A691CBF39A07FA8A042CB0AB0600EB43F22F9E4DBD247E5AAEC`

## candidate

- source:
  `alakazam_staged_20260729/versions/alakazam_newdeck_v2_continuity_fix7_h1_unique_attach`
- closure:
  `D61C5A342020141BA0C558908070C83F27B714197B8A9E1E81AC2ADB9C576BEA`
- planner:
  `E414CE7705E804025D549297157B0F48C30F5F5E6FF98373A7F2FDCC890ADA85`
- adapter:
  `alakazam_staged_20260729/eval_adapters/alakazam_newdeck_v2_continuity_fix7_h1_unique_attach`
- adapter `main.py`:
  `426F1BBB71583A691CBF39A07FA8A042CB0AB0600EB43F22F9E4DBD247E5AAEC`

両版のdeck SHA-256は
`F598F5E578D0440C96DC0492EAECF2E19739B7A23225BE57114A724EF7D0FB94`
であり、normalized hashは
`4414e8995e50c7a00d4b6aa7d9229f63c1dff5261643ec7cd86c4e329113ed69`
である。

## engineとchecked tools

- engine:
  `analysis_outputs/cynthia_v9_vs_v11_poffin_role_selection_20260713/seeded_engine`
- engine tree:
  `466638706BD5C6915E25D1B3CB9E3D966390FBC263F4ED3153108E29C0194FFF`
- paired runner:
  `tools/run_seeded_paired_suite.py`
- paired runner SHA-256:
  `5EC25C98F2777FF61DE2DBD0A03A08519A7FEA4B2B4C510B5B8895BC2000E000`
- battle runner:
  `tools/run_local_battle.py`
- battle runner SHA-256:
  `E1ABA0151CDAEE425B858511AA760CE5C5647D555DDEFBD69D7319C29C5B773B`
- combiner:
  `tools/combine_staged_panel_results.py`
- combiner SHA-256:
  `CABFB6ECB500EF1395B05EDB5A9775193B8A13578E3EDF35C0CED04214175C77`
- metric runner:
  `tools/run_alakazam_staged_metric_suite.py`
- metric runner SHA-256:
  `BCC98229B23C86FC5EB248D3F1E254337008FF4E85BD85224B3B3D6F570F1EEA`
- Python:
  `.venv-rl/Scripts/python.exe`, `3.11.6`

## opponents

- `marnie`
- `cynthia`
- `alakazam_mirror`
- `rocket_mewtwo_spidops_proxy`
- `kangaskhan_crustle`
- `historical_silver`
- `direct_frozen`

相手pathはfix7 smoke specと同一である。

RocketはMewtwo／Spidops proxyであり、完全一致Mewtwo ex／Ariadosとは呼ばない。

## schedule

- seed bases:
  `202608500`, `202608510`, `202608520`, `202608530`, `202608540`
- games per opponent / seed base / seat: `10`
- seats: `0`, `1`
- max steps: `1000`
- paired rows: `700`
- manifest rows: `210`
- child summaries: `2,100`
- expected paired semantic schedule SHA-256:
  `619BA954971C33FDC698810A58DF1E2C0786FFF16B6A0CCD2715DC33B04FD076`
- expected manifest semantic schedule SHA-256:
  `9277E7463E1372FCE8095BD86A79FA35EC616177034CBEA7894BCBC5419AAAB3`

fresh outputs:

- panels:
  `alakazam_staged_20260729/evaluations/comparison_c_aligned_fix7_panels`
- combined:
  `alakazam_staged_20260729/evaluations/comparison_c_aligned_fix7_combined`
- v2 formal metrics:
  `alakazam_staged_20260729/metrics/formal_v2_fix7_aligned_7opp_50seed`
- v2 formal summary:
  `alakazam_staged_20260729/metrics/formal_v2_fix7_aligned_7opp_50seed_summary`
- v2 transaction audit:
  `alakazam_staged_20260729/metrics/formal_v2_fix7_aligned_7opp_50seed/v2_h1_transaction_audit.json`

35個の`(seed_base, opponent)` panelを独立directoryへ出す。

各panelはbaseline A、baseline duplicate B、candidateを両seatで実行する。

失敗attemptをpoolせず、最初の`report.valid=true`だけを採用する。

## safety hard gate

- 700 unique paired keys
- baseline/candidate schedule差0
- 35 valid panels、manifest 210行
- baseline A/Bの全summary field差0
- child exit、action error、timeout、max-step、invalid winner 0
- formal v2は700 games、70 complete blocks
- callback start/end差0
- structural invalid、exception、fallback、abort、pending transaction 0
- paired candidateとformal v2のresult/steps差0

## mechanism completeness hard gate

完了transactionについて、次をすべて満たす。

- total `>= 20`
- 両seatで1件以上
- 3 opponents以上
- 3 seed bases以上
- Historical-Silverで1件以上
- start = attach verified = attack dispatched = KO resolved
- fault、abort、pending、owner conflict 0

満たさない場合は仮説の機構完全性不足としてv2を棄却し、
未使用seed holdoutへ進まずfix5 v1を保持する。

## 診断

mechanism gateを通る場合でも、このaligned結果だけでv2を採用しない。

overall、matchup、seat、seed-base、gain/loss、exact sign testに加え、
first attack、attack gap、post-KO continuity、max consecutive attack、
attack hand、Powerful Hand counter、second line、fallback、安全性を報告する。

event分母が版ごとに変わる率は観測記述であり、単純差を因果効果と呼ばない。

