# Archaludon integrated agent: source-only implementation gap audit

## Scope

This audit uses only the submitted source and deck. It does not use live battle
results or replay-derived action labels.

- Candidate:
  `candidates/archaludon_integrated_public_turn_plan_transaction_v1`
- Source SHA256:
  `3E23CC048CF87E148ACA3E7B017B5B3AAA8C422BD1580BF553222CA79BB466A2`
- Deck SHA256:
  `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`

## Executive conclusion

The current agent is not yet a general public-state turn planner. It consists
of:

1. a greedy scalar-scoring historical parent;
2. seventeen fixed-precedence, highly certified exception rules;
3. a fail-closed arbitration layer that returns to the greedy parent whenever
   a card, effect, board shape, or collision is not exactly supported.

This architecture is safe against many invalid-action failures, but it is
strategically conservative and poorly generalized. The verification boundary
has become the strategy boundary: unfamiliar but legal positions are not
evaluated approximately; they are handed back to the weakest part of the
policy.

## P0: fundamental gaps

### 1. The deck and policy disagree about non-ex Archaludon

Verified source facts:

- The deck contains two copies of non-ex Archaludon.
- `need_nonex_archaludon()` returns true only after Ogerpon has already been
  identified.
- `score_evolve()` assigns non-ex evolution `-1000` outside Ogerpon, apart
  from one narrow final-Prize special case.
- Search and discard preservation for non-ex Archaludon are also primarily
  Ogerpon-gated.
- Matchup detection uses the opponent's current Active and Bench, not an
  inferred deck identity.

Consequences inferable from the source:

- The two deck slots are dead or actively suppressed in most matchups.
- Before Ogerpon is publicly revealed, the agent can fail to preserve the card
  that is supposed to be its Ogerpon answer.
- Exact lethal, one-Prize trading, Basic-Pokémon immunity, attack continuity,
  and Active escape do not affect the base evolution score.
- `need_duraludon()` and `need_archaludon()` do not consistently treat a
  non-ex Archaludon as an existing completed attacker line.

Missing implementation:

- A general non-ex role evaluator based on damage, Prize value, prevention,
  expected survival, attack continuity, and backup readiness.
- A deck-policy contract that explains why every included card is searched,
  preserved, played, or deliberately treated as a matchup-only dead card.

### 2. There is no general damage/effect engine in the parent policy

Verified source facts:

- `best_attack_damage()` recognizes Raging Hammer dynamically and otherwise
  reads only a small fixed base-damage table.
- `effective_damage()` applies Metal Weakness only. It does not apply
  Resistance, Full Metal Lab, tools, abilities, status, prior attack effects,
  damage counters, or attack-text modifiers.
- `opp_max_damage()` returns one constant per coarse matchup, except for a
  hand-count estimate for Alakazam.
- `opp_max_damage()` is never called anywhere else in the submitted source, so
  even that coarse opponent-damage estimate is not part of the final decision
  path.
- Attack selection in the parent uses damage amount as the score; attack
  effects are not part of the general score.
- Exact overlay calculators implement some Weakness, Resistance, Full Metal
  Lab, Metal Defender, or Coated Attack behavior, but only for whitelisted
  cards and exact text signatures.
- The separate calculators are internally inconsistent. In
  `_nacr_attack_damage()`, the Raging Hammer formula returns through a branch
  that never applies the later Weakness, Resistance, and stadium reduction.
  The Turbo Flare helper subtracts 20 for Resistance, while the other
  calculators subtract 30.

Missing implementation:

- One shared damage pipeline for both players:
  printed damage, variable attack formula, Weakness, Resistance, stadium,
  tools, abilities, attack effects, prevention, status, and damage-counter
  placement.
- A distinction between attack damage and effects that place damage counters.
- Damage ranges for coin/random attacks instead of rejecting the whole line.
- Current-turn and next-turn persistence for Metal Defender, Coated Attack,
  self-locks, immunity, and similar effects.
- Removal of rule-local damage formulas after the shared calculator becomes
  authoritative.

### 3. Opponent abilities are not modeled generally

Verified source facts:

- The historical parent does not enumerate the skills on the opponent's
  Pokémon when estimating damage or readiness.
- The most general-looking one-turn dominance component has an explicit
  whitelist of only eight opponent attack signatures.
- Its supported opponent skills are effectively limited to exact Run Away Draw
  and Psychic Draw forms; an unknown skill makes the card unsupported.
- Other certified components reject boards when skill text contains terms such
  as damage, attack, Weakness, Resistance, Prize, or attack cost unless that
  exact text is already supported.

Consequences inferable from the source:

- Damage-increasing abilities, damage reduction, attack-cost reduction,
  Energy acceleration, free retreat, switching, healing, spread damage,
  Bench protection, evolution acceleration, hand growth, and Prize modifiers
  are usually invisible to the parent and ineligible for the precise rules.
- The agent falls back exactly when opponent-card semantics matter most.

Missing implementation:

- A semantic ability/effect registry shared by every rule.
- Public ability activation limits and already-used markers.
- Ability contributions to current damage, reachable next-turn damage,
  switching, Energy, hand size, and board development.

### 4. There is no general opponent-turn readiness model

Verified source facts:

- `opp_max_damage()` does not inspect each visible attacker, its actual Energy,
  retreat cost, evolution path, or available manual attachment.
- The parent does not enumerate `Active -> retreat/switch -> attacker`,
  `Basic -> evolution -> attack`, or `one Energy short -> attach -> attack`.
- A few overlays compute a ready-successor envelope, but only for exact
  supported attacks, empty/supported tools, known stadiums, known skills, and
  exact Energy representations.
- Unknown effects return `None`, which suppresses the overlay rather than
  producing a conservative damage interval.

Missing implementation:

- A reachable-next-turn threat graph containing manual attachment, known
  acceleration, evolution, retreat/switch, gust, attack, and Prize yield.
- Separate `ready now`, `ready after one ordinary resource`, and
  `speculative/hidden resource` threat classes.
- Minimum and maximum public damage rather than one matchup constant.

### 5. The parent is a one-callback greedy scorer, not a turn planner

Verified source facts:

- `choose_options()` scores every current option independently and selects the
  numerically highest option.
- Multi-card selections also rank cards independently against the same
  pre-selection observation.
- The parent has no general representation of
  `search -> discard -> evolve -> ability -> attach -> Boss -> attack`.
- Only individually patched scenarios have transaction state.

Consequences inferable from the source:

- A locally high score can destroy a later attack or Prize route.
- Discard pairs, multiple Energy placements, search targets, and sequential
  setup actions are not evaluated as a bundle.
- A rule can repair the first action while handing subsequent callbacks back
  to unrelated parent scores.

Missing implementation:

- A small deterministic turn-plan layer that compares complete legal action
  bundles by their resulting public state.
- Transaction ownership for general search, evolution, acceleration, gust,
  attack, and recovery sequences rather than one transaction per replay-shaped
  exception.

### 6. Score magnitudes mix ordering and strategic value

Verified source facts:

- Most items default to `20000`.
- Explorer defaults to `16000`.
- A normal attack is scored approximately by its printed damage, commonly
  `30` to `220`.
- An ability in MAIN receives score `1`.
- Optional activation returns `100000` for YES and `-100000` for NO.
- Ending the turn scores `0`.

Consequences inferable from the source:

- The system primarily says "perform positive non-terminal actions before
  attacking"; it does not compare their effect on win probability.
- Search and draw items tend to be consumed before a safe attack unless a
  special negative exception exists.
- Abilities can be delayed behind attacks or accepted unconditionally,
  independent of their actual effect.
- Scores from different action classes are not commensurate.

Missing implementation:

- Separate legality/mandatory-action handling, hard tactical dominance, action
  sequencing, and soft strategic comparison.
- A score based on resulting state rather than arbitrary per-card constants.

### 7. Setup is hard-coded to create avoidable fragility

Verified source facts:

- The agent always chooses to go second.
- It always rejects setup Bench placement with
  `-10000, "never bench during setup"`.
- Cinderace is always the preferred setup Active.

Consequences inferable from the source:

- A Duraludon present in the opening hand is deliberately not used as a backup
  Bench Pokémon.
- The policy creates lone-Active states that later rules must repair with
  Ultra Ball or Turbo Flare.
- Setup does not depend on hand composition, matchup, mulligan information, or
  the availability of an attack recipient.

Missing implementation:

- A setup formation rule that retains Cinderace's opening plan while placing a
  safe Duraludon backup when legal and useful.

## P1: major strategic coverage gaps

### 8. Prize-clock reasoning is exception-based, not universal

The base policy can value a current KO and terminal Boss target, but it does not
compare:

- one-Prize versus two-Prize Active exposure;
- how many attacks each player needs to finish;
- whether taking a KO activates the opponent's better return attacker;
- whether declining a KO changes the opponent's promotion;
- whether a sacrifice creates a two-turn win;
- whether a same-Prize attack preserves a better next attacker.

The precise Prize rules require exact Prize counts and exact board shapes. One
integrated rule requires exactly two Prizes for both players, two full-health
Archaludon ex, exactly three Metal each, Full Metal Lab, no tools, and exact
Bench identities. This is a test fixture, not a general race evaluator.

### 9. Matchup detection is brittle

Verified source facts:

- Detection uses only current Active and Bench IDs.
- Great Tusk and Crustle are returned as the same `"crustle"` matchup.
- A hybrid board is assigned to the first matching branch.
- Unrecognized boards receive generic maximum damage `220`.
- Discard/public-history markers are largely not used by `detect_matchup()`.

Missing implementation:

- Independent board properties and threat tags instead of one exclusive
  archetype label.
- Persistent public archetype evidence from discarded, searched, revealed,
  and previously seen cards.
- Separate Great Tusk mill, Crustle immunity, Alakazam hand scaling,
  Basic-attacker, spread, gust, and evolution-engine features.

### 10. Opponent hidden-resource inference is almost absent

The source contains a small Alakazam hand-size ceiling and a probability model
for our own Duraludon access. It does not generally track:

- cards the opponent searched or revealed;
- known cards returned to hand;
- remaining copies inferred from public zones;
- likely evolution, gust, switch, Energy, or damage-modifier access;
- archetype-conditioned but non-certain hand ranges.

Missing implementation:

- A public known-hand ledger plus bounded possible-hand facts.
- Threat evaluation with `certain`, `available from known search`, and
  `plausible from hidden hand` tiers.

### 11. Search, draw, discard, and recovery lack shared resource accounting

Verified source facts:

- `safe_discard_count()` recognizes mainly early Metal, Cinderace, and surplus
  draw supporters.
- Generic discard gives positive utility to Boss, Full Metal Lab, and Pokégear.
- The last-Boss ledger protects a very specific Ultra Ball discard shape, not
  all irreversible resource spends.
- Explorer and search callbacks score cards independently.
- Ultra Ball can receive its full `20000` "fuel Alloy" score from Metal
  availability without first establishing that the other required discard is
  strategically expendable.
- Night Stretcher can be approved because Metal recovery is urgent, but its
  later TO_HAND callback ranks Duraludon above Metal. The use decision and the
  recovery-target decision therefore need not pursue the same plan.
- The parent does not maintain a general count of remaining attackers,
  evolutions, Energy, Boss, recovery, healing, stadiums, or tools.

Missing implementation:

- A public resource ledger with role-specific minimum reserves.
- Search/discard/recovery plans evaluated against the complete remaining attack
  line and Prize route.
- Prize-card uncertainty and visible-copy accounting for every essential role.

### 12. Bench formation and backup readiness are incomplete

Verified source facts:

- Playing Duraludon receives a fixed positive score.
- `need_duraludon()` uses coarse matchup-specific target counts.
- It does not consistently count non-ex Archaludon as an existing line.
- No base score prices Bench liabilities, gust targets, spread damage, or
  whether a Bench Pokémon can become an attacker next turn.

Missing implementation:

- Desired board shapes by phase: setup, first attacker, second attacker, and
  endgame.
- Backup readiness measured by actions/Energy required, not card identity
  alone.
- Bench-risk accounting for gust, spread, and easy Prize targets.

### 13. Retreat, promotion, and sacrifice logic are too static

Verified source facts:

- Retreat is usually `-100`; it becomes positive mainly when an existing
  Archaludon attack route is already ready.
- Promotion priorities are static:
  Cinderace > non-ex Archaludon > Archaludon ex > Duraludon.
- Current HP, opposing damage, Prize clock, attack readiness, status escape,
  retreat cost, and the desired sacrifice are not jointly compared.

Missing implementation:

- A promotion/retreat evaluator based on survival, Prize liability, next
  attack, free-retreat/switch access, and deliberate sacrifice value.

### 14. Healing and tools use coarse thresholds

Verified source facts:

- Jumbo Ice Cream uses matchup HP thresholds and a special Alakazam estimate.
- Hero's Cape has static target scores, with one narrow certified survival
  overlay.
- Exact future damage, attack continuity, Raging Hammer damage loss, tool
  replacement, and opponent removal effects are not handled generally.

Missing implementation:

- Healing/tool decisions based on crossing a verified survival threshold,
  preserving lethal damage, and changing the number of attacks or Prizes
  needed.

### 15. Damage-counter and Bench-damage targeting is not strategic

`SelectContext.DAMAGE` simply prefers the target with the lowest current HP.
It does not optimize KO thresholds, future spread, evolution denial, Prize
value, retreat/promotion consequences, or whether damage will be erased by
return-to-hand effects.

### 16. Status conditions and persistent effects are mostly exclusion gates

The base policy does not plan around Sleep, Paralysis, Confusion, Poison, or
Burn. Certified rules commonly require all statuses to be false. Status does
not feed a general switch/retreat/attack-validity plan.

## P2: architecture and maintenance gaps

### 17. Fixed rule precedence can select the wrong valid rule

Seventeen rules are assigned immutable ranks 3 through 19. When multiple rules
are eligible, the lowest numeric rank wins; their resulting states are not
compared. Unknown/equal collisions fail closed to the historical parent. An
active transaction also suppresses later newly eligible rules.

Missing implementation:

- Compare compatible proposed plans by tactical dominance and resulting state.
- Reserve fixed precedence only for true terminal/legality constraints.

### 18. Many repairs are gated on the parent's exact bad action

Verified source facts:

- The Turbo repair starts only when the parent chose RETREAT or END.
- The immunity-aware non-ex repair starts only when the parent chose END.
- The general rotation repair starts only when the parent chose ATTACK.
- The sacrificial-Active evolution repair starts only when the parent chose
  Active ex evolution.
- The one-turn target-dominance rule starts only when the parent chose one of
  its registered attacks.
- PAN starts only when the parent chose Raging Hammer.
- NMR starts only when the parent chose one unique Boss.

Consequences inferable from the source:

- A board can satisfy the strategic principle but never be examined because
  the greedy parent happened to choose a different bad action.
- The parent is acting as both fallback and activation oracle, even though the
  overlays exist specifically because the parent is incomplete.

Missing implementation:

- Generate candidate plans from board properties first, then compare them with
  the parent plan. Parent action identity should be a regression reference, not
  a semantic precondition.

### 19. Certificates are overfitted to exact examples

Examples visible in source:

- The post-attachment non-ex rule hard-codes target card `743`, its Basic
  ancestor, exact HP `110/140`, an exact Energy representation, exact tool and
  stadium shapes, and a same-turn attachment witness.
- The equal-two-Prize rule hard-codes exact Prize counts, exact attackers,
  exact Energy, full HP, empty tools, stadium, and exact Bench composition.
- The one-turn dominance rule supports six exact opponent card signatures and
  eight exact attack signatures.

These checks are useful for regression fixtures, but they should not define the
production rule's semantic boundary.

Missing implementation:

- Property-based certificates such as
  `one-Prize attacker + payable 120 + exact KO + better Prize route`, with
  identity-specific exceptions only where card text actually requires them.

### 20. Fail-closed safety returns to a strategically weak parent

Fail-closed behavior is correct for legality and unknown engine state. It is
not sufficient for strategy. At present, unsupported abilities, tools, attack
texts, Energy representations, status, stadiums, and board shapes generally
disable the improved rule and restore the historical scalar choice.

Missing implementation:

- A layered fallback:
  exact semantics -> conservative interval semantics -> generic public-state
  planner -> only then historical parent.

### 21. Stale deck logic and other deck-policy mismatches remain

The deck contains zero Relicanth, but the historical parent still has
Relicanth setup, play, search, discard, Boss, and Raging Hammer planning
branches. The source comment says Relicanth was cut, so these branches are
unreachable under the current deck and make maintenance/auditing harder.

Additional verified mismatches:

- Full Metal Lab's base play rule recognizes Duraludon and Archaludon ex as
  Metal targets but omits non-ex Archaludon. It also does not evaluate that the
  stadium reduces damage to the opponent's Metal Pokémon too.
- Jumbo Ice Cream is always rejected on non-ex Archaludon, regardless of
  whether healing it crosses a survival threshold.
- The base Hero's Cape target rule evaluates Archaludon ex and Duraludon but
  not non-ex Archaludon.
- Poké Pad can search Rule-Box-free Pokémon, yet the non-ex demand function is
  disabled outside already-identified Ogerpon.

### 22. Latent nondeterministic fallback remains

An older `_cum_exact_parent_agent()` contains `random.sample()` on exception.
The final submitted `agent()` currently uses a deterministic emergency path,
so this is not evidence of live nondeterminism. It is nevertheless dead,
dangerous fallback code that could become reachable during refactoring.

## What is missing as a coherent whole

The source needs four shared layers rather than more exact replay-shaped rules:

1. **Card semantics layer**  
   Damage, damage counters, abilities, attack effects, tools, stadiums,
   status, Energy payment, retreat, Prize value, and effect duration.

2. **Reachability layer**  
   Our and opponent current attackers, one-resource attackers, evolution
   attackers, switch/gust routes, and bounded hidden-hand threats.

3. **Turn-plan layer**  
   Deterministic legal sequences through search, discard, bench, evolve,
   ability, attach, gust, heal, retreat, and attack.

4. **Decision layer**  
   Hard rules for legality and forced terminal dominance; then comparison of
   Prize race, survival, attack continuity, resource reserves, and comeback
   probability. Scalar tie-breaking should occur only among plans that survive
   those checks.

Until these layers exist, adding more narrow certified rules will continue to
produce safe but rare activations while leaving most decisions to the same
incomplete parent score.
