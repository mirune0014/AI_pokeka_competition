# Task 8 root-verified evidence

## Frozen parent

- Candidate: `archaludon_public_complete_supporter_purpose_arbitration_t7_v1`
- Parent `main.py` SHA-256:
  `8364A91B1DAF48968D9D5C3BBA257D43546E27AB7076841A5400124048602E28`
- Deck SHA-256:
  `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`
- Task 8 must be an isolated child of this exact parent.

## Exact card effect and current gap

Lillie's Determination (`1227`) shuffles the hand into the deck and draws six
cards, or eight cards when exactly six Prize cards remain. The played Lillie is
discarded. Therefore:

- `draw_n = 8 if own_prizes == 6 else 6`;
- `shuffle_count = hand_count - 1`;
- `post_hand_count = draw_n`;
- `post_deck_count = deck_count + shuffle_count - draw_n`;
- every other physical hand serial becomes `DECK_UNKNOWN`;
- no shuffled identity may be assumed to be redrawn.

The inherited generic scorer normally gives Lillie a fixed positive score and
contains narrow matchup exceptions. A score cannot distinguish guaranteed
renewal from shuffling away the only evolution, Boss, manual Energy, recovery,
search, or next-attacker route.

## Earlier census and its correct interpretation

The frozen earlier pre-edit census is preserved at:

- `strategy/archaludon_human_fundamentals_planner_20260731/next_after_fml_no_actionable_boundary_20260801/ROOT_PRE_EDIT_LILLIE_VERIFICATION.md`;
- `.../LILLIE_NUMERICAL_AUDIT_SOL_ULTRA.md`;
- `.../STRATEGY_SELECTION_LILLIE_V1.md`.

Root verified 207 manifest replays, 25,880 callbacks and 256 historical Lillie
PLAY turns. The old detector found 346 deduplicated PLAY directions but zero
HOLD directions, so that old narrow hypothesis was correctly stopped before
implementation. This does not prove that holding Lillie is never correct. It
proves that the old protected-route detector failed to identify a natural HOLD
boundary. The user has since explicitly requested a practical human-player
implementation and permits live diagnosis after destructive errors are ruled
out.

## Human-player boundary required for Task 8

Task 8 must compare complete public routes, not card identity or hand size
alone.

1. Never displace Task 7 terminal Boss, current exact terminal attack, or a
   live Task 4–7 transaction.
2. Before Lillie, materialize a safe, immediately executable physical route
   when it can be completed without consuming the Supporter right:
   - a Basic that prevents a zero-Bench loss or is the exact next attacker;
   - a legal evolution that completes the current/next attacker;
   - the one manual Metal that completes a payable current/next attack;
   - an already-certified Pad/Ultra Ball/Night Stretcher/Tool/Stadium route.
3. If a unique required physical card cannot be materialized this turn but is
   bound to a complete next-turn attack, evolution, recovery, Boss or backup
   route, hold Lillie. Do not assume it will be redrawn.
4. Play Lillie when no higher public route is displaced and its exact count
   transform gives guaranteed hand renewal, exact deckout-margin improvement,
   or an already-supported public hand-size survival benefit.
5. Do not hold every Energy or Pokémon merely by identity. A card is protected
   only by an explicit physical route/minimum-count certificate.
6. Direct Lillie and Pokégear-to-Lillie must use the Task 7 route schema and a
   single owner. Task 7 terminal Boss remains higher priority at Gear reveal.
7. Explorer comparison may preserve an already-certified Explorer transaction,
   but Task 8 must not predict Explorer's hidden top-six identities.
8. Task 9 remains responsible for nonterminal harmful-KO, general Boss target,
   and comeback-mode valuation.

## Practical safety gate

- exact parent/deck hashes; only candidate `main.py` differs;
- compile/import/final callable, legal 60 cards, ACE SPEC 1, cache-free;
- both seats and option/duplicate permutations;
- six-Prize draw-8 and other-Prize draw-6 count transforms;
- PLAY, MATERIALIZE-THEN-PLAY, HOLD, and parent-identical controls;
- protected terminal Boss, exact evolution, one-Metal attack completion,
  zero-Bench Basic, recovery/search route, and ready backup;
- expendable duplicate copies are not protected above route minima;
- hidden drawn-card identities never affect the action or certificate;
- Gear reveal containing every Boss/Explorer/Lillie subset preserves Task 7
  terminal Boss priority and selects Lillie only for a predeclared complete
  renewal purpose;
- current plus historical shadow with every first difference classified;
- extracted both-seat smoke with zero action errors, no max-step hit, no stale
  owner, and transaction conservation.

This gate checks destructive correctness and determinism. It does not require a
positive local win-rate before practical use.
