# Controlling automation handoff update - 2026-07-23 00:52 JST

This file supersedes every earlier current-live, quota, write, first-loss, and next-candidate statement in `AUTOMATION_HANDOFF.md` and `AUTOMATION_HANDOFF_UPDATE_20260722_0738.md`. All other repository, model, evidence, and Kaggle-ownership rules in `AGENTS.md` remain controlling.

Root owns planning, raw-evidence verification, documentation, packaging, and every Kaggle write. Keep competition edits under `autonomous_gold_20260715`; existing artifacts are read-only inputs. Candidate implementation workers alone use Fast `ptcg_candidate_worker`. Use deterministic public-state rules only; no RL, learned rankers, imitation, Gold-action cloning, or replay-derived opponent-policy proxies. Historical-Silver Archaludon remains the primary executable anchor and complete historical agents remain the anti-overfitting population.

## Current live submission

Current live is Kaggle `54906455`, exploratory `alakazam_active_dudunsparce_run_away_ko_transaction_v4`.

- Submitted policy SHA-256: `B89DCB6363CBD6ADF094115CF0CF5B93D6B9975A2505E1B976F387AAE8A198CD`.
- Transaction SHA-256: `B70D7374E0D3C4613EBEC3CE0B8EBA931C641CB9423B8140817BCFCB7F996535`.
- Clean archive SHA-256: `D1A7DF3B39F6E4CDA9FBB312863867CCD15E73F8040C40F0D1384BC2F1FF7194`.
- Package manifest SHA-256: `24C1E8995FA0C7A64A8FEBFBEA9E422D8ACBFD5A8454A6D5F559881521978C57`.
- Formal-parent policy SHA-256: `6AEF53400B9413037FB79DDCB9BE752A632FF4E0803B1D00EE84F188C44EDB6C`.
- Submission record: `live/54906455/SUBMISSION_RECORD.md`, SHA-256 `10D306CA36CA088BF32F05BE0F4180156FE2F1DBA6F308C96E057C42AA49BB59`.
- Never resubmit this exact source or archive.

At the root-authenticated `2026-07-23 00:33 JST` checkpoint, submission `54906455` was `COMPLETE` at API score `509.6`. The episode service had one validation `87485384` and one public loss `87485519` against Yunioshi submission `54906437`. The exact episode-table SHA-256 was `F694BB09AB81BDB5CAA54FB50430041C07B063A9DA52B26DD80F8A96A6E83BFA`; public replay SHA-256 was `E4296E1DA5F2192C0CF67CCD0859B15766CDCEBE3B7C618164F254A6901BC02C`. UTC-day quota was `3/5` used and `2/5` remaining with refs `54893740`, `54895497`, and `54906455`. Refresh before treating any status, score, episode set, or quota as current.

## First public loss

The immutable correct-seat shadow compared v4 with the exact formal parent over `83` unique callbacks. Schedules and all actions were identical; there were zero v4 starts, aborts, invalid actions, duplicate mismatches, parent-call mismatches, emergencies, mandatory fallbacks, or unclassified differences.

- Shadow spec SHA-256: `BB81D16D89243ACBE7F2516DD96638B6D0EF0F7529F05FC9EA22B5ECC1E8D358`.
- Comparison SHA-256: `371E23C05B0F42E7C62EB584AD4FA74246DEB379FE96F01D1B657FB80CAECB1E`.
- Root diagnosis: `live/54906455/ROOT_FIRST_PUBLIC_DIAGNOSIS.md`, SHA-256 `141A089EE4711F78E2727C37E971AE93483FF4326816B670CD697EF318E6600B`.

The loss is inherited and not caused by v4. Visible Team Rocket's Articuno `414` made Powerful Hand `1072` place exactly zero counters into Basic Team Rocket's Mewtwo ex. The parent selected the zero-output attack twice, at displayed observation steps `87` and `105` (raw array/shadow keys `86` and `104`), and lost two Alakazam. This defect is independently repeated in prior report SHA-256 `37481B016563D005E9C2A544F5318BB40FA169A12F7C5DBDAD49330FCD3DA742`.

## Frozen successor

Sol-Ultra and root selected exactly one sibling candidate directly from the formal parent: `alakazam_public_articuno_zero_output_disruption_guard_v1`. Do not stack Active-Dudunsparce v4.

- Strategy contract: `strategy/articuno_zero_output_disruption_guard_20260723/STRATEGY_SELECTION.md`, SHA-256 `53EEC345D16BEFFA521C4F6599CFC8BDC371D4CB1A928A36C2108A82850B322E`.
- Root evidence: `strategy/articuno_zero_output_disruption_guard_20260723/ROOT_VERIFIED_EVIDENCE.md`, SHA-256 `11DAEA18132057D8413D9BFEE1970132A68645A3B94961226987093407C5E929`.
- Fast worker `/root/implement_articuno_zero_output_guard` is the only source writer and owns only the matching new candidate and implementation directories. Collect its final output; do not use transient hashes.

The rule starts only when the parent's unique Powerful Hand is publicly certified to resolve to zero under exact Articuno Repelling Veil, the target is an exact Basic Team Rocket Pok?mon, one exact Enhanced Hammer can remove the protected Active's unique Special Energy, and that removal makes every printed Active attack unpaid. It then performs Hammer -> exact Energy -> END with snapshot/rollback, duplicates, and fail-closed semantics. Evolved Team Rocket targets and ordinary-damage attacks remain negative controls.

## Next wake

1. Refresh authenticated submissions, score/status, UTC quota, and exact episode IDs before any external write. Compare the new episode set against `{87485384, 87485519}` and download every genuinely new replay.
2. Shadow every new public replay in the correct seat against formal parent SHA `6AEF...DB6C`; inspect every v4 start/continuation and every first action difference. Score movement without a policy difference is not causal evidence.
3. Collect the Fast worker. Root independently verifies the exact parent diff, frozen hashes, focused controls, both-seat engine continuations for both anchors, current-plus-historical shadows, every changed position, compile/import, legal60/ACE1, loader-only/last, cache-free state, duplicates, valid actions, and both-seat smoke. Never weaken the frozen contract.
4. Freeze any remaining checked execution under a new immutable destination and use `ptcg_eval_runner` only for deterministic execution. Use Sol-Ultra numerical/qualitative audit where interpretation is required, root recomputation, then one `ptcg_sol_ultra_worker` for final breakage-only judgment.
5. The user authorizes practical exploratory submission when structural gates pass; weak win rate alone is not a blocker. Root alone packages and submits. Never submit a duplicate, invalid, illegal, unpackaged, filler, known-broken, or stale-hash artifact. Immediately before a write, refresh again and record exact quota, hashes, rows, schedule equality, faults, and decision.

Continue practical submit-repair cycles until live Gold or no credible next move remains.
