# Immutable execution specification: public unique terminal-attack dominance v1

Status: `FROZEN_FOR_DETERMINISTIC_EXECUTION`

The operator executes the checked census exactly once and reports only raw
paths, hashes, exit code, row counts, and verbatim stdout/stderr.  It does not
interpret or repair the results.

## Bound inputs

- strategy: `STRATEGY_SELECTION_PUBLIC_UNIQUE_TERMINAL_ATTACK_DOMINANCE_V1.md`
  - SHA-256 `7165420EB6F84BC28CFDC1096F9C8851B85196796B916015AC7B8696CB48EB43`
- runner: `freeze_pre_edit_unique_terminal_attack_census.py`
  - SHA-256 `1F52AA13AC94105C0226BD0E14263938EF45CB870A46D63E201B43C45756A0B4`
- exact parent `candidates/archaludon_purpose_first_pokegear_boss_transaction_v1/main.py`
  - SHA-256 `558EE5DB29E001428B0D59813613FABEE8E15B96E422746C104BDFAB4DC22DB6`
- exact deck `candidates/archaludon_purpose_first_pokegear_boss_transaction_v1/deck.csv`
  - SHA-256 `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`
- corpus manifest: the runner-bound immutable manifest
  - SHA-256 `90A512D5C9AE5EAD8DF92F370C32716959EC0929F9465451E7BB0926DBEB5A68`
- expected corpus: 207 replay files, 209 target seats, 25,880 parent calls

## Exact command

From `C:\Users\amuam\project\AI_pokeka_competition`:

```powershell
& 'C:\Users\amuam\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -I -B 'autonomous_gold_20260715\strategy\archaludon_human_fundamentals_planner_20260731\next_after_search_guard_no_actionable_boundary_20260801\freeze_pre_edit_unique_terminal_attack_census.py'
```

No environment override, output redirection, retry, partial rerun, aggregation,
or destination reuse is permitted.

## Immutable destination and schema

Destination must not exist before execution:

`pre_edit_unique_terminal_attack_census_raw`

Expected files:

- `all_callback_rows.csv`
- `causal_first_differences.csv`
- `source_manifest.json`
- `summary.json`

The runner must refuse existing output and hash mismatches.  Any nonzero exit,
missing file, unexpected file, cache artifact, manifest mismatch, duplicate raw
callback key, nonidentical semantic retry, invalid parent action, or row-count
disagreement is preserved as failure evidence and is not repaired in place.

## Known-residue interpretation

The four old search rows and three search-scope earliest starts are reproduced
inside the original search-only scope.  Global causal ordering for this broader
all-family rule may begin earlier in the same turn; that does not erase or
inflate the search residue.

## Operator return

Return the exact command, process exit code, elapsed time, stdout/stderr,
destination listing, SHA-256 for all four outputs, CSV data-row counts, and any
cache files.  Numerical meaning is reserved for the independent Sol-Ultra
evaluator and root verification.
