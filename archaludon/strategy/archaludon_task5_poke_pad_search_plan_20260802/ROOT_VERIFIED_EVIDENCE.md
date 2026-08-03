# Root-verified evidence: Task 5 Poké Pad search plan

Date: 2026-08-02 JST

## Immutable parent

- Parent directory: `autonomous_gold_20260715/candidates/archaludon_public_pre_attack_executable_successor_bench_zero_continuity_gate_v1`
- Parent `main.py` SHA-256: `CAF2C696AE9F6102C1A4A8E67649C309104064CAABF9643865BE766D91BDE8DD`
- Parent `deck.csv` SHA-256: `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`
- Task plan SHA-256 before Task 5 implementation: `C1B5825E26A827E25E204F67CB7635B1AC09DF787CF2A0B26F71F5C62249F6F0`

Task 5 must copy this exact parent into a new isolated candidate. It may change only `main.py`. The 60-card deck and the other eleven package entries are invariant.

## Deck facts

Poké Pad is card `1152`, four copies. Its exact registered text searches the deck for a Pokémon without a Rule Box and puts it into hand.

The deck's eligible Pokémon roles are:

- Duraludon `169`, four copies: Basic successor and evolution base;
- Cinderace `666`, four copies: Basic free-retreat Turbo Flare engine;
- Archaludon `840`, two copies: non-Rule-Box Stage 1 for Duraludon, one-Prize Coated Attack route.

Archaludon ex `190` is not Poké Pad eligible.

## Existing behavior and gap

The cumulative parent already contains a narrow `_pfc_search_watch` path. It arms only when the parent has already selected Poké Pad, Active is exactly Duraludon, Bench is empty, and the current attack route is certified. On the reveal callback it considers only Duraludon. It then requires a visible Archaludon ex, a visible hand Metal, and a visible discarded Metal before it owns `Duraludon to hand -> Duraludon to Bench -> current attack`.

Therefore it does not provide a general Task 5 plan for:

- a Cinderace Active that should search Duraludon before Turbo Flare;
- a nonempty but non-executable Bench;
- choosing Cinderace when the deck needs a free-retreat setup engine;
- choosing non-ex Archaludon when an existing Duraludon can evolve and Coated Attack is the concrete route;
- completing the revealed target's placement/evolution purpose when the old narrow certificate is unavailable;
- safe recovery when the expected target is absent from the reveal options.

Task 4 now prevents the inherited non-terminal attack fallback from overwriting a valid parent Poké Pad play at Bench zero or under exact no-successor proof. Task 5 must own what happens after that protected play without weakening Task 4's terminal and transaction-owner precedence.

## Replay anchors

- Episode `89347400`, correct seat 1, replay SHA-256 `F389CF9FD13BE52D155A3FA7B9FF5750358F3016848640236D4E2562DA1053A4`: Cinderace remained alone and attacked before formation. This replay proves the board-formation objective, but its two material parent actions were Explorer and Ultra Ball, not Poké Pad. It is a negative/no-special-case anchor for Task 5.
- Episode `89285518`, replay SHA-256 `CD63C977911B1A287C56E53D267F08D5C68D1322927416673F2D2266B43BB890`: Task 4 preserves a Poké Pad parent action at step 26 under exact no-successor proof.
- Episode `89282820`, replay SHA-256 `8861144C5AF9E93A3435A323F9480F1FB01B6E5C9D2549635394DCF4F9B00A0D`: Task 4 preserves Poké Pad at step 62 under exact no-successor proof.
- Episode `89293161`, replay SHA-256 `E442E950C2D5C7F516CD25CD5D5CA2E98819426A6CD27CEEC18E0161F89B3C33`: prior loss audit identified an early Cinderace search/Bench formation failure. Use only as a qualitative continuity anchor; do not encode its episode identity.

The Task 4 checked regression set contained 389 correct-seat decisions and seven parent-candidate differences. All Task 4 differences preserved a board-forming/support prefix; it did not choose any Poké Pad search result.

## Required Task 5 boundary

Select exactly one coherent public-state deterministic rule that owns Poké Pad from MAIN play through its reveal-dependent target choice and the immediately available realization of that target's declared role.

Required priorities:

1. exact terminal win;
2. existing transaction owner;
3. exact already-executable attacker/backup facts and Bench capacity;
4. one declared Poké Pad role;
5. inherited parent outside the transaction.

The rule may use only current public state and exact card/effect metadata. It must not infer hidden deck contents, use replay IDs, imitate recorded actions, or stack an Ultra Ball policy. It must fail safely when options do not contain a target for the declared role, and it must not consume a last Bench slot without a declared executable purpose.

## Required verification

- exact parent hash and source diff;
- focused both-seat, option-permutation, duplicate-callback, target-present, target-absent, full-Bench, terminal, existing-owner, and malformed-state fixtures;
- complete multi-callback engine-shaped path for each admitted Poké Pad role;
- correct-seat shadow of the replay anchors and inspection of every first difference;
- compile/import, Kaggle loader-last-callable, legal 60/ACE1, cache-free package;
- both-seat exact-engine smoke with zero action errors and no max-step hit.

This Task 5 gate is implementation safety, not a win-rate claim. Broad local strength is not required before the user-requested practical live probe, but known-broken or invalid behavior is forbidden.
