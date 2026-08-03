# Deferred loss memo — episode 88779311

Status:
`REJECTED_AS_SELECTION_SOURCE__DEFER_ONLY_NEGATIVE_CONTROL__DO_NOT_STACK`

Controlling correction:
`ROOT_CORRECTION_88779311_LAST_BENCH_EVOLUTION.md`

The original local observation that a single 30-counter event does not KO the
evolved body is true but incomplete. The full public damage package and
decision-time information boundary reject the proposed rule. Nothing in this
memo authorizes implementation.

Replay:
`autonomous_gold_20260715/live/55077607/refresh_20260729_1855/episode_88779311_replay.json`

Replay SHA-256:
`846F9BEA46F3B08A9109863152D88D207488D881436A6F80E76D8B1EF537C2D5`

The target was seat 0 and lost. Root shadowed all 56 actionable callbacks:
H6 v2 was exactly parent-identical with zero invalid actions, exceptions, or
stale transactions. This episode is not H6 causal evidence and does not
authorize an H6 repair.

## Root-verified relevant path

- The game opened on a lone Cinderace and did not expose Duraludon until a
  later Poke Pad. This created an early setup deficit but does not itself prove
  a deterministic policy alternative.
- At row 97, the parent had a Cape-bearing three-Metal Active Duraludon at
  200/230 and a one-Metal Bench Duraludon at 130/130. Archaludon ex was legal
  on either. The parent scores were `17,000` for Active and `20,000` for Bench,
  and it evolved the Bench. This preserved the current Raging Hammer while
  building a ready successor; it is not a certified error.
- At row 140, after a correct Boss target and before Metal Defender, our board
  was Active Archaludon ex `190#7` at 140/300 with three Metal and exactly one
  Bench Pokémon: Hero's-Cape Duraludon `169#6` at 10/230 with three Metal.
  Hand contained non-ex Archaludon `840#32`.
- Legal options were evolve the last Bench Duraludon, Metal Defender, Retreat,
  or End. The exact historical scores were `-1,000` for evolution
  (`hold non-ex Archaludon outside Ogerpon`) and `220` for Metal Defender.
  The parent attacked.
- On the opposing turn, public Night Stretcher recovered Darkness
  `7#66`, attached it to Munkidori `112#78`, and enabled Adrena-Brain.
  Moving 30 damage to the 10-HP Bench Duraludon KOd the last Bench and
  discarded its three Metal plus Hero's Cape. Shadow Bullet then KOd the
  Active Archaludon ex and ended the game by board-out.

## Original incomplete local arithmetic

The Cape-bearing Duraludon at 10/230 carried 220 retained damage.

- Non-ex Archaludon has 180 base maximum HP.
- Retaining Hero's Cape gives projected maximum HP `280`.
- Evolution retains 220 damage, so projected current HP is `60`.
- The already public, currently reachable Adrena-Brain movement is `30`.
- Projected post-movement HP is therefore `30`, not a KO.

This proves survival against the isolated 30-counter movement only. It does
not prove board-out prevention. The controlling correction adds Shadow
Bullet's simultaneous 30 Bench damage, giving `60 - 30 - 30 = 0`, and records
that Night Stretcher was a hidden future topdeck at row 140.

## Rejected hypothesis — last-board evolution survival gate

Potential trigger:

- ordinary Main callback before a nonterminal inherited attack;
- exactly one Bench Pokémon remains;
- it is a legal evolution target already holding the public damage counters
  and Tool;
- a currently legal, publicly reachable damage-counter or Bench-damage event
  KOs the Basic before our next turn;
- the legal evolution's exact retained-damage HP is strictly above the full
  certified public event package;
- failure to evolve plus the publicly payable Active KO produces board-out;
- the evolution does not displace an exact same-turn match win or a stronger
  certified Prize route.

Potential change: apply only a local score modifier to that one evolution
option, then return to the exact parent attack after confirmation.

Mandatory negatives:

- more than one surviving Bench Pokémon;
- evolution remains inside the full damage package;
- the threatening Ability/attack is not currently reachable from public
  board, discard, hand/recovery, Energy, and legal actions;
- evolution consumes the only exact terminal or higher-Prize line;
- the evolved body creates an immediate worse public Prize loss;
- relevant damage, prevention, Tool, Stadium, status, or continuous effect is
  unsupported.

This replay is a mandatory negative for Bench/future-board valuation. The rule
must not fire when the full public event package reaches projected HP or when
any required recovery/access was not public at decision time. It must not be
combined with H6 or generalized to `always evolve a damaged Bench`.
