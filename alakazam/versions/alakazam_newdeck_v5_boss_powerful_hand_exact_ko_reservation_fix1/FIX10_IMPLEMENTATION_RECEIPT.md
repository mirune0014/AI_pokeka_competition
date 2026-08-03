# Atomic Boss + Powerful Hand exact-KO reservation Fix1 receipt

Candidate: `C:\Users\amuam\project\AI_pokeka_competition\alakazam_staged_20260729\versions\alakazam_newdeck_v5_boss_powerful_hand_exact_ko_reservation_fix1`

Immutable parent: `C:\Users\amuam\project\AI_pokeka_competition\alakazam_staged_20260729\versions\alakazam_newdeck_v4_public_tactical_monotonicity_fix9`

Fixture directory: `C:\Users\amuam\project\AI_pokeka_competition\alakazam_staged_20260729\fixtures\episode_89096241_public_observations`

## Provenance and closures

- Immutable comparison spec SHA-256: `00DE158B13C08D216A932433D6AE62674AA1B9928AB26CE26ADC61BDEFFAEDC9`.
- Source replay SHA-256: `E10E204CECE7C6EEE63C153650A4C69D81719C68F5B0CAF650B18C826A28F035`.
- Parent Fix9 closure: `FDD25914489AE74F6A0454BF70A484BC545F2C468BDC88C2653AD85F018F999E`.
- Atomic Fix1 source closure: `C438D6C5986C794017F4F5E57319725A4FF7388C9A0483AFA7A4BD443E969E19`.
- Immutable parent `main.py`: `3BA6BBB80B459533BF92088A13949C35E1B3F37D66562E6B2C17356D66FA43D1`.
- Immutable parent tactical planner: `F0CA3132B2F315EB4065CDD70AD9109C6AA1D8AA51073E1BC5B8F4F7F9BC3679`.
- Parent/candidate deck: `F598F5E578D0440C96DC0492EAECF2E19739B7A23225BE57114A724EF7D0FB94`.

## Changed paths and hashes

Compared with the immutable parent:

- `main.py`: `00C46A2B3B4FBF5EFAAC991D94166797CACAF6D051E831ABC9B1BBEB2CECF733`.
- `planner_boss_powerful_hand_exact_ko_reservation.py`: `C6C28D549E5D0C652C983E8863E5305F6C8B16C771C98B839CEA4384310926F1`.
- `test_v5_boss_powerful_hand_exact_ko_reservation_fix1.py`: `3DE50D4D5473A09367E9725B9E68A9F0CDE7D3378D8CAD4F98039DE8E7B06B24`.
- `fixtures/episode_89096241_public_observations/step_111_seat0_main.json`: `6D00B08DD5F31F36E8753B021348412A4281EF7B7D2DCA1E0693A7F7367F13E6`.
- `fixtures/episode_89096241_public_observations/step_114_seat0_boss_target.json`: `8245F56CECFA45270D48CAB11EFEB1087EA066E60A1AB1CBAE5A0FBAF1C39AD3`.
- `fixtures/episode_89096241_public_observations/step_115_seat0_main.json`: `7BE147D80DB20CD26477919ACC08E60F95A19BFE424A0E63BDCB5B0A820520B8`.

The receipt self-hash is recorded externally after writing.

## Behavioral contract

The outer layer delegates complete Fix9 only at an unowned MAIN prompt. It arms a transaction only when this rule itself replaces an exact-cost Poffin or Rare Candy play with Boss and the reserved target is either terminal or has known prize value at least two. Nonterminal one-prize KOs do not arm it.

The transaction owns exactly two callbacks:

1. `EXPECT_BOSS_TARGET`: require exact Boss target prompt, same owner/turn, action count `+1`, raw/parsed agreement, unique public serials, exact Boss serial, exact one-card hand decrement, exact supporter flag, and complete public-state fingerprint equality after only the certified Boss delta. Reproject the saved target serial with the actual post-Boss hand and return its unique legal target action.
2. `EXPECT_ATTACK`: require the immediate normal MAIN prompt, same owner/turn, action count `+1`, unchanged hand, exact public fingerprint after only the certified switch and Boss-to-discard delta, saved target serial uniquely Active, legal Powerful Hand, and a fresh positive eligible KO projection. Clear the transaction before returning Powerful Hand.

Every prompt, owner, turn, raw/parsed, public fingerprint, action count, serial uniqueness, legality, hand-count, or KO-projection mismatch clears the transaction before delegating to Fix9. General Boss actions never arm the transaction. Policy logic contains no episode, opponent, target-card-ID, or private-information predicate.

## Fixture actions and traces

- Exact replay step 111 remains parent `[7]` Poffin and candidate `[4]` Boss, saving target serial `82`, known prizes `2`, hand `16 -> 15`, damage `300`; optional-first projection is hand `14`, damage `280`, non-KO.
- Atomic dominance fixture: Fix9 MAIN `[7]`; Fix9 TARGET `[1]` selects a three-prize positive non-KO survivor; candidate sequence is `[4]` Boss -> `[0]` saved two-prize exact-KO target -> `[0]` Powerful Hand. Trace stages are `ARMED_BOSS_TARGET`, `TARGET_REBOUND`, and `ATTACK_COMMITTED`. Transaction is `None` immediately after the attack action is produced.
- Rare Candy loss boundary: hand 17, parent Candy `[13]`; candidate Boss `[4]`. Boss-only projection is hand 16 / damage 320 / KO; Candy + Alakazam + Boss is hand 14 / damage 280 / non-KO.
- Rare Candy preservation boundary: hand 18, parent Candy `[13]`; candidate `[13]`; Candy + Boss leaves hand 15 / damage 300 / KO, with no transaction.
- Nonterminal one-prize boundary: parent Poffin `[0]`, candidate `[0]`, no transaction.
- Terminal one-prize boundary: parent Poffin `[0]`, candidate Boss `[1]`, saved prize value one with `terminal=True`.
- Prompt, turn, and unrelated public-fingerprint mismatch cases each returned parent `[0]`, published `ABORTED`, and observed `FIX10_TRANSACTION is None` inside the parent delegate.
- Existing Boss-stall, Kadabra attack, 2HKO, lethal-preserving Poffin, unavailable Boss, known-zero, and unknown-effect boundaries remain parent-selected.

## Verification commands and outcomes

Python commands ran from the candidate directory with `PYTHONPATH=..\..\submissions\alakazam_newdeck_v4_c2_safe_final_20260730\runtime_smoke_extract`.

1. `py -3.11 -m py_compile planner_boss_powerful_hand_exact_ko_reservation.py main.py test_v5_boss_powerful_hand_exact_ko_reservation_fix1.py` — exit 0.
2. `py -3.11 -m unittest -v test_v5_boss_powerful_hand_exact_ko_reservation_fix1` — exit 0; 11 tests; 0 failures; 0 errors; 0 skips.
3. `py -3.11 -m unittest test_v4_public_tactical_monotonicity_fix9 test_v4_public_damage_continuity_fix5 test_v4_public_survival_bench0_fix5` — exit 0; 64 tests; 0 failures; 0 errors; 0 skips.
4. `py -3.11 -m unittest discover -s . -p 'test_*.py'` — exit 0; 267 tests; 0 failures; 0 errors; 0 skips. This is the parent 256 plus 11 focused Fix1 tests.
5. Atomic fixture smoke — exit 0: parent MAIN `[7]`, parent Fix9 TARGET `[1]`, candidate `[4] -> [0] -> [0]`, saved serial `82`, saved prizes `2`, final transaction `null`.
6. Independent source-closure recomputation matched `C438D6C5986C794017F4F5E57319725A4FF7388C9A0483AFA7A4BD443E969E19`.
7. Prohibited-policy scan for `target_id|episode|opponent.?name` returned no matches.
8. Root and runtime `deck.csv` each contain exactly 60 non-empty rows and both hash to `F598F5E578D0440C96DC0492EAECF2E19739B7A23225BE57114A724EF7D0FB94`.

## Known limitations and evaluator focus

- The initial reservation supports only exact Poffin cost one and exact Rare Candy + Alakazam cost two. Other optional actions fail closed rather than estimating draws, discards, or modifiers.
- Valid owned TARGET and ATTACK callbacks intentionally do not invoke Fix9; any failed validation first destroys ownership and then delegates normally.
- Full public-state equality is deliberately strict and may abort on any additional public mutation, even one that would leave the KO tactically viable.
- The transaction is current-turn and two-callback only; it has no cross-turn recovery.
- No large match panel or archive was created. No Kaggle or other external write was performed.