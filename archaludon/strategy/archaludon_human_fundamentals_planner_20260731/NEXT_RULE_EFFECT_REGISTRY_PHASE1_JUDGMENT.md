# Next-rule judgment: deterministic public-effect registry phase 1

## Decision

Select **Option B: deterministic public-effect registry phase 1** as the one
next rule hypothesis. Do not implement Trainer-purpose transactions in this
candidate.

Hypothesis:

> If every decision-relevant, deterministic public effect in the frozen phase-1
> set is converted into a typed state transition and updates the same combat,
> return, readiness, resource-ledger, and transaction fields used by PCRD v2,
> then PCRD v2 can make more human-valid exact decisions without weakening its
> hierarchy or reopening inherited fixed-score behavior.

Trainer-purpose transactions must follow this layer. Pokégear, Explorer,
Lillie, Night Stretcher, Cape, Ice Cream, Full Metal Lab, Boss, and attachment
plans all ask whether an action changes Prize, survival, return damage, attack
continuity, or exact backup readiness. Implementing them while those fields
ignore visible effects would either make a false exact claim or fall back to
the inherited score branch the program is meant to replace.

## Verified basis

- PCRD v2 candidate `main.py` SHA-256:
  `4B9851F54A49DE19614F4E9AACBB430539A2DB8CCCEA3EC57108FF21DDB34ED8`.
- Root verification SHA-256:
  `AC856C29D7CEF3564B70D8E59B38AD06A927EF0290B9A69393E93463B0AE62D0`.
- Root independently verified `38/38` tests, frozen16 outcomes of
  `3 positive / 1 conditional parent / 12 negative parent`, both-seat exact
  transactions `2/2`, duplicate semantic stability, and zero invalid action,
  exception, or stale transaction.
- PCRD v2 is therefore a destructive-safety development parent, not yet a
  strength promotion or submission candidate.
- Controlling planning artifacts:
  - `NEXT_HYPOTHESIS_OPTIONS.md` SHA
    `14A68B1971CAE6E529250E6C945B9DD2A94AD60FEC2D7D1F9D1DF7C59B57E529`;
  - `EFFECT_REGISTRY_PHASE1.md` SHA
    `949C9610DBBAD145E549E01EA09FF6D55E0170238089DE511EF25E05B9A3B5BA`;
  - `SCORE_FALLBACK_REPLACEMENT_MAP.md` SHA
    `42EAF9FE18C499547B9FD7D6C2650A15EA02EF5902C47F574EBF84F0C7A6B2BB`;
  - `ROOT_PUBLIC_EFFECT_COVERAGE_GAPS.md` SHA
    `80F90EA3841A1D3642CE8A66062E6001485C7185E6D5A697286CA5684DAD4EC6`;
  - `PLAYER_FUNDAMENTALS_ACCEPTANCE_MATRIX_JA.md` SHA
    `F273C043D4C479F15CC464600B14D51823BECF55D4AF22F68A0B8971F166A386`.

## Exact implementation scope

### Parent and mutation boundary

1. Make one isolated candidate from exact PCRD v2. Its final callable is the
   direct parent and must be invoked exactly once per callback.
2. Preserve PCRD v2, its deck, and all non-`main.py` package files as exact
   bytes. Append one registry layer; do not edit the deck, add Trainer-purpose
   rules, use opponent IDs/replay keys, or change Codex/Kaggle state.
3. Any registry non-admission returns the exact PCRD v2 action. PCRD v2's
   frozen lexicographic selector, doomed-chip guard, post-reply ledger, and
   transaction ownership remain authoritative.

### Typed registry contract

Each entry must bind exact normalized text/hash plus card/attack/Ability ID and
declare all state consumers it updates. A name-only whitelist is forbidden.
Use typed handlers for `ATTACK_ACCESS`, `DAMAGE_MODIFIER`, `MAX_HP_MODIFIER`,
`DAMAGE_PREVENTION`, `ATTACK_EFFECT_PREVENTION`, `DAMAGE_COUNTER_MOVE`,
`DAMAGE_COUNTER_PREVENTION`, `ATTACK_LOCK`, `POST_DAMAGE_COUNTER_RETURN`,
`POST_ATTACK_RESOURCE_LOSS`, `ENERGY_ACCELERATION`, `EVOLUTION_ACCESS`,
`SWITCH_OR_RETREAT`, and `HEAL_OR_RETURN`.

The one phase-1 candidate owns only these deterministic named effects:

- combat/access: Memory Dive, Flower Curtain, Adrena-Brain, Shadow Bullet,
  Spiky Wheel, Rock Fighting Energy, Mist Energy, Premium Power Pro,
  Mega Brave, Accelerating Stab, Spiky Energy, Grow Grass Energy, Cynthia's
  Power Weight, Mysterious Rock Inn, Superb Scissors, Cheer On to Glory,
  Draconic Buster, Raging Curse, Battle Cage, and symmetric Full Metal Lab;
- public readiness: Punk Up and Assemble Alloy; Run Away Draw, Trading Places,
  Teleportation Attack, Switch, and Surfer; Aura Jab and Turbo Flare;
  Ascension, Rare Candy, and Forest of Vitality; Wally's Compassion and Jumbo
  Ice Cream.

Existing exact PCRD handlers, including Assemble Alloy, Run Away Draw, Turbo
Flare, Jumbo Ice Cream, and Full Metal Lab, must be migrated or called through
the same registry with byte-for-byte behavioral parity; there must not be two
conflicting semantic sources.

Rapid-Fire Combo, all coin-flip distributions, and hidden Supporter/search/
Energy access are explicitly out of scope. They remain unknown to this layer;
do not replace them with expected damage or assumed access. Sacred Ash,
Lana's Aid, Hilda, Dawn, Champion's Call, Spikemuth Gym, Lunar Cycle,
Run Errand, Fighting Gong, Energy Search, Dusk Ball, Enhanced Hammer,
Buddy-Buddy Poffin, Telepath Psychic Energy, and Enriching Energy are also
deferred unless already fully handled by the direct parent.

### Required semantic updates

- Calculate weakness/resistance, ignore-effect rules, temporary modifiers,
  prevention, Full Metal Lab, and HP modifiers in the rules-correct order.
- Preserve damage versus attack-effect versus damage-counter distinctions.
  Bench damage/counters must enumerate a legal target and apply Flower Curtain
  or Battle Cage as appropriate.
- Turn-limited attack locks and Premium Power Pro require current public log /
  once-per-turn proof; they never persist by guess.
- Memory Dive exposes only printed attacks on visible `preEvolution` cards and
  retains their exact Energy cost/text.
- Spiky Energy resolves after attack damage and still returns counters when
  its damaged Active is KO'd. Draconic Buster removes all source Energy in the
  post-attack resource ledger.
- Punk Up/Assemble Alloy use only attachments visible after the resolved
  evolution callback. Aura Jab/Turbo Flare acceleration affects following-turn
  readiness, never the current attack.
- Switching enumerates the resulting legal Active and attacks. Never remove
  the last own Pokémon with Run Away Draw or treat an unavailable switch card
  as public.
- Ascension/Rare Candy/Forest of Vitality obey stage, target, turn, and
  `appearThisTurn` legality. Wally/Jumbo heal only with a public legal card and
  target and must project returned/discarded Energy/cards.
- Every handler must update all applicable PCRD certificates: current damage /
  KO / Prize, exact public reply routes, attacker survival, next payable
  attack, exact backup conversion, post-action/post-reply resource ledger, and
  saved callback transaction.

## Hard precedence

The registry supplies semantics; it never supplies a score. Final action
precedence remains:

1. legality and completion of the direct parent's or registry layer's active
   saved transaction;
2. exact current win;
3. exact terminal-loss avoidance;
4. current Prize and KO;
5. exact public-return prevention, survival, and attack continuity;
6. exact ready-backup conversion and next Prize timing;
7. post-action/post-reply resource dominance;
8. exact semantic tie or any uncertainty returns PCRD v2.

An effect may change a higher-layer field only through its exact typed state
transition. Raw damage, an Ability name, a playable Trainer, or a generic
YES/maximum-count option is never independently preferred.

## Positive and boundary-negative fixtures

Production code must not inspect fixture IDs. The worker must supply at least
one positive and one boundary negative for every named effect, using the
following frozen meanings:

| Handler/effects | Required positive | Required negative |
|---|---|---|
| Memory Dive | visible pre-evolution attack appears with printed cost/text | hidden/missing pre-evolution, unpaid or locked attack is absent |
| Flower Curtain | Bench non-Rule-Box attack damage becomes zero | Active or Rule-Box Bench is not protected |
| Adrena-Brain | Darkness-equipped Munkidori legally moves an exact 1–3 counters | no Darkness, no damaged ally, no legal target, or Battle Cage blocks Bench placement |
| Shadow Bullet | 180 Active plus 30 to one legal Bench target | no legal Bench target or applicable prevention blocks only the prevented component |
| Spiky Wheel | exact `20 + 40 × attached Darkness` | non-Darkness attachment is not counted |
| Rock Fighting / Mist | attack effects are prevented while legal damage remains | absence of the Energy gives no prevention; damage itself is not falsely prevented |
| Premium Power Pro | activated current-turn Fighting attack gains exactly 30 before weakness/resistance | non-Fighting or unproved/expired activation gains zero |
| Mega Brave / Accelerating Stab | same attack is excluded on the immediately following turn from public log proof | a different attack or later turn remains legal |
| Spiky Energy | damaged attached Active returns two counters after damage, including target KO | no attack damage, wrong zone, or absent attachment returns none |
| Grow Grass / Power Weight | +20/+70 changes max/current HP and a KO boundary | absent modifier changes neither HP nor preserved damage |
| Mysterious Rock Inn | damage from a Pokémon ex to Crustle is prevented | non-ex source is not prevented |
| Superb Scissors | target-side effects are ignored for its damage calculation | source/stadium rules outside the printed ignore scope still apply |
| Cheer On to Glory | each applicable public Cynthia modifier contributes exactly +30 | non-Cynthia or absent modifier contributes zero |
| Draconic Buster | 260 resolves, then every attached source Energy is removed from readiness/ledger | another attack or zero attachments causes no fabricated loss |
| Raging Curse | exact visible Bench damage-counter sum ×10, ignoring weakness | Active counters are excluded and zero Bench counters yields zero |
| Battle Cage | opponent attack/Ability counter placement on either Bench is prevented | Active damage/counters and non-counter effects are unaffected |
| Full Metal Lab | both players' Metal targets reduce 30 after weakness/resistance | absent Stadium or non-Metal target receives no reduction |
| Punk Up / Assemble Alloy | only post-callback visible attachments create readiness | hidden/unresolved evolution or unavailable Energy creates no route |
| Run Away / switch family | legal switch projects the new Active and exact attacker | no Bench, illegal target, hidden card, or self-loss route is rejected |
| Aura Jab / Turbo Flare | visible acceleration changes following-turn readiness | it does not pay the current attack or assume hidden Energy |
| Ascension / Rare Candy / Forest | one exact legal evolution route is projected | stage, availability, or turn/appear restriction violation is rejected |
| Wally / Jumbo | public legal heal/return changes HP and resources exactly | hidden/unavailable card, ineligible target, or unchanged KO boundary gives no exact benefit |

All symmetric effects require self/opponent variants. All optional or
multi-callback effects require YES/NO or count/target boundaries, option-order
permutation, same-ID physical-copy permutation, and duplicate callback replay.

## Fail-closed conditions

Return exact PCRD v2 when any decision-relevant condition holds:

- unknown or mismatched card/effect text, ID, duration, log proof, once-per-turn
  state, target, serial, stage, payment, or callback binding;
- a relevant public effect lacks a handler or one of its required consumer
  updates;
- multiple non-equivalent targets/routes remain incomparable;
- a deterministic handler encounters coin flip, unresolved variable range, or
  hidden-card access;
- an interaction between prevention, ignore effects, HP, weakness/resistance,
  Stadium, damage counters, KO, or post-attack resource movement is not exact;
- transaction owner collision, stale transition, duplicate mismatch,
  exception, or invalid direct-parent action.

Never treat unsupported as zero, partially apply an effect, infer opponent
policy from a replay, or let a registry result bypass PCRD v2's hierarchy.

## Minimal verification gates

All gates are mandatory before local strength evaluation:

1. Candidate identity: exact PCRD v2 direct-parent prefix/package/deck; final
   agent calls it exactly once; compile succeeds in the frozen Python runtime.
2. Destructive non-regression: all inherited tests remain green; frozen16 is
   exactly `3 positive / 1 conditional parent / 12 negative parent`; the
   existing both-seat PCRD transactions remain `2/2`; invalid, exception,
   stale, rollback, and duplicate mismatch counts remain zero.
3. Coverage: every named effect has the positive and boundary-negative fixture
   above; symmetric effects pass both owners/seats; old exact handlers have
   parity fixtures; no name-only registry entry exists.
4. Transactions: each new callback family is completed in both seats in a
   checked-engine fixture; option/serial reorder and duplicate callback yield
   the same semantic action; starts equal completions and no partial effect is
   left active.
5. Attribution: serialize effect ID/type/text hash, before/after state,
   consumers updated, selected/fallback reason, callback stage, and unsupported
   reason. Inspect every naturally changed position; each must be explained by
   one exact registry transition and the first changed action must respect the
   unchanged PCRD hierarchy.
6. Execution smoke: both seats, zero invalid actions, action errors,
   exceptions, stale transactions, duplicate mismatches, and max-step hits.

Passing these gates makes the registry candidate a development parent only.
It is not strength promotion evidence. Trainer-purpose transactions remain the
next single hypothesis after root verifies this registry's exact coverage and
destructive safety.

## Regression risks and exact evidence needed next

Risks are interaction-order errors, confusing damage with effects/counters,
incorrect turn-duration persistence, applying post-attack acceleration to the
current attack, consuming hidden resources, and registry/legacy-handler
disagreement. A large batch can also fail closed so broadly that it changes
nothing; coverage telemetry must distinguish safe silence from completed
ownership.

The next evidence is: candidate/package hashes; a registry manifest mapping
every named effect to its type, text hash, and consumers; focused positive /
negative and symmetry results; unchanged frozen16 JSON; both-seat transaction
JSON with fault counters; and the complete set of naturally changed trace
positions. No simulation aggregate or Kaggle write is authorized by this
judgment.
