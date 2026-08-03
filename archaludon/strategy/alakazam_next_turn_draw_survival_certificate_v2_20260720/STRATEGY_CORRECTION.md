# Strategy correction: next-turn draw survival certificate v2

Selected: 2026-07-20 JST  
Owner: root  
Sol-Ultra verdict: conditional `ACCEPT-TO-IMPLEMENT` for one v1 correction; v1 is rejected

## Why v1 is rejected

The fixed schedule was structurally clean, but exact-v3 scored 86/144 and v1 scored 84/144, with zero gains and two regressions. The compact 72-key subset was 37 versus 35. Both regressions came from the same over-suppression:

- `known_target/historical_silver/p1/2026071600`, step 123;
- `known_target/marnie_sota/p0/2026071600`, step 135.

In both states the parent selected an Active Kadabra-to-Alakazam evolution with deck count one and two Prizes remaining. V1 replaced the evolution with END because the evolution's optional draw could consume the final deck card. The parent instead evolved, drew, attached a Psychic Energy already present in the pre-draw hand, and took the final two Prizes. Thus v1 correctly identified a positive-deck-to-zero effect but incorrectly removed a complete terminal route.

The originally proposed repair based on an already energized Kadabra is also rejected: both Active Kadabra had zero Energy.

## Authorized correction only

Create `candidates/alakazam_next_turn_draw_survival_certificate_v2` as an exact sibling of frozen v1 source/runtime/deck:

- v1 source SHA-256: `225CDAC94FD1C87C3956993120D519F8B191279CA8737F758B717E8DDA9E3F07`;
- runtime SHA-256: `9CA7A415451B84343165EF8A5CDC0D67BBF1B4969A13C984C09B142B4898CD9A`;
- deck SHA-256: `7B413177E5077777F2178143839C0155B03B92BBC8B3A6607621A7D43F351141`.

Add one `DRAW_FREE_TERMINAL_EVOLUTION` transaction. It may start only when:

- deck count is exactly one;
- the parent selected a specific ordinary evolution of the complete, turn-ready Active Kadabra into Alakazam;
- the Active has zero Energy and the turn's attachment remains unused;
- a Psychic Energy already in hand is frozen Basic-first, then by serial; the unseen top card is irrelevant;
- the current opponent Active and all relevant public blockers are complete and clear;
- consuming the held Alakazam and frozen Energy still leaves `20 * handCount` at or above target HP;
- the exact Powerful Hand KO takes the final Prizes or boards out the opponent.

The frozen transaction is:

`EVOLVE -> ACTIVATE NO -> attach frozen Psychic -> optional Telepath search [] -> Powerful Hand -> resolution`

Telepath's optional Bench search must be skipped only when its exact callback has `minCount == 0`. A required search or any missing/ambiguous prompt fails closed. The route may not use a newly drawn identity, Enriching Energy, Boss, a Bench evolution, a prior attachment, a status-blocked attacker, a nonterminal target, or any broader attachment policy.

Every stage freezes and revalidates player, turn, action count, exact card and Pokémon serials/fingerprints, nested Kadabra stack, hand carry, deck count one, both fields, target, HP/modifiers, Prize counts, status, attachment state, and option bijections. A mismatch clears once and delegates inherited v1 behavior without restarting on the same observation.

## Positive fixtures

- Historical-Silver regression: freeze the parent-selected Alakazam despite two legal Active-evolution copies; choose ACTIVATE NO, attach pre-existing Basic Psychic ID 5, and take the final two Prizes with deck one.
- Marnie regression: choose ACTIVATE NO, attach pre-existing Telepath Psychic ID 19, explicitly choose an empty optional search, and take the final two Prizes with deck one.

The projected no-draw attack damages are 460 against 300 HP and 420 against 320 HP, respectively.

## Retention and gates

- Preserve the two live v1 suppressions: `86892228/S155` and `86893328/S158`.
- Preserve the initial-ten total of exactly two parent differences over 669 callbacks and zero invalid actions.
- Preserve all v1 safe-draw, Dudunsparce, D=0, malformed, inherited-latch, and Starmie controls.
- Negative tests must cover insufficient damage, nonterminal Prize value, no pre-existing Psychic, attachment already used, status/blocker, Bench evolution, deck not one, required Telepath search, serial/option ambiguity, stale stage, and repeated callbacks.
- Rerun the immutable 144-key fixed schedule with deterministic duplicates.
- Before any exploratory submission review: at least 86/144 overall, at least 37/72 on the compact subset, both v1 regressions recovered, zero new regression against exact-v3, zero action/max-step/duplicate/schedule faults, and trace-confirmed completion of both corrected routes.

This correction is part of the same next-turn draw-survival hypothesis. No second strategic rule is authorized.
