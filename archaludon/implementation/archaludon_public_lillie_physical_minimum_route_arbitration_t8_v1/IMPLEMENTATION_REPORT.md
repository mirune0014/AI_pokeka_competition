# Task 8 implementation report

## Scope and behavioral intent

- Exact parent: `autonomous_gold_20260715/candidates/archaludon_public_complete_supporter_purpose_arbitration_t7_v1/main.py`, SHA-256 `8364A91B1DAF48968D9D5C3BBA257D43546E27AB7076841A5400124048602E28`.
- Isolated candidate: `autonomous_gold_20260715/candidates/archaludon_public_lillie_physical_minimum_route_arbitration_t8_v1`.
- Rule/purpose: `PUBLIC_LILLIE_PHYSICAL_MINIMUM_ROUTE_ARBITRATION_T8_V1` / `PUBLIC_HAND_RENEWAL_WITH_PHYSICAL_ROUTE_MINIMA`.
- Direct Lillie and Pokégear-to-Lillie are arbitrated using public count transforms and exact physical route minima. The exact Task 7 callable remains the direct parent, with terminal Task 7 Boss/PF decisions above Task 8.
- Direct Lillie chooses the minimum legal physical serial. It draws exactly 8 at six prizes and 6 otherwise; the post-Lillie deck count does not inspect hidden redraw identities.
- Pokégear-to-Lillie keeps the existing `_pfgear_transaction` owner, selects the minimum revealed Lillie serial, records exact empty-reveal whiffs, and rechecks inherited Boss/Explorer routes before every reversible pre-Lillie stage. Family enumeration is context/type exact: `TO_HAND` + `CARD` at `GEAR_PLAY_EMITTED`, and `MAIN` + `PLAY` at `GEAR_LILLIE_SELECT_EMITTED`.
- A same-family Boss/Explorer route protects exactly one copy and binds the lowest visible physical serial as canonical. Ambiguous metadata fails closed.
- A legal, non-skipped Jumbo Ice Cream route is materialized before Lillie or Pokégear. Direct parent Ice actions retain the parent's exact option/serial; Task 8 does not replace parent attacks or unrelated hard routes. The route uses the existing `PCRD_JUMBO_ICE_CREAM` owner and records a settled Task 8 inherited-route certificate without opening a second owner.
- Existing directions remain `PLAY_LILLIE`, `MATERIALIZE_THEN_REEVALUATE`, `HOLD_LILLIE`, and `GEAR_LILLIE`. Protected cards are exact refs/minimum copies rather than blanket family protection.

## Files changed or created

- Candidate `main.py`: SHA-256 `74C20CCA851E6BCADB62382314656AE7506BD964C29DCE38A80BB5F665A0E971`.
- Candidate `deck.csv`: unchanged from parent, SHA-256 `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`.
- Candidate package's other 10 files: byte-identical to parent.
- `run_focused_fixtures.py`: `3B0A6A32CDEFDC1648CCF77542BE56BA5F737216DA04489E667E1FA8A3428AE8`.
- `focused_fixture_results.json`: `1E01AD7FE67C7B562074A1D7200200C732EB587985C7AEFFAA9AEE9B1A028AA9`.
- `run_replay_shadow.py`: `12B9CE246E309EAA5C6AFDB6F9A9EEE68385CE161D67E9806531AF920E2A90AB`.
- `replay_shadow_results.json`: `80597C07A7BCFDB676EC8BAF612C4853A151A3255BCE9B3D98601B1BF9AE4895`.
- `build_first_difference_ledger.py`: `B951BE93E713B3D61C1896B207A2BC88B75FC225E9E9346937C4E487C2C4D337`.
- `first_difference_ledger.json`: `D2364460B12C6EEF4FD2FF4E71923EA7EF95EF9B317551E562923CF09DE90C53`.
- `verify_structure.py`: `360CBA592C1A2C8A68E1218266329A2E8A57A5507E7D15F17BD4FB35BC37ADBB`.
- `structural_results.json`: `E645C210DC7B6313348727E8CD8409AE76112973EDAD42B10B13CF5EF3356CA4`.
- `engine_smoke_seat0.jsonl`: `301E69425F5BD46DA78BA4E4B2E2DFCE116881596BE8BBCBC3668E2DC4B57ED0`.
- `engine_smoke_seat1.jsonl`: `F4014A8827738C5B3F4E8F6ECF148254D3B129F27ACA6C8A42F936AC8F104913`.

## Focused fixtures

- Command: `.\.venv-rl\Scripts\python.exe -B autonomous_gold_20260715\implementation\archaludon_public_lillie_physical_minimum_route_arbitration_t8_v1\run_focused_fixtures.py`.
- Outcome: exit 0; `268/268 PASS`, including the inherited Task 7 fixtures. Task 8 conservation: `104 starts = 39 completes + 8 whiffs + 57 aborts + 0 live`; holds true.
- Exact Ice rows passed on both seats and meaningful option reversals: `89288811:78` Ice `[0]`/ref 35 over Gear `[3]`; `89286075:123` Ice `[2]`/ref 36 over Lillie `[0]`; direct rows `89308835:107` ref 95, `88397927:119` ref 36, `88482123:54` ref 34, and `88579549:128` ref 96.
- Duplicate Explorer replay passed: `87868636:49` begins Gear in the parent, then `:51` aborts before Lillie to Explorer; family count 2, minimum count 1, canonical serial 43. Synthetic `GEAR_LILLIE_SELECT_EMITTED` Boss/Explorer fail-close passed on both seats and reversed options.
- Exact Gear reveal rows passed with and without Lillie, both seats, and reversed options: `89291523:17` Explorer `[1]`; `87672938:77` Boss `[0]`; `88197270:13` Explorer `[1]`; `88338429:17` Boss `[0]`; `88507294:86` Explorer `[1]`; `88589778:96` Explorer `[0]`; `88660007:30` Explorer `[0]`; `88682711:77` Explorer `[3]`.
- Prior regression rows remain fixed: `88035562:30` exact evolution `[6]`; `88357830:69` exact evolution `[2]`; `89289898:31` Explorer `[0]`.

## Full current + historical shadow and ledger

- Command: `.\.venv-rl\Scripts\python.exe -B autonomous_gold_20260715\implementation\archaludon_public_lillie_physical_minimum_route_arbitration_t8_v1\run_replay_shadow.py`.
- Outcome: exit 0; 252 readable episodes, 9,306 decisions, 115 authoritative first differences in 115 episodes, and 220 Task 8 activations. Inputs were 46 current and 207 historical replay files; one known truncated current replay was unreadable. Snapshot SHA-256: `A29B61F31A84401404BF1701DDC5CF959A330EA6894C9283C533017B99ED4C9D`.
- Authoritative directions: `PLAY_LILLIE=17`, `MATERIALIZE_THEN_REEVALUATE=52`, `HOLD_LILLIE=39`, `GEAR_LILLIE=7`. Gear first differences whose parent semantic is Boss/Explorer: 0. Task 7 terminal first differences: 0. Unexpected first differences: 0. Module-load parent duplicate-control difference: 1, recorded separately.
- Prefix safety totals: Task 8 exceptions/invalid `0/0`; Task 7 invalid `0`; PF Gear invalid/owner collisions `0/0`. Exact-parent and candidate Task 7 owner collisions were both 1 on the same historical boundary, so candidate excess was 0.
- Task 8 settlement conservation: `143 starts = 57 completes + 0 whiffs + 86 aborts + 0 live`; holds true.
- Command: `.\.venv-rl\Scripts\python.exe -B autonomous_gold_20260715\implementation\archaludon_public_lillie_physical_minimum_route_arbitration_t8_v1\build_first_difference_ledger.py`.
- Outcome: exit 0; 115 ledger rows reproduced. Direction counts match shadow. Obvious-bad 0, wrong/missing-purpose 0, rollback rejection 0, settled holds 39, settled inherited Ice routes 1, and counterfactual suffix not interpretable 75.

## Compile, structure, deck, and native smoke

- Compile command: set `PYTHONPYCACHEPREFIX` to the assigned implementation `.compile_cache`, then run `.\.venv-rl\Scripts\python.exe -m py_compile` on candidate `main.py` and the four implementation scripts.
- Compile outcome: exit 0; the verified temporary cache was removed afterward.
- Structure command: `.\.venv-rl\Scripts\python.exe -B autonomous_gold_20260715\implementation\archaludon_public_lillie_physical_minimum_route_arbitration_t8_v1\verify_structure.py`.
- Structure outcome: exit 0; final AST callable `agent`; import callable true; 12 package entries; non-main byte mismatches `[]`; deck count 60; ACE SPEC count 1; no candidate cache entries.
- Seat 0 smoke command: `.\.venv-rl\Scripts\python.exe -B tools\run_local_battle.py --engine-dir autonomous_gold_20260715\candidates\archaludon_public_lillie_physical_minimum_route_arbitration_t8_v1 --agent-a autonomous_gold_20260715\candidates\archaludon_public_lillie_physical_minimum_route_arbitration_t8_v1 --agent-b analysis_outputs\reference_agents\historical_silver_archaludon_54495224 --games 1 --max-steps 1000 --seed-base 2026080209 --no-trace --summary autonomous_gold_20260715\implementation\archaludon_public_lillie_physical_minimum_route_arbitration_t8_v1\engine_smoke_seat0.jsonl`.
- Seat 0 outcome: exit 0; 126 steps; action errors 0; max-step false; result 1.
- Seat 1 smoke command: `.\.venv-rl\Scripts\python.exe -B tools\run_local_battle.py --engine-dir autonomous_gold_20260715\candidates\archaludon_public_lillie_physical_minimum_route_arbitration_t8_v1 --agent-a analysis_outputs\reference_agents\historical_silver_archaludon_54495224 --agent-b autonomous_gold_20260715\candidates\archaludon_public_lillie_physical_minimum_route_arbitration_t8_v1 --games 1 --max-steps 1000 --seed-base 2026080210 --no-trace --summary autonomous_gold_20260715\implementation\archaludon_public_lillie_physical_minimum_route_arbitration_t8_v1\engine_smoke_seat1.jsonl`.
- Seat 1 outcome: exit 0; 131 steps; action errors 0; max-step false; result 0.

## Archive, tradeoffs, and evaluator requirements

- Archive: none created. No packaging, commit, push, upload, submission, Notebook, or Discussion action was performed.
- Tradeoff: the rule intentionally spends a legal Jumbo Ice Cream before Lillie/Gear and protects/materializes exact public routes. It can delay renewal when hidden redraws would have been favorable. Same-family supporter protection is minimum-one/canonical-lowest only; duplicate copies are deliberately not blanket-protected.
- Shadow cannot score counterfactual suffix outcomes. The evaluator must run the immutable paired both-seat schedule against the exact Task 7 parent and check absolute/adjacent matchup floors, action errors, max-step hits, seat/seed sensitivity, and all four direction buckets.
- Inspect Ice materialization for attack-continuity or prize-exchange regressions, especially the six cited replay rows. Inspect duplicate Boss/Explorer fail-close at every reversible Gear stage, especially `87868636:49/:51`, and confirm the three prior regression rows remain exact.
