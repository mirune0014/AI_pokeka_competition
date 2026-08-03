# v2 fix5 H1 unique-attach smoke specification

## Purpose

This specification freezes a fresh 140-game structural and transaction smoke for
`V2_H1_UNIQUE_BENCH_ALAKAZAM_ATTACH_THEN_KO`.

The smoke is a prerequisite safety check.

It is not Comparison C and its rows may not be pooled into any strength result.

## Frozen identity

- repository HEAD:
  `54f09edb2b3f6dd2def7c2c49efde16dfeda97c9`
- branch:
  `codex/alakazam-staged-development`
- contract SHA-256:
  `9C49DD7F551ED0E093DCC0952224F458113CFB45913272BC85939E046745A244`
- v1 closure SHA-256:
  `5FFA8776CA95E16C7030C55B5682DE42BA21C06964C790A3D6312B60FBAA5009`
- candidate source:
  `alakazam_staged_20260729/versions/alakazam_newdeck_v2_continuity_fix5_h1_unique_attach`
- candidate closure SHA-256:
  `816BC9CE5ECF1A11A40C481EF04E7CF4A7FA685B901E3EC3347D288823A3BB55`
- candidate `main.py` SHA-256:
  `D3293798774D6B47425B1F4A537507E541B44B241B5E49D83B164686D0B120B9`
- candidate v2 planner SHA-256:
  `52F721BA11ABBE6303A476FDE0250EDF086A20E1361839C630D1865AA6178524`
- candidate deck SHA-256:
  `F598F5E578D0440C96DC0492EAECF2E19739B7A23225BE57114A724EF7D0FB94`
- candidate adapter `main.py` SHA-256:
  `426F1BBB71583A691CBF39A07FA8A042CB0AB0600EB43F22F9E4DBD247E5AAEC`
- candidate tests:
  `166/166`

## Runtime

- Python:
  `C:/Users/amuam/project/AI_pokeka_competition/.venv-rl/Scripts/python.exe`
- Python version:
  `3.11.6`
- engine:
  `analysis_outputs/cynthia_v9_vs_v11_poffin_role_selection_20260713/seeded_engine`
- engine tree SHA-256:
  `466638706BD5C6915E25D1B3CB9E3D966390FBC263F4ED3153108E29C0194FFF`
- runner:
  `tools/run_alakazam_staged_metric_suite.py`
- runner SHA-256:
  `BCC98229B23C86FC5EB248D3F1E254337008FF4E85BD85224B3B3D6F570F1EEA`

## Opponents

- `marnie=meta_agents/marnie_sota_live_85033057_simple`
- `cynthia=meta_agents/cynthia_garchomp_nasuo445_v80_legal_complete_role_cycle`
- `alakazam_mirror=meta_agents/alakazam_oselcoun_live_85035844_simple`
- `rocket_mewtwo_spidops_proxy=meta_agents/rocket_mewtwo_spidops_kashiwashira_20260703_simple`
- `kangaskhan_crustle=meta_agents/kangaskhan_crustle_mpgaming_v13_backupkang_two_growline`
- `historical_silver=analysis_outputs/reference_agents/historical_silver_archaludon_54495224`
- `direct_frozen=alakazam_staged_20260729/eval_adapters/alakazam_800_frozen`

Rocket is a Mewtwo/Spidops proxy and is not the exact public Mewtwo/Ariados list.

## Schedule

- version:
  `v2=alakazam_staged_20260729/eval_adapters/alakazam_newdeck_v2_continuity_fix5_h1_unique_attach`
- seed base:
  `202608550`
- seeds:
  `202608550..202608559`
- seats:
  `0, 1`
- games per block:
  `10`
- opponents:
  `7`
- expected games:
  `140`
- expected blocks:
  `14`
- max steps:
  `1000`
- watchdog seconds:
  `120`
- output:
  `alakazam_staged_20260729/metrics/smoke_v2_fix5_h1_unique_attach_seed202608550`

## Hard gate

- 14 unique completed blocks
- 140 completed games
- exit code nonzero 0
- timeout 0
- partial block 0
- invalid winner 0
- action error 0
- max-step hit 0
- exception 0
- structurally invalid callback 0
- candidate generic fallback 0
- first-legal fallback 0
- v2 fault-abort 0
- irreversible abort fault 0
- pending transaction 0
- transaction stage counts internally consistent

Any failure blocks the aligned 50-seed safety panel and Comparison C.
