# Rule 10 implementation report

## Identity and files

- Parent: `autonomous_gold_20260715/candidates/archaludon_historical_silver_single_resolver_salvage_rule5_trial_v1`.
- Candidate: `autonomous_gold_20260715/candidates/archaludon_historical_silver_single_resolver_salvage_rule10_trial_v1`.
- Evidence: `autonomous_gold_20260715/implementation/archaludon_historical_silver_single_resolver_salvage_rule10_trial_v1`.
- Parent `main.py`: `D966E455E5110F9D5616195AEAAC8663E6A92F310DAFC4B7F79E4D37149A9C62`.
- Candidate `main.py`: `2C9249F74CA37429DECEA4801E736E13085E50C19956BB0C75176B9D6759245A`.
- Deck: `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`.
- Historical-Silver executable parent: `F4B578453C9D953BE94885144DD50E05DBA4510DF3340BE27ADE07495896046E`.
- Strategy: `77C272880882B9C02473C00C88AEFD1F3447D696DF341990E5D62B0D14AD88B4`.
- Frozen requirements: `24282FA6A0EF91D936E2E5B2AAD725904EF3223FCFBDF9BEEA16C62C726038C9`.
- No archive was created.

Only candidate `main.py` differs from the 13-file Rule 5 package. The diff is
807 insertions and four line replacements. All 12 other package files are
byte-identical to Rule 5. Zero deck changes were made.

The source hunks are at Rule 5 old/new line anchors: `1/1`, `4/4`, `29/30`,
`74/76`, `89/99`, `1100/1111`, `1164/1639`, `1754/2234`, `1920/2698`,
`1929/2717`, `1951/2743`, `2005/2798`, `2010/2803`, and `2021/2815`.
They add only the Rule 10 constant/activity fields, bounded public oracle,
Rule 10 owner lifecycle/proposal, resolver registration, and telemetry.

## Behavioral intent

`EXACT_PROACTIVE_FULL_METAL_LAB_EXCHANGE_V1` inserts the lowest-serial uniquely
bound Full Metal Lab before Rule 5's sole exact payable nonterminal attack only
when the bounded one-reply oracle proves identical current attack outcomes and
a strict opponent return-KO/finish threshold improvement. The owner lifecycle
is `FML_EMITTED -> ATTACK_EMITTED -> CLEAR`; retries rebind semantic roles,
receipts re-prove the full certificate, matching attack logs clear before any
retry handling, and post-spend natural aborts increment fault telemetry.

Opponent Metal Pokemon are rejected outright. This is the conservative
implementation of the no-opponent-protection requirement and prevents the
symmetric Stadium effect from helping any opposing current or backup Pokemon.
Opponent replies are admitted only when every payable attack is fixed numeric
damage with empty effect text. The four exact Rule 5 attack/effect paths are
admitted for the stored own attack. Basic-Energy payment certificates record
the complete attached ledger and printed cost; no cards are modeled as spent.

## Verification

Focused and inherited tests:

```text
py -3.11 -B -m unittest discover -s autonomous_gold_20260715/implementation/archaludon_historical_silver_single_resolver_salvage_rule10_trial_v1/tests -p test_*.py -v
Ran 35 tests in 0.145s -- OK
```

The seven Rule 10 test methods cover both seats and all four stored Rule 5
attacks, KO-to-survival, current forced promotion, reply board-out removal,
non-KO reply, Weakness/Resistance/FML ordering, FML and attack retries,
option reversal, physical-copy determinism, serial remap rejection, matching
attack receipt precedence, terminal precedence, ambiguous promotion, and
post-spend faulting. The 28 inherited Rule 1/4/5 methods also pass.

Compile/import/layout:

```text
py -3.11 -m py_compile autonomous_gold_20260715/candidates/archaludon_historical_silver_single_resolver_salvage_rule10_trial_v1/main.py autonomous_gold_20260715/implementation/archaludon_historical_silver_single_resolver_salvage_rule10_trial_v1/run_shadow.py autonomous_gold_20260715/implementation/archaludon_historical_silver_single_resolver_salvage_rule10_trial_v1/tests/test_rule10_fml_exchange.py
py -3.11 -B autonomous_gold_20260715/implementation/archaludon_historical_silver_single_resolver_salvage_rule10_trial_v1/verify_candidate.py
```

Outcome: both commands exited zero; seven Python files compiled in memory;
import/final-loader passed; one
top-level/final agent, one resolver, one owner assignment, and one static parent
call inside agent; 13 package files and 12 preserved non-main files; deck 60,
ACE SPEC one; Rules 2/3/6/7/8/9 absent; zero cache paths. Machine output:
`verification_summary.json` SHA-256
`1B2032439A3ED843B95FED144E1DB093522051E9BB765883C1712AF810B211CC`.

Both-seat checked-engine smoke:

```text
.venv-rl/Scripts/python.exe -B tools/run_local_battle.py --engine-dir analysis_outputs/cynthia_v9_vs_v11_poffin_role_selection_20260713/seeded_engine --agent-a autonomous_gold_20260715/candidates/archaludon_historical_silver_single_resolver_salvage_rule10_trial_v1 --agent-b autonomous_gold_20260715/baseline/historical_silver_archaludon_54495224 --deck-a autonomous_gold_20260715/candidates/archaludon_historical_silver_single_resolver_salvage_rule10_trial_v1/deck.csv --deck-b autonomous_gold_20260715/baseline/historical_silver_archaludon_54495224/deck.csv --games 1 --max-steps 1000 --trace-dir autonomous_gold_20260715/implementation/archaludon_historical_silver_single_resolver_salvage_rule10_trial_v1/smoke/candidate_p0/traces --trace-options --seed-base 803210001 --engine-seed --summary autonomous_gold_20260715/implementation/archaludon_historical_silver_single_resolver_salvage_rule10_trial_v1/smoke/candidate_p0/summary.jsonl
.venv-rl/Scripts/python.exe -B tools/run_local_battle.py --engine-dir analysis_outputs/cynthia_v9_vs_v11_poffin_role_selection_20260713/seeded_engine --agent-a autonomous_gold_20260715/baseline/historical_silver_archaludon_54495224 --agent-b autonomous_gold_20260715/candidates/archaludon_historical_silver_single_resolver_salvage_rule10_trial_v1 --deck-a autonomous_gold_20260715/baseline/historical_silver_archaludon_54495224/deck.csv --deck-b autonomous_gold_20260715/candidates/archaludon_historical_silver_single_resolver_salvage_rule10_trial_v1/deck.csv --games 1 --max-steps 1000 --trace-dir autonomous_gold_20260715/implementation/archaludon_historical_silver_single_resolver_salvage_rule10_trial_v1/smoke/candidate_p1/traces --trace-options --seed-base 803210002 --engine-seed --summary autonomous_gold_20260715/implementation/archaludon_historical_silver_single_resolver_salvage_rule10_trial_v1/smoke/candidate_p1/summary.jsonl
```

Candidate seat 0 terminated in 149 steps; candidate seat 1 terminated in 158.
Both had zero action errors and zero max-step hits. Raw summaries are under
`smoke/candidate_p0` and `smoke/candidate_p1`; combined output is
`smoke_summary.json`.

Full replay shadow:

```text
.venv-rl/Scripts/python.exe -B autonomous_gold_20260715/implementation/archaludon_historical_silver_single_resolver_salvage_rule10_trial_v1/run_shadow.py
```

Outcome: 46 current plus 207 historical source paths, both seats, 30,977
callbacks, 252 readable replays, zero invalid actions, exceptions, action
differences, first differences, Rule 10 starts, completions, aborts, or faults.
The existing truncated `episode_89287701_replay.json` is the sole malformed
source. Corpus hash:
`A29B61F31A84401404BF1701DDC5CF959A330EA6894C9283C533017B99ED4C9D`.
All changed-position and activity files are persisted even though empty:
`shadow_differences.json`, `shadow_activity_events.json`, and
`shadow_summary.json`.

## Evaluator status and tradeoffs

The frozen activity gate yields `DEFER-DORMANT`: complete shadow has zero
natural starts and therefore no complete non-fixture FML-to-same-attack
transaction. The rule was not widened and fixed160 was not run. Do not treat
the focused lifecycle as natural activation or integrate this candidate.

The deliberate tradeoff is high dormancy: opponent Metal, any payable reply
effect text, Tools, Special Energy, status, unsupported Ability, tie, multiple
forced promotions, unknown payment, or any certificate drift returns exact
Rule 5. The evaluator should confirm the zero-activity `DEFER-DORMANT` decision,
not infer strength from the neutral shadow or smoke.
