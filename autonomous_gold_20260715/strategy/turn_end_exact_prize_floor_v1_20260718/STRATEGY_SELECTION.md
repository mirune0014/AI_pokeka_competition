# Strategy selection: turn-end exact Prize floor v1

## Frozen parent and hypothesis

- Candidate: `alakazam_turn_end_exact_prize_floor_v1`.
- Exact parent: `alakazam_fez_public_retaliation_guard_v2` / live submission
  `54790261`.
- Parent source SHA-256:
  `A776D74ECE4C08B9FA71225E81C444F5C39134863C884CF44C704CE52F55F122`.
- The exploratory Boss-v2 source/submission is **not** the parent and must not
  be stacked into this candidate.

Frozen hypothesis:

> Let productive board development occur first.  When the unchanged parent is
> about to END, make a zero-Prize attack, or irreversibly spend a resource
> reserved by a fully public same-turn Prize route, complete the exact
> EVOLVE / Psychic ATTACH / optional certified BOSS / ATTACK route as one
> deterministic two-to-four-action transaction.

This is a turn-end attack floor, not an attach-first KO rule and not a replay
step patch.  Source predicates may not contain episode IDs, opponent names,
seeds, saved results, or exact turn numbers.

## Bound evidence

- Active-Psychic attach-first audit SHA-256:
  `DFA65CB1BFDC053686B108FBC6DB4B1E328721B1DD847ACF3B2E39A9857A30FD`.
  Root independently recomputed parent `78/144`, candidate `84/144`, zero
  execution/action/max-step faults, and Alakazam-Rmy `9/16 -> 7/16`.
- Eight-loss qualitative report SHA-256:
  `A8A266F1EC10A1BC7E5A3E35A9DC1CE2D8B32CB5199B1B3A8EDB2F452DA02FD3`.
- Domain translation matrix SHA-256:
  `BD351D710E2024BD201D2D223AF838901D3CC060B46AE959AE8E15991418AB34`.
- Fixed 144-key schedule SHA-256:
  `4271E31503F37EFE4B1BBB9ED2D3569D79D9C1E9B2A20387CCAC131F28346010`.

The attach-first candidate proved the exact public attach-to-Powerful-Hand
mechanism: all 60 changed starts completed a same-turn KO, producing 11 gains
and five regressions.  The five regressions were sequencing failures rather
than invalid attacks: the candidate pre-empted productive parent PLAY actions;
four parent games still developed the board and attacked later that turn.
Therefore this successor preserves the attack certificate while moving its
authority to the turn-ending boundary.

## Public route certificate

At a complete own `MAIN` observation, turn 2 or later, enumerate at most four
actions using only exact current options and known cards.  A route is eligible
only when all affected card identities, serials, Energy, Tools, evolution
stacks, statuses, Stadium, hand fingerprint, deck count and Prize counts are
publicly complete and unique.

Allowed route actions are:

1. an exact evolution of the fixed Active attack lane, if already in hand and
   legally offered;
2. an exact Basic/Telepath Psychic attachment to that fixed Active;
3. a certified Boss card plus a certified fixed target, only when needed for a
   strictly better Prize result or the final Prize;
4. one fixed exact-damage attack or Powerful Hand `1072` that takes at least
   one Prize.

Examples are `ATTACH -> ATTACK`, `EVOLVE -> ATTACK`,
`EVOLVE -> ATTACH -> ATTACK`, and
`EVOLVE/ATTACH -> BOSS -> target -> ATTACK`.  Every card and hand-cost
transition must be included in the final damage calculation.  Weakness,
Resistance, Tools, Stadium, Skills and visible protection must be exactly
resolved.  Future draws, hidden search hits and opponent choices are never
assumed.

Non-final Telepath routes additionally require
`deck_after_required_effects > post_KO_prizes`; equality fails closed.  Its
optional search selects zero cards.  A mandatory or ambiguous callback makes
the route ineligible.

Route ordering is deterministic: final Prize, more certified Prizes, no Boss,
fewer actions, then Active/target/card serials and option index.

## Parent delegation and override boundary

Existing accepted-v6 Hilda, Enriching-reserve, Fez, Run-Away-Draw and fragile
bench behavior remains authoritative.  An active inherited transaction always
wins and no new route may begin.

Even when a route exists, delegate ordinary non-Boss PLAY, non-reserved
EVOLVE, and ABILITY actions to the parent and recompute on the next observation.
Override only when the exact parent top action is:

- END;
- an ATTACK certified to take zero Prizes while the route takes one or more;
- an attachment to a different Pokemon using the route's reserved manual
  attachment;
- an evolution that consumes a route-reserved card serial on a different
  lane;
- a Supporter, retreat or Energy payment that irreversibly removes a required
  route resource; or
- already the route's first action, in which case return that identical action
  and start the latch.

Do not stop Hilda/Dawn merely to make an equal-value gust.  A Boss-dependent
route may reserve the Supporter only for final Prize or strictly more certified
Prizes than the best Boss-free route.

After a transaction starts, permit only its frozen actions.  Optional draw,
search/setup, non-route evolution/attachment, retreat, disruption and a second
Boss are forbidden until the attack completes.  The latch may not cross an
opponent turn.

## Fail-closed boundaries

Delegate the exact parent action on any unknown or mismatch: incomplete hand,
duplicate/missing serial, ambiguous option/callback, unknown Energy unit,
unresolved damage/protection, route longer than four actions, search-dependent
route, changed Active/target/hand/deck/Prize/Stadium, Boss-target mismatch,
existing-latch conflict, or unsafe deck-clock equality.  A route that fails
after an irreversible first action is an implementation-gate failure even if
the fallback remains legal.

## Fixed Phase-0 gate

Reuse the exact 144-key schedule above and the frozen v6 parent result/tree;
do not rerun the parent.  Candidate execution must have exact key equality,
zero command/action/schema/max-step/hash faults and deterministic repeat
traces.  Practice-first exploratory PASS requires:

- total at least `82/144`;
- P0 at least `44`, P1 at least `34`;
- known and fresh each at least `39`;
- Rmy at least `9`, Oselcoun at least `7`;
- Historical-Silver at least `7`, Marnie at least `10`;
- every other opponent no worse than parent minus one;
- all five old attach-first regressions recovered;
- at least seven of the eleven old gains retained;
- every first difference classified as a frozen route action or prevention of
  reserved-resource destruction; and
- every started transaction completes its same-turn attack and Prize.

Target buckets are Historical-Silver, Marnie, Dragapult, both Alakazam mirrors
and Great Tusk.  Retention buckets are Mega Lucario, Starmie,
Kangaskhan/Crustle, both seats, both schedule blocks, and every inherited-v6
overlay boundary.

Passing this short gate permits one explicitly labelled exploratory live probe
under the user's practice-first cadence.  It does not itself replace v6 as the
accepted baseline.

