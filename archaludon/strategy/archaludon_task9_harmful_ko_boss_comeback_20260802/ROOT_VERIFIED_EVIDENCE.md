# Task 9 root-verified evidence

## Scope

Task 9 is the final high-level combat layer requested by the user.  It must
combine harmful-KO avoidance, nonterminal Boss targeting, public next-reply
control, reset-wall handling, and comeback selection.  It is not allowed to
learn an opponent policy or infer a hidden card identity from a replay.

The implementation parent is the accepted Task 8 candidate
`archaludon_public_lillie_physical_minimum_route_arbitration_t8_v1`, frozen at
`main.py` SHA-256
`74C20CCA851E6BCADB62382314656AE7506BD964C29DCE38A80BB5F665A0E971`.
Its final judgment is `ACCEPT` and commit `ce5557a` is pushed.  No implementation
may start from any earlier transient Task 8 file.

## Existing hard priorities

The cumulative parent already owns engine callbacks and card transactions.
Task 9 must never preempt them midway.  The required order is:

1. legal/mandatory engine callback and live transaction;
2. an exact win this turn, including Task 7 terminal Boss;
3. prevent an exact next-opponent-turn loss when a legal plan does so;
4. compare complete attack/Boss/no-KO plans by Prize race and public reply;
5. if every exact plan loses, enter comeback ordering;
6. exact parent fallback when public effects or plan completion are unknown.

Fixed additive scores may not trade away a higher layer for a lower one.

## Root-verified live failures that motivate the layer

- Episode 89292594: with one Prize remaining, the agent used Explorer and hit a
  fresh Mega Lucario instead of using held Boss on a one-Prize Bench target for
  the exact win.  Task 7 now covers this terminal subset.
- Episode 89273226: Boss was held while a damaged Bench Mega Lucario was in
  exact KO range; the agent attacked a fresh Active instead.  This is a
  nonterminal higher-Prize Boss conversion and remains Task 9 work.
- Episodes 89285518, 89282820, and 89287701: attacking while suppressing a
  useful Duraludon reduced board depth immediately before the Active was KO'd.
  Task 9 must compare the opponent's public return and remaining successor,
  not only current damage.
- Episodes 89288811 and 89277996: the opponent's public Bench-damage attack
  could remove both Active and an unprotected backup; available evolution was
  skipped.  Exact board-wipe avoidance must dominate ordinary attack value.
- The user identified reset-wall play as a separate tactical class: nonlethal
  chip into Dudunsparce/other voluntary hand-return walls is not durable
  progress when the opponent can reset it while developing a Bench engine.
  Existing effect registry support for `RUN_AWAY_DRAW` must be used rather than
  assuming all damage persists.

These are mechanism examples, not action labels to imitate and not episode-ID
exceptions.

## Plans that must be considered

At an owner-free ordinary MAIN attack boundary, build complete plans only from
legal public actions:

- attack the current Active;
- intentionally select a non-KO attack or END only when that changes the exact
  Prize/return race in our favor;
- play Boss, bind a legal Bench target, then bind the resulting attack;
- materialize a one-Prize wall or a surviving/ready successor before attacking
  when it prevents an exact terminal reply;
- remove a ready Bench attacker or next-turn evolution engine instead of
  taking a lower-value Active KO when the removal changes the exact winning
  turn;
- if a reset wall can erase nonlethal damage, treat chip as zero durable
  progress unless the same plan also changes Prize timing, locks retreat, or
  removes the Bench engine.

No plan may assume a future draw or arbitrary deck order.  A public hand,
discard, attached Energy, legal one-step evolution, legal manual attachment,
registered acceleration/switch/return effect, or known remaining resource
count may establish a separate access tier.  An unknown hand requirement may
increase the opponent-resource requirement in comeback ordering, but may not
be treated as certainly present or certainly absent.

## Exact plan outputs

Each compared plan must record:

- current attacker, target, attack, effective damage, KO and Prize result;
- weakness/resistance, Stadium, Tool, Ability and registered prevention or
  return effects used by the damage certificate;
- post-action Active/Bench and an exact ready successor if one exists;
- opponent public reply tier: ready now, one manual attachment, one public
  evolution, registered public accelerator/switch/return, or hidden multi-card;
- whether the reply takes the opponent's final Prize or wipes our board;
- whether damage is durable against a registered return/heal wall;
- remaining physical Boss/search/recovery/energy/evolution refs;
- exact next own KO turn when public information is complete;
- uncertainty and fail-closed reason when it is not.

## Hard dominance and comeback order

Use hard conditional dominance for:

- exact win now;
- avoiding an exact next-turn loss or board wipe;
- taking more Prize now with no worse exact terminal reply;
- removing all exact terminal reply routes;
- one-shotting a return wall where nonlethal chip is resettable;
- Bossing a prepared threat/evolution engine when that strictly delays the
  opponent's exact winning turn without delaying ours;
- refusing a harmful KO when KO promotion creates an exact terminal reply and
  a legal no-KO/Boss/wall plan avoids it.

If all supported plans lose, do not maximize ordinary board score.  Order by:

1. more turns until exact loss;
2. more additional distinct public resources/actions required from opponent;
3. more surviving own comeback outs and executable attackers;
4. fewer self-deckout risks;
5. deterministic semantic/serial ordering only at a complete tie.

Unknown combat-relevant text blocks exact dominance and returns the parent.  It
does not justify assigning zero damage or ignoring an Ability.

## Required telemetry and practical safety gate

Every override must name one purpose:

- `EXACT_LOSS_AVOIDANCE`;
- `HARMFUL_KO_VETO`;
- `RESET_WALL_ONE_SHOT_OR_BYPASS`;
- `NONTERMINAL_BOSS_PRIZE_CONVERSION`;
- `READY_THREAT_OR_ENGINE_REMOVAL`;
- `COMEBACK_RESOURCE_REQUIREMENT`.

Record compared complete plans, the winning hard layer, effect-registry
coverage, uncertainty, physical refs, owner handoffs, duplicate count, and the
first changed action.  Safety requires compile/import, legal 60-card deck and
one ACE SPEC, final callable loader, no caches, deterministic option-order and
duplicate behavior, exact callback completion, both-seat smoke, no invalid
actions or max-step hit, and manual inspection of every first difference.
Per the user's instruction, low local win rate alone is not a rejection reason;
a known destructive move, invalid action, incomplete transaction, or
nondeterminism is.
