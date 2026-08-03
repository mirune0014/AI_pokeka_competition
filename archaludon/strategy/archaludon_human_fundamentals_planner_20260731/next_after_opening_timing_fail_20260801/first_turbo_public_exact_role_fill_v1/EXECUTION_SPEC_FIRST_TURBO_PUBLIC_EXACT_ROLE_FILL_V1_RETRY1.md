# Immutable pre-edit execution specification: retry 1

Status: `FROZEN_FOR_DETERMINISTIC_EXECUTION`

## Why a new execution exists

Attempt 1 stopped before producing raw callback rows because the runner rejected
an engine retry with the same semantic snapshot key. The controlling strategy
requires deduplication by that key. This retry preserves attempt 1 and uses a
new runner and new destination. It collapses a repeated key only when parent
semantics, contract semantics, validity, owners, classification, direction, and
error state are identical; any disagreement remains fatal.

## Bound inputs

- Formal parent `main.py`: `558EE5DB29E001428B0D59813613FABEE8E15B96E422746C104BDFAB4DC22DB6`
- Formal parent `deck.csv`: `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`
- Source manifest: `90A512D5C9AE5EAD8DF92F370C32716959EC0929F9465451E7BB0926DBEB5A68`
- Checked parent loader/helper: `3441E6DFA25140E9C70CABB58E9F36CF3DF76FCD25B3B36311590FA83CF9EF8B`
- Strategy selection: `E3E6C7BBA58DB125FCF2594FD0EA3A2DE826563DDE5B96DD95682BB213C0389D`
- Opening timing stop report: `456536AA5494B398DC9B4651431AEF604355B1F2879777F77F8D47A8025D1293`
- Hero Cape stop report: `FB01EBB6451ED5696D3FA0C17EDD81BBE9C53ADF72AE54B20C671551D2C38627`
- Attempt-1 runner: `42243ED174DFF40D80BD6DBD7004E81B339FBE22576CFAE7ED2D408E20B075F1`
- Attempt-1 specification: `3DE92E1B0461E4396D2FE5B502FCBD7D945B727E48D3553715BC7CE66F18DF21`
- Attempt-1 failure record: `320EA49356A071C32F788C38097AE264BB356E0EF61DA51B9E702087513A2E6C`
- Retry-1 census runner: `558EF4BEBEE3A213886F98F7E1F0452F61090953A0DD61291B03C958C02E471B`

Expected corpus integrity remains exactly 207 replay files, 209 target seats,
and 25,880 selectable parent callbacks.

## Command

Working directory:

`C:\Users\amuam\project\AI_pokeka_competition`

Environment:

`PYTHONDONTWRITEBYTECODE=1`

Command:

`C:\Users\amuam\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe C:\Users\amuam\project\AI_pokeka_competition\autonomous_gold_20260715\strategy\archaludon_human_fundamentals_planner_20260731\next_after_opening_timing_fail_20260801\first_turbo_public_exact_role_fill_v1\freeze_pre_edit_first_turbo_exact_role_fill_census_retry1.py`

## Immutable destination

`C:\Users\amuam\project\AI_pokeka_competition\autonomous_gold_20260715\strategy\archaludon_human_fundamentals_planner_20260731\next_after_opening_timing_fail_20260801\first_turbo_public_exact_role_fill_v1\pre_edit_first_turbo_exact_role_fill_census_retry1_raw`

The destination must not exist before execution. Expected files are:

- `first_turbo_callback_rows.csv`
- `first_turbo_transaction_rows.csv`
- `predicted_first_differences.csv`
- `source_manifest.json`
- `summary.json`

## Operator restrictions

Execute only the exact command and return raw paths, exit code, stdout/stderr,
row counts, and hashes. Do not interpret rates, action quality, implementation
permission, or promotion.

