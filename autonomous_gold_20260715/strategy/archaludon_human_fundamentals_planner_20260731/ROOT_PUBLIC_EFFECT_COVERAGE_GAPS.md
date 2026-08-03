# Root audit: public effect coverage gaps

## 2026-07-31 phase-1 update

The original audit below is the pre-implementation gap list.
It must not be read as the current status.

`archaludon_deterministic_public_effect_registry_phase1_v1` now has
34 exact semantic effects and 37 ID / entry / text-hash bindings.

The final decision path directly consumes 20 combat/return semantics,
retains two checked legacy action transactions, observes nine callback effects,
and records three route-semantics effects whose final target callback is still
parent-owned.

Newly covered from the original high-priority list include:

- Memory Dive;
- Flower Curtain;
- Adrena-Brain, including Active/Bench targets and Battle Cage prevention;
- Shadow Bullet route semantics with one chosen Bench target;
- Spiky Wheel;
- Rock Fighting Energy and Mist Energy;
- Premium Power Pro stacking by distinct current-turn serial;
- Mega Brave and Accelerating Stab next-turn locks;
- Spiky Energy post-return projection;
- Grow Grass Energy and Cynthia's Power Weight;
- Mysterious Rock Inn and Superb Scissors;
- Cheer On to Glory, Draconic Buster, and Raging Curse;
- Punk Up and Aura Jab callback observation;
- Run Away Draw;
- Trading Places and Teleportation Attack route semantics;
- Switch and Surfer public-current previews;
- Rare Candy, Ascension, and Forest of Vitality public-current previews;
- Wally's Compassion and Jumbo Ice Cream public-current previews.

The current high-priority gaps are narrower:

- Repelling Veil;
- Rapid-Fire Combo's variable coin-flip range;
- Telepath Psychic Energy and Enriching Energy;
- Enhanced Hammer;
- Buddy-Buddy Poffin;
- Sacred Ash and Lana's Aid;
- Hilda, Dawn, Champion's Call, and Spikemuth Gym;
- Lunar Cycle and Run Errand;
- Fighting Gong, Energy Search, and Dusk Ball;
- final callback ownership for Shadow Bullet, Trading Places,
  and Teleportation Attack;
- action ownership, rather than observation only, for Punk Up, Aura Jab,
  Switch, Surfer, Rare Candy, Ascension, Forest of Vitality,
  Wally's Compassion, and Jumbo Ice Cream.

An observer is not a completed human action rule.
The TODO keeps these items partial until the final `agent` owns the legal action
and its continuation.

This is a direct comparison of the fixed760 anti-overfitting population's deck
lists and card metadata against `PUBLIC_COMBAT_RETURN_DOMINANCE_V1`.

The current child intentionally fails closed when a relevant public effect is
unsupported. This is safe, but it means “the agent considered the Ability” is
not yet true for most of the population. It often returns to the inherited
score policy instead.

## Supported now

- our Assemble Alloy and setup-only Explosiveness;
- Sturdy;
- Run Away Draw;
- resolved Psychic Draw evolution triggers;
- Full Metal Lab, Hero's Cape, Jumbo Ice Cream;
- our five attacks: Hammer In, Raging Hammer, Metal Defender, Coated Attack,
  Turbo Flare;
- current-time Powerful Hand;
- Weakness, Resistance, Prize value, payable retreat, one ordinary attachment.

## High-priority unsupported public effects

### Damage and KO boundary

- Memory Dive: evolved Pokémon may use previous-Evolution attacks.
- Repelling Veil: effects protection for Basic Team Rocket's Pokémon.
- Flower Curtain: Bench damage prevention for non-Rule-Box Pokémon.
- Adrena-Brain: moves up to three damage counters.
- Punk Up: evolution-time five-Energy acceleration.
- Shadow Bullet: Active damage plus 30 Bench damage.
- Spiky Wheel: damage scales with attached Darkness Energy.
- Rock Fighting Energy / Mist Energy: attack-effect prevention.
- Premium Power Pro: +30 damage for Fighting attacks this turn.
- Aura Jab: damage plus three-Energy acceleration.
- Mega Brave / Accelerating Stab: cannot-use-again next-turn locks.
- Wally's Compassion: full heal plus Energy return.
- Spiky Energy: two damage counters returned to the attacker.
- Grow Grass Energy and Cynthia's Power Weight: maximum-HP modifiers.
- Mysterious Rock Inn: damage prevention from Pokémon ex.
- Superb Scissors: ignores effects on the target.
- Rapid-Fire Combo: coin-flip variable damage.
- Cheer On to Glory: +30 damage for Cynthia's Pokémon.
- Draconic Buster: 260 and discard-all-Energy.
- Raging Curse: damage from all Benched Cynthia damage counters.
- Battle Cage: prevents Bench damage-counter placement.

### Readiness, switching, healing, and access

- Telepath Psychic Energy: attachment plus two Basic Psychic Pokémon to Bench.
- Enriching Energy: attachment plus draw four.
- Trading Places and Teleportation Attack: self-switch.
- Rare Candy: Basic-to-Stage-2 evolution.
- Enhanced Hammer: Special Energy removal.
- Buddy-Buddy Poffin: two low-HP Basics directly to Bench.
- Sacred Ash / Lana's Aid: recovery.
- Hilda / Dawn / Champion's Call / Spikemuth Gym: deterministic search access.
- Lunar Cycle / Run Errand: public draw engines.
- Switch / Surfer: switching access.
- Fighting Gong / Energy Search / Dusk Ball: exact search access.
- Ascension: attack-based immediate evolution.
- Forest of Vitality: same-turn Grass evolution.

## Consequence

The present fail-closed behavior prevents false “certain KO/survival” claims,
but it does not satisfy the user's requirement to play like a strong human
against visible Abilities and card effects.

The repair order should be:

1. exact deterministic damage, HP, protection, and attack-lock effects;
2. exact public acceleration, evolution, switch, heal, and recovery routes;
3. variable/coin-flip outcomes represented as bounded ranges, not a fake exact
   scalar;
4. hidden draw/search represented by known access classes and remaining-card
   counts, not opponent-policy imitation.

Each effect needs a positive and a negative fixture. An effect is not complete
merely because its name is whitelisted; it is complete only when it changes the
same combat/return fields a human uses and the final agent returns the expected
legal action.
