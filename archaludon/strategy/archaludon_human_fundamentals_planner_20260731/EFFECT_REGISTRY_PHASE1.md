# Public effect registry phase 1

This is the first deterministic coverage batch after the PCRD selector is
repaired. It is a future implementation specification, not part of PCRD v2.

## Exact in-play effects

- **Memory Dive**: enumerate attacks from each visible `preEvolution` card on
  the evolved source; retain printed Energy cost and attack text.
- **Flower Curtain**: prevent attack damage to Benched non-Rule-Box Pokémon.
- **Adrena-Brain**: when Munkidori has Darkness Energy, expose a once-per-turn
  route moving 0–3 counters from one damaged ally to one opponent Pokémon.
- **Shadow Bullet**: 180 Active plus 30 to a legal Bench target.
- **Spiky Wheel**: `20 + 40 × attached Darkness Energy`.
- **Rock Fighting / Mist Energy**: prevent effects of attacks, not damage.
- **Premium Power Pro**: +30 to Fighting attack before Weakness/Resistance for
  the current turn only.
- **Mega Brave / Accelerating Stab**: exclude the locked attack on the user's
  immediately following turn; identify the prior attack from public logs.
- **Spiky Energy**: after attack damage to the attached Active, place two
  counters on the attacker even if the target is KO'd.
- **Grow Grass Energy / Cynthia's Power Weight**: include +20 / +70 maximum HP
  and current HP boundary.
- **Mysterious Rock Inn**: prevent damage from Pokémon ex to Crustle.
- **Superb Scissors**: ignore effects on the opponent's Active when calculating
  its damage.
- **Cheer On to Glory**: +30 to attacks by each Cynthia's Pokémon for each
  applicable public modifier, before Weakness/Resistance.
- **Draconic Buster**: 260 then remove all attached Energy from the source.
- **Raging Curse**: `10 × total damage counters on visible Benched Cynthia's
  Pokémon`, ignoring Weakness.
- **Battle Cage**: prevent placement of damage counters on either player's
  Bench by opponent attack/Ability effects.
- **Full Metal Lab**: after Weakness/Resistance, reduce attack damage to each
  Metal target by 30 for both players.

## Exact public readiness effects

- **Punk Up / Assemble Alloy**: after the evolution callback resolves, use the
  visible attached Energy; do not assume a hidden evolution from hand.
- **Run Away Draw / Trading Places / Teleportation Attack / Switch / Surfer**:
  enumerate legal Active changes and the resulting attacker, not just the
  current Active.
- **Aura Jab / Turbo Flare**: apply visible acceleration only after the attack;
  use it when evaluating the following turn, not the current attack.
- **Ascension / Rare Candy / Forest of Vitality**: enumerate only legally
  accessible evolution routes under the current turn and appear-this-turn
  rules.
- **Wally's Compassion / Jumbo Ice Cream**: exact heal only when the card and
  legal target are publicly available to the acting player; otherwise it is a
  hidden access route, not certain.

## Variable effects

- **Rapid-Fire Combo**: keep minimum `200`, unbounded-by-rule-but-deck-engine
  bounded maximum, and probability mass by heads count. Never replace it with a
  single exact damage.
- hidden Supporter, search, or Energy access: represent as a required-card set
  and remaining-copy class. Do not assume it exists and do not imitate a replay
  policy.

## Phase-1 acceptance

- one positive and one boundary negative per effect;
- symmetric self/opponent combat calculation where applicable;
- exact callback or log evidence for turn-limited effects;
- no unsupported effect silently treated as zero;
- both-seat deterministic execution;
- all naturally changed positions inspected.
