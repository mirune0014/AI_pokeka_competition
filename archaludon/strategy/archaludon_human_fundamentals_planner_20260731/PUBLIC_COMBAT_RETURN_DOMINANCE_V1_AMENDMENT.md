# Controlling amendment: Run Away Draw exact effect

## Authority

This amendment corrects one descriptive phrase in
`V2_FINAL_JUDGMENT_AND_NEXT_HYPOTHESIS.md`
(SHA-256
`3197091ED365BCEB962674BA40591CA303B7B79B6CC050D6A150D9F637E0AE64`).
All other parts of that implementation contract remain controlling.

## Root-verified metadata

Card ID `66`, Dudunsparce, has:

- Ability name: `Run Away Draw`
- Exact text:
  `Once during your turn, you may draw 3 cards. If you drew any cards in this
  way, shuffle this Pokémon and all attached cards into your deck.`

It does not return to the hand and does not perform a healing action.

## Required implementation

- Treat Run Away Draw as an exact public leave-play/shuffle transition.
- Non-KO chip damage is not persistent progress when the visible activation
  remains executable, because the damaged Dudunsparce and all attached cards
  leave play and are shuffled into the deck.
- Do not model the transition as return to hand, healing, retreat, switch, or
  discard.
- The activation must still satisfy its exact once-per-turn, draw, callback,
  board-survival, and engine-transition conditions.
- If the public observation cannot prove the exact activation or transition,
  mark the route `UNKNOWN` and preserve exact V2.

The contract's general requirement remains unchanged: normalized engine/card
metadata is authoritative, and unsupported or contradictory text cannot be
treated as zero or benign.
