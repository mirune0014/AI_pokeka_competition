# Rule 5 trial implementation report

## Scope and behavior

- Frozen source: accepted Rule 4 parent `archaludon_historical_silver_single_resolver_salvage_rule4_trial_v1`, `main.py` SHA-256 `F6B6266D870D3F134544A91616C27673620557D149C0496CC2034E7674F010D9`.
- Frozen selection: `STRATEGY_SELECTION.md` SHA-256 `C7417858C932B156AF115DFCB6A11878CF239E4FA7CD4FC7BBDC43631A15B2FF`.
- Trial: `archaludon_historical_silver_single_resolver_salvage_rule5_trial_v1`.
- Added only `PARENT_EXACT_ATTACK_WIN_OR_UNIQUE_HIGHER_PRIZE_BOSS_TRANSACTION_V1` over the exact four-attack registry: Duraludon Hammer In `223`, Duraludon Raging Hammer `224`, Archaludon ex Metal Defender `253`, and Archaludon Coated Attack `1212`.
- The direct branch preserves a parent-selected exact terminal attack or selects the sole distinct exact terminal attack ID. Damage applies printed damage, exact Raging Hammer counters, Weakness, Resistance, and exact Full Metal Lab in that order; Prize take is exact printed Prize value capped by own remaining Prize.
- The Boss branch starts only from the parent's unique registered ATTACK option and a single distinct Bench serial that the same attack exactly KOs for strictly more Prize than the current Active. It uses the lowest-serial legal Boss `1182`, then one shared owner through `BOSS_EMITTED -> BOSS_CONFIRMED -> TARGET_CONFIRMED -> CLEAR`, rebinds same-prompt retries by semantic role at the lowest option position, rechecks the same attacker, attack ID, target, damage, KO, and Prize take after the switch, and clears on completion or mismatch.
- Rules 1 and 4, the complete stored Historical-Silver parent, deck, and all non-`main.py` candidate files are preserved byte-for-byte. There remains one public `agent`, one `_resolve`, one parent call per callback, one shared owner, and six-field proposals. Unsupported Tools, Special Energy, special conditions, unknown abilities/modifiers, Stadiums other than exact Full Metal Lab, effect callbacks, and incomplete public metadata fail closed to the parent.

## Verification

Focused command:

```powershell
py -3.11 -B -m unittest discover -s autonomous_gold_20260715/implementation/archaludon_historical_silver_single_resolver_salvage_rule5_trial_v1/tests -p test_*.py -q
```

Outcome: exit `0`; `28/28` test groups passed (`13` inherited Rule 1, `9` inherited Rule 4, `6` Rule 5). Rule 5 coverage includes all four registered attacks; parent-selected and overridden direct wins; Weakness, Resistance, and Full Metal Lab order; Boss conversions `0->1`, `0->2`, `1->2`, and `1->3`; full transaction on both seats; same-prompt retries; option permutation; semantic duplicates with minimum-position binding; direct-win precedence; equal/lower Prize, non-unique target, used Supporter, status, Tool, and stale-owner negatives.

In-memory compile/import/structure/deck command compiled the final `main.py`, three fixtures, and `run_shadow.py` without creating bytecode. Outcome: exit `0`; five files compiled; import passed; one top-level `agent`; one `_resolve`; one static `_parent.agent` call inside `agent`; final callable `agent`; deck count `60`; ACE SPEC count `1`. The candidate and implementation trees contain zero `__pycache__` directories and zero `.pyc` files. All `12` non-`main.py` candidate files are byte-identical to accepted Rule 4.

Frozen shadow command:

```powershell
py -3.11 -B autonomous_gold_20260715/implementation/archaludon_historical_silver_single_resolver_salvage_rule5_trial_v1/run_shadow.py
```

Outcome: exit `0`; frozen corpus SHA-256 `B88C25BC8F26F959F85D00D27FD7B148D22034D71B2588DF73AAF8C8E0B15004`; `77` readable replays plus known malformed episode `89287701`; `4,262` callbacks; zero invalid actions, exceptions, or wrapper faults; two action differences, both `DIRECT_EXACT_CURRENT_WIN`; zero natural Boss starts; zero transaction confirmations.

Every shadow difference was inspected:

- `episode_89273754`, seat `1`, step `73`, turn `8`: parent attached Basic Metal serial `116`; Rule 5 selected Metal Defender `253`. Archaludon ex serial `70`, exact 220 printed damage doubled to `440` by the target's Metal Weakness, KOs Mega Abomasnow ex serial `11`, and takes the remaining `2` Prize.
- `episode_89280169`, seat `1`, step `161`, turn `22`: parent evolved Archaludon ex serial `67`; Rule 5 selected Metal Defender `253`. Archaludon ex serial `70` deals exact `220` to the already-damaged Mega Starmie ex serial `25`, KOs it, and takes the remaining `1` Prize. The occupied exact Full Metal Lab does not reduce damage to the Water target.

Checked-engine smoke used `tools/run_local_battle.py`, the checked seeded engine, and exact Historical-Silver as opponent:

```powershell
.venv-rl/Scripts/python.exe -B tools/run_local_battle.py --engine-dir analysis_outputs/cynthia_v9_vs_v11_poffin_role_selection_20260713/seeded_engine --agent-a autonomous_gold_20260715/candidates/archaludon_historical_silver_single_resolver_salvage_rule5_trial_v1 --agent-b autonomous_gold_20260715/baseline/historical_silver_archaludon_54495224 --deck-a autonomous_gold_20260715/candidates/archaludon_historical_silver_single_resolver_salvage_rule5_trial_v1/deck.csv --deck-b autonomous_gold_20260715/baseline/historical_silver_archaludon_54495224/deck.csv --games 1 --max-steps 1000 --trace-dir autonomous_gold_20260715/implementation/archaludon_historical_silver_single_resolver_salvage_rule5_trial_v1/smoke/candidate_p0/traces --trace-options --seed-base 803205001 --engine-seed --summary autonomous_gold_20260715/implementation/archaludon_historical_silver_single_resolver_salvage_rule5_trial_v1/smoke/candidate_p0/summary.jsonl
.venv-rl/Scripts/python.exe -B tools/run_local_battle.py --engine-dir analysis_outputs/cynthia_v9_vs_v11_poffin_role_selection_20260713/seeded_engine --agent-a autonomous_gold_20260715/baseline/historical_silver_archaludon_54495224 --agent-b autonomous_gold_20260715/candidates/archaludon_historical_silver_single_resolver_salvage_rule5_trial_v1 --deck-a autonomous_gold_20260715/baseline/historical_silver_archaludon_54495224/deck.csv --deck-b autonomous_gold_20260715/candidates/archaludon_historical_silver_single_resolver_salvage_rule5_trial_v1/deck.csv --games 1 --max-steps 1000 --trace-dir autonomous_gold_20260715/implementation/archaludon_historical_silver_single_resolver_salvage_rule5_trial_v1/smoke/candidate_p1/traces --trace-options --seed-base 803205002 --engine-seed --summary autonomous_gold_20260715/implementation/archaludon_historical_silver_single_resolver_salvage_rule5_trial_v1/smoke/candidate_p1/summary.jsonl
```

Outcome: candidate seat `0`, seed `803205001`, terminal in `110` steps, action errors `0`, max-step false; candidate seat `1`, seed `803205002`, terminal in `155` steps, action errors `0`, max-step false.

## Final hashes and evaluator handoff

- trial `main.py`: `D966E455E5110F9D5616195AEAAC8663E6A92F310DAFC4B7F79E4D37149A9C62`
- stored Historical-Silver parent: `F4B578453C9D953BE94885144DD50E05DBA4510DF3340BE27ADE07495896046E`
- deck: `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`
- Rule 1 fixture: `93B2CC2F3F334018FEFF685828F62A1C577898005B569A24BF85D489D10B350B`
- Rule 4 fixture: `7F8BDCD59D2B10ACD557B9DA302233758C54394459A6CEAB7CEF3416B21DB863`
- Rule 5 fixture: `8010D7137CE4381291DBAE33A3596D23489AF1E1D249E892636DED7AA22BFA10`
- shadow runner: `4A77FA5AA1AA2AD61294D28935F9AC46A912A12AA1589BEE8D9379BBB97E343E`
- shadow summary: `3C24F89CDD5E509BCB2455CD1BC019BB5CFB75CA1A89F2B206B9D1ACB256CE71`
- shadow differences: `C55F4E465FEC0103897E4294E2E0EA53B3FA93F146A9B27BBEB87398ECF18B97`
- smoke seat 0 summary: `304E08FB5BECB6956C5BD0B57CC5E395E245382117F35A3B839E8225E40916CA`
- smoke seat 1 summary: `C1EB7E8C146708CCF3151D3CF7263AF61369ECCAFD62D272A48F831B9F036741`

Known tradeoff: the exact modifier boundary is intentionally conservative, so many legal attacks and Boss opportunities remain parent-owned. The frozen shadow naturally exercises two direct wins but no Boss start; focused both-seat transaction fixtures prove the complete owner lifecycle, while the checked-engine games prove legal execution but do not constitute causal Boss evidence. The evaluator must run the frozen fixed160, inspect both direct first differences and every new Boss start/completion, require only the two allowed first-difference classes, verify stored/executed attack ID equality and recorded `current_take`/`target_take`, and apply the frozen fault/gain/regression/cell gates. No fixed160, archive, commit, push, package, or Kaggle action was performed.
