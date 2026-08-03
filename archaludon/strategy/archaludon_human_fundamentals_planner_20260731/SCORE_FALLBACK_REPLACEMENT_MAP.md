# Inherited score fallback replacement map

This maps reachable single-action scores in the preserved Silver-derived
fallback to their required human-condition replacements.

| inherited behavior | defect | replacement owner |
|---|---|---|
| playable Pokémon `18000` | benches without proving role or Bench capacity value | complete setup/backup plan |
| Full Metal Lab `20000` when our Active is Metal | ignores that the Stadium also protects opposing Metal | symmetric combat/return plan |
| generic item `20000` | “usable” is mistaken for “useful now” | card-purpose transaction |
| Ultra Ball skip `-1000` | search target and both discard costs are separated | complete Ultra Ball transaction |
| Explorer `16000` | does not bind take-two/discard-four to Alloy and attack | complete turn sequence |
| Lillie `5000` | can shuffle away a complete attack/Boss line | pre/post-hand plan comparison |
| Boss target fixed scores | immediate HP/Prize can hide retreat, switch, threat, and final-Prize timing | target-specific Prize/return plan |
| non-ex Archaludon `-1000` | suppresses valid KO, Basic prevention, and one-Prize-wall lines | ex/non-ex/un-evolved combat plans |
| ex evolution scores from discard Metal count | may evolve a doomed Active or fail to make a payable attack | evolution-to-attack transaction |
| attachment fixed scores | can overattach Active and starve backup | attack-cost and next-attacker allocation |
| Cape ex `11000`, Duraludon `8000` | card identity replaces actual KO-boundary change | post-Cape return calculation |
| retreat default negative | can preserve a dying Active at the expense of a ready attacker | retreat/switch attack-continuity plan |
| generic Ability `1` | does not understand cost, once-per-turn state, or board effect | effect registry |
| attack score equals raw damage | ignores KO, Prize, prevention, target return, and harmful chip | combat/Prize hierarchy |
| generic YES over NO | accepts optional effects without checking harm | effect-specific callback transaction |
| number equals selected number | always maximizes count even when overattachment/discard/deckout is harmful | effect-specific bounded allocation |
| generic take/discard/target values | callback choices can contradict why the card was played | saved transaction and rollback |
| negative-score filtering in multi-select | can choose locally cheap cards that destroy the complete plan | constrained combination selection |

## Replacement rule

No fixed score is removed by changing it to a different constant.
It is removed only when the final callable agent owns the callback with:

1. an exact card/effect classification;
2. a complete legal purpose;
3. a saved multi-callback transaction when needed;
4. action-after-effect and return-after-action evaluation;
5. an explicit negative condition;
6. deterministic fallback to the preserved parent when unknown.

The inherited score remains reachable only for states not yet owned by a
completed replacement layer. TODO completion must state which score branches
are no longer reachable, not merely that a newer helper exists.
