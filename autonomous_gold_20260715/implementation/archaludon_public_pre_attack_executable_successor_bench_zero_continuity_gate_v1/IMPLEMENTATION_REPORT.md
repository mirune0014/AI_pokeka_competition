# Task 4 implementation report

## Scope and behavioral intent

- Parent: `autonomous_gold_20260715/packages/archaludon_public_exact_same_active_attack_dominance_v1_clean_20260801_2352/extracted_frozen_verification`
- Candidate: `autonomous_gold_20260715/candidates/archaludon_public_pre_attack_executable_successor_bench_zero_continuity_gate_v1`
- Rule: `PUBLIC_PRE_ATTACK_EXECUTABLE_SUCCESSOR_BENCH_ZERO_CONTINUITY_GATE_V1`
- Only candidate `main.py` changed. All 11 non-main package entries are byte-identical to the frozen parent.
- The rule is a veto inside SAPT's existing no-purpose/`SECURED_ATTACK_NOW` branch. It preserves the exact parent action at the exact Bench-zero binding-unknown boundary, or for an admitted board-forming family when the existing public planner proves an exact empty executable-backup set after the worst public reply. It does not choose search results or Ultra Ball costs, create a search transaction/watch, consume callbacks, or change terminal/direct-attack/owner behavior.

## Hashes and diff scope

- Parent `main.py`: `914B8419ECAFB57D8F0CDC462E6035DB0EE6325044DFBCCE216F0FE759CE92DF`
- Candidate `main.py`: `CAF2C696AE9F6102C1A4A8E67649C309104064CAABF9643865BE766D91BDE8DD`
- Parent and candidate `deck.csv`: `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`
- `run_focused_fixtures.py`: `FE284BAECE388B614B27EB86205DAE6305D966E15C8D571D16B263947DD0BB80`
- Replay comparator evidence: `EA50C230E4C89178C36E185635C1C326A4EB9D5E07EE034FD7A6033B3C02212D`
- `git diff --no-index --numstat parent/main.py candidate/main.py`: `383` insertions, `7` deletions. Every semantic hunk is in the existing SAPT section: rule/text constants, eight private guard/proof helpers, the veto call immediately before `_practice_bind_attack`, and nested telemetry. The only out-of-section byte difference is adding the missing final newline at EOF.

## Verification commands and results

1. Frozen source verification before copying:

   `Get-FileHash -Algorithm SHA256 <parent>/main.py; Get-FileHash -Algorithm SHA256 <parent>/deck.csv`

   Result: exact required parent hashes above. The candidate contains the complete 12-entry cache-free package layout.

2. Final compilation:

   `py -3.11 -m py_compile <candidate>/main.py <implementation>/run_focused_fixtures.py`

   Result: exit `0`. Bytecode was redirected to the owned temporary compile-cache tree and that tree was removed afterward.

3. Focused fixtures:

   `py -3.11 <implementation>/run_focused_fixtures.py`

   Result: `33` assertions passed. Coverage includes both seats, option permutation, duplicate-call stability, Bench-zero Explorer/Ultra Ball, all four nonempty admitted families with exact empty-backup proof, terminal/parent ATTACK/parent END/RETREAT negatives, active owner, full Bench, zero-deck Poké Pad and Ultra Ball, Night Stretcher without a discarded Basic, existing executable backup, unknown proof, malformed/ambiguous state, a bound non-board Bench-zero prefix with a non-exception rejection, and non-MAIN pass-through. Every returned action was validated against the observation's selection bounds.

4. Checked replay comparator:

   `py -3.11 tools/compare_replay_agent_actions.py --engine-dir <candidate> --replay C:/Users/amuam/Downloads/89347400.json --left <parent> --right <candidate> --output <implementation>/replay_89347400_parent_vs_candidate.json`

   Result: target seat `1`; `11` decision rows; exactly `2` parent/candidate differences. Step `12` restores parent Explorer's Guidance (`1185`), and step `19` restores parent Ultra Ball (`1121`). The other `9` decision rows are parent-identical; the frozen parent matches all recorded actions.

5. Package/deck/AST/import/hash audit:

   `py -3.11 -B - <focused audit script>`

   Result: package file count `12`, exact expected layout, zero non-main hash mismatches, deck count `60`, Hero's Cape ACE SPEC count `1`, AST last top-level callable `agent` at line `31406`, import succeeds, final `agent` is callable, and the Task 4 rule ID is present.

6. Cache audit:

   `Get-ChildItem <candidate>,<implementation> -Recurse -Force | Where-Object { $_.Name -eq '__pycache__' -or $_.Extension -eq '.pyc' }`

   Result: zero matches after cleanup.

## Known limitations and evaluator focus

- Replay observations are independent snapshots. The comparator proves the two local decisions, not the downstream game line that Explorer or Ultra Ball would produce.
- Nonempty-Bench activation intentionally fails closed unless the existing planner returns an `EXACT` baseline, `EXACT` worst public reply, `EXACT` backup proof with `exact_backup_ready == False` and empty routes, and exact post-action/post-reply ledgers.
- Poké Pad and Ultra Ball require a positive public deck count; Ultra Ball proves only two visible other hand cards and never selects costs. Night Stretcher requires a visible discarded exact Basic Pokémon.
- The Bench-zero generic escape is restricted to SAPT's exact `card_or_target_binding_unknown` rejection. Other reasons must classify as one of the four admitted board-forming families.
- No broad win-rate simulation was run. No archive was created, and no Kaggle or other external write occurred.

Evaluator should specifically recheck the exact-plan proof against adjacent matchups and confirm that preserving the two replay prefixes improves board formation without regressing secured-attack conversion.
