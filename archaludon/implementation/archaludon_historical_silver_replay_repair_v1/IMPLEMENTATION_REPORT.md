# Archaludon replay repair v1 implementation report

## Base
- branch: `codex/archaludon-replay-repair-v1`
- starting commit: `82c6b8fb53a683653fc91f7b7a69ffb4404d2bbb`
- copied formal source path: `archaludon/final/archaludon_historical_silver_single_resolver_salvage_v1`
- new candidate path: `archaludon/candidates/archaludon_historical_silver_replay_repair_v1`

## Changed files
- `archaludon/candidates/archaludon_historical_silver_replay_repair_v1/main.py`
  - Setup now supports Cinderace or Duraludon as the recorded Active, preserves the setup ledger across turn-0 intermediate contexts, avoids duplicate backups, and limits Rule5 proof to the attacker/current-target/candidate-target pair.
  - Added explicit Rule5 benign-skill allowlist, printed-prize lookup, and fail-closed handling for unknown higher-prize bench candidates.
  - Added a raw-loader guard so `__file__` is optional: normal imports use the archive directory, while Kaggle validation uses `/kaggle_simulations/agent`.
- `archaludon/candidates/archaludon_historical_silver_replay_repair_v1/_historical_silver_parent.py`
  - Restricted the four strong Crustle suppressions to opponent Active card ID 345; broad matchup detection and long-game deck-preservation rules remain unchanged.
- `archaludon/implementation/archaludon_historical_silver_replay_repair_v1/tests/test_rule1_setup.py`
  - Copied Rule1 regression tests, updated changed expectations, and added Duraludon-start, intermediate-ledger, and invalid-state coverage.
- `archaludon/implementation/archaludon_historical_silver_replay_repair_v1/tests/test_rule4_materialization.py`
  - Copied existing Rule4 regression tests with the new candidate path.
- `archaludon/implementation/archaludon_historical_silver_replay_repair_v1/tests/test_rule5_attack_transaction.py`
  - Copied Rule5 regression tests and added local-scope, unknown-prize, skill-policy, and target-pair coverage.
- `archaludon/implementation/archaludon_historical_silver_replay_repair_v1/tests/test_parent_crustle_scope.py`
  - Added focused active-only Crustle override tests.
- `archaludon/implementation/archaludon_historical_silver_replay_repair_v1/IMPLEMENTATION_REPORT.md`
  - This report.

## Implemented behavior
- setup backup
- setup intermediate preservation
- active-only Crustle hard suppression
- local Rule5 higher-prize proof

## Explicit non-goals
- Rule3
- deck change
- third-line general policy
- new framework
- final promotion / Kaggle submission

## Validation
- py_compile: `.venv-ptcg\Scripts\python.exe -m py_compile ...main.py ..._historical_silver_parent.py`; exit code `0`.
- unittest: `.venv-ptcg\Scripts\python.exe -m unittest discover -s archaludon/implementation/archaludon_historical_silver_replay_repair_v1/tests -p "test_*.py" -v`; `41` tests, `41` passed, `0` failed, exit code `0`.
- raw-loader check: executing `main.py` without `__file__` and importing it normally both produce a callable `agent`; exit code `0` for each.
- repaired package: `archaludon/packages/archaludon_historical_silver_replay_repair_v1_validationfix1_clean_20260810/submission_archaludon_historical_silver_replay_repair_v1_validationfix1_20260810.tar.gz`; 13 members, zero caches, extracted source hashes match, local artifact registration passes, and extracted no-`__file__` execution passes.
- `python -m unittest ...` with the system Python 3.9 was not usable because the bundled `cg.api` uses Python 3.10+ union annotations; the repository venv is Python 3.11.6 and passed the complete suite above.
- `git diff --cached --check` over the changed Python/Markdown/test files: exit code `0`; copied formal `cg/` files were kept byte-for-byte, including their pre-existing whitespace/line-ending form.
- formal final diff: empty (`git diff -- archaludon/final`).
- source/candidate deck SHA-256: `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A` for both files.

## Remaining uncertainty
- smoke was not executed. The existing fixed160 wrapper exits before execution because its frozen schedule file `autonomous_gold_20260715/evaluation_specs/archaludon_historical_silver_single_resolver_salvage_v1_rule1/fixed160_spec.json` is absent; no new smoke/evaluation infrastructure was created, and fixed760/long seed search were not run.
