# Purpose-bound Lillie hand/deck non-displacement v1

## Decision

Full Metal Lab v1 is stopped before implementation as
`FALSIFIED_PRE_EDIT__NO_ACTIONABLE_BOUNDARY__RARE_NARROW`.

The next single hypothesis is
`PURPOSE_BOUND_LILLIE_HAND_DECK_NONDISPLACEMENT_V1`, directly from the exact
historical-Silver Archaludon parent.

## Hypothesis

Treat Lillie's Determination as an exact hand/deck-count exchange, not as a
generic draw bonus.  Play it only when the exact count transformation gives
guaranteed hand renewal or deckout-margin improvement without displacing a
higher-ranked current attack, Prize route, supporter purpose, attachment,
evolution, recovery route, or ready backup.  Hold it when a unique required
physical card would move from `HAND_READY` to `DECK_UNKNOWN`.

Never predict the identities of cards drawn by Lillie.

## Exact effect

- `draw_n = 8` exactly when six Prize cards remain; otherwise `6`.
- The played Lillie is discarded.
- `shuffle_count = hand_count - 1`.
- Require `deck_count + shuffle_count >= draw_n`.
- `post_hand_count = draw_n`.
- `post_deck_count = deck_count + shuffle_count - draw_n`.
- Every shuffled physical serial becomes `DECK_UNKNOWN`; none is assumed to be
  redrawn.

## Hard hierarchy

1. Legality, exact metadata, live-owner precedence, and actual engine options.
2. Exact win now.
3. Exact terminal-loss avoidance.
4. Current payable attack, KO, and Prize.
5. Current-attacker survival, next attacker, and backup readiness.
6. Unique Boss/Explorer purpose, attachment, evolution, recovery, and other
   public-purpose resources, including the Supporter right.
7. Exact hand-count gain and deckout horizon.

A lower layer may never compensate for a loss at an earlier layer.

## Census directions

- `PLAY_LILLIE`: exact `HAND_RENEWAL` or `DECKOUT_MARGIN`, no protected route
  or serial displaced, and a unique Lillie first role is emittable.
- `HOLD_LILLIE`: the parent selected Lillie, but it would destroy an exact
  higher-ranked route whose full semantic queue and unique first action are
  known.
- `APPROVE_PARENT_LILLIE`: an exact Lillie purpose exists but the action is
  parent-identical.
- `EQUAL`: no strict public improvement.
- `REJECT`: hidden-draw benefit, unsupported relevant hand-size effect,
  unknown resource purpose, owner collision, stale role, or incomplete
  alternative.

Historical Lillie actions are coverage evidence, not action labels.

## Frozen inputs

- Parent `main.py` SHA-256:
  `558EE5DB29E001428B0D59813613FABEE8E15B96E422746C104BDFAB4DC22DB6`
- Deck SHA-256:
  `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`
- Source manifest SHA-256:
  `90A512D5C9AE5EAD8DF92F370C32716959EC0929F9465451E7BB0926DBEB5A68`

The census runner and output hashes are frozen only after execution; they must
not be invented beforehand.

## Strict implement/stop gate

Integrity:

- 207 manifest entries and 209 target seats;
- exactly 25,880 parent calls, once per callback;
- zero invalid parent actions and manifest mismatches;
- exactly 256 historical Lillie PLAY turns, both seats;
- unique row keys and exact admitted Lillie metadata.

Actionability:

- at least 40 strict-purpose-classified unique turns, both seats, at least 20
  replays;
- at least 20 uniquely emittable actionable turns, both seats, at least 10
  replays;
- at least 12 predicted first differences, both seats, at least 8 replays;
- at least three `PLAY_LILLIE` and three `HOLD_LILLIE`, each direction present
  in both seats;
- HOLD covers at least two distinct protected roles among current attack,
  Boss, attachment/evolution, recovery, and ready backup;
- every predicted difference is root-audited `GOOD_CAUSAL`;
- zero hidden-draw-as-benefit, unknown-as-zero, owner-overlap, stale-role, or
  unemittable-alternative rows among actionable evidence.

Passing every gate authorizes one isolated implementation.  Failing any gate
stops this hypothesis as `RARE_NARROW/NO_ACTIONABLE_BOUNDARY`; thresholds may
not be relaxed after observing the result.
