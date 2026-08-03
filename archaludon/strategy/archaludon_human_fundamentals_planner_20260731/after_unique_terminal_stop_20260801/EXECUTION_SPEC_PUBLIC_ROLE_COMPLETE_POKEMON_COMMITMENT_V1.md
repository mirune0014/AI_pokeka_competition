# Immutable execution specification: public role-complete Pokemon commitment v1

Status: `FROZEN_FOR_DETERMINISTIC_EXECUTION`

## Bound inputs

- strategy SHA-256:
  `B0223A65081382006E64277F60EC8D17D6A0BF5E8231667BDA11ECAA517AD4B4`
- runner SHA-256:
  `02F4BF76B415F492EA8DA02A3F7FD47009C92B41C31E8D2A90C6C56844E67E43`
- exact parent / deck SHA-256:
  `558EE5DB29E001428B0D59813613FABEE8E15B96E422746C104BDFAB4DC22DB6` /
  `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`
- manifest SHA-256:
  `90A512D5C9AE5EAD8DF92F370C32716959EC0929F9465451E7BB0926DBEB5A68`
- stopped terminal root report / independent audit SHA-256:
  `DC8A74945964896603583AECA068B80661DD231FE9759C05BE3441EFCE56D77E` /
  `F41954FFA3538D77B1495FDAF153EC15F9FE1499BFF7E27CF220FBD718B57B69`

## Exact command

Run once from `C:\Users\amuam\project\AI_pokeka_competition`:

```powershell
& 'C:\Users\amuam\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -I -B 'autonomous_gold_20260715\strategy\archaludon_human_fundamentals_planner_20260731\after_unique_terminal_stop_20260801\freeze_pre_edit_role_complete_pokemon_commitment_census.py'
```

No environment override, output redirection, retry, partial rerun, aggregate
rewrite, or destination reuse is permitted.

## Immutable destination and outputs

Destination must be absent before execution:

`pre_edit_role_complete_pokemon_commitment_census_raw`

Expected files:

- `all_callback_rows.csv`
- `pokemon_commitment_opportunities.csv`
- `causal_first_differences.csv`
- `source_manifest.json`
- `summary.json`

The runner refuses an existing destination and any bound hash mismatch.  A
nonzero exit, missing/unexpected file, cache artifact, manifest mismatch,
duplicate raw key, nonidentical retry, or row-count discrepancy is preserved as
failure evidence and is never repaired in place.

## Operator return

The deterministic operator reports only exact command, exit code, elapsed
time, verbatim stdout/stderr, destination listing, SHA-256 for every output,
CSV data-row counts, and cache-file count.  It must not interpret the numeric
gate or recommend implementation.
