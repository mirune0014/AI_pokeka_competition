# v2 fix8 H1 unique attach smoke immutable specification

## identity

- candidate closure:
  `AB4F6FD57911BAE1D5CF9FAE2013298FC1744E401E52C65855BAB127A638FD57`
- candidate planner:
  `12266E3311F878F99C6C6924274B22288912889E3F51B4B62DBDA8A1D35DB724`
- candidate adapter:
  `alakazam_staged_20260729/eval_adapters/alakazam_newdeck_v2_continuity_fix8_h1_unique_attach`
- adapter `main.py`:
  `426F1BBB71583A691CBF39A07FA8A042CB0AB0600EB43F22F9E4DBD247E5AAEC`
- deck:
  `F598F5E578D0440C96DC0492EAECF2E19739B7A23225BE57114A724EF7D0FB94`
- engine tree:
  `466638706BD5C6915E25D1B3CB9E3D966390FBC263F4ED3153108E29C0194FFF`
- metric runner:
  `BCC98229B23C86FC5EB248D3F1E254337008FF4E85BD85224B3B3D6F570F1EEA`
- Python: `3.11.6`

## schedule

7 opponentsはMarnie、Cynthia、Alakazam mirror、Rocket proxy、
Kangaskhan／Crustle、Historical-Silver、direct frozenとする。

- seed base: `202608570`
- games per opponent / seat: `10`
- seats: `0`, `1`
- max steps: `1000`
- watchdog: `120 seconds`
- total: `140 games`
- output:
  `alakazam_staged_20260729/metrics/smoke_v2_fix8_h1_unique_attach_seed202608570`

## hard gate

- 14/14 complete blocks
- 140 games
- callback start/end差0
- exit、timeout、partial、stderr 0
- action error、max-step、invalid winner 0
- structural invalid、exception、fallback 0
- irreversible abort、sequence fault、pending transaction 0
- start/attach/attack/KOの順序違反0
- active owner conflict 0

smokeの勝率と発火数は採否根拠にしない。

