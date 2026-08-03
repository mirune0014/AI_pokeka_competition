# Immutable pre-edit execution specification

Status: `FROZEN_FOR_DETERMINISTIC_EXECUTION`

## Purpose

Execute the pre-edit actionability census for
`PUBLIC_SECURED_ATTACK_POKEMON_SEARCH_PURPOSE_GUARD_V1`. This is not a candidate
evaluation and does not authorize a source edit or submission.

## Bound inputs

- formal parent `main.py`: `558EE5DB29E001428B0D59813613FABEE8E15B96E422746C104BDFAB4DC22DB6`
- formal parent `deck.csv`: `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`
- source manifest: `90A512D5C9AE5EAD8DF92F370C32716959EC0929F9465451E7BB0926DBEB5A68`
- checked parent loader/helper: `3441E6DFA25140E9C70CABB58E9F36CF3DF76FCD25B3B36311590FA83CF9EF8B`
- strategy: `6D98BF4300BC059F1E7E7B9EA31FD98CBCE15CA68510DBF168F2DB26A2F7E69A`
- first-Turbo stop: `7277B8ECD82C577CF775CCF2C058DACAAA01435F00A9A99B9041C1889B21F458`
- TODO: `8AE7B706CF5BE4E3EF659A10CEB4F8C5E516E67BECDA4421173AF06567BB1224`
- acceptance matrix: `F273C043D4C479F15CC464600B14D51823BECF55D4AF22F68A0B8971F166A386`
- action-frequency report: `9A440FA409161153F8801354884FD66EC88DE522B14D5067D23ADDCBA0804ECC`
- effect-gap report: `253F8CB535DFF70F561E93EA57066E3C5E563DCE9735F91AF56AF327A714D3D1`
- frozen census runner: `A60CDB559DBC0BC6B985654B3BCDC499F2C6D712F7795526D7DC190EE77803F8`

Expected integrity is exactly 207 replay files, 209 target seats, and 25,880
selectable parent callbacks. The runner calls the formal parent once per
selectable target callback in replay order. It records but does not imitate
historical actions.

## Command

Working directory:

`C:\Users\amuam\project\AI_pokeka_competition`

Environment:

`PYTHONDONTWRITEBYTECODE=1`

Command:

`C:\Users\amuam\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe C:\Users\amuam\project\AI_pokeka_competition\autonomous_gold_20260715\strategy\archaludon_human_fundamentals_planner_20260731\next_after_first_turbo_no_actionable_boundary_20260801\freeze_pre_edit_search_purpose_guard_census.py`

## Immutable destination

`C:\Users\amuam\project\AI_pokeka_competition\autonomous_gold_20260715\strategy\archaludon_human_fundamentals_planner_20260731\next_after_first_turbo_no_actionable_boundary_20260801\pre_edit_search_purpose_guard_census_raw`

The destination must not exist before execution. Expected files:

- `orientation_rows.csv`
- `search_guard_callback_rows.csv`
- `predicted_first_differences.csv`
- `source_manifest.json`
- `summary.json`

## Operator restrictions

Execute the exact command once and report command, exit code, stdout/stderr,
elapsed time, raw paths, data-row counts, and SHA-256 hashes. Do not write code
or aggregates and do not interpret the actionability gate.

