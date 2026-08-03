# v2 fix7 H1 unique attach smoke immutable specification

## 凍結identity

- candidate source:
  `alakazam_staged_20260729/versions/alakazam_newdeck_v2_continuity_fix7_h1_unique_attach`
- candidate closure:
  `D61C5A342020141BA0C558908070C83F27B714197B8A9E1E81AC2ADB9C576BEA`
- candidate planner:
  `E414CE7705E804025D549297157B0F48C30F5F5E6FF98373A7F2FDCC890ADA85`
- adapter:
  `alakazam_staged_20260729/eval_adapters/alakazam_newdeck_v2_continuity_fix7_h1_unique_attach`
- adapter `main.py`:
  `426F1BBB71583A691CBF39A07FA8A042CB0AB0600EB43F22F9E4DBD247E5AAEC`
- deck:
  `F598F5E578D0440C96DC0492EAECF2E19739B7A23225BE57114A724EF7D0FB94`
- engine:
  `analysis_outputs/cynthia_v9_vs_v11_poffin_role_selection_20260713/seeded_engine`
- engine tree:
  `466638706BD5C6915E25D1B3CB9E3D966390FBC263F4ED3153108E29C0194FFF`
- runner:
  `tools/run_alakazam_staged_metric_suite.py`
- runner:
  `BCC98229B23C86FC5EB248D3F1E254337008FF4E85BD85224B3B3D6F570F1EEA`
- Python:
  `.venv-rl/Scripts/python.exe`, `3.11.6`

## 相手とschedule

相手は、Marnie、Cynthia、Alakazam mirror、Rocket Mewtwo／Spidops proxy、
Kangaskhan／Crustle、Historical-Silver、direct frozenの7種とする。

- version: `v2`
- seed base: `202608560`
- games per opponent / seat: `10`
- seats: `0`, `1`
- max steps: `1000`
- watchdog: `120 seconds`
- total: `140 games`
- output:
  `alakazam_staged_20260729/metrics/smoke_v2_fix7_h1_unique_attach_seed202608560`

## hard gate

次の値をすべてrootがraw sidecarとrunner ledgerから再計算する。

- block: `14/14 complete`
- games: `140`
- callback start/end差: `0`
- child exit、timeout、partial、stderr: `0`
- action error、invalid winner、max-step: `0`
- structural invalid、exception: `0`
- generic fallback、first-legal fallback: `0`
- irreversible abort、transaction abort、sequence fault: `0`
- pending transaction: `0`
- defer callback上のV2 selected rule: `0`

1件でも非0なら同一seed比較へ進まない。

smokeの発火数は診断値であり、機構完全性の正式閾値は
7対面・50 seed・両seatの700試合で判定する。

