# Future loss memo — low-HP Active to fresh backup attack pivot

Status: deferred; do not mix into the active search-aware or cumulative build.

## Evidence

- Live submission:
  `55083165`
- Episode:
  `88835861`
- Correct seat:
  `1`
- Replay SHA-256:
  `EFE4DF5C07C84897871E75BBD35089A421BB5A408FE3D03299E8D2821ECF966E`
- Bounded analysis:
  `autonomous_gold_20260715/live/55083165/refresh_20260730_0211/ANALYSIS_88835861.md`
- Analysis SHA-256:
  `7BCDBFA7B38B6164990EC84B09B2DEC5AC70E32D6CC86833AEB35CC78E46A81F`
- Exact callback audit:
  `62` callbacks including deck request and one valid empty selection;
  `0` Hero-parent semantic differences, `0` invalid actions, `0` exceptions,
  `0` duplicate instability, and `0` Hero starts.

The loss is inherited from exact Historical-Silver. It is not attributable to
Hero's Cape or to the active search-aware terminal rule.

## Public-state hypothesis

At replay step 85, the damaged Active Archaludon ex had 110 HP and three
Metal. A Benched Duraludon had two Metal, Archaludon ex was in hand, one
Basic Metal was visibly discarded, and retreat was legal for two Energy.
The opponent's current Mega Lucario ex had publicly used Mega Brave and could
not repeat it on its next turn. Historical-Silver attacked immediately.

Narrow future transaction to test:

`evolve the two-Metal Bench Duraludon -> Assemble Alloy the visible discarded
Metal -> retreat the low-HP Active for two Energy -> promote the fresh
Archaludon ex -> preserve the same Metal Defender attack`

This may preserve the same 220 damage while presenting a fresh 300-HP
two-Prize attacker instead of a 110-HP attacker that the observed Aura Jab
could remove.

## Required proof before implementation

- Exact same-turn engine transaction in both seats.
- Exact retreat payment, promotion identity, attack legality, and attack
  identity after the pivot.
- No assumption about the opponent's hidden switch, gust, evolution, or
  damage modifier.
- Both routes compared under the public next-attack envelope; same-action and
  different-action collision tests against H6 v2, Hero, H5 v2, and any
  active cumulative transaction.
- Duplicate/reorder/serial/reset/exception/rollback gates and a full shadow.
- Confidence remains low until exact-engine evaluation shows that preserved
  attack plus survivability changes an outcome without sacrificing a parent
  win.

