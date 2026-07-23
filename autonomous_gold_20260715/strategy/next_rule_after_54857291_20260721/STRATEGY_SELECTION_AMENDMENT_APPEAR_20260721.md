# Controlling amendment: current-turn evolved Alakazam readiness

Date: 2026-07-21 JST  
Role: read-only Sol-Ultra strategy judge

## Ruling

**AMEND, do not reject or replace, the exact two-Prize Basic-PLAY lethal
conversion hypothesis.** Explicitly permit a current-turn evolved Active
Alakazam and a current-turn evolved paid Benched Alakazam successor when their
complete public stacks, Energy payment, and the engine's current legal options
prove the required readiness.

This is the smallest semantic correction. `appearThisTurn=True` is not itself
an attack prohibition. At the Active, the unique legal Powerful Hand option is
direct engine evidence that the attack is usable now. At the Bench, a complete
Stage-2 already carrying payable Psychic Energy needs no future evolution or
attachment; its next possible attack is on a later own turn, after the current
turn boundary.

The implementation worker remains paused until root hands off this amendment.
No candidate, deck, runtime, package, or Kaggle state is changed by this
judgment.

## Controlling precedence

This file has controlling precedence over
`STRATEGY_SELECTION.md`, SHA-256
`9F805909768D40FF9A591C52C7ABD586ED2C5B0BA414349BE115EBED1DC72058`,
only where that report:

1. describes Active `743/s73` or successor `743/s72` as old at
   `87111553/S85`;
2. requires `active.appearThisTurn == false` in Base prerequisite 3;
3. treats age, rather than a complete resolved evolution plus exact payment
   and current attack legality, as part of attacker or successor readiness; or
4. describes the S85 positive or its mutations as having an old Active or old
   successor.

The corrected facts and predicates below replace those statements. Everything
else in the original selection remains frozen and controlling: exact formal
parent `4A95DC...2AE16`; no stacking of `E5922E...51F6`; exact two-Prize scope;
optional Basic-Pokemon PLAY only; exact lethal-crossing inequality; separate
paid Alakazam successor; nonterminal/Bench and no-higher-Boss guards;
stateless precedence; all one-/three-Prize anti-anchors; numerical thresholds;
package restrictions; and root-only external writes.

## Corrected verified facts

Replay:
`autonomous_gold_20260715/live/54857291/refresh_20260721_0204/episode_87111553_replay.json`,
SHA-256
`67D3BEBFFEFC7EF22926A08751F19A6BF5C38187711716290DCC28ADC95668C6`.

The root reconstruction and direct observation checks agree:

- S72 has paid Active Kadabra `742/s70`, `appearThisTurn=False`, and
  unenergized Benched Kadabra `742/s68`, also false.
- The S72->S73 transition completes the Active evolution. At S73 the Active
  is Alakazam `743/s73`, `appearThisTurn=True`, with the exact lineage
  `[Abra 741, Kadabra 742]` and Telepath Psychic Energy. S73 is the ACTIVATE
  prompt; after its exact YES/draw resolution, ordinary MAIN at S74 already
  contains legal Powerful Hand `1072` while `s73` remains true.
- Benched Kadabra `742/s68` remains false through S79, is already paid by
  Basic Psychic Energy, and the S79->S80 transition completes its evolution.
  At S80 the Bench is Alakazam `743/s72`, `appearThisTurn=True`, with exact
  lineage `[Abra 741, Kadabra 742]` and the same Basic Psychic Energy. Its
  ACTIVATE/draw and later setup resolve before S85.
- At S85 both `s73` and `s72` are `appearThisTurn=True`. Each has a complete
  serial-distinct Stage-2 stack and payable Psychic Energy. S85 is ordinary
  MAIN with no owned evolution/selection prompt and contains the unique legal
  Powerful Hand option. The parent then chooses the optional Dunsparce PLAY.

Thus the original positive was internally impossible under the false-only
predicate. The correction does not assume an unobserved old source or hidden
history; it uses the exact public current stack, public boolean, exact payment,
resolved context, and current legal option.

## Corrected readiness predicates

These clauses replace the age portion of Base prerequisite 3 and clarify Base
prerequisite 8.

### Active attacker

Require all of the following:

1. Active is exactly Alakazam `743`; `appearThisTurn` is an actual boolean,
   either false or true. Missing, non-boolean, or raw/parsed disagreement fails
   closed.
2. Its owner, positive serial/HP, exact max HP, Energy/Tool cards, and complete
   evolution lineage are exact and globally serial-unique. A true Alakazam
   must still be a complete Stage-2 line: `[Abra]` through a legal Rare-Candy
   lineage or `[Abra, Kadabra]` through ordinary evolution. Empty, reversed,
   unknown, duplicate, or malformed lineage fails closed.
3. Public Energy units pay Powerful Hand now; status/effect and target
   protection checks remain clear; exact hand damage still satisfies the
   frozen lethal-crossing inequality.
4. The current callback is ordinary MAIN after every evolution, ACTIVATE,
   selection, and draw callback has resolved. No inherited owner existed at
   entry, none is active, and no stale owner was cleared on this callback.
5. Exactly one fully encoded legal `ATTACK/1072` option is present on this
   observation. For `appearThisTurn=True`, this legal option is mandatory
   positive proof; printed metadata or projected future legality alone is not
   sufficient.

No runtime log-history reconstruction is required or permitted. If the
current complete state and option envelope do not independently prove the
attack, delegate to the exact parent.

### Paid successor

Require a serial-distinct Benched Alakazam `743` with:

1. boolean `appearThisTurn`, either false or true, agreeing in raw and parsed
   state;
2. complete exact Stage-2 lineage, positive HP, exact max HP, unique component
   serials, clear public effects, and correct ownership; and
3. already attached public Energy units that pay Powerful Hand unchanged.

The successor is not required to have appeared before this turn. It is already
fully evolved and paid, and the selected action ends the current own turn by
attacking; therefore no same-turn promotion/attack is credited. The
certificate claims only readiness for its next possible own attack after a
normal promotion/turn boundary. A Kadabra, future evolution, Energy in hand,
future attachment, future draw, or current Active still does not count.

All four boolean combinations `(Active false/true, successor false/true)` are
semantically eligible only when every unchanged combat, lineage, payment,
parent-action, Prize, and Boss predicate passes. No equality between the two
flags and no episode/step exception may be coded.

## Corrected precedence and fail-closed behavior

Precedence is unchanged: inherited continuations, emergency starts, ordinary
parent scoring/overlays, and Fez bridge resolve first. The stateless helper may
replace only the later finalized optional Basic-Pokemon PLAY. It remains after
all S72-S84 setup in the positive replay and before new guarded-Teleportation,
stranded-retreat, or Hilda starts.

The helper must never act on EVOLVE, ACTIVATE/YES-NO, Psychic Draw resolution,
card-selection, or any non-MAIN callback. It must not remember that an earlier
evolution occurred, predict that a current Kadabra will evolve, or turn a
printed but absent attack into a readiness claim. Current state and legal
options are the sole authority.

On incomplete/malformed lineage, non-boolean or inconsistent
`appearThisTurn`, missing/duplicate Powerful Hand, unpaid attacker/successor,
status/effect ambiguity, active inherited owner, stale cleanup, or any other
failed original predicate, return exact guarded-parent identity. The rule
remains atomic and creates no latch.

## Amended anchors and tests

### Required positive

`87111553/S85/seat1` remains the sole frozen natural Basic-PLAY positive, now
with exact assertions:

- Active `743/s73`: `appearThisTurn=True`, lineage `[741,742]`, Telepath
  Psychic paid, unique legal Powerful Hand;
- successor `743/s72`: `appearThisTurn=True`, lineage `[741,742]`, Basic
  Psychic paid;
- parent PLAY Dunsparce -> candidate Powerful Hand; `280 >= 270 > 260`;
- exact two-Prize target, no higher Boss route, no inherited-state mutation.

The checked-engine continuation and both-seat reindex remain required.

### Mandatory sequence anti-anchors

- S72 pre-evolution MAIN, S73 ACTIVATE/YES, S79 pre-evolution MAIN, S80
  ACTIVATE/YES, and every intervening selection/draw/setup callback through
  S84 must remain exact parent behavior. The first candidate difference in
  this replay must be S85, never an earlier evolution or draw.
- Mutate the Active at S85 to true with incomplete/duplicate/reversed lineage,
  no payable Psychic, no legal Powerful Hand, multiple/malformed attack
  encodings, status, or raw/parsed flag mismatch: exact parent identity.
- Mutate the successor to true with incomplete/duplicate lineage, zero Energy,
  nonpayable Energy, wrong owner, nonpositive HP, or a Kadabra requiring future
  evolution: exact parent identity.
- Replace S85 MAIN with EVOLVE, ACTIVATE, selection, looking, an active latch,
  or a just-cleared stale owner: exact parent identity.
- Preserve the original report's one-/three-Prize, parent-action-class,
  terminal, no-backup, higher-Boss, protection, hand-threshold, duplicate,
  option-order, seat, and exception anti-anchors unchanged.

Focused synthetic controls must test all four Active/successor boolean pairs.
Changing only a well-formed boolean must not change eligibility; changing any
lineage, payment, legal-option, or context proof must fail exactly at that
predicate.

## Evaluation and package changes

All numerical floors and schedules in the original report are unchanged. Add
the following mandatory mechanism checks before compact72:

1. current-22 and historical shadow telemetry records both
   `active_appear_this_turn` and `successor_appear_this_turn`, exact lineages,
   Energy payment, parent action class, and legal Powerful Hand count at every
   first difference;
2. `87111553` is parent-identical through S84 and first differs at S85 with
   the boolean pair `(true,true)`;
3. checked-engine S85 continuation preserves the exact true flags at the
   decision, selects legal Powerful Hand, reaches KO/two-Prize resolution, and
   leaks no state;
4. every natural true-flag start is qualitatively inspected. Any earlier
   setup cutoff, projected-future readiness, or true flag accepted without
   complete lineage/payment/legal-option proof rejects the candidate; do not
   add another exception;
5. compact72, the Historical-Silver exposure extension if needed, full144,
   duplicate controls, action-error/max-step checks, adjacent floors, and
   package eligibility retain exactly the original thresholds.

The observed mechanism must be reported separately for `false/false`, mixed,
and `true/true` starts. Aggregate strength cannot cure a failed true-flag
sequence gate.

## Residual risk and exact evidence needed next

Allowing current-turn evolved lines increases reachable starts relative to the
contradictory false-only contract, but it does not broaden target Prize value,
parent action class, setup ordering, or resource routes. The residual risk is
still cutting off a useful optional Basic after completing only two attackers;
the paid-successor and exact two-Prize conversion gates bound, but do not prove
away, that long-horizon risk.

Next require the paused worker to implement this amended generic predicate
directly from the exact formal parent, then provide focused flag/lineage tests,
the S72-S85 parent-equality/first-difference proof, checked-engine KO/Prize
continuation, and callback-complete shadow evidence before any numerical run.
If a legal `appearThisTurn=True` start causes an earlier setup cutoff or a
mechanism-first loss, reject the rule rather than restoring an episode-specific
age exception.
