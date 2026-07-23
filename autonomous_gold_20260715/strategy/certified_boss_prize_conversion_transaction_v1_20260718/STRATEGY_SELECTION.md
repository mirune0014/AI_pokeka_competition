# Certified Boss prize-conversion transaction v1

## Decision

Implement one isolated deterministic Boss gate/transaction directly from
`alakazam_fez_public_retaliation_guard_v2`.  Do not stack the rejected
`alakazam_active_psychic_immediate_ko_transaction_v1` overlay.

Immutable parent `main.py` SHA-256:
`A776D74ECE4C08B9FA71225E81C444F5C39134863C884CF44C704CE52F55F122`.
The deck remains the exact 60-card parent deck, SHA-256
`7B413177E5077777F2178143839C0155B03B92BBC8B3A6607621A7D43F351141`.

## Root-verified evidence

- Submission `54790261` was `7-5` over 12 public games at the last refresh,
  score `600.2`.  All four newly inspected losses contain an uncertified
  Boss action as their earliest public route break.  The loss diagnosis is
  SHA-256
  `46C8DAC315842286346011D4A79A0ACDA724694076C0C3F0033731259594EB55`.
- Three losses spend Boss without any same-turn attack.  Two exact states
  change a guaranteed current-Active KO into a non-KO: `340 >= 210` becomes
  `320 < 330`, and `200 >= 140` becomes `180 < 210`.
- The Active-Psychic candidate is eligible zero times in those four losses.
  Its fixed Phase-0 result is parent `78/144`, candidate `84/144`, but Rmy
  falls `9/16 -> 7/16`; all five regressions preempt setup with an early
  one-Prize KO.  The independent audit is SHA-256
  `DFA65CB1BFDC053686B108FBC6DB4B1E328721B1DD847ACF3B2E39A9857A30FD`
  and its disposition is `HOLD`.
- The seven-win control audit preserves all same-turn Boss KOs and identifies
  two non-attacking public threat-control branches: Riolu and a Hero's Cape
  Staryu.  It is SHA-256
  `CF6775154C9A65A1FB89C0FDD32029FDDC3D355F0A55D360A374914CC8BAE0BF`.

## Frozen rule hypothesis

Only when the inherited v6 top `MAIN` choice is Boss and no older transaction
has priority:

1. Enumerate fully public opposing Bench targets and the exact currently
   legal attack from the current Active.
2. For energized Active Alakazam, compute post-Boss Powerful Hand damage as
   exactly `20 * (handCount - 1)`.  Credit no future draw, search, evolution,
   attachment, retreat, or hidden card.
3. Permit an immediate conversion only when the selected target is certainly
   KO'd, its Prize gain is at least the guaranteed Prize gain from attacking
   the current Active, the deck/Prize clock remains viable, and all protected
   serials and public effect checks are exact.
4. Rank multiple certified targets deterministically by final-Prize, Prize
   gain, HP, then serial.
5. Bind `PLAY Boss -> exact target -> post-Boss revalidation -> exact attack`.
   Freeze Boss, hand, attacker, target, prizes, deck and stadium.  Clear and
   delegate on every mismatch; never reuse a stale option index.
6. If the inherited top Boss is not certified, suppress it and take the exact
   next inherited action.  Preserve only the already public non-attacking
   threat-control family whose target is in
   `{Solrock, Riolu, Duskull, Staryu}`.

This is a public-state general rule, not an episode, seed, seat, opponent or
archetype exception.

## Fixed Phase-0 gate

Use the same 144 paired keys as the rejected Active-Psychic comparison:
nine opponents, both seats, four known and four fresh seeds.  Require exact
schedule equality, zero execution/action/max-step faults, and:

- total `>= 78/144`;
- P0 `>= 44/72`, P1 `>= 34/72`;
- known `>= 39/72`, fresh `>= 39/72`;
- Rmy `>= 9/16`, Oselcoun `>= 7/16`, Historical-Silver `>= 5/16`;
- every other opponent no worse than one win below its parent bucket;
- every first action difference certified as either a Boss transaction start
  or suppression of an uncertified inherited Boss;
- protected same-turn Boss KOs and Riolu/Staryu controls remain unchanged.

This is a live-feedback candidate: after the structural, engine, fixed-panel
and package gates pass, the next Kaggle slot is an intended practical probe,
not a claim of perfect local proof.
