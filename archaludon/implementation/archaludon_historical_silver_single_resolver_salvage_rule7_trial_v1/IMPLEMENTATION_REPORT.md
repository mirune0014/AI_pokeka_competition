# Rule 7 trial implementation report

## Scope and behavioral intent

- Frozen parent: accepted Rule 5 candidate `archaludon_historical_silver_single_resolver_salvage_rule5_trial_v1`; parent `main.py` SHA-256 `D966E455E5110F9D5616195AEAAC8663E6A92F310DAFC4B7F79E4D37149A9C62`.
- Frozen strategy SHA-256: `7F39297030D9DD83978FBCF5C7887B67E6C7455604B5A9E3B0D2D130447860E4`; controlling final-release amendment SHA-256: `13376C2D6D7808446E4EBC869E7F696BBAC22EA226C3A866237A02D26554FE34`.
- Candidate changes only `main.py`; all 12 non-`main.py` package files, including the 60-card deck, are byte-identical to Rule 5.
- Added only `PARENT_TURBO_FLARE_EXACT_PRIMARY_THEN_ONE_BACKUP_TRANSACTION_V1` on exact Cinderace `666` Turbo Flare `965` `ATTACH_TO` / `ATTACH_FROM` callbacks.
- The only recipient roles are current printed Archaludon ex `190` / Metal Defender `253`, Archaludon `840` / Coated Attack `1212`, and Duraludon `169` / Raging Hammer `224`. Each has exact deficit `3 - current Basic Metal`; Hammer In, future evolution, future draw, Prize, threat, and score logic are not used.
- Allocation exactly fills one primary by deficit, fixed role order, and serial; only then may it give the remainder to one backup. No target receives beyond three Basic Metal and no third target receives Energy.
- Physical Energy and targets bind by serial. The implementation preserves the parent's physical Energy copies when useful count is unchanged, prefers the lowest parent copies when reducing count, uses the lowest equivalent UI position, and freezes `energy_serial -> target_serial` at `ATTACH_TO`.
- One shared `_materialization_owner` runs `ENERGY_SET_EMITTED -> TARGET_EMITTED` for intermediate Energy, with exact prior log-and-board confirmation before advancing. On the sole remaining exact legal target, `RULE7_FINAL_EXACT_TARGET_RELEASE_UNCONFIRMED_V1` emits `FINAL_TARGET_EMITTED`, records `UNCONFIRMED_ENGINE_TERMINAL_BOUNDARY`, and clears the shared owner before returning. It does not add the final Energy to confirmed serials or report a completed/confirmed state.
- A passive token deterministically rebinds an identical final prompt under option permutation while keeping the owner null. The first nonmatching callback clears the token and continues through the normal resolver in that same callback. `ZERO_EMITTED` likewise clears without suppressing the next own callback.
- There remains one top-level `agent`, one `_resolve`, one shared owner, one static `_parent.agent` call inside `agent`, and the existing six-field proposal.

## Verification

Focused plus inherited Rules 1/4/5:

```powershell
py -3.11 -B -m unittest discover -s autonomous_gold_20260715/implementation/archaludon_historical_silver_single_resolver_salvage_rule7_trial_v1/tests -p test_*.py -q
```

Outcome: exit `0`; `37/37` test groups passed. The eight Rule 7 groups cover all three roles from zero, one, and two Basic Metal to exact three across both seats; final target release fields and immediate null owner; passive retry under final-prompt permutation; same-callback continuation into Rule 5; one-Metal Duraludon receiving exactly two; primary then one backup; no third recipient or overattachment; empty/all-ready zero and retry; insufficient Energy; unsupported Benched Cinderace; Special Energy; unknown Tool modifier; evolution-card invariance; physical/option permutation; equivalent UI duplicates; earlier-attachment confirmation; wrong source; target loss; and turn/result discontinuity. The other `29` groups are the complete inherited Rule 1 (`13`), Rule 4 (`10`, including Rule 7 ZERO same-callback continuation), and Rule 5 (`6`) tests.

Candidate verifier:

```powershell
py -3.11 -B autonomous_gold_20260715/implementation/archaludon_historical_silver_single_resolver_salvage_rule7_trial_v1/verify_candidate.py
```

Outcome: exit `0`; six Python files compiled in memory; import callable; one top-level `agent`; one top-level `_resolve`; one static parent call; candidate layout `13` files; `12` non-main files byte-identical to Rule 5; deck count `60`; Hero's Cape ACE SPEC count `1`; zero `__pycache__` and `.pyc`.

Frozen Rule 5 versus Rule 7 replay shadow:

```powershell
py -3.11 -B autonomous_gold_20260715/implementation/archaludon_historical_silver_single_resolver_salvage_rule7_trial_v1/run_shadow.py
```

Outcome: exit `0`; corpus SHA-256 `B88C25BC8F26F959F85D00D27FD7B148D22034D71B2588DF73AAF8C8E0B15004`; `78` source paths, `77` readable replays and known malformed `episode_89287701`; `4,262` callbacks; `46` natural starts; `65` intermediate target emissions; `23` final unconfirmed target emissions; `23` first/action differences; `0` invalid actions, exceptions, or faults. Classes are `12` primary exact fills, `4` single-backup remainders, `3` useful-count reductions, `4` empty-Bench zero selections, and `0` target-concentration-only differences. All 23 first differences are individually recorded and inspected in `shadow_differences.json` and `SHADOW_FIRST_DIFFERENCE_REVIEW.md`.

The runner performs `23` explicit counterfactual rollbacks at the first changed action because the stored suffix contains the historical parent action. On all `23` same-action final emissions, ownership was null immediately; there were zero owner-release violations and zero prohibited final-status fields. Their `23` following nonmatching callbacks all cleared the passive token and continued, with zero passive-suppression violations. Final emissions remain explicitly unconfirmed.

Checked-engine both-seat smoke:

```powershell
.venv-rl/Scripts/python.exe -B tools/run_local_battle.py --engine-dir analysis_outputs/cynthia_v9_vs_v11_poffin_role_selection_20260713/seeded_engine --agent-a autonomous_gold_20260715/candidates/archaludon_historical_silver_single_resolver_salvage_rule7_trial_v1 --agent-b autonomous_gold_20260715/baseline/historical_silver_archaludon_54495224 --deck-a autonomous_gold_20260715/candidates/archaludon_historical_silver_single_resolver_salvage_rule7_trial_v1/deck.csv --deck-b autonomous_gold_20260715/baseline/historical_silver_archaludon_54495224/deck.csv --games 1 --max-steps 1000 --trace-dir autonomous_gold_20260715/implementation/archaludon_historical_silver_single_resolver_salvage_rule7_trial_v1/smoke/candidate_p0/traces --trace-options --seed-base 803207001 --engine-seed --summary autonomous_gold_20260715/implementation/archaludon_historical_silver_single_resolver_salvage_rule7_trial_v1/smoke/candidate_p0/summary.jsonl
.venv-rl/Scripts/python.exe -B tools/run_local_battle.py --engine-dir analysis_outputs/cynthia_v9_vs_v11_poffin_role_selection_20260713/seeded_engine --agent-a autonomous_gold_20260715/baseline/historical_silver_archaludon_54495224 --agent-b autonomous_gold_20260715/candidates/archaludon_historical_silver_single_resolver_salvage_rule7_trial_v1 --deck-a autonomous_gold_20260715/baseline/historical_silver_archaludon_54495224/deck.csv --deck-b autonomous_gold_20260715/candidates/archaludon_historical_silver_single_resolver_salvage_rule7_trial_v1/deck.csv --games 1 --max-steps 1000 --trace-dir autonomous_gold_20260715/implementation/archaludon_historical_silver_single_resolver_salvage_rule7_trial_v1/smoke/candidate_p1/traces --trace-options --seed-base 803207002 --engine-seed --summary autonomous_gold_20260715/implementation/archaludon_historical_silver_single_resolver_salvage_rule7_trial_v1/smoke/candidate_p1/summary.jsonl
```

Outcome: candidate seat 0, seed `803207001`, terminal in `120` steps, action errors `0`, max-step false; candidate seat 1, seed `803207002`, terminal in `128` steps, action errors `0`, max-step false. Both candidate-side traces contained zero Turbo Flare effect callbacks and zero Rule 7 starts/final emissions; these games prove loader/legal execution only. No extra simulation was run for the amendment.

## Final hashes

- Candidate `main.py`: `9C2D5935364C0940967D48D85E2690EC386569143CD922186A31C716C5391BC1`
- Deck: `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`
- Rule 1 fixture: `2D0D073B4CB3411B949B14EBED48AC641CF8AF5ED05D040EEE029C851930F683`
- Rule 4 fixture: `528F5A1687F5601DFB00E6C09D925329FBF870A6317DEA61B45C2D41265DEE45`
- Rule 5 fixture: `28BFC65F54E9C201F2E9C8D712D494130C2DBBEF136DE7CE370F8C146BD65F12`
- Rule 7 fixture: `7635F4CCA0B927E8C1F799E74AC485B706F55F13A65B622C524F4F15BEF88D0A`
- Shadow runner: `D751A864F783ADC920B1E9E31A3B3FD7E6C1FE569165B42F4555990BF9DF8C4D`
- Shadow summary: `9995A4BA526826E60BC723C172543F6D3B646F253EE2C9B0E462CFCAB53C8DB9`
- Shadow differences: `0A9B27256067D87C3835E98235BACAF0C9EA3E7E6A867647E1F4609254E7C72D`
- First-difference review: `E17567197CA5A0FBB8CE09B26D5907AD7FC1CE0F4BF48F4C1018EA7D0569F082`
- Candidate verifier: `797D4D1E1F4CA616A24442F12EA8592FADC9BFBE070E1CF5C8087B8088326A44`
- Consolidated smoke summary: `0F4DBECC8F5134B0B3D85653DF519F6835C635724C6A2A2A2BAA96241426ED13`
- Smoke seat 0 raw summary: `FB677805EE5EB67DEF5F24EF69C23DCB976F56D83517AF87587F911336ED1E6E`
- Smoke seat 1 raw summary: `491594C28162FFAD35BB934A330035ED70CFF0866BF59F8395B44845F812F461`

## Known tradeoffs and evaluator handoff

- The exact boundary deliberately returns the parent for any unsupported Bench Pokémon, Special Energy, unrecognized Tool/cost surface, duplicate physical serial, malformed binding, missing confirmation, or source/seat/turn/result/target discontinuity.
- The frozen replay cannot execute a candidate-controlled suffix after a changed first action; those 23 transactions are deliberately rolled back. The fixed160 evaluator must supply the independent post-state checks required by the amendment.
- The evaluator must run the immutable fixed160 schedule and verify every natural final emission against the next engine state: exact primary readiness, cap three, at most one backup, no third recipient, null owner at emission, no next-callback cleanup suppression, and all ordinary stage gates. A natural start without an externally verified final emission is incomplete and rejected; zero starts is `DEFER-DORMANT`.
- No fixed160, added simulation, archive, package, commit, push, Kaggle call, Notebook/Discussion publication, or external write was performed.
