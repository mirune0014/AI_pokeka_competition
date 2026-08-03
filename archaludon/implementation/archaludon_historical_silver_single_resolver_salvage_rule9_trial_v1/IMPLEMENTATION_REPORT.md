# Rule 9 trial implementation report

## Scope and behavioral intent

- Frozen Rule 5 parent `main.py` SHA-256: `D966E455E5110F9D5616195AEAAC8663E6A92F310DAFC4B7F79E4D37149A9C62`.
- Frozen deck SHA-256: `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`.
- Frozen Rule 9 selection SHA-256: `E34153B3B3886BCC074EA597A8741A6A100C9E18E59780B60797AA8820BE11FD`.
- Added only `PARENT_GEAR_EXACT_LAST_PRIZE_BOSS_CONTINUATION_V1` after inherited Rule 5 direct win, Rule 4 materialization, and Rule 5 in-hand Boss conversion decline. Rules 7 and 8 are absent.
- Rule 9 arms only when the once-called parent already returns one physically bound Gear `1122` PLAY and the exact public oracle proves one payable attack, a nonterminal current Active, and exactly one Bench target that the same attack KOs for all remaining Prizes. The entry action is the exact parent list.
- The existing sole `_materialization_owner` carries `GEAR_PLAY_EMITTED -> GEAR_HIT_EMITTED | MISS_EMPTY_EMITTED -> BOSS_PLAY_EMITTED -> BOSS_TARGET_EMITTED -> ATTACK_EMITTED -> CLEAR`. No wrapper, second owner, scorer, planner, or simulator was added. There remains one public `agent`, one `_resolve`, and one `_parent.agent` call.
- The exact engine reveal is `CARD/TO_HAND`, Gear-bound, `min=0,max=1`, with `current.looking` and unique `LOOKING` option bindings. The branch chooses the lowest-serial revealed Boss; Boss plus Explorer/Lillie still chooses Boss; every well-formed no-Boss reveal, including Explorer/Lillie-only, emits `[]`, confirms the resolution ledger at the next exact MAIN, then clears.
- A Boss hit confirms hand/discard/deck/action-count/log transitions, emits only the bound Boss PLAY, binds the pre-certified unique SWITCH target, re-proves the identical attack/damage/Prize certificate after movement, and emits the terminal attack. Same-prompt retries rebind semantic roles; option/looking reordering is positional only. Duplicate semantic roles, identity/metadata/seat/turn/ledger drift, changed target/attack, or ambiguity clears to that callback's exact Rule 5 parent action with irreversible-abort telemetry.
- Every proposal retains exactly `rule_id`, `action`, `category`, `purpose`, `exact_proof`, and `transaction`. Deck, stored Historical-Silver parent, requirements, and all other candidate package files are byte-identical to Rule 5.

## Verification

Focused command:

```powershell
py -3.11 -B -m unittest discover -s autonomous_gold_20260715/implementation/archaludon_historical_silver_single_resolver_salvage_rule9_trial_v1/tests -p test_*.py -q
```

Outcome: exit `0`; `35/35` groups passed (`13` Rule 1, `9` Rule 4, `6` Rule 5, `7` Rule 9). Rule 9 fixtures cover both seats and complete Gear->Boss->target->attack for attacks `223`, `224`, `253`, and `1212`; all eight Boss/Explorer/Lillie subsets; two physical Bosses with minimum serial; option and looking reversal; identical retry at every emitted step; exact no-Boss confirmation; one/multiple/zero attack and target boundaries; non-Gear parent; Boss in hand; current terminal; HP one above lethal; Supporter used; no Bench; deck zero; status, Tool, Stadium, and ability rejection; wrong Gear effect/serial; malformed/duplicate reveal and target roles; stale deck ledger; changed attack; owner collision; metadata drift; and opponent hidden-hand identity invariance. Raw and summary artifacts are `focused_test_raw.txt` and `focused_test_summary.json`.

Structure/import/deck command:

```powershell
py -3.11 -B autonomous_gold_20260715/implementation/archaludon_historical_silver_single_resolver_salvage_rule9_trial_v1/verify_candidate.py
```

Outcome: exit `0`; seven Python files compiled in memory; import passed; one top-level/final runtime `agent`; one `_resolve`; one owner assignment; one static parent call inside `agent`; Rule 7/8 absent; `13` package files and all `12` non-`main.py` files preserved; deck `60`; ACE SPEC `1`; zero cache paths. Machine output is `verification_summary.json`.

Full shadow command:

```powershell
py -3.11 -B autonomous_gold_20260715/implementation/archaludon_historical_silver_single_resolver_salvage_rule9_trial_v1/run_shadow.py
```

Outcome: exit `0`; ordered corpus SHA-256 `A29B61F31A84401404BF1701DDC5CF959A330EA6894C9283C533017B99ED4C9D`; all `46` current plus `207` historical paths; both seats; `252` readable replays plus known malformed current episode `89287701`; `30,977` callbacks; zero invalid actions, wrapper exceptions, Rule 9 starts, Boss hits, misses, Boss plays, targets, terminal attack emissions, confirmations, irreversible aborts, first differences, or other action differences. `shadow_differences.json` is the complete empty classification, so every observed first difference was inspected vacuously. Artifacts are `shadow_source_manifest.json`, `shadow_summary.json`, and `shadow_differences.json`.

Checked-engine smoke commands:

```powershell
.venv-rl/Scripts/python.exe -B tools/run_local_battle.py --engine-dir analysis_outputs/cynthia_v9_vs_v11_poffin_role_selection_20260713/seeded_engine --agent-a autonomous_gold_20260715/candidates/archaludon_historical_silver_single_resolver_salvage_rule9_trial_v1 --agent-b autonomous_gold_20260715/baseline/historical_silver_archaludon_54495224 --deck-a autonomous_gold_20260715/candidates/archaludon_historical_silver_single_resolver_salvage_rule9_trial_v1/deck.csv --deck-b autonomous_gold_20260715/baseline/historical_silver_archaludon_54495224/deck.csv --games 1 --max-steps 1000 --trace-dir autonomous_gold_20260715/implementation/archaludon_historical_silver_single_resolver_salvage_rule9_trial_v1/smoke/candidate_p0/traces --trace-options --seed-base 803209001 --engine-seed --summary autonomous_gold_20260715/implementation/archaludon_historical_silver_single_resolver_salvage_rule9_trial_v1/smoke/candidate_p0/summary.jsonl
.venv-rl/Scripts/python.exe -B tools/run_local_battle.py --engine-dir analysis_outputs/cynthia_v9_vs_v11_poffin_role_selection_20260713/seeded_engine --agent-a autonomous_gold_20260715/baseline/historical_silver_archaludon_54495224 --agent-b autonomous_gold_20260715/candidates/archaludon_historical_silver_single_resolver_salvage_rule9_trial_v1 --deck-a autonomous_gold_20260715/baseline/historical_silver_archaludon_54495224/deck.csv --deck-b autonomous_gold_20260715/candidates/archaludon_historical_silver_single_resolver_salvage_rule9_trial_v1/deck.csv --games 1 --max-steps 1000 --trace-dir autonomous_gold_20260715/implementation/archaludon_historical_silver_single_resolver_salvage_rule9_trial_v1/smoke/candidate_p1/traces --trace-options --seed-base 803209002 --engine-seed --summary autonomous_gold_20260715/implementation/archaludon_historical_silver_single_resolver_salvage_rule9_trial_v1/smoke/candidate_p1/summary.jsonl
```

Outcome: candidate seat `0`, seed `803209001`, terminal in `151` steps, zero action errors, no max-step hit; candidate seat `1`, seed `803209002`, terminal in `138` steps, zero action errors, no max-step hit. Raw traces and summaries are under `smoke/`; combined machine output is `smoke_summary.json`.

## Hashes and evaluator handoff

- Candidate `main.py`: `FC2ACC8F1AA08AC32D85B20001E420D9D036853B117FF11539D985D99B7395D0`.
- Deck: `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`.
- Stored Historical-Silver parent: `F4B578453C9D953BE94885144DD50E05DBA4510DF3340BE27ADE07495896046E`.
- Rule 9 fixture: `DCF4BB8123E0AF49B0B70F645F41D517C4ECBD23E20341F796BA462B4ED8E8ED`.
- Verification runner: `C4E0F504924CAA86607E75938A008FB4E4479078FA8C304D073981A960626695`.
- Shadow runner: `B0944F6248FA4E8FA7DADDD7836977E833B4DC703312A2C21E8FE2AFC64023D3`.
- Shadow source manifest: `66FC543C849FD7AA29F41408297CFB8FF994DFB65774D850395951AC00FE9F07`.
- Shadow summary: `DC012467E07ECFB1A7304DB3CA7946EE7F139FA41E360ABA0AF927912061CFEB`.
- Shadow differences: `4F53CDA18C2BAA0C0354BB5F9A3ECBE5ED12AB4D8E11BA873C2F11161202B945`.
- Smoke seat `0` summary: `10DFB2FE08C1BAAC87EE898C91E3DEE14618195A502F89EF9BB0B6F923D49E4B`.
- Smoke seat `1` summary: `6DACC460541A01967D8D40F64404C8B137E396FA36CD0EE0877E7DEF4A4AE742`.

Known tradeoff/status: the branch deliberately rejects every incomplete or ambiguous public certificate and therefore remains dormant in the complete replay shadow. Because natural activity has `0` starts and `0` Boss-hit completions, the local decision is `DEFER-DORMANT`; the rule was not widened. The evaluator must run the immutable fixed160 against the exact hashes above, require at least one natural complete Gear->Boss->target->same-attack transaction across shadow/fixed160, inspect every first difference against the five allowed classes, and apply the frozen strength/fault/cell gates. If starts remain zero or no natural Boss-hit completion occurs, retain `DEFER-DORMANT`. No fixed160, archive, package, commit, push, Kaggle call, or external publication was performed.
