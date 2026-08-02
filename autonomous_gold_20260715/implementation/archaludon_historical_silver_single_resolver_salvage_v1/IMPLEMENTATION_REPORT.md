# Rule 1 implementation report

## Scope and intent

- Baseline: exact Historical-Silver Archaludon `main.py` and unchanged deck.
- Candidate: a thin wrapper with one final `agent`, one `_resolve`, no scorer or
  chooser copy, and no transaction owner.
- Implemented behavior: `EXACTLY_ONE_DURALUDON_SETUP_V1` only.  The wrapper
  commits the exact parent-selected own-hand Active card ID/serial/seat during
  `SETUP_ACTIVE_POKEMON`.  At `SETUP_BENCH_POKEMON`, it may replace only exact
  parent `[]` with the single minimum-serial Duraludon option after all frozen
  proof gates pass.  An identical or option-permuted retry rebinds the same
  serial and never substitutes another copy.  Every rejection returns the
  original parent action object.
- Proposal keys are exactly `rule_id`, `action`, `category`, `purpose`,
  `exact_proof`, and `transaction`; `transaction` is always `None`.

## Files and hashes

| File | SHA-256 |
|---|---|
| `candidates/.../main.py` | `153D8461FB66927DB9731CBE614B71FF5398B8EAE8980AE0BB4D46ADD0E8792A` |
| `candidates/.../_historical_silver_parent.py` | `F4B578453C9D953BE94885144DD50E05DBA4510DF3340BE27ADE07495896046E` |
| `candidates/.../deck.csv` | `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A` |
| `implementation/.../tests/test_rule1_setup.py` | `03C47201A5FA6102AC3932018158712A28EB40D7310455D0033BC131154648AE` |
| `implementation/.../smoke/summary.jsonl` | `5A5FFE4BADD9B12049D200688C88F3962013834F633FF426A03BB3CC2620735C` |

The frozen parent and deck hashes exactly match `REQUIREMENTS.md`.  The
candidate contains the copied runtime `cg/` files and `requirements.txt`, plus
the wrapper, exact parent, and deck.  No archive was created.

## Verification commands and outcomes

### Focused fixtures

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
py -3.11 -B -m unittest discover -s 'autonomous_gold_20260715/implementation/archaludon_historical_silver_single_resolver_salvage_v1/tests' -p 'test_*.py' -v
```

Outcome: exit 0; 13 test groups passed.  Coverage includes both seats,
one/multiple Duraludon, reversed/permuted options, identical/reversed retry,
same-serial rebinding, no replacement, Duraludon/Relicanth/unknown Active,
visible/already-emitted/full Bench, count bounds, no Duraludon, malformed hand,
owner/serial/index/card binding, duplicate serials, turn/seat/result mismatch,
Active serial mismatch, exact identity on Active setup/Mulligan/IS_FIRST/deck
request, exact proposal/telemetry fields, no owner, one public agent, one
resolver, last-callable loader order, and exactly one parent call per callback.

### Compile, import, deck, parent, loader, and cache checks

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
py -3.11 -B -c "from pathlib import Path; files=[Path(r'autonomous_gold_20260715/candidates/archaludon_historical_silver_single_resolver_salvage_v1/main.py'),Path(r'autonomous_gold_20260715/candidates/archaludon_historical_silver_single_resolver_salvage_v1/_historical_silver_parent.py'),Path(r'autonomous_gold_20260715/implementation/archaludon_historical_silver_single_resolver_salvage_v1/tests/test_rule1_setup.py')]; [compile(p.read_text(encoding='utf-8'),str(p),'exec') for p in files]; print('COMPILE_OK', len(files))"
py -3.11 -B -c "import hashlib,sys; from pathlib import Path; c=Path(r'autonomous_gold_20260715/candidates/archaludon_historical_silver_single_resolver_salvage_v1').resolve(); sys.path.insert(0,str(c)); import main; deck=[int(x) for x in (c/'deck.csv').read_text().splitlines() if x.strip()]; ace=sum(bool(main._parent.CARD_DB[x].aceSpec) for x in deck); print('IMPORT_OK', callable(main.agent)); print('DECK_COUNT',len(deck)); print('ACE_SPEC_COUNT',ace); print('PUBLIC_FUNCTIONS',[n for n,v in main.__dict__.items() if callable(v) and getattr(v,'__module__',None)==main.__name__ and not n.startswith('_')]); print('PARENT_SHA256',hashlib.sha256((c/'_historical_silver_parent.py').read_bytes()).hexdigest().upper()); print('DECK_SHA256',hashlib.sha256((c/'deck.csv').read_bytes()).hexdigest().upper())"
Get-ChildItem 'autonomous_gold_20260715/candidates/archaludon_historical_silver_single_resolver_salvage_v1','autonomous_gold_20260715/implementation/archaludon_historical_silver_single_resolver_salvage_v1' -Recurse -Force | Where-Object { $_.Name -eq '__pycache__' -or $_.Extension -eq '.pyc' }
```

Outcome: `COMPILE_OK 3`, import callable, deck count 60, ACE SPEC count 1,
public local functions exactly `['agent']`, frozen hashes matched, and the cache
query returned no entries.  Whole-parent hash identity also proves its
`score_option` and `choose_options` bytes were not changed.

### Single seeded engine smoke

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
py -3.11 -B 'tools/run_local_battle.py' --engine-dir 'analysis_outputs/cynthia_v9_vs_v11_poffin_role_selection_20260713/seeded_engine' --agent-a 'autonomous_gold_20260715/candidates/archaludon_historical_silver_single_resolver_salvage_v1' --agent-b 'analysis_outputs/reference_agents/historical_silver_archaludon_54495224' --games 1 --max-steps 1000 --trace-dir 'autonomous_gold_20260715/implementation/archaludon_historical_silver_single_resolver_salvage_v1/smoke/traces' --trace-options --seed-base 803202601 --engine-seed --summary 'autonomous_gold_20260715/implementation/archaludon_historical_silver_single_resolver_salvage_v1/smoke/summary.jsonl'
```

Outcome: exit 0; started true, 77 steps, action errors 0, max-step false,
terminal result 0.  The repository's file-spec loader successfully loaded the
wrapper and its local exact-parent module.  A pre-fix invocation exposed that
this loader does not insert the candidate directory into `sys.path`; the only
integration correction was the standard local-directory insertion at the top
of the wrapper, after which all focused fixtures and this smoke passed.

## Known tradeoffs and evaluator instructions

- The single smoke seed did not offer Duraludon to candidate seat 0 during
  setup, so it validates loader/runtime non-destruction but not a natural Rule
  1 activation.  Rule activation and retry semantics are covered by focused
  fixtures.  Do not widen the rule because of this dormant smoke.
- Replay shadow and frozen fixed160 were intentionally not run by this worker.
  The evaluator should run the immutable parent/candidate schedule, both seats
  and identical seeds, verify zero invalid actions/exceptions, and inspect
  every first difference.  Every difference must be a turn-0
  `SETUP_BENCH_POKEMON` selection of exactly one minimum-serial Duraludon after
  a ledger-bound Cinderace Active; telemetry `parent_call_count` must remain 1
  and both owner fields must remain `None`.
- Explicitly include option-order permutation and duplicate callback checks in
  replay shadow.  A retry must select the originally emitted serial; a changed
  prompt, missing serial, visible Duraludon, or any ambiguous binding must be
  exact-parent fallback.
- No fixed160, fixed760, broad simulation, package/archive, commit, push, or
  Kaggle operation was performed.
