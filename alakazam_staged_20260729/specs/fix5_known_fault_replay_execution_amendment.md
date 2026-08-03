# fix5 known-fault replay execution amendment

## Purpose

This schedule replays every fix4 fault cell using the immutable fix5 candidate.
It is a runtime safety gate, not a win-rate comparison.

## Frozen runtime

- Engine:
  `analysis_outputs/cynthia_v9_vs_v11_poffin_role_selection_20260713/seeded_engine`
- Engine tree SHA-256:
  `466638706BD5C6915E25D1B3CB9E3D966390FBC263F4ED3153108E29C0194FFF`
- Metric launcher SHA-256:
  `BCC98229B23C86FC5EB248D3F1E254337008FF4E85BD85224B3B3D6F570F1EEA`
- Battle runner SHA-256:
  `E1ABA0151CDAEE425B858511AA760CE5C5647D555DDEFBD69D7319C29C5B773B`
- Candidate adapter:
  `alakazam_staged_20260729/eval_adapters/alakazam_newdeck_v1_package_runtime_certified_fix5`
- Candidate closure SHA-256:
  `5FFA8776CA95E16C7030C55B5682DE42BA21C06964C790A3D6312B60FBAA5009`
- Games per block: `10`
- Seats: `0`, `1`
- Max steps: `1000`
- Watchdog: `180` seconds per block

## Hammer schedule

- Opponent:
  `kangaskhan_crustle=meta_agents/kangaskhan_crustle_mpgaming_v13_backupkang_two_growline`
- Seed bases:
  `202608510`, `202608530`, `202608540`
- Expected blocks: `6`
- Expected games: `60`
- Destination:
  `alakazam_staged_20260729/metrics/targeted_fix5_hammer_fault_replay_202608510_530_540`

The exact prior faults are:

- base `202608510`, seat `1`, games `5`, `6`, `8`;
- base `202608530`, seat `0`, games `5`, `7`;
- base `202608530`, seat `1`, game `7`;
- base `202608540`, seat `0`, game `7`.

Each route must start and complete
`V1_HAMMER_UNIQUE_SPECIAL_ENERGY_CURRENT_KO`. The stored expected fingerprint
must preserve Mega Kangaskhan ex's current and maximum HP while removing Grow
Grass Energy.

## Boss schedule

- Opponent:
  `rocket_mewtwo_spidops_proxy=meta_agents/rocket_mewtwo_spidops_kashiwashira_20260703_simple`
- Seed base: `202608540`
- Expected blocks: `2`
- Expected games: `20`
- Destination:
  `alakazam_staged_20260729/metrics/targeted_fix5_boss_repelling_veil_202608540`

The prior protected routes were seat `0`, games `1` and `7`. When exact
Articuno ID `414` and Basic Team Rocket's Mewtwo ex ID `431` reproduce, no
`V1_BOSS_TERMINAL_PRIZE_KO` transaction may start at those positions.

The same cell must retain at least one exact, unprotected v1 Boss or Alakazam
route when its certificate is satisfied; suppressing all affected candidates
is a gate failure.

## Acceptance

Both destinations must be fresh. All 80 games and eight blocks must complete.
Callback and transaction starts must pair exactly with ends/completes. Every
safety, fallback, unknown-route, timeout, action-error, exception, and max-step
count must be zero.

These rows are not pooled with smoke, formal safety, or Comparison B.
