# Archaludon human-fundamentals planner TODO

The current Japanese execution checklist, including the rejected v1 evidence
and parent-preserving successor requirements, is `TODO_JA.md`. It is the
controlling checklist for the next implementation.

## Current status

`IN PROGRESS — first implementation failed the human-play audit`

The first source version passed legality and focused synthetic tests, but its
own both-seat engine smoke exposed two submission-blocking fundamentals errors:

- it ended the turn with a legal positive-damage Archaludon ex attack;
- it declined a legal defensive Archaludon ex evolution even though the
  evolution converted a nearly-KO'd Duraludon into a surviving future
  attacker.

Therefore, checked boxes below must mean that the behavior affects the
production action choice. A semantic tag, helper function, or synthetic test
that is not connected to arbitration is not sufficient.

The completed identical-seed/both-seat v1b evaluation was mechanically valid
but catastrophic: parent 8/16, candidate 1/16, zero paired gains and seven
paired regressions. The rejected v1 must never be packaged or submitted.
See `../../evaluations/archaludon_human_fundamentals_turn_planner_v1/ROOT_V1B_REJECTION.md`.

The current correction pass must also remove hard-coded two-Prize clock
assumptions, make known one-resource threats affect safety decisions, prevent
wasted Energy acceleration, and choose safe visible alternatives inside
purpose-bound search transactions.

## Objective

Build a deterministic public-state Archaludon agent whose default behavior
matches strong human Pokémon TCG fundamentals. The new policy must reason from
card effects, resulting board state, Prize exchange, attack continuity, and
resource roles. It must not use the old parent's selected action as the
activation condition for an improvement.

This candidate is a new isolated child of:

`candidates/archaludon_integrated_public_turn_plan_transaction_v1`

The parent remains read-only.

## Non-negotiable design rules

- [ ] Legality and engine safety are hard gates.
- [ ] Terminal wins and prevention of immediate terminal losses are hard
      branches.
- [ ] Exact tactical dominance is handled by conditions, not arbitrary score
      bonuses.
- [ ] Soft scores are allowed only to break ties between strategically
      admissible plans.
- [ ] Every action that consumes a card must have a declared purpose.
- [ ] Search, discard, recovery, evolution, acceleration, gust, retreat, and
      attack callbacks belonging to one purpose form one transaction.
- [ ] Unknown card text does not silently become zero damage or zero threat.
- [ ] Improved rules are generated from board properties, never from the
      identity of the action selected by the historical parent.
- [ ] No episode IDs, replay IDs, opponent IDs, or replay-shaped exact board
      identities are production conditions.

## Phase 0: freeze and isolate

- [ ] Copy the exact parent into
      `candidates/archaludon_human_fundamentals_planner_v1`.
- [ ] Record parent `main.py`, deck, runtime, and card-database hashes.
- [ ] Preserve the legal 60-card deck unchanged for the first policy-only
      candidate.
- [ ] Remove caches and generated artifacts from the candidate tree.
- [ ] Add a source-only contract showing that the only policy change is the
      human-fundamentals controller and its shared semantic helpers.

## Phase 1A: shared card semantics

### Damage and attack effects

- [ ] Replace rule-local damage arithmetic with one authoritative damage
      function used for our attacks and opponent attacks.
- [ ] Apply printed/formula damage.
- [ ] Distinguish attack damage from damage-counter placement.
- [ ] Apply Weakness and Resistance with the engine's exact value.
- [ ] Apply Full Metal Lab symmetrically to both players.
- [ ] Apply Hero's Cape through actual maximum/current HP.
- [ ] Apply Metal Defender's next-turn no-Weakness effect.
- [ ] Apply Coated Attack's Basic-Pokémon damage prevention.
- [ ] Support Raging Hammer from actual damage counters.
- [ ] Support fixed damage, hand-size scaling, Energy scaling, discard scaling,
      self-damage scaling, and simple coin/random ranges.
- [ ] Return `(floor, expected class, ceiling, confidence)` for effects that
      cannot be known exactly.
- [ ] Never certify survival from an unknown ceiling.

### Abilities and persistent effects

- [ ] Normalize public ability text into semantic tags:
      damage modifier, prevention, Energy acceleration, draw/hand growth,
      evolution acceleration, switch/retreat, healing, Prize modifier, Bench
      damage, return-to-hand/deck, and usage limit.
- [ ] Track whether a public once-per-turn ability has already been used.
- [ ] Feed ability effects into damage, readiness, hand ceiling, and board
      continuity.
- [ ] Preserve exact known effects for Assemble Alloy and Explosiveness.
- [ ] Treat unsupported ability text as an uncertainty interval, not a reason
      to disable all strategy.

### Public state and resources

- [ ] Maintain a deterministic public ledger for our essential resources:
      Duraludon, both Archaludon forms, Metal, Boss, recovery, draw, search,
      healing, tool, and stadium.
- [ ] Maintain known opponent cards from play, discard, revealed/search
      callbacks, and cards publicly returned to hand.
- [ ] Count visible copies and mark Prize/hidden-zone uncertainty.

## Phase 1B: reachable attack and threat model

- [ ] Enumerate our payable attacks now.
- [ ] Enumerate our attacks after one manual attachment.
- [ ] Enumerate our attacks after a legal hand evolution and known ability.
- [ ] Enumerate Active-to-retreat/switch-to-Bench attack routes.
- [ ] Enumerate opponent attacks in the same classes.
- [ ] Distinguish:
      `READY_NOW`, `ONE_ORDINARY_RESOURCE`, `KNOWN_COMBO`, and
      `HIDDEN_SPECULATIVE`.
- [ ] Include visible evolution successors by card semantics rather than an
      exact card-ID fixture.
- [ ] Include attack, Bench damage, gust, retreat/switch, Energy acceleration,
      and Prize yield in each route.
- [ ] Produce minimum and maximum public return damage and the number of Prizes
      exposed by each of our candidate Actives.

## Phase 1C: strong-player hard decisions

### Setup

- [ ] Prefer going second while Turbo Flare is the opening plan, but express
      the reason as first-attack access rather than a permanent magic number.
- [ ] Put Cinderace Active when Explosiveness is legal.
- [ ] Bench a Duraludon during setup when it provides a Turbo Flare recipient,
      a backup Pokémon, or donk protection and does not create a strictly worse
      public board.
- [ ] Never use `never bench during setup`.

### Terminal and Prize clock

- [ ] Take a legal terminal win immediately unless another action is mandatory.
- [ ] Prevent an immediate public terminal loss when a legal line exists.
- [ ] Compare attacks by number of Prizes gained now, Prizes exposed next, and
      attacks remaining for both players.
- [ ] Prefer a one-Prize Active when it takes the same Prize and the ex is
      publicly one-shot.
- [ ] Allow deliberate sacrifice when it creates a shorter or strictly safer
      winning Prize route.
- [ ] Allow declining a KO when the KO creates a forced losing promotion/return
      attack and a non-KO line preserves a better route.
- [ ] Allow targeting a Bench evolution engine instead of the Active when the
      resulting Prize/attack route dominates.

### General non-ex Archaludon role

- [ ] Remove the blanket `-1000` outside Ogerpon.
- [ ] Evolve to non-ex when any of these property-based conditions dominates:
      exact 120 KO, favorable two-hit conversion, Basic-damage prevention,
      one-Prize wall, avoidance of an ex-only immunity, recovery of a stranded
      Active, or preservation of a better Prize route.
- [ ] Keep ex evolution when Assemble Alloy or 220 damage produces the better
      route after return-threat and Prize calculations.
- [ ] Search and preserve non-ex based on reachable role, not detected deck
      name.
- [ ] Count non-ex Archaludon as a completed attacker line in board-formation
      logic.

### Attack, retreat, promotion, healing, and tool use

- [ ] Compare every legal attack by KO/Prize, effect, return threat, continuity,
      and next attacker.
- [ ] Retreat only when the resulting Active/Bench state dominates staying.
- [ ] Promote by survival, Prize liability, attack readiness, free retreat,
      and sacrifice value; remove static identity-only order.
- [ ] Heal only when healing crosses a survival/attack-count threshold or
      preserves a winning route.
- [ ] Do not heal when it removes a required Raging Hammer KO without a
      compensating benefit.
- [ ] Attach Hero's Cape to any legal Pokémon when it changes the attack count
      or Prize route; do not exclude non-ex by identity.
- [ ] Play Full Metal Lab only after comparing its effect on both players.

## Phase 1D: conservative card use and turn transactions

### Generic action-use rule

- [ ] Remove "all items = 20000".
- [ ] A card is admissible only if its transaction has a declared purpose:
      complete current attack, create backup, achieve/deny KO, change Prize
      clock, preserve survival, recover essential resource, improve hand
      quality, or prevent deck-out.
- [ ] If the current attack/terminal route is already secured, permit only
      setup actions that cannot reduce that route under the public worst case.
- [ ] Preserve cards whose only gain is speculative and unnecessary this turn.

### Ultra Ball and Poké Pad

- [ ] Choose the search target before committing the play.
- [ ] Verify the complete discard pair before committing Ultra Ball.
- [ ] Protect the last functional attacker, evolution, Boss, recovery, draw,
      stadium, tool, and Metal reserve needed by the selected route.
- [ ] Search non-ex/ex/Duraludon by the resulting turn plan, not fixed identity
      order.

### Pokégear, Explorer, and Lillie

- [ ] Decide which supporter effect is needed before playing Pokégear.
- [ ] Compare Explorer and Lillie by hand transformation, deck size, resource
      loss, current attack security, and next attacker.
- [ ] Do not play draw/search merely because it is legal.
- [ ] Preserve Boss when a visible gust route matters.

### Night Stretcher

- [ ] Choose the intended recovery target before playing the card.
- [ ] Lock the callback to that target unless the observed public state
      invalidates the plan.
- [ ] Support Pokémon and Metal recovery through one shared resource plan.

### Energy acceleration

- [ ] Treat Turbo Flare's up-to-three placements as one allocation plan.
- [ ] Treat Assemble Alloy's up-to-two placements as one allocation plan.
- [ ] Allocate Energy to current and next attackers by attacks-to-ready, not
      static target scores.

## Phase 1E: arbitration and fallback

- [ ] Add hard precedence only for:
      legality, mandatory engine contexts, terminal win, immediate terminal
      loss prevention, and an already committed valid transaction.
- [ ] Generate all other candidate plans from the same board snapshot.
- [ ] Compare plans by a common lexicographic result:
      terminal result, Prize-race turns, immediate Prizes, Prizes exposed,
      guaranteed attack continuity, return-damage survival, essential resource
      reserve, and only then a deterministic tie-break.
- [ ] Do not resolve strategic conflicts by fixed rule rank.
- [ ] Fallback order:
      exact semantics -> conservative interval semantics -> generic
      fundamentals planner -> historical parent only for truly unsupported
      engine contexts.

## Phase 1 source-only acceptance tests

- [ ] Compile/import succeeds.
- [ ] Legal 60-card deck; exact source deck unchanged.
- [ ] Exactly one final callable `agent`.
- [ ] No cache/generated files in the package.
- [ ] Deterministic duplicate callback behavior.
- [ ] No production condition contains an episode/replay/opponent ID.
- [ ] Fundamentals decisions do not require a particular parent action.
- [ ] Setup tests cover Cinderace Active plus Duraludon Bench, Duraludon-only
      fallback, and no-legal-Bench negative.
- [ ] Non-ex tests cover exact 120 KO, Basic prevention, one-Prize wall,
      ex-better negative, and generic non-Ogerpon identities.
- [ ] Damage consistency tests cover Weakness, Resistance, Full Metal Lab on
      both players, Hero's Cape HP, Raging Hammer, Metal Defender, Coated
      Attack, hand scaling, discard scaling, and counter placement.
- [ ] Ability tests cover damage modifier, Energy acceleration, draw growth,
      prevention, retreat/switch, and unknown-text uncertainty.
- [ ] Threat tests cover ready now, one manual attachment, evolution, visible
      acceleration, retreat-to-attacker, and hidden-speculative separation.
- [ ] Prize tests cover same-KO one-Prize versus two-Prize exposure, deliberate
      sacrifice, decline-KO, terminal Boss, and Bench-engine targeting.
- [ ] Item tests prove no-purpose cards are held and purpose-bound
      search/discard/recovery callbacks complete their selected transaction.
- [ ] Full-engine both-seat smoke completes with zero invalid actions,
      exceptions, or max-step hits attributable to the candidate.

## Phase 2 TODO: broaden semantic coverage

- [ ] Classify every legal card's public attack and ability semantics from the
      competition card database.
- [ ] Add bounded handling for complex coin distributions, spread allocation,
      effects ignoring Pokémon effects, and multi-target attacks.
- [ ] Add public known-hand inference from every supported search/reveal/return
      effect.
- [ ] Add matchup feature vectors without exclusive archetype labels.
- [ ] Add two-turn bounded plan comparison for lines whose first action does
      not immediately change attack readiness.

## Phase 3 TODO: deck-policy iteration

- [ ] After the fundamentals policy is stable, measure whether all 60 cards
      have a live role.
- [ ] Only then consider changing card counts or removing cards whose role
      remains dominated.
- [ ] Evaluate deck changes separately from policy changes.
