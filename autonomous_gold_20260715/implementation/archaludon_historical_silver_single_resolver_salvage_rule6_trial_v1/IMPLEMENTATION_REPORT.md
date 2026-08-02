# Rule 6 trial implementation report

## Scope and behavioral intent

- Frozen parent: accepted Rule 5 candidate `archaludon_historical_silver_single_resolver_salvage_rule5_trial_v1`, `main.py` SHA-256 `D966E455E5110F9D5616195AEAAC8663E6A92F310DAFC4B7F79E4D37149A9C62`.
- Frozen strategy: `STRATEGY_SELECTION.md` SHA-256 `428CBF0B516592AEB1BD7BABA939ADC5E2357F4D4FD53E493C30D9F5C805EBFE`.
- Added only Rule ID `PARENT_POKE_PAD_EMPTY_BENCH_DURALUDON_ONE_METAL_READY_SUCCESSOR_TRANSACTION_V1` for role `DURALUDON_ONE_METAL_READY_SUCCESSOR`.
- Activation requires the once-called exact parent to select physical Poké Pad `1152`, exact Pad/Duraludon/Hammer In/Basic Metal metadata, an exactly empty Bench with capacity, no Duraludon `169` in hand, unused attachment, a visible lowest-serial Basic Metal `8`, one distinct legal registered current attack, an exact false Rule 5 terminal proof, and exact public state/options/deck count.
- The shared owner performs `PAD_PLAY_EMITTED -> PAD_TARGET_EMITTED -> DURALUDON_BENCH_EMITTED -> METAL_ATTACH_EMITTED -> CLEAR_TO_CURRENT_PARENT`. It chooses the lowest physical Duraludon serial and lowest equivalent UI position, confirms every public transition, places that same Basic on the empty Bench, attaches the frozen lowest-serial Metal, proves Hammer In `223` payable, clears, and returns the parent action computed once for the actual current callback.
- If Duraludon is absent and empty selection is legal, the owner emits `[]`, repeats `[]` for an identical callback, then clears to the current parent after exact effect resolution. Cinderace `666` and non-ex Archaludon `840` are never substituted.
- Existing Rule 1, Rule 4, Rule 5, exact Historical-Silver parent/scorer, and all non-`main.py` package files remain unchanged. There is one public `agent`, one `_resolve`, one shared `_materialization_owner`, one static `_parent.agent` call, and the existing six-field proposal schema.

## Focused and inherited tests

Command:

```powershell
py -3.11 -B -m unittest discover -s autonomous_gold_20260715/implementation/archaludon_historical_silver_single_resolver_salvage_rule6_trial_v1/tests -p test_*.py -q
```

Outcome: exit `0`; `35/35` test groups passed: `13` inherited Rule 1, `9` inherited Rule 4, `6` inherited Rule 5, and `7` Rule 6. Rule 6 coverage includes complete both-seat Pad/target/hand/Bench/Metal/ready paths; whiff and parent recovery; duplicate callbacks and option permutations at every owned stage; multiple physical Duraludon cards and equivalent duplicate UI rows; lowest Metal serial; conflicting duplicate semantics; wrong effect and source; failed target movement and attachment; non-Pad parent; nonempty/no-capacity Bench; no Metal; used attachment; Duraludon already in hand; no/multiple current attack IDs; exact terminal precedence; existing owner; and seat/turn/result discontinuity.

## Frozen current plus historical shadow

Command:

```powershell
py -3.11 -B autonomous_gold_20260715/implementation/archaludon_historical_silver_single_resolver_salvage_rule6_trial_v1/run_shadow.py
```

Outcome: exit `0`; frozen ordered corpus SHA-256 `B88C25BC8F26F959F85D00D27FD7B148D22034D71B2588DF73AAF8C8E0B15004`; `46` current plus `32` frozen historical paths; `77` readable replays plus known malformed episode `89287701`; `4,262` callbacks; natural starts `1`; action differences `1`; ready completions `0`; whiff emissions/completions `0/0`; invalid actions `0`; exceptions `0`; fault count `0`; all differences allowed.

The only first/action difference is `episode_89288308`, seat `1`, step `45`, turn `4`, class `POKE_PAD_DURALUDON_TARGET`. Pad serial `76` and frozen Metal serial `112` are recorded; the saved current attack is Metal Defender `253` on Active Archaludon ex serial `70`. The parent selects Duraludon serial `66`; Rule 6 selects the lower physical serial `65`. The next recorded observation follows the parent's serial `66`, so the candidate detects that counterfactual target-movement mismatch at step `46`, clears its owner, and returns the current parent. This one fail-closed is recorded separately as `owned_fail_closed_count=1`; it is not an illegal action, exception, stale owner, or wrapper fault.

Artifacts:

- `shadow_summary.json` SHA-256 `63EBFE999FD8918C67A45DE2401CC53224EAFFE0A8C2520E081ABC74AFE87ADA`
- `shadow_differences.json` SHA-256 `55AB30EA634CD9A3359A19B523AEB5278F6966D5E8A72167630EB45C55B9F8FF`

## Compile, import, package, deck, loader, and cache checks

Command:

```powershell
py -3.11 -B autonomous_gold_20260715/implementation/archaludon_historical_silver_single_resolver_salvage_rule6_trial_v1/verify_candidate.py
```

Outcome: exit `0`; `7` changed/verification Python files compiled in memory; import passed; one top-level `agent`; one `_resolve`; one static parent call; loader-last function is callable `agent`; deck count `60`; ACE SPEC count `1`; package file count `13`; all `12` non-`main.py` files byte-identical to the Rule 5 parent; zero `__pycache__` directories and zero `.pyc` files. The one temporary compile cache created during initial development was removed from the assigned candidate directory before final verification.

## Both-seat checked-engine smoke

Commands:

```powershell
.venv-rl/Scripts/python.exe -B tools/run_local_battle.py --engine-dir analysis_outputs/cynthia_v9_vs_v11_poffin_role_selection_20260713/seeded_engine --agent-a autonomous_gold_20260715/candidates/archaludon_historical_silver_single_resolver_salvage_rule6_trial_v1 --agent-b autonomous_gold_20260715/baseline/historical_silver_archaludon_54495224 --deck-a autonomous_gold_20260715/candidates/archaludon_historical_silver_single_resolver_salvage_rule6_trial_v1/deck.csv --deck-b autonomous_gold_20260715/baseline/historical_silver_archaludon_54495224/deck.csv --games 1 --max-steps 1000 --trace-dir autonomous_gold_20260715/implementation/archaludon_historical_silver_single_resolver_salvage_rule6_trial_v1/smoke/candidate_p0/traces --trace-options --seed-base 803206001 --engine-seed --summary autonomous_gold_20260715/implementation/archaludon_historical_silver_single_resolver_salvage_rule6_trial_v1/smoke/candidate_p0/summary.jsonl
.venv-rl/Scripts/python.exe -B tools/run_local_battle.py --engine-dir analysis_outputs/cynthia_v9_vs_v11_poffin_role_selection_20260713/seeded_engine --agent-a autonomous_gold_20260715/baseline/historical_silver_archaludon_54495224 --agent-b autonomous_gold_20260715/candidates/archaludon_historical_silver_single_resolver_salvage_rule6_trial_v1 --deck-a autonomous_gold_20260715/baseline/historical_silver_archaludon_54495224/deck.csv --deck-b autonomous_gold_20260715/candidates/archaludon_historical_silver_single_resolver_salvage_rule6_trial_v1/deck.csv --games 1 --max-steps 1000 --trace-dir autonomous_gold_20260715/implementation/archaludon_historical_silver_single_resolver_salvage_rule6_trial_v1/smoke/candidate_p1/traces --trace-options --seed-base 803206002 --engine-seed --summary autonomous_gold_20260715/implementation/archaludon_historical_silver_single_resolver_salvage_rule6_trial_v1/smoke/candidate_p1/summary.jsonl
```

Outcome: candidate seat `0`, seed `803206001`, terminal in `149` steps, action errors `0`, max-step false; candidate seat `1`, seed `803206002`, terminal in `152` steps, action errors `0`, max-step false.

- Aggregate smoke summary SHA-256: `FC29BEE8590967A50883FF0D9CDA74117A0EB99F34E442DE6970960ED2E2AACD`
- Seat 0 summary SHA-256: `79CC07973C7883E02BD28F84B5CB2D834DFA92035CE650131F4CE02CC652AE1C`
- Seat 1 summary SHA-256: `1DF743756905EF66D411A1FFFF6F370EF7B0CFA7BA763614A4A03563F65278DD`

## Final hashes, tradeoff, and evaluator handoff

- Candidate `main.py`: `02180DB5EA65356FA85301D7978EF088725FCA241B84EE68B29E102B77655164`
- Deck: `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`
- Stored Historical-Silver parent: `F4B578453C9D953BE94885144DD50E05DBA4510DF3340BE27ADE07495896046E`
- Rule 6 focused fixture: `84B8F058952699056C8825E248E5B84A694278FF9FCE56736A81FDD52B45E89C`
- Shadow runner: `770471F6343CA87056216B657AAC65815C4B577EC409415F38444023E18DC50F`
- Verification script: `787170BD8D7899D57C88DD4CD5CC48280D81627ACB2529F8292C4A2CEC1726AD`

Known tradeoff: the frozen shadow has one natural start and proves the intended lower-serial target difference, but its recorded continuation follows the parent-selected serial and therefore cannot observe the candidate's ready or whiff completion. Focused engine-shaped fixtures prove both completion routes, while the two smoke games prove legal execution but contain no attributable Rule 6 completion. The evaluator must run the parent-defined immutable comparison, inspect the `episode_89288308` first difference, require only the four allowed classes, verify same-turn Bench plus frozen-Metal readiness after successful search, inspect whiff recovery, and apply the strategy's dormant/incomplete and regression gates. No fixed160/additional simulation, archive, commit, push, package, Kaggle, or other external write was performed.
