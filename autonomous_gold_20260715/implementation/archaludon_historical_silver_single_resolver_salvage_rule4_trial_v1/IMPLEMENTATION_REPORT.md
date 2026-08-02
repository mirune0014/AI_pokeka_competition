# Rule 4 trial implementation report

## Scope and behavior

- Frozen source: accepted Rule 1 parent `archaludon_historical_silver_single_resolver_salvage_v1`, source `main.py` SHA-256 `153D8461FB66927DB9731CBE614B71FF5398B8EAE8980AE0BB4D46ADD0E8792A`.
- Trial: `archaludon_historical_silver_single_resolver_salvage_rule4_trial_v1`.
- Added only `PARENT_LILLIE_EXACT_CURRENT_MATERIALIZATION_V1` with the four frozen priorities: Duraludon placement, ready benched Duraludon evolution, Active third Basic Metal, and Full Metal Lab.
- Rule 4 starts only from an exact parent Lillie `1227` PLAY. It owns only `MATERIALIZATION_EMITTED`, rebinds semantic retries by serial, confirms the physical postcondition, clears, and returns the parent action computed once from the new callback. It never owns Lillie or emits an END.
- Rule 1 and the complete Historical-Silver parent remain unchanged. Rule 2 and Rule 3 are absent. No search, general scorer, attack chooser, Boss, Pokégear, Explorer, Ultra Ball, Poké Pad, Night Stretcher, or Turbo Flare policy was added.

## Verification

Focused command:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
py -3.11 -B -m unittest discover -s autonomous_gold_20260715/implementation/archaludon_historical_silver_single_resolver_salvage_rule4_trial_v1/tests -p test_*.py -q
```

Outcome: exit 0, `22/22` test groups passed (`13` inherited Rule 1 and `9` Rule 4 groups). Rule 4 coverage includes both seats for all four positive routes and parent return; every route's ambiguity/metadata/legality boundaries; new-this-turn Duraludon; ex Prize floor; used attachment; unknown Energy; occupied Stadium; opposing Metal; deterministic minimum serials; all-route retry/permutation; stale turn; owner conflict; failed receipt; non-Lillie parent; used Supporter; effect, mandatory, and post-attack callbacks.

In-memory compile/import/structure/deck check covered final `main.py`, both fixtures, and `run_shadow.py`: exit 0, four files compiled, import passed, one top-level `agent`, one `_resolve`, one static `_parent.agent` call in `agent`, final callable `agent`, deck count `60`, ACE SPEC count `1`. Candidate and evidence trees contain zero `__pycache__` directories and zero `.pyc` files. All `12` non-`main.py` candidate files are byte-identical to the frozen Rule 1 parent.

Frozen shadow command:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
py -3.11 -B autonomous_gold_20260715/implementation/archaludon_historical_silver_single_resolver_salvage_rule4_trial_v1/run_shadow.py
```

Outcome: exit 0; frozen corpus SHA-256 `B88C25BC8F26F959F85D00D27FD7B148D22034D71B2588DF73AAF8C8E0B15004`; `77` readable replays plus the known malformed episode `89287701`; `4,262` callbacks; zero invalid actions, exceptions, or wrapper faults; two natural starts/action differences; both immediately preceding Rule 1 actions were exact Lillie PLAYs; both differences classified `BENCH_EVOLUTION_BEFORE_LILLIE`.

Every changed callback was inspected:

- `episode_89279065`, seat 1, step 41, turn 8: parent Lillie serial `108`; unique Archaludon ex serial `68` evolution onto older bench Duraludon serial `66`, exactly three Basic Metal serials `113/115/112`, opposing Prize count `6`.
- `episode_89283885`, seat 1, step 34, turn 5: parent Lillie serial `107`; unique non-ex Archaludon serial `91` evolution onto older bench Duraludon serial `64`, exactly three Basic Metal serials `93/119/122`, opposing Prize count `6`.

The replay corpus is counterfactual after each first difference, so it contains zero materialization confirmations; focused checked poststates prove receipt/clear/re-evaluate behavior.

Checked-engine smoke used `tools/run_local_battle.py`, the checked seeded engine, and exact Historical-Silver as opponent:

- candidate seat 0, seed `803204001`: terminal in `53` steps, action errors `0`, max-step false;
- candidate seat 1, seed `803204002`: terminal in `105` steps, action errors `0`, max-step false.

## Final hashes and evaluator handoff

- trial `main.py`: `F6B6266D870D3F134544A91616C27673620557D149C0496CC2034E7674F010D9`
- stored Historical-Silver parent: `F4B578453C9D953BE94885144DD50E05DBA4510DF3340BE27ADE07495896046E`
- deck: `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`
- Rule 1 fixture: `943A6C53FFB61E7022ED0D15213A68B6B808B091914CF3E6B5FDB409989959AA`
- Rule 4 fixture: `EF1E6C82346028C72065D9C7059497DE292B1EB4156A0F32F1F932AD1FC9135A`
- shadow runner: `D88330CE7B093590178740875C64DBF5BC8D6406BA9CCA09B11BFBCB8A1A98B4`
- shadow summary: `B37F5162A12F25B9C179DF7E891FC3410621F1FAA59A83D4B2FB5D2AB3C3D594`
- shadow differences: `AFF84E8BE667B9D36834DA00356BE5C755C5965D3E13C321E38C0F1EFBC02718`
- smoke seat 0 summary: `BFFE8F9B3F04ADD06E95E83DE0892826E8E9185717A52C3623452B0032F8B24D`
- smoke seat 1 summary: `25F67A8EF770E40C3BA6CF9FB13EE93D8917C30AA9049A0DC872C3C2F418BAFF`

Known tradeoff: strict metadata and serial completeness deliberately returns Rule 1 in uncertain states. The frozen shadow supplies two natural Rule 4 starts but no causal post-difference outcome. The evaluator must run the frozen fixed160, inspect both natural evolution starts plus any new starts and completions, verify every first difference stays in the four allowed classes with an exact parent Lillie, and apply the frozen fault/gain/regression/seat/opponent gates. No fixed160, archive, commit, push, package, or Kaggle action was performed.
