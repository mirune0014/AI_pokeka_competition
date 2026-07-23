# Final Strategy Judgment: Active-Kadabra Pre-Attack Stage-Up v1

Judgment time: 2026-07-18 15:50 JST  
Authority correction and re-freeze: 2026-07-18 15:54 JST  
Role: read-only final strategy judge  
Candidate: `alakazam_active_kadabra_pre_attack_stage_up_v1`

## Decision

**A — PACKAGE_AND_SUBMIT_ONE_EXPLORATORY_PROBE near 17:15 JST, after the mandatory authenticated refresh. Keep exact v3 as the rollback and strength baseline.**

This is authorization for one live-learning probe, not an adoption, promotion, or claim that the candidate is stronger than v3. The fixed local panel shows exact outcome parity and clean execution, while the intended rule activates too sparsely for that panel to estimate its live value. A single controlled submission is therefore the proportionate next experiment, especially under the user's explicit preference to validate sound candidates in practice rather than reserve all quota for unattainable local certainty.

## Frozen identity

- Strategy selection: `STRATEGY_SELECTION.md` — SHA-256 `55236B1EE92F43AD151001608270BEEBFB1869F7235D08F8FBEE0FC74D877B85`
- Candidate source: `main.py` — SHA-256 `6F773CD374D27CA01D2DD97C12D70A705E5BB38749E735B451BCD72876838581`
- Exact parent v3 source — SHA-256 `49E954F53E043CD79D928DFB2340CCB5D85A17F33CCB824C871CCE153C0C9C95`
- Implementation diff — SHA-256 `D989CA6879722F766134BC1B4765FBAF333A7BFC980AAF35DA04654568B40589`
- Runtime — SHA-256 `9CA7A415451B84343165EF8A5CDC0D67BBF1B4969A13C984C09B142B4898CD9A`
- Deck — SHA-256 `7B413177E5077777F2178143839C0155B03B92BBC8B3A6607621A7D43F351141`
- Phase-0 schedule — SHA-256 `4271E31503F37EFE4B1BBB9ED2D3569D79D9C1E9B2A20387CCAC131F28346010`
- Execution freeze — SHA-256 `D058898AD3AFC02638723C048CC1F945C17EBC44DC77CD2347194A78EF31F41C`
- Execution report — SHA-256 `644AC5B6AE8E5627D40C67F31422ABCFB64F65A6FC8F602184DA4FA2CF1E79D4`
- Independent numerical audit — SHA-256 `9C2F63C8015BE80401EEFF0324623E7E8F4A6D4304FEA3463E6FD846C1172DBA`
- Root Phase-0 verification — SHA-256 `614C14810365A44F1A2C094FAA19BD0F62A3177435DE644B9A77376EDCF25BDC`
- Candidate summary/trace tree — SHA-256 `20F7048D001C8F53EC92926AFD955F4BCE2B7FEF06632B94602CBB29CB9D0122`
- Candidate full-raw tree — SHA-256 `17D5488C64DC0B075695251ACC13E6A7FED397FFCBFDEB387337E81AA8BB0B35`
- v3 summary/trace tree — SHA-256 `E732A0F8F496664F671377A9F000B00AE4184A68B78F1E211C2AC1F069FF6276`
- v3 full-raw tree — SHA-256 `1B62E96F68BB555DB8D48731BC70915E2F522D42B55AD7F48FE0230F80244D3B`

### Authority correction record

The first freeze of this judgment contained two submission-critical transcription errors in the v3 tree-digest lines. The following strings are explicitly **rejected and non-authoritative**:

- rejected v3 summary/trace transcription: `E732380E7604D80B408818BFAB7894451BDFE237D6B8C731571E3DB2B98C6276`;
- rejected v3 full-raw transcription: `1B62BDBB4D2EF78269BF2D2227C24AEE78973A1ADEB8BD9B42EBB1BDC17D1D3B`.

The corrected bound authorities are the two values in the list above. They agree exactly across the execution freeze, independent numerical audit, audit reproducer output, and root Phase-0 verification: summary/trace `E732A0F8F496664F671377A9F000B00AE4184A68B78F1E211C2AC1F069FF6276`; complete raw `1B62E96F68BB555DB8D48731BC70915E2F522D42B55AD7F48FE0230F80244D3B`.

Every other hash bound in this section was rechecked against the cited audit/root documents and, where it is a direct file authority, independently recomputed from disk. Strategy selection, candidate source/runtime/deck, exact parent source, implementation diff, schedule, execution freeze/report, independent audit, root verification, and both candidate tree digests all match the values recorded above. No raw artifact, paired row, outcome, trace interpretation, or gate result changed. The correction therefore leaves Decision A unchanged; it removes the former document-level invalidation rather than changing the evaluated candidate.

Any mismatch invalidates this judgment until the changed artifact is re-evaluated.

## Verified evidence

### Structural and engine safety

- Compile, import, callable-agent, legal 60-card deck, copy-cap, deterministic-cache, and artifact-hash checks passed.
- All 12 focused rule tests passed. They cover the exact `EVOLVE -> YES -> PH` engine sequence, one- and two-copy canonical choice, deck-three rejection and deck-four start, Mist Energy, Rock Chestplate, status, Splas​hing Dodge heads, draw-offer/resolution state failures, 48 named retention callbacks, and 532 full-win retention callbacks.
- All inherited v3 active-Psychic, live, stranded, checked-engine, first-boundary, and strict-Prize-boundary tests passed.
- Both packaged historical-Silver smoke games, one from each seat at seed `2026101741`, completed as wins with zero action errors and no max-step hit.
- The latch is observation-state driven and fail-closed: `await_draw_offer`, `await_draw_resolution`, and `await_resolution`; it does not branch on drawn-card identity.

### Fixed paired Phase 0

- Exact schedule equality: 144 unique `(panel, opponent, seat, seed)` rows for candidate and v3; no duplicate or missing keys.
- Total: candidate `86/144`, v3 `86/144`.
- Seat: P0 `45/72` versus `45/72`; P1 `41/72` versus `41/72`.
- Panel: known `44` versus `44`; fresh `42` versus `42`.
- Every opponent bucket is exactly equal: Oselcoun 8, Rmy 7, Dragapult 15, Great Tusk 4, historical Silver 8, KC 10, Marnie 11, Lucario 14, and Starmie 9.
- Outcome changes: `0` gains and `0` regressions.
- Execution failures: zero nonzero exits, action errors, max-step hits, or first-player mismatches.
- The independent audit recomputation reproduced the report, schedule, hashes, tree hashes, row counts, and structural gates.

The practical exploratory-probe gate passes. The strict adoption gate fails: total wins do not reach 87, and gains do not exceed regressions. Therefore v3 remains the accepted baseline regardless of an un-attributed live score movement.

## Changed-position judgment

Only two of 144 paired traces changed. Both are intended Active-Kadabra stage-up sequences in the Marnie/P1 bucket, and both remain losses:

1. Known seed `2026071599`, S124: the rule starts at hand/deck/prizes `20/5/3`, evolves Active Kadabra, accepts the three-card draw, and uses PH 440 to KO a 110-HP one-Prize target. Candidate later loses by deck-out with two Prizes remaining; v3 loses with one deck card and three Prizes remaining.
2. Fresh seed `2026101802`, S117: the rule starts at `17/4/5`, uses PH 380 to KO a 320-HP two-Prize target, and later loses by deck-out with three Prizes remaining; v3 loses with five Prizes remaining.

Both traces are complete, valid, related to the frozen hypothesis, and show real tactical Prize conversion. Neither proves match-level improvement. Their common risk is equally real: spending three deck cards from a starting deck of four or five. The existing guard rejects deck three and permits deck four because the post-draw deck remains nonempty, except that this does not model the full subsequent deck clock. That is acceptable uncertainty for one probe, but it is not acceptable evidence for adoption.

The rule's domain value is coherent: when Super Psy Bolt is the unique finalized attack but cannot take the best exact KO, it stages an already powered Active Kadabra into Alakazam only when the resulting exact KO has strictly higher Prize yield. The three-Prize Mega Lucario fixture is the highest-value target case. Modifier and transient-prevention checks fail closed, and identical Alakazam copies resolve canonically.

## Why submit rather than defer

- The candidate has no known invalid or broken behavior and preserves all fixed-panel outcomes.
- The mechanism is strategically distinct, deterministic, interpretable, and narrowly gated.
- Two activations in 144 games are insufficient to estimate whether extra Prize conversion outweighs the three-card deck cost in the live opponent population.
- The latest authenticated snapshot available to this judgment, captured at 14:20 JST, showed quota use `2/5`; exploratory submission `54799469` was complete at 709.5 and exact v3 `54797361` at 770.3. These values are stale by design and cannot authorize a write without a new refresh.
- The preceding submission was around 14:15 JST, so approximately 17:15 JST respects the requested three-hour learning cadence while using only one candidate.

This judgment does not infer value from submission `54799469`'s score. Its one public win contained valid activations of a different rule, but that is neither evidence for nor against this candidate, and the two mechanisms must not be stacked without a new full evaluation.

## Mandatory pre-submit conditions for the root

The root may consume exactly one Kaggle slot only if all of the following hold immediately before the write:

1. Wait until approximately 17:15 JST unless a later operational constraint provides a concrete reason to adjust. Make only one external submission write in this cycle.
2. Refresh authenticated Kaggle submissions, status, score, UTC-day quota, public episode IDs, and every genuinely new public replay. Independently verify the ID set difference against the prior snapshot.
3. Confirm at least one slot remains, no identical candidate/package has already been submitted, and no upload row was created by an earlier attempt. If the competition objective has already been achieved by a live-Gold submission, cancel this exploratory write as unnecessary.
4. Recheck every frozen hash above. Do not silently repackage a changed source, runtime, deck, freeze, or evaluated output under this judgment.
5. Build a clean archive, re-extract it, and verify compile/import, callable agent, legal 60 cards, copy caps, ACE SPEC constraint, deterministic initial action, frozen-file identity, and packaged smoke from both seats with zero errors and no max-step hit.
6. Confirm the refresh contains no new evidence of an action error, incomplete/fail-open latch, modifier or transient-prevention no-start violation, deleted terminal attack, failed exact KO, or known v3 win converted to a candidate loss by this rule.
7. Use an ASCII-safe description such as: `Alakazam Active-Kadabra stage-up v1; 86/144 parity; exploratory live probe`.
8. If the Kaggle CLI reports a local CP932/printing exception after upload, refresh the API and CLI submission list before any retry. Never double-submit based only on the local exception.

Abort rather than submit if any condition fails, the quota is absent, the artifact is duplicate or invalid, a hash drifts, or genuinely new evidence identifies a causal safety violation. A mere score movement in the prior exploratory submission is not itself a reason to stack, cancel, or attribute anything; only concrete replay evidence can alter this rule judgment.

## Required live-learning protocol

For every genuinely new public episode of this probe, compare the candidate and exact v3 statefully at every target callback. Do not attribute a score change, win, or loss to the rule unless the rule actually activates.

For each activation, record:

- episode, seat, step, opponent/deck diagnosis, and terminal result;
- start hand, deck, and Prize counts, with deck bucket `4-5` versus `>=6`;
- target HP, target Prize value, pre-stage-up attack damage/Prize yield, and post-stage-up exact damage/Prize yield;
- visible modifier certificate and transient-prevention result;
- the full `EVOLVE -> YES -> PH` latch sequence, including whether it completed or failed closed;
- Prize delta, next-turn attack continuity, final deck count, and terminal reason.

Primary target: exact three-Prize conversion against Mega Lucario. Secondary targets: meaningful one- or two-Prize conversions in mirrors and Marnie-like resource-pressure games. Mandatory risk target: deck-four/five activations followed by avoidable deck-out or loss of attack continuity.

Immediately roll back to exact v3 and reject the rule if live evidence shows an action error, incomplete/fail-open sequence, hidden drawn-card identity dependence, Mist/Rock/transient-protection violation, stage-up exact-KO failure, erased terminal attack, or a causally attributable v3 win becoming a candidate loss. Repeated low-deck activations that spend three cards without producing match-level tempo or Prize benefit are grounds for a new, separately evaluated deck-clock guard; they are not grounds to patch this frozen submission in place.

## Next decision question

**Does the exact one-, two-, or three-Prize conversion obtained by staging Active Kadabra outweigh the three-card deck expenditure, and does that answer differ between start-deck `4-5` and `>=6`, or by target Prize value?**

Until fresh evidence answers that question and a new candidate passes the strict gate, exact v3 remains the rollback baseline and this candidate remains an exploratory probe only.
