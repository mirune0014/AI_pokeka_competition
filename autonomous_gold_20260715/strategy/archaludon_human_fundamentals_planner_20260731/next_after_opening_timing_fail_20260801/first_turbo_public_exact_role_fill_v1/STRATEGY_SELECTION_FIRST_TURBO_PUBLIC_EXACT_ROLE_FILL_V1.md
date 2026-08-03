# Strategy selection — first Turbo public exact role fill v1

## Status

`PRE_EDIT_CENSUS_ONLY`

No source edit is authorized until the frozen census passes every gate below.

## Hypothesis

On the target seat's first public Turbo Flare transaction, choose at most three
Basic Metal Energy and their Bench targets by exact role-attack deficits rather
than by generic three-Energy target scores.

The rule may change only the `ATTACH_TO` Energy count or an `ATTACH_FROM`
target. It does not change mulligan, setup, first/second choice, the MAIN
action, or the Turbo Flare attack itself.

## Boundary and ordering

The callback must expose the exact Cinderace source serial, the current Turbo
Flare attack log, legal option roles, visible Bench, attached Energy, and exact
card/attack metadata. No H3, PFC, PCRD, cumulative component, PF Gear, or other
owner/watch may be live.

Candidate allocation order:

1. make the closest exact primary role attack payable;
2. minimize that role's remaining Energy deficit;
3. make the closest exact backup role attack payable;
4. minimize the backup deficit;
5. avoid attaching beyond the selected role cost;
6. preserve the exact parent action on semantic ties.

Role attacks come from exact metadata:

- Duraludon → Raging Hammer;
- Archaludon ex → Metal Defender;
- non-ex Archaludon → Coated Attack;
- a Benched Cinderace → Turbo Flare.

Physical Basic Metal copies are semantic copies. When the useful count is
unchanged, keep the parent's selected physical copies; never report a
difference caused only by Energy serial or option order.

Any ambiguity, unsupported card/effect, stale retry, forced minimum-count
conflict, hidden future card, owner collision, or equal allocation returns the
exact parent action.

## Positive and negative boundaries

Positive:

- exact-cost fill redirects one Energy to complete a role attacker;
- remaining Energy forms a closest public backup;
- the parent selects more Energy than all exact useful public deficits;
- the parent targets an already role-payable Pokémon while a unique incomplete
  role target exists.

Negative:

- the parent already performs the same semantic allocation;
- there is only one legal target and the parent count is useful;
- multiple target plans are tied or incomparable;
- H3 or another owner controls the transaction;
- any decision needs a hidden draw, Prize identity, future evolution, or
  unobserved deck order.

## Frozen implement/stop gate

Implementation requires all of the following without threshold relaxation:

- exact 207 replay files, 209 target seats, and 25,880 parent calls;
- zero manifest mismatches, duplicate keys, or invalid parent actions;
- at least 80 first-Turbo transactions over at least 64 replays and both seats;
- at least 24 immediate semantic first-action differences over at least 16
  transactions, 12 replays, and both seats;
- at least eight differences specifically from exact-cost fill or overfill
  avoidance;
- at least 24 parent-equal negative controls over at least 16 transactions and
  both seats;
- zero invalid contract actions, hidden-information use, H3 changes, owner
  collisions among predicted changes, stale retries, semantic-copy noise,
  duplicate transaction keys, or non-Turbo changes;
- root inspection classifies every predicted difference `GOOD_CAUSAL`.

Any failed floor means
`STOP__FIRST_TURBO_EXACT_ROLE_FILL_NOT_ACTIONABLE`. Passing authorizes one
isolated Sol-xhigh source implementation; it does not authorize promotion or
submission.

## Required raw evidence

Persist callback rows, one transaction summary per first Turbo, a predicted
difference ledger, exact source/input hashes, parent and contract roles,
owner state, effect/attack identity, selected Energy serials, Bench role
snapshots, attack costs, deficits, emitted legality, rejection reasons, and
first-difference attribution. Deduplicate by replay hash, seat, Turbo source,
turn, callback stage, and snapshot hash—not by callback volume.
