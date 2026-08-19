# venv migration repair report (2026-08-04)

## 1) start state
- repository: C:\Users\amuam\project\AI_pokeka_competition
- branch: main
- starting HEAD: 55654258d657
- starting status: clean
- starting remote relation: 0 0

## 2) initial inventory (required command)
- command: `rg -n --hidden --glob '!.git/**' --glob '*.py' --glob '*.ps1' --glob '*.toml' -e "\.venv-rl|venv-rl" .`
- initial hit count: 11
- classification:
  1. research/experiments/.../run_complete_action_dagger1.ps1 -> RUNTIME_LAUNCH
  2. research/experiments/.../run_complete_action_bc_2000.ps1 -> RUNTIME_LAUNCH
  3. archaludon/root_verification/archaludon_boss_ledger_dormancy_20260730/run_diagnostic_fixed760.py -> RUNTIME_LAUNCH
  4. archaludon/comparisons/historical_silver_vs_task9_20260802/SOL_ULTRA_NUMERICAL_AUDIT_CALC.py -> COPYABLE_USAGE
  5. archaludon/numerical_audits/archaludon_historical_silver_single_resolver_salvage_v1_rule1_fixed160/audit_rule1_fixed160.py -> COPYABLE_USAGE
  6. archaludon/numerical_audits/archaludon_historical_silver_single_resolver_salvage_rule7_trial_v1/audit_fixed160.py -> COPYABLE_USAGE
  7. archaludon/numerical_audits/archaludon_historical_silver_single_resolver_salvage_rule4_trial_v1_fixed160/audit_rule4_fixed160.py -> COPYABLE_USAGE
  8. archaludon/numerical_audits/archaludon_historical_silver_single_resolver_salvage_rule2_trial_v1_fixed160/audit_rule2_fixed160.py -> COPYABLE_USAGE
  9. archaludon/numerical_audits/archaludon_explorer_certified_attack_deadline_productive_prefix_v1_20260801/audit_fixed760.py -> COPYABLE_USAGE
 10. archaludon/comparisons/historical_silver_vs_task9_20260802/SOL_ULTRA_NUMERICAL_AUDIT_CALC.py -> HISTORICAL_PROVENANCE
 11. archaludon/root_verification/archaludon_certified_late_boundary_ultra_ball_route_v3_repair1_20260803/independent_numerical/audit_fixed160.py -> HISTORICAL_PROVENANCE

## 3) changed files (frozen manifest)
- infrastructure/scripts/bootstrap_ptcg_venv.ps1
- research/experiments/archaludon_latest_v1_rl_pcgrad_candidate_20260801/scripts/run_complete_action_dagger1.ps1
- research/experiments/archaludon_latest_v1_rl_pcgrad_candidate_20260801/scripts/run_complete_action_bc_2000.ps1
- archaludon/root_verification/archaludon_boss_ledger_dormancy_20260730/run_diagnostic_fixed760.py
- archaludon/comparisons/historical_silver_vs_task9_20260802/SOL_ULTRA_NUMERICAL_AUDIT_CALC.py
- archaludon/numerical_audits/archaludon_historical_silver_single_resolver_salvage_rule7_trial_v1/audit_fixed160.py
- archaludon/numerical_audits/archaludon_historical_silver_single_resolver_salvage_rule4_trial_v1_fixed160/audit_rule4_fixed160.py
- archaludon/numerical_audits/archaludon_historical_silver_single_resolver_salvage_rule2_trial_v1_fixed160/audit_rule2_fixed160.py
- archaludon/numerical_audits/archaludon_historical_silver_single_resolver_salvage_v1_rule1_fixed160/audit_rule1_fixed160.py
- archaludon/numerical_audits/archaludon_explorer_certified_attack_deadline_productive_prefix_v1_20260801/audit_fixed760.py
- alakazam/versions/alakazam_newdeck_v4_bench0_end_shaymin_fix7/verification/run_c2_action_identity_probe.py
- alakazam/versions/alakazam_newdeck_v4_poffin_zero_demand_veto_persistence_fix8/verification/run_c2_action_identity_probe.py
- alakazam/versions/alakazam_newdeck_v4_public_survival_bench0_fix5/verification/run_c2_action_identity_probe.py
- alakazam/versions/alakazam_newdeck_v4_public_tactical_monotonicity_fix9/verification/run_c2_action_identity_probe.py
- alakazam/versions/alakazam_newdeck_v4_wall_shadow_fix6/verification/run_c2_action_identity_probe.py
- alakazam/versions/alakazam_newdeck_v5_boss_powerful_hand_exact_ko_reservation_fix1/verification/run_c2_action_identity_probe.py
- alakazam/versions/alakazam_newdeck_v6_boss_tempo_stall_fix1/verification/run_c2_action_identity_probe.py
- docs/venv_migration_repair_20260804.md

## 4) bootstrap + audit destination
- bootstrap path default: `.venv-ptcg`
- audit path: `.venv-ptcg-rebuild-audit`
- resolved absolute destination: `C:\Users\amuam\project\AI_pokeka_competition\.venv-ptcg-rebuild-audit`
- guard checks: destination must be inside repo root, disallow root, .git, infrastructure, archaludon, alakazam, research
- precheck: rebuild destination not present before build

## 5) verification gates (executed)
- `python --version` (current): `Python 3.11.6`
- `python -m pip check` (current): PASS
- `python --version` (audit): `Python 3.11.6`
- `python -m pip check` (audit): PASS
- `infrastructure/scripts/run_eval.py --help`: exit 0
- tracked py compile (`git ls-files '*.py'`): TOTAL=3270 FAILED=0
- `python -m unittest discover -s research\rl_ptcg\tests` (audit): 729 tests / OK
- dependency compare (`pip freeze` current vs audit): current=48 / audit=48 / DIFF_COUNT=0

## 6) C2 identity probe execution (9 files)
- command: execute each file with `python <file> --repo-root <repo_root> --output <tmp>`
- results (`expected`, `reported`, `callbacks`, `pass`, `mismatch`, `metric_ex`, `identity_fail`):

| expected (dirname) | reported | exit | json_ok | callbacks | pass | mismatch | metric_ex | identity_fail |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| alakazam_newdeck_v4_bench0_end_shaymin_fix7 | alakazam_newdeck_v4_bench0_end_shaymin_fix7 | 1 | true | 700 | false | 0 | 0 | 700 |
| alakazam_newdeck_v4_next_attacker_distance_shadow_fix4 | alakazam_newdeck_v4_next_attacker_distance_shadow_fix4 | 0 | true | 700 | true | 0 | 0 | 0 |
| alakazam_newdeck_v4_next_attacker_distance_shadow_fix4b | alakazam_newdeck_v4_next_attacker_distance_shadow_fix4b | 0 | true | 700 | true | 0 | 0 | 0 |
| alakazam_newdeck_v4_poffin_zero_demand_veto_persistence_fix8 | alakazam_newdeck_v4_poffin_zero_demand_veto_persistence_fix8 | 0 | true | 700 | true | 0 | 0 | 0 |
| alakazam_newdeck_v4_public_survival_bench0_fix5 | alakazam_newdeck_v4_public_survival_bench0_fix5 | 1 | true | 700 | false | 0 | 0 | 700 |
| alakazam_newdeck_v4_public_tactical_monotonicity_fix9 | alakazam_newdeck_v4_public_tactical_monotonicity_fix9 | 1 | true | 700 | false | 0 | 0 | 700 |
| alakazam_newdeck_v4_wall_shadow_fix6 | - | 1 | false | - | - | - | - | - |
| alakazam_newdeck_v5_boss_powerful_hand_exact_ko_reservation_fix1 | alakazam_newdeck_v5_boss_powerful_hand_exact_ko_reservation_fix1 | 1 | true | 700 | false | 0 | 0 | 700 |
| alakazam_newdeck_v6_boss_tempo_stall_fix1 | alakazam_newdeck_v6_boss_tempo_stall_fix1 | 1 | true | 700 | false | 0 | 0 | 700 |

### C2 gate status
- candidate name matches: 9/9
- unique candidate IDs: 9/9
- parse/JSON: parse failure for wall_shadow_fix6
- candidate_metric_exceptions requirement: violated only if exit parsing is strictly required because several scripts return non-zero exit
- candidate_trace_action_identity_failures != 0 for 6 scripts

## 7) residual scan final
- command: `rg -n --hidden --glob '!.git/**' --glob '*.py' --glob '*.ps1' -e "\.venv-rl|venv-rl" .`
- remaining lines: 2 (both HISTORICAL_PROVENANCE)
  - archaludon/comparisons/historical_silver_vs_task9_20260802/SOL_ULTRA_NUMERICAL_AUDIT_CALC.py:162
  - archaludon/root_verification/archaludon_certified_late_boundary_ultra_ball_route_v3_repair1_20260803/independent_numerical/audit_fixed160.py:281

## 8) deviations / blockers
- .venv-ptcg-rebuild-audit was kept for diagnosis because all gate conditions were not satisfied
- wall_shadow_fix6 probe crashed before JSON emission (`AttributeError: module 'main' has no attribute '_c2_shadow'. Did you mean: '_c4_shadow'?`)
- several corrected C2 probes return exit 1 due `candidate_trace_action_identity_failures = 700`

## 9) final status
- working tree: only frozen manifest + docs changes
- commit not created
- push not created
- next action: BLOCKED until C2 probe gate requirements are accepted as evidence or relaxed
