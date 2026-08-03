# Night Stretcher attack-legality repair amendment

## Status and authority

This amendment controls the successor to frozen source
`07C567E6F3B1E53DDC3DBFA0757DD2E981FD16CBEBCB4E019D332FE73CAD0C8D`.
That source is rejected and must not be packaged, submitted, or advanced to the
fixed-760 evaluation.  Its completed full shadow was safe at the action-binding
level, but it exposed one destructive route-completion bug and failed the
precommitted natural-frequency gate.

The repair remains deterministic and public-state-only.  It may not use replay
identity, remembered opponent policy, hidden cards, or an episode-specific
exception.

## Root-verified evidence

The immutable full shadow processed 207 replay files, 209 target seats, and
25,880 callbacks.  It reported zero invalid parent/candidate actions, zero
faults, zero duplicate-state issues, and zero untraceable overrides.  However:

- only 11 unique complete transaction starts were observed, below the required
  16;
- only four first differences across two replay files were observed, below the
  required ten across six replay files;
- three of those differences were repeated counterfactual observations of the
  same physical state lineage in `88035562`;
- the remaining first difference, `88660007 / seat 1 / step 12 / turn 1`, was
  destructive.

At `88660007 / seat 1 / step 12`, `firstPlayer == 1` and `yourIndex == 1`.
PBNS projected Night Stretcher `90` -> Metal `115` -> attach to Active Duraludon
`63` -> Hammer In `223`.  The damage/payment certificate correctly computed 30
damage, but the player was taking the first turn of the game and therefore had
no legal ATTACK option.  The exact engine consumed Night Stretcher and the
recovered/attached Metal, then offered only END.  The saved ATTACK step became
unavailable and PBNS rolled back too late to restore the spent Item.  The exact
parent had ended immediately and preserved those resources.

This proves that attack damage, Energy payment, and attack access are distinct
certificates.  A route may be payable and meaningful yet still illegal this
turn.

## Controlling single repair

Add one exact public **attack-turn legality certificate** and require it before
constructing or starting any PBNS route whose lifecycle contains an `ATTACK`
step.  This includes `ATTACK_NOW`, Active `EVOLVE_ATTACK_NOW`, backup-continuity
routes whose current attacker is reserved, and every terminal/win attack route.

The certificate must establish all of the following for the projected attacker
and exact attack ID:

1. **Game-turn permission.**  Reject when `current.turn == 1` and
   `current.yourIndex == current.firstPlayer`.  This is the first player's first
   turn, where attacking is forbidden even after Energy becomes payable.
2. **Exact public attack access.**  The attack is printed on the projected
   attacker or is available through an already-certified public Memory Dive
   lineage.  Unknown access fails closed.
3. **No exact self-lock.**  Existing public same-attack locks such as Mega Brave
   or Accelerating Stab must be checked through the existing exact lock
   machinery.  A proven lock rejects the route; unknown lock evidence fails
   closed.
4. **No known public turn/status prohibition.**  Reuse existing engine-facing
   attack-effect/status evidence.  If a public attack-prevention state is known,
   reject.  If the policy cannot distinguish a prohibition from an ordinary
   pre-payment absence of the ATTACK UI option, fail closed unless the only
   missing condition is the exact saved Energy/evolution sequence itself.
5. **Lifecycle re-certification.**  Immediately before emitting the saved
   ATTACK step, re-run the legality certificate against the actual post-route
   state and require a uniquely bound legal ATTACK option for the exact attack
   ID.  If it is absent, clear/delegate without having started a route that could
   not be certified at admission.  The admission gate, not this late fallback,
   is the resource-safety mechanism.

The first-turn check is necessary but not sufficient.  Do not implement this as
an episode exception or as a single `turn != 1` shortcut that bypasses public
attack locks.

## Required implementation behavior

- `88660007 / seat 1 / step 12` must remain exactly parent-identical at the
  initial callback: choose END and do not play Night Stretcher.
- `88035562 / seat 0 / step 62` must retain the legal conversion when all exact
  certificates hold: Night Stretcher -> Metal -> attach -> Hammer In.
- The same positive conversion must complete in the native engine in both seats
  on a legal later turn.  A synthetic fixture that merely injects an ATTACK
  option is insufficient.
- Test all four `(firstPlayer, yourIndex)` pairs at turn 1.  Exactly the two
  pairs where the acting player is `firstPlayer` must reject; the other two may
  proceed only when the engine actually exposes the attack after the saved
  route.
- Test a later-turn exact attack lock, an unknown-lock negative, and an unlocked
  positive in both seats.
- Exact current-KO guards must also ignore attacks that are not legal this turn;
  an illegal theoretical KO may not veto a safe parent line.
- Preserve all 60 previously passing focused checks, exact parent prefix,
  unchanged legal 60-card deck/ACE count, last-callable loader behavior,
  deterministic duplicate binding, and cache-free packaging tree.

## Evaluation decision

After focused and native-engine verification, run a fresh immutable full shadow
against the same corpus and inspect every first difference.  Do not weaken the
original frequency thresholds.  Because source `07C...` already failed them,
the expected result is a safe but rare research artifact, not promotion.  If
the repaired source again has fewer than 16 unique starts or fewer than ten
first differences across six replays, record `RARE_NARROW_FAIL`, skip fixed-760,
and move to the next broader human-fundamental rule.

