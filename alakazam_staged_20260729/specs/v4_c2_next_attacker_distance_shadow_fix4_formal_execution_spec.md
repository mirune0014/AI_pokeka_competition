# v4 C2 next-attacker-distance shadow fix4 formal execution specification

Date: 2026-07-30

## Purpose

Collect a fresh, candidate-only, fixed-700-game diagnostic suite for C2.
The run verifies raw action identity, route-class reachability, and analyzer
integrity.  It does not estimate or compare win rates.

## Frozen policy

- parent:
  `alakazam_staged_20260729/versions/alakazam_newdeck_v3_exact_evolution_ko_fix2`
- parent closure:
  `DC90205DE06AE3E2E41ADC661577096BB02EE5B42AB9F4366FC1A01154745B47`
- candidate:
  `alakazam_staged_20260729/versions/alakazam_newdeck_v4_next_attacker_distance_shadow_fix4`
- candidate closure:
  `802A1DD3344287EFE5EAC16F1B07DF79FF2727CF6767359EB3747470D09D4C38`
- candidate main SHA-256:
  `B2E354952ACEE44F7D0E40B44C83CA7A9B8379619FC3E13D98B8C33E894B7C4F`
- analyzer SHA-256:
  `B4784B7804602188D8253B41D0033F553C0A59DD5B7F34D5C2CA60E368266405`
- deck SHA-256:
  `F598F5E578D0440C96DC0492EAECF2E19739B7A23225BE57114A724EF7D0FB94`

Binding inputs:

- frozen C2 spec SHA-256:
  `096AC9F8C968A5BE645ECE87119241B1965C9110433E4872721881F16956FFE9`
- strategy-judge amendment SHA-256:
  `C33EBED6B5C945924F0ED4AFAC1C0029C9B129D870EE4FE583D3612948CD70B6`
- implementation receipt SHA-256:
  `054805C047B24820989292C3EC172FF80FEECEB9B644AA75C458F20070DFBAD1`

## Frozen tools

- engine:
  `analysis_outputs/cynthia_v9_vs_v11_poffin_role_selection_20260713/seeded_engine`
- engine 11-file tree:
  `466638706BD5C6915E25D1B3CB9E3D966390FBC263F4ED3153108E29C0194FFF`
- metric launcher:
  `tools/run_alakazam_staged_metric_suite.py`
- launcher SHA-256:
  `BCC98229B23C86FC5EB248D3F1E254337008FF4E85BD85224B3B3D6F570F1EEA`
- metric common SHA-256:
  `78A0BE6E87368939D7FCE590E1AA65B5DFFA228DE224FFB53AA42C8DE1EF295B`
- battle runner SHA-256:
  `E1ABA0151CDAEE425B858511AA760CE5C5647D555DDEFBD69D7319C29C5B773B`
- candidate-local collector:
  `verification/c2_sidecar_collector.py`
- collector SHA-256:
  `67F19C955E83E99FECB21C148E9EF49AB63BC03062B0A7163E37A4951DC96289`

## Immutable schedule

- opponents: 7
- seats: 0 and 1
- seed bases:
  `202608500, 202608510, 202608520, 202608530, 202608540`
- games per seat and seed-base cell: 10
- actual seed: `seed_base + game`
- max steps: 1000
- watchdog: 180 seconds
- expected games: 700
- expected blocks: 70

Opponents:

```text
marnie=meta_agents/marnie_sota_live_85033057_simple
cynthia=meta_agents/cynthia_garchomp_nasuo445_v80_legal_complete_role_cycle
alakazam_mirror=meta_agents/alakazam_oselcoun_live_85035844_simple
rocket_mewtwo_spidops_proxy=meta_agents/rocket_mewtwo_spidops_kashiwashira_20260703_simple
kangaskhan_crustle=meta_agents/kangaskhan_crustle_mpgaming_v13_backupkang_two_growline
historical_silver=analysis_outputs/reference_agents/historical_silver_archaludon_54495224
direct_frozen=alakazam_staged_20260729/eval_adapters/alakazam_800_frozen
```

## Destination

```text
alakazam_staged_20260729/metrics/
  formal_v4_c2_next_attacker_distance_shadow_fix4_7opp_50seed/
```

The destination must not exist before execution.  Failed or partial output is
retained and never overwritten; a retry uses a new suffixed destination.

## Exact command

```powershell
& .\.venv-rl\Scripts\python.exe -B .\tools\run_alakazam_staged_metric_suite.py `
  --engine-dir analysis_outputs/cynthia_v9_vs_v11_poffin_role_selection_20260713/seeded_engine `
  --version c2=alakazam_staged_20260729/versions/alakazam_newdeck_v4_next_attacker_distance_shadow_fix4 `
  --opponent marnie=meta_agents/marnie_sota_live_85033057_simple `
  --opponent cynthia=meta_agents/cynthia_garchomp_nasuo445_v80_legal_complete_role_cycle `
  --opponent alakazam_mirror=meta_agents/alakazam_oselcoun_live_85035844_simple `
  --opponent rocket_mewtwo_spidops_proxy=meta_agents/rocket_mewtwo_spidops_kashiwashira_20260703_simple `
  --opponent kangaskhan_crustle=meta_agents/kangaskhan_crustle_mpgaming_v13_backupkang_two_growline `
  --opponent historical_silver=analysis_outputs/reference_agents/historical_silver_archaludon_54495224 `
  --opponent direct_frozen=alakazam_staged_20260729/eval_adapters/alakazam_800_frozen `
  --seed-base 202608500 `
  --seed-base 202608510 `
  --seed-base 202608520 `
  --seed-base 202608530 `
  --seed-base 202608540 `
  --games-per-block 10 `
  --max-steps 1000 `
  --watchdog-seconds 180 `
  --output-dir alakazam_staged_20260729/metrics/formal_v4_c2_next_attacker_distance_shadow_fix4_7opp_50seed
```

## Raw collector

After all 70 blocks complete successfully:

```powershell
& .\.venv-rl\Scripts\python.exe -B `
  .\alakazam_staged_20260729\versions\alakazam_newdeck_v4_next_attacker_distance_shadow_fix4\verification\c2_sidecar_collector.py `
  .\alakazam_staged_20260729\metrics\formal_v4_c2_next_attacker_distance_shadow_fix4_7opp_50seed `
  --rows-out .\alakazam_staged_20260729\metrics\formal_v4_c2_next_attacker_distance_shadow_fix4_7opp_50seed\c2_callback_audit_rows.jsonl `
  --summary-out .\alakazam_staged_20260729\metrics\formal_v4_c2_next_attacker_distance_shadow_fix4_7opp_50seed\c2_mechanical_summary.json
```

The collector is a mechanical row and coverage extractor only.  It must not
aggregate game scores.

## Integrity gates

All are mandatory:

- 70 complete blocks and 700 unique
  `(opponent, policy_seat, seed_base, game, seed)` games;
- 700 nonempty sidecars and battle traces;
- exit code, timeout, action error, max-step, invalid-result counts are zero;
- every completed callback has the exact C2 trace schema and closure hashes;
- `raw_parent_action == applied_action == CALL_END.selected_action`, including
  Python type and element order;
- action-identity failures are zero;
- normal metric exceptions and wrapper exceptions are zero;
- observation fingerprints are non-null and stable;
- conflicting route classes for the same fingerprint are zero;
- duplicate callback keys are rejected and duplicate decisions do not increase
  unique-state coverage.

## Reachability gates

- at least 50 unique observation fingerprints;
- both policy seats;
- at least three opponents, including at least two non-mirrors;
- at least five unique states in each class:
  `CERTIFIED`, `POSSIBLE`, `UNKNOWN`, `IMPOSSIBLE`.

`UNKNOWN` must remain ahead of unproven `IMPOSSIBLE` in route reduction.

If integrity fails, status is `REJECT`.  If integrity passes but a reachability
gate is short, status is `INSUFFICIENT_EVIDENCE`.  Only if both groups pass may
the side-effect-free C2 analyzer be inherited by C3.

