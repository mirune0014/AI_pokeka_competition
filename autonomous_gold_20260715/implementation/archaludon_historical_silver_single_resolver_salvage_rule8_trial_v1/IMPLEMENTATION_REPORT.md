# Rule 8 trial implementation report

## Scope and behavioral intent

- Frozen parent: accepted Rule 5 `main.py` SHA-256 `D966E455E5110F9D5616195AEAAC8663E6A92F310DAFC4B7F79E4D37149A9C62`.
- Frozen selection: `STRATEGY_SELECTION.md` SHA-256 `6E9B540F6FC7E5927222725B1ED0D0280D10EE5989B24BD49D1D6E984303C04F` plus controlling undamaged-Duraludon amendment SHA-256 `C6AAD9BAB0A3FC6F66A608236C22DA08F58D4A726E10AD7EAA035D456F17A6D5`.
- Added only `PUBLIC_EXACT_SAME_ACTIVE_ATTACK_DOMINANCE_V1`. The once-called Rule 5 parent remains the complete policy, there is one final `agent`, one `_resolve`, and the existing single transaction owner is unchanged. Rule 8 is stateless and emits no owner.
- Resolver order is unchanged through active transactions, Rule 5 exact current wins, Rule 4 attack-preserving materialization, and Rule 5 higher-Prize Boss conversion. Rule 8 is the final ordinary-`MAIN` branch after all of them.
- Rule 8 accepts only a unique parent `ATTACK 223` and unique legal `223`/`224` options on the same uniquely identified Active Duraludon `169` and unchanged uniquely identified opposing Active. It semantically rebinds by seat, attacker ID/serial, target ID/serial, and attack ID, so option order is not identity.
- The branch reuses the accepted Rule 5 exact public-board, option, card/attack metadata, Basic Metal Energy, modifier, and damage/Prize helpers. The fixed pair metadata must expose only attack ID, name, text, printed damage, and Energy cost; its exact known resource consequences are zero recoil, self-damage, Energy discard/consumption, and additional side effects. It computes final damage, KO, and Prize take for both attacks and emits `224` only when all three dimensions are no worse and at least one is strictly better.
- Unknown/malformed/duplicate binding, Tool, unsupported Stadium, status/modifier, Energy mismatch, invalid Weakness/Resistance, attack metadata/effect disagreement, equal outcome, active owner, or any higher-priority Rule 5 proposal returns the exact Rule 5 action. Rule 7 is absent.
- The candidate deck, stored Historical-Silver parent, requirements, and `cg` package are byte-identical to Rule 5.

## Verification

Focused command:

```powershell
py -3.11 -B -m unittest discover -s autonomous_gold_20260715/implementation/archaludon_historical_silver_single_resolver_salvage_rule8_trial_v1/tests -p test_*.py -v
```

Outcome: exit `0`; `32/32` test groups passed (`13` inherited Rule 1, `9` inherited Rule 4, `6` inherited Rule 5, `4` Rule 8). Rule 8 fixtures cover both seats; undamaged non-KO `30 -> 80`; damaged non-KO `30 -> 110`; non-KO to exact KO; exact Prize gain; reversed options; identical prompt retry; wrong parent/Active; missing, duplicate, or differently bound attacks; duplicate serial; metadata, Tool, Stadium, modifier, Weakness, Resistance, Energy, recoil, discard, and secondary-effect mismatch; active owner; terminal Rule 5 precedence; malformed callback; and equal comparison fail-closed. Raw output is `focused_test_raw.txt`; machine summary is `focused_test_summary.json`.

Structure/compile/import command:

```powershell
py -3.11 -B autonomous_gold_20260715/implementation/archaludon_historical_silver_single_resolver_salvage_rule8_trial_v1/verify_candidate.py
```

Outcome: exit `0`; seven Python files compiled in memory; import passed; one top-level `agent`; one `_resolve`; one static `_parent.agent` call inside `agent`; final top-level and runtime-local function `agent`; Rule 7 absent; `13` candidate package files with all `12` non-`main.py` files preserved; deck count `60`; ACE SPEC count `1`; zero `__pycache__`/`.pyc`. Raw and machine outputs are `verification_raw.txt` and `verification_summary.json`.

Full two-seat current/historical shadow command:

```powershell
py -3.11 -B autonomous_gold_20260715/implementation/archaludon_historical_silver_single_resolver_salvage_rule8_trial_v1/run_shadow.py
```

Outcome: exit `0`; ordered corpus SHA-256 `A29B61F31A84401404BF1701DDC5CF959A330EA6894C9283C533017B99ED4C9D`; all `46` current plus all `207` historical replay paths; both seats; `252` readable replays plus known malformed current episode `89287701`; `30,977` callbacks; zero invalid actions; zero wrapper exceptions; zero natural Rule 8 starts; zero action differences. `shadow_differences.json` is therefore the complete empty first-difference classification. The local status is dormant pending the evaluator's fixed160; conditions were not widened.

Checked-engine smoke commands used `tools/run_local_battle.py`, the checked seeded engine, exact Historical-Silver as opponent, one game per candidate seat, seeds `803208001` and `803208002`, and max steps `1000`. Candidate seat `0` terminated in `111` steps with zero action errors and no max-step hit. Candidate seat `1` terminated in `95` steps with zero action errors and no max-step hit. Raw traces and summaries are under `smoke/candidate_p0` and `smoke/candidate_p1`.

## Final hashes and evaluator handoff

- Candidate `main.py`: `B0BD42D71617EEA041AFCF54F84B9C92FD894A2A3A6BD1CCAD95645CD1952507`.
- Deck: `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`.
- Stored Historical-Silver parent: `F4B578453C9D953BE94885144DD50E05DBA4510DF3340BE27ADE07495896046E`.
- Rule 8 fixture: `15CE7A4A1A725E45929C7ECEBDD4C10870D26D09D5633295489164F90451EB86`.
- Shadow runner: `562D2DD8710DF68FFA654414B8C25505D4B9F8E7AC560880FE65785202EE33BA`.
- Shadow source manifest: `66FC543C849FD7AA29F41408297CFB8FF994DFB65774D850395951AC00FE9F07`.
- Shadow summary: `1DB74E1A069FC1F21B15143F27A91AF9FF8AFD3F3E34014686F4644226EB5FF8`.
- Shadow differences: `4F53CDA18C2BAA0C0354BB5F9A3ECBE5ED12AB4D8E11BA873C2F11161202B945`.
- Smoke seat `0` summary: `CB4E0A84E2CCCF92BB1A3C0BB5D5618D698EE14D5C995A348E40B10DBC965782`.
- Smoke seat `1` summary: `3A6D74F267CEF5D9F92B3D857500A6B8BBBEE2195A39503FF83B6D5E8FC8A476`.

Known tradeoff: the exact boundary rejects all Tools, Special Energy, unsupported Stadiums/modifiers, unknown target abilities, and any metadata/effect ambiguity. The full replay shadow contains no natural Rule 8 start, so it supplies no causal action difference; focused engine-shaped fixtures prove the intended branch and the checked-engine games prove legal execution only. The evaluator must run the immutable fixed160 against the exact hashes above, classify every first difference strictly as same-attacker/same-target `ATTACK 223 -> ATTACK 224` with a persisted Pareto proof, and apply the frozen fault/regression/cell gates. If shadow plus fixed160 has zero starts, record `DEFER-DORMANT` and do not integrate. No fixed160, archive, package, commit, push, Kaggle call, or external publication was performed.
