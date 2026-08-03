# v2 fix6 H1 unique attach smoke immutable specification

## 凍結identity

- candidate source:
  `alakazam_staged_20260729/versions/alakazam_newdeck_v2_continuity_fix6_h1_unique_attach`
- candidate policy closure:
  `B7F7F65851B18EFCEE75299B2D115D3718968D654D15DF46C4AED14BC66E717F`
- candidate planner:
  `4D2A9F1F16EDB3F1CF505E8996D9FE8C16B4C743BCF7F2329792C189EE097B05`
- evaluation adapter:
  `alakazam_staged_20260729/eval_adapters/alakazam_newdeck_v2_continuity_fix6_h1_unique_attach`
- adapter `main.py`:
  `426F1BBB71583A691CBF39A07FA8A042CB0AB0600EB43F22F9E4DBD247E5AAEC`
- deck:
  `F598F5E578D0440C96DC0492EAECF2E19739B7A23225BE57114A724EF7D0FB94`
- engine:
  `analysis_outputs/cynthia_v9_vs_v11_poffin_role_selection_20260713/seeded_engine`
- engine tree:
  `466638706BD5C6915E25D1B3CB9E3D966390FBC263F4ED3153108E29C0194FFF`
- metric runner:
  `tools/run_alakazam_staged_metric_suite.py`
- runner SHA-256:
  `BCC98229B23C86FC5EB248D3F1E254337008FF4E85BD85224B3B3D6F570F1EEA`
- Python:
  `.venv-rl/Scripts/python.exe`, `3.11.6`

## 相手

- `marnie`:
  `meta_agents/marnie_sota_live_85033057_simple`
- `cynthia`:
  `meta_agents/cynthia_garchomp_nasuo445_v80_legal_complete_role_cycle`
- `alakazam_mirror`:
  `meta_agents/alakazam_oselcoun_live_85035844_simple`
- `rocket_mewtwo_spidops_proxy`:
  `meta_agents/rocket_mewtwo_spidops_kashiwashira_20260703_simple`
- `kangaskhan_crustle`:
  `meta_agents/kangaskhan_crustle_mpgaming_v13_backupkang_two_growline`
- `historical_silver`:
  `analysis_outputs/reference_agents/historical_silver_archaludon_54495224`
- `direct_frozen`:
  `alakazam_staged_20260729/eval_adapters/alakazam_800_frozen`

RocketはMewtwo／Spidops proxyであり、公開データ上の完全一致
Mewtwo ex／Ariados deckではない。

## schedule

- version: `v2`
- seed base: `202608550`
- games per opponent / seat: `10`
- seats: `0`, `1`
- max steps: `1000`
- watchdog: `120 seconds`
- total: `7 × 2 × 10 = 140 games`
- output:
  `alakazam_staged_20260729/metrics/smoke_v2_fix6_h1_unique_attach_seed202608550`

## hard gate

次のいずれかが1件でもあれば、同一seed比較へ進まない。

- nonzero child exit
- timeout、partial block、nonempty stderr
- action error、invalid winner、max-step
- structural invalid、exception、first-legal fallback
- irreversible abort、transaction abort、pending transaction
- callback start/end不一致
- attach start/verify不一致
- attack dispatch/KO resolution不一致
- complete後のactive V2 owner
- v1/core/parent ownerを横取りした証跡

このsmokeの勝率は採否根拠に使わない。

