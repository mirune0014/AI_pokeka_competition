# Strategy selection: Alakazam protected Great Tusk Kadabra lane v2

- Selection time: 2026-07-16 23:24 +09:00
- Parent: exact public Best-5 Alakazam
- Deck change: none
- Implementation target: `alakazam_protected_great_tusk_kadabra_lane_v2`
- Kaggle action: none at selection time

## Predecessor disposition

`alakazam_visible_mill_clock_minimum_draw_v1` is rejected and is not this
candidate's parent. Its corrected Phase-0 trace gate qualified only `3/8`
keys versus the frozen `4/8` minimum, removed two parent same-turn knockouts,
and regressed one loss from five prizes taken to two. No Phase-1 command was
run. The rejection record is
`decisions/20260716_2316_alakazam_visible_mill_clock_minimum_draw_v1_reject.md`,
SHA256 `3E01D0548722B43020181A2F07D6542B134911B7BADF9D33B2414654099CA736`.

## Selected single hypothesis

When the opponent's Active is Great Tusk `58` with public Mist Energy `11` or
Rock Fighting Energy `20`, Powerful Hand `1072` can be prevented because it
places damage counters as an attack effect. Super Psy Bolt `1071` is ordinary
damage and hits Great Tusk's Psychic weakness for 60. If no public same-turn
knockout route outranks it, reserve one Kadabra as a persistent direct-damage
bypass attacker until the protected target leaves or loses its protection.

This is a public card-interaction rule. It is not a learned opponent policy,
replay imitation, or a continuation of the rejected deck-clock behavior.

## Root-verified mechanism

The checked engine card data states:

- Great Tusk `58`: Psychic weakness;
- Mist Energy `11` and Rock Fighting Energy `20`: prevent effects of attacks;
- Powerful Hand `1072`: base damage zero and places two damage counters for
  each card in hand;
- Super Psy Bolt `1071`: 30 ordinary Psychic damage.

In corrected fixed traces, parent Alakazam attacks into protected Great Tusk
recorded `HP_CHANGE 0`, while Kadabra recorded `-60`. At
`p1/2026071501`, Kadabra took the protected knockout and the paired candidate
eventually won; the parent evolved to Alakazam, dealt zero, and decked out.
Conversely, the rejected broad rule delayed parent same-turn knockouts at
`p0/2026071501` and the unprotected Crustle at `p1/2026071552`. Those failures
define hard exclusions for this narrower hypothesis.

## Read-only Sol-Ultra selection

The strategy judge selected `protected_great_tusk_kadabra_lane_v2` with this
priority order:

1. certified win now;
2. certified unprotected same-turn Alakazam knockout, including a legal Boss
   target;
3. remove every protecting Energy with Enhanced Hammer and take a certified
   same-turn Alakazam knockout;
4. protected-target Kadabra lane;
5. exact parent order.

The exact executable contract is frozen separately under
`implementation/alakazam_protected_great_tusk_kadabra_lane_v2` before source
implementation. Selection authorizes implementation and local evaluation only;
it does not authorize packaging or submission.

