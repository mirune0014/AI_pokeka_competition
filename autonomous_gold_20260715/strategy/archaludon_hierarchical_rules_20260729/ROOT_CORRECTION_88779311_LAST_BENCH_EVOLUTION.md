# Root correction — episode 88779311 last-Bench evolution

Decision:
`REJECT_SELECTION_SOURCE__PRESERVE_AS_NEGATIVE_CONTROL`

This correction supersedes the selection claim in
`DEFERRED_LOSS_MEMO_88779311_LAST_BENCH_EVOLUTION.md`. It does not alter the
verified replay path or H6 parent identity.

## Decision-time information boundary

At target decision row 140:

- the opponent's public hand count was three and deck count was 23;
- the target could not see opponent hand identities;
- Night Stretcher `1097#101` was not in the opponent's actual three-card hand.

At the next opponent turn:

- deck count changed `23 -> 22`;
- hand count changed `3 -> 4`;
- the new four-card hand included Night Stretcher `1097#101`.

Night Stretcher was therefore the next-turn draw, not a card publicly known or
deterministically accessible at row 140. A rule using it at row 140 would leak
future hidden information.

## Complete damage package

The legal non-ex Archaludon evolution would retain Hero's Cape and 220 damage:

- projected maximum HP: `180 + 100 = 280`;
- projected current HP: `280 - 220 = 60`.

Even granting the hidden future Stretcher route:

- Adrena-Brain places 30 damage on the sole Bench;
- Shadow Bullet simultaneously places another 30 damage on that Bench while
  KOing the Active;
- projected Bench HP is `60 - 30 - 30 = 0`.

The evolution therefore does not prevent board-out.

## Consequence

No last-Bench evolution implementation is selected from this replay. It is a
mandatory negative requiring:

1. all recovery, attachment, Ability, and attack enablers used by the threat
   certificate to be public at the decision callback; and
2. projected post-evolution HP to be strictly greater than the complete
   public counter-movement plus Bench-damage package.

For this exact package, projected HP must be strictly greater than 60.
