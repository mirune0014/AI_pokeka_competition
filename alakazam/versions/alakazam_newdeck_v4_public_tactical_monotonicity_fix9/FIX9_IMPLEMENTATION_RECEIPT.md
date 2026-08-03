# Fix9 implementation receipt

Candidate: `alakazam_newdeck_v4_public_tactical_monotonicity_fix9`

Immediate delegate baseline: `alakazam_newdeck_v4_public_survival_bench0_fix5` (byte-identical C3 survival Fix5 wrapper/modules)

Immediate delegate baseline closure: `5C1BAD6C505358BFF7550A89F167D3DE19B0D2540C6C54ED85324F961A37E134`

Candidate source closure: `FDD25914489AE74F6A0454BF70A484BC545F2C468BDC88C2653AD85F018F999E`

## Behavioral intent

- Keep the byte-identical C3 survival Fix5 wrapper/modules, which retain complete C2 as the general deterministic ranker, as the immediate delegate.
- Apply priority: terminal win; certified higher-prize Boss KO; exact current Powerful Hand KO; effective target safety; C3 public Bench-0 survival; UNIQUE/IMPORTANT successor protection; callback-local Poffin timing and role cardinality; C2.
- Re-evaluate C2 on stable-key filtered observations and remove only a replacement certified harmful.
- Keep Poffin decisions callback-local; there is no Fix8 latch or persistent veto state.
- Use all legal Poffin bench capacity, with 0/1/2 role selection and no third Dunsparce; reserve a sole final slot for Abra and select nothing when only Dunsparce is offered.
- On an exact live Boss child, rebind only to a certified terminal target, a strictly higher exact-prize KO, a same-prize KO over a positive survivor, or from known-zero to positive damage; keep non-dominated positive ties and never prefer a lower-prize KO over a higher-prize survivor.
- Treat exact public Mist Energy and matching-type Rock Fighting Energy as known-zero effective targets; retain UNKNOWN for incomplete or mismatched metadata.
- Count exact Rare Candy plus Alakazam as a two-card lower-bound hand spend, and rerank direct final-slot denial through stable option keys.
- Compute the same logical policy closure in source and packaged layouts: packaged `_policy_main.py` stands in for logical `main.py`, wrapper names are excluded, and the absent packaged `runtime/main.py` uses its frozen validated row.

## Verification

All commands ran from the repository root except unittest/smoke commands, which ran from this candidate directory with `PYTHONPATH` set to `../../submissions/alakazam_newdeck_v4_c2_safe_final_20260730/runtime_smoke_extract`.

1. Changed Python compile:

   `py -3.11 -m py_compile <8 changed Python files>`

   Result: PASS (`PY_COMPILE_CHANGED_8=PASS`).

2. Focused Fix9 tests:

   `py -3.11 -m unittest -v test_v4_public_tactical_monotonicity_fix9`

   Result: PASS, 16 tests.

3. Focused Fix9 plus reused public-damage/Bench-0 tests:

   `py -3.11 -m unittest -v test_v4_public_tactical_monotonicity_fix9 test_v4_public_damage_continuity_fix5 test_v4_public_survival_bench0_fix5`

   Result: PASS, 64 tests.

4. Full candidate discovery:

   `py -3.11 -m unittest discover -s . -p 'test_*.py'`

   Result: PASS, 256 tests in 5.529s.

5. Runtime smoke:

   Deck handshake plus fixture `step_148_energized_kadabra_alakazam_in_hand_main.json` through `main.agent`.

   Result: PASS; deck count 60; fixture action `[0]`; trace rule `V4_PUBLIC_TACTICAL_MONOTONICITY_BUNDLE_FIX9`.

6. Deck validation:

   Root `deck.csv`: 60 cards. Runtime `deck.csv`: 60 cards. SHA-256 for both: `F598F5E578D0440C96DC0492EAECF2E19739B7A23225BE57114A724EF7D0FB94`.

7. Exclusion scan:

   `rg -n "PERSISTENT_HOLD|POFFIN_ZERO_DEMAND_LATCH|opponent.?name|seed" planner_public_tactical_monotonicity.py`

   Result: no matches.

No archive was created and no external submission action was taken.

## Evaluator focus

- Run a real Boss play/target callback pair with one protected Team Rocket Basic and one damageable target; the main guard must avoid an all-zero Boss route and the target child must rebind away from a protected selection when a damageable option exists.
- Exercise a malformed normal-main prompt containing only a dead Poffin and no legal non-Poffin action; the policy deliberately refuses to return the dead Poffin.
- Strategic (non-mechanical) Poffin defer preserves C2 if the filtered rerank cannot certify an admissible replacement.
