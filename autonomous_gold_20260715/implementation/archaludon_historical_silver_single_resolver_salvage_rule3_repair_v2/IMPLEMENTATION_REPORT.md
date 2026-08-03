# Rule 3 repair v2 implementation evidence

## Candidate

- Baseline: `autonomous_gold_20260715/final/archaludon_historical_silver_single_resolver_salvage_v1`
- Candidate: `autonomous_gold_20260715/candidates/archaludon_historical_silver_single_resolver_salvage_rule3_repair_v2`
- Candidate `main.py` SHA-256: `4287A616E1611F5697964D9F4065978EED1CEA72CDB48C9F63F1430D69106C35`
- Controlling parent-prefix amendment SHA-256: `C55458C1A8AD4649845BDAE707067DAD295EF7D1F938DF5371E2502EF263344C`
- Candidate `deck.csv` SHA-256: `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`
- Parent module SHA-256: `F4B578453C9D953BE94885144DD50E05DBA4510DF3340BE27ADE07495896046E`
- Package entries: `13`; the only baseline package difference is `main.py`.
- No archive was created.

## Behavioral intent

Integrate the two declared-complete Ultra Ball Rule 3 routes into the existing single resolver and shared `_materialization_owner`. The Active-Duraludon route is globally gated at `current.turn >= 3` and `appearThisTurn == False`. The repair preserves Silver's exact physical discard action and exact same-card search action, rebinds the searched target from the actual hand and legal post-search option, verifies the live evolved Active before Alloy, and records an explicit terminal owner snapshot after irreversible aborts. Existing Rule 1/4/5 helper bodies remain source-identical except for the four shared integration surfaces: `_owner_view`, `_resolve`, `_emit_telemetry`, and `agent`.

When Silver selects a different legal physical Ultra Ball cost pair, Rule 3 now adopts that exact parent pair instead of stopping. Turbo Flare can always continue from the unchanged paid attacker and empty Bench. The Active-ex route adopts it only after recomputing exact attached, discarded, and retained Metal Energy into at most two Assemble Alloy attachments plus an optional manual attachment. A nonviable parent pair falls back cleanly while provisional, or uses the original planned pair only when the target is mathematically guaranteed outside the Prizes. A search whiff after adopting the parent pair is also a clean provisional release because every emitted action remains parent-identical.


After exact Active-ex attack readiness, Rule 3 now retains sole ownership in `ACTIVE_READY_PARENT_PREFIX` and emits every legal Historical-Silver setup/effect action byte-for-byte until Silver itself selects Metal Defender. END, RETREAT, another attack, readiness/Active/turn discontinuity, unowned or invalid effects, duplicate-parent mismatch, and callback-budget exhaustion abort irreversibly without replacing the parent action. Duplicate callbacks preserve the original physical references and do not consume the 64-callback budget. Turbo Flare now preserves an eligible parent's exact Basic Metal copies and order for the required 0--3 cards; only an ineligible parent action uses the deterministic serial fallback.
## Verification commands and outcomes

All commands ran from the repository root.

1. Focused two-route/two-seat callback suite:

   ```powershell
   & '.venv-rl/Scripts/python.exe' -B 'autonomous_gold_20260715/implementation/archaludon_historical_silver_single_resolver_salvage_rule3_repair_v2/run_focused.py'
   ```

   Exit `0`; `276` passed, `0` failed. In addition to the prior two-route and dynamic-parent-cost cases, this covers both seats through immediate parent Metal Defender and the full Lillie -> Poke Pad/search -> Ultra Ball discard/search -> Basic placement -> Metal Defender prefix; MAIN/effect/attack duplicates and option permutations; terminal precedence; END, RETREAT, another attack, Active identity/serial/lineage, turn, readiness, monotonic count, unowned/invalid effects, multi/unclassified MAIN, duplicate-parent mismatch, and 64/65 callback boundaries; plus Turbo 0/1/2/3 eligible parent-copy order, fallback, duplicate, and reordered-option behavior.

2. Inherited Rule 1/4/5 tests:

   ```powershell
   & '.venv-rl/Scripts/python.exe' -B -m unittest discover -s 'autonomous_gold_20260715/implementation/archaludon_historical_silver_single_resolver_salvage_rule3_repair_v2/tests' -v
   ```

   Exit `0`; `28` tests passed.

3. Syntax compilation without emitting package bytecode:

   ```powershell
   & '.venv-rl/Scripts/python.exe' -B -c "from pathlib import Path; roots=[Path(r'autonomous_gold_20260715/candidates/archaludon_historical_silver_single_resolver_salvage_rule3_repair_v2'),Path(r'autonomous_gold_20260715/implementation/archaludon_historical_silver_single_resolver_salvage_rule3_repair_v2')]; files=[p for root in roots for p in root.rglob('*.py')]; [compile(p.read_text(encoding='utf-8-sig'),str(p),'exec') for p in files]; print('compiled_python_files',len(files))"
   ```

   Exit `0`; `12` Python files compiled. (`utf-8-sig` is required because inherited `cg/api.py` has a BOM.)

4. Import and immutable metadata check:

   ```powershell
   & '.venv-rl/Scripts/python.exe' -B -c "import importlib.util,sys,pathlib; p=pathlib.Path(r'autonomous_gold_20260715/candidates/archaludon_historical_silver_single_resolver_salvage_rule3_repair_v2/main.py'); sys.path.insert(0,str(p.parent)); spec=importlib.util.spec_from_file_location('rule3_repair_v2_import_check',p); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); print('import_ok',callable(m.agent)); print('metadata_exact',m._r3_metadata_exact())"
   ```

   Exit `0`; import callable `True`, metadata exact `True`.

5. Deck legality using checked card metadata:

   ```powershell
   & '.venv-rl/Scripts/python.exe' -B -c "import sys,pathlib; sys.path.insert(0,r'autonomous_gold_20260715/candidates/archaludon_historical_silver_single_resolver_salvage_rule3_repair_v2'); from cg.api import all_card_data; d=[int(x) for x in pathlib.Path(r'autonomous_gold_20260715/candidates/archaludon_historical_silver_single_resolver_salvage_rule3_repair_v2/deck.csv').read_text().splitlines()]; cards={c.cardId:c for c in all_card_data()}; print(len(d),[x for x in d if cards[x].aceSpec])"
   ```

   Exit `0`; exactly `60` cards and exactly one ACE SPEC, card `1159`.

6. Structural/source comparison:

   ```powershell
   & '.venv-rl/Scripts/python.exe' -B -c "import ast,pathlib; bp=pathlib.Path(r'autonomous_gold_20260715/final/archaludon_historical_silver_single_resolver_salvage_v1/main.py'); cp=pathlib.Path(r'autonomous_gold_20260715/candidates/archaludon_historical_silver_single_resolver_salvage_rule3_repair_v2/main.py'); bs=bp.read_text(); cs=cp.read_text(); b=ast.parse(bs); c=ast.parse(cs); bf={n.name:n for n in b.body if isinstance(n,ast.FunctionDef)}; cf={n.name:n for n in c.body if isinstance(n,ast.FunctionDef)}; print([n for n in bf if ast.get_source_segment(bs,bf[n])!=ast.get_source_segment(cs,cf[n])]); print(len(bf)-sum(ast.get_source_segment(bs,bf[n])!=ast.get_source_segment(cs,cf[n]) for n in bf)); print(list(cf)[-1])"
   ```

   Exit `0`; only `_owner_view`, `_resolve`, `_emit_telemetry`, and `agent` differ among the 56 inherited functions; 52 common helper bodies are source-identical; last top-level callable is `agent`. AST checks also found one top-level `agent`, one top-level `_resolve`, and one static `_parent.agent` call.

7. Exact checked-engine seed `271958318`, candidate in seat 0 versus `submission_archaludon_gtmidguard_lucariobev_crustledeckguard_archattach_ruleinline_20260710`:

   ```powershell
   & '.venv-rl/Scripts/python.exe' tools/run_local_battle.py --engine-dir analysis_outputs/cynthia_v9_vs_v11_poffin_role_selection_20260713/seeded_engine --agent-a autonomous_gold_20260715/candidates/archaludon_historical_silver_single_resolver_salvage_rule3_repair_v2 --agent-b submission_archaludon_gtmidguard_lucariobev_crustledeckguard_archattach_ruleinline_20260710 --games 1 --max-steps 1000 --trace-dir autonomous_gold_20260715/implementation/archaludon_historical_silver_single_resolver_salvage_rule3_repair_v2/seed271958318/candidate/traces --trace-options --seed-base 271958318 --engine-seed --summary autonomous_gold_20260715/implementation/archaludon_historical_silver_single_resolver_salvage_rule3_repair_v2/seed271958318/candidate/summary.jsonl
   ```

   Exit `0`; `133` steps, result `0`, `0` action errors, no max-step hit. The corresponding frozen-parent command used the same arguments with `--agent-a autonomous_gold_20260715/final/archaludon_historical_silver_single_resolver_salvage_v1` and the sibling `parent` output directory. All `133/133` actions and all compared prompt/state/log fields were identical; both trace SHA-256 values are `350D9A7103BB9E0036CBFD09A235ACB1658A1C49F65CA44477A504AA9627DC6A`.

8. Checked-engine seat-1 smoke:

   ```powershell
   & '.venv-rl/Scripts/python.exe' -B tools/run_local_battle.py --engine-dir analysis_outputs/cynthia_v9_vs_v11_poffin_role_selection_20260713/seeded_engine --agent-a submission_archaludon_gtmidguard_lucariobev_crustledeckguard_archattach_ruleinline_20260710 --agent-b autonomous_gold_20260715/candidates/archaludon_historical_silver_single_resolver_salvage_rule3_repair_v2 --games 1 --max-steps 1000 --trace-dir autonomous_gold_20260715/implementation/archaludon_historical_silver_single_resolver_salvage_rule3_repair_v2/smoke_seat1/traces --trace-options --seed-base 271958318 --engine-seed --summary autonomous_gold_20260715/implementation/archaludon_historical_silver_single_resolver_salvage_rule3_repair_v2/smoke_seat1/summary.jsonl
   ```

   Exit `0`; `133` steps, result `0`, `0` action errors, no max-step hit.

9. Final layout/hash check:

   Candidate and baseline each contain `13` files, no `__pycache__`, and no non-`main.py` hash difference. No archive/package was created.

## Evaluator attention

The engine results in items 7--8 predate SHA `4287A616E1611F5697964D9F4065978EED1CEA72CDB48C9F63F1430D69106C35` and are not current-amendment acceptance evidence.

Run the parent-owned natural gates. Seed `271958323` must retain ownership across Silver's complete setup/effect prefix and preserve its eventual physical Metal Defender action and win. Seed `271958324` must preserve the parent's exact Turbo Basic Metal serial order. Seed `271958318` must stay trace-identical. Also verify no natural Rule 3 start reaches any irreversible prefix abort before freezing a new evaluation SHA.
