# Task 9 strategy selection

## Selected rule

`PUBLIC_PRIZE_RACE_THREAT_CONTROL_T9_V1`

Implement one final wrapper, one shared exact planner, and one ownership domain.
The six labels below are purposes inside that planner, not stacked rules:

- `EXACT_LOSS_AVOIDANCE`;
- `HARMFUL_KO_VETO`;
- `RESET_WALL_ONE_SHOT_OR_BYPASS`;
- `NONTERMINAL_BOSS_PRIZE_CONVERSION`;
- `READY_THREAT_OR_ENGINE_REMOVAL`;
- `COMEBACK_RESOURCE_REQUIREMENT`.

Parent: accepted Task 8 `main.py` SHA-256
`74C20CCA851E6BCADB62382314656AE7506BD964C29DCE38A80BB5F665A0E971`.
Root evidence SHA-256:
`816DC0A3690ACE09AF617A47E2AD4844743D205511704F59B3670253CCF3BF7D`.

## Activation and precedence

Save and call the exact Task 8 callable once.  Existing/mandatory callbacks,
live inherited owners, and Task 7 exact-win Boss retain priority.  A fresh Task
9 start requires owner-free ordinary MAIN, live game, exact serials, admitted
effect inventory, supported statuses, and an exact parent plan.  If the parent
cannot be mapped to a complete exact plan, return it unchanged.

## Complete public plan families

Enumerate only legal complete plans:

1. every payable current-Active attack;
2. legal END as unchanged-board/no-attack;
3. every legal Boss target times every payable post-gust attack;
4. exact active setup plans already supported by `_pcrd_generate_plans`;
5. one-step successor plans followed by the same exact attack: play Duraludon,
   evolve a Bench Duraludon including forced Assemble Alloy, or attach one exact
   Metal to a Bench line when it creates a payable successor;
6. the exact parent-proposed formation plan.

Do not combine arbitrary speculative setup actions.  Existing card owners keep
their forced callbacks.

Each plan records physical refs, attacker/target/attack/payment, effective
damage, KO/Prize, all admitted combat effects, post-action board, minimum board
after every certain public reply, ready successor attacks, reply tier, terminal
and board-wipe counts, damage durability, remaining critical refs, exact finite
finish horizon, and an explicit unknown reason.

Opponent hand identity is removed before threat construction.  A public
one-attachment possibility is a separate non-certain tier.

## Reset walls

For a non-KO certificate with `persistent_progress == False` and
`run_away_draw_executable == True`, durable damage is zero.  An exact one-shot
KO or exact Boss bypass may dominate it when terminal reply is no worse.  If
neither exists, preserve the parent rather than forcing END.  A lone
Dudunsparce without a legal promotion is not a reset wall.  Only registered
return/heal effects qualify.

## Harmful KO and wipe proof

A nonterminal KO is harmful only when forced promotion creates an exact
terminal reply or exact board wipe and another complete legal plan avoids it.
Board wipe includes no surviving Bench, exact simultaneous Active/Bench loss,
and registered exact counter-placement removal of the remaining board.  Do not
veto an ordinary nonterminal Prize trade when an exact successor remains.

## Boss purposes

`NONTERMINAL_BOSS_PRIZE_CONVERSION` requires strictly more current Prizes with
no worse loss/wipe horizon, successor continuity, or own finish horizon.

`READY_THREAT_OR_ENGINE_REMOVAL` requires the target serial in an exact public
reply as attacker, evolution source, switch/return source, or registered
Ability engine, and its removal must delay the opponent finish or eliminate an
exact terminal/wipe route without delaying ours.  Never infer an engine from an
archetype or hidden evolution.

## Hard ordering

Use no additive score.  Compare:

1. exact win now;
2. longer exact loss/board-wipe horizon;
3. more current Prizes only with no worse layer 2;
4. fewer exact terminal/wipe routes and durable reset-wall progress;
5. stronger surviving attacker/successor continuity and no later own finish;
6. resource preservation.

Unknown or incomparable first differences return the parent.

If every supported plan loses, comeback ordering is:

1. more exact turns until loss;
2. more distinct opponent public actions/resources required;
3. more executable attackers and physical comeback outs;
4. lower self-deckout risk;
5. fewer irreversible resources consumed;
6. semantic then serial ordering at a complete tie.

## Owner and lifecycle

Use one Task 9 transaction.  Boss lifecycle:

`BOSS_PLAY_EMITTED -> BOSS_TARGET_EMITTED -> POST_GUST_MAIN_VERIFIED -> ATTACK_EMITTED`

Verify seat, turn, action count, physical Boss movement, Supporter flag, board
fingerprint, target, exact attack, and option multiset at every transition.
PCRD-compatible setup plans hand off to the existing executor; Task 9 and PCRD
may never be live simultaneously.  Release Task 9 immediately after emitting
the attack so aftereffects retain their owners.  Retries rebind semantic roles;
option order cannot change semantic decisions; equivalent physical copies use
lowest serial only after semantic comparison.

## Required fixtures and gate

Fixtures must cover terminal Boss invariance; synthetic damaged three-Prize
Bench Boss conversion; positive/negative harmful KO; Dudunsparce one-shot,
Boss bypass, fallback and lone-wall cases; Bench-damage wipe avoidance;
positive/negative ready-threat removal; all-losing comeback; unknown effects;
weakness/resistance/FML/Cape/Coated/Ability damage; both seats, permutations,
duplicates, stale Boss target, owner collisions and Turbo handoff.

Accept practical safety when compile/import, legal60/ACE1, final loader,
cache-free, focused both-seat fixtures, exact callback conservation, both-seat
smoke, zero invalid/owner/nondeterministic/max-step error, and inspection of all
current-plus-historical first differences pass.  Every override needs exactly
one purpose and a complete certificate.  Low local win rate alone is not a
rejection reason.

## Non-goals

No hidden-hand guess, opponent/archetype policy, replay exception, learned
ranking, unregistered-effect optimism, unjustified multi-turn certainty,
deck-list change, or unrelated search/Supporter redesign.
