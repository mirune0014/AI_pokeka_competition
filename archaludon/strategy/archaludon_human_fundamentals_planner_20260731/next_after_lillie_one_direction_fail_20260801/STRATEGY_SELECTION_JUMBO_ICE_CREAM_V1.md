# Purpose-bound Jumbo Ice Cream survival/attack/Prize v1

## Authorization

`PRE_EDIT_CENSUS_ONLY`

No candidate source edit is authorized until the frozen natural-history gate
passes in both directions.

## Hypothesis

At a transaction-free clear MAIN callback with an actual legal Jumbo Ice Cream
option, compare two exact public worlds:

- `NO_HEAL`;
- `HEAL_80`, using `min(80, max_hp - current_hp)` on the Active Pokémon with
  at least three attached Energy.

Enumerate every actual legal attack separately in each world.  Do not require
the same attack to remain best.  Healing is valuable only when it improves a
higher-ranked survival, Prize, or continuity result.  Healing is harmful when
removing the same damage counters loses a better Raging Hammer win, KO, or
Prize route.

## Hard hierarchy

1. Legality, exact metadata, live-owner precedence, and actual engine options.
2. Exact immediate win.
3. Avoidance of exact terminal loss.
4. Current payable attack, KO, and Prize conversion.
5. Current-attacker survival, public return Prizes, attack count, board and
   backup continuity.
6. Next-attacker readiness and next-Prize timing.
7. Hand/resource conservation, including moving Jumbo from hand to discard.

A lower layer cannot compensate for damage at a higher layer.

## Directions

- `PLAY_ICE`: the heal world strictly dominates at the first hard layer and a
  deterministic current Jumbo action is emittable.
- `HOLD_ICE`: the no-heal world strictly dominates, the parent selected Jumbo,
  and the complete no-heal continuation has one current first action.
- `APPROVE_PARENT_ICE`: the parent already selected the certified heal.
- `EQUAL`: no higher-layer boundary; preserve the exact parent.
- `REJECT`: hidden information, incomplete return graph, multiple
  nondominated plans, owner collision, stale state, unsupported effect, or an
  unemittable route.

No opponent identifier, matchup threshold, inferred attack legality,
hidden-hand assumption, or Archaludon-ex-only restriction may participate.

## Frozen inputs

- Parent `main.py`:
  `558EE5DB29E001428B0D59813613FABEE8E15B96E422746C104BDFAB4DC22DB6`
- Deck:
  `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`
- Source manifest:
  `90A512D5C9AE5EAD8DF92F370C32716959EC0929F9465451E7BB0926DBEB5A68`
- Corpus: 207 replays, 209 target seats, 25,880 callbacks.
- Historical control: 92 physical Jumbo PLAY records, 82 unique turns, both
  seats.

Runner/output hashes remain pending until execution and must not be invented.

## Required output

- `freeze_pre_edit_jumbo_ice_cream_actionability_census.py`
- `pre_edit_jumbo_ice_cream_actionability_census_raw/opportunity_rows.csv`
- `pre_edit_jumbo_ice_cream_actionability_census_raw/summary.json`

Each row binds replay/hash, seat/step/turn/snapshot, parent action and owners,
Jumbo roles/serials, Active HP/Energy, exact no-heal and heal plan sets, actual
attack roles, selected best plans, first hard comparison, complete first
action, purpose, direction, and rejection reason.

## Mandatory implement/stop gate

Integrity:

- exact 207/209 corpus and 25,880 single parent calls;
- zero invalid actions or manifest mismatches;
- exactly 92 physical Jumbo plays and 82 unique turns, both seats;
- unique `(replay, seat, step, turn, snapshot_hash)` rows;
- exact Jumbo metadata and actual engine attack options.

Actionability, counting only the earliest independent callback per turn:

- at least 24 strict two-world classifications, both seats and at least 12
  replays;
- at least 16 uniquely emittable actionable turns, both seats and at least 8
  replays;
- at least 10 predicted first differences, both seats and at least 6 replays;
- at least three `PLAY_ICE` and three `HOLD_ICE`, each direction in both seats;
- at least three independent `SURVIVAL_OR_PRIZE_CLOCK` turns and three
  `RAGING_HAMMER_KO_PRESERVATION` turns;
- every predicted difference root-audited `GOOD_CAUSAL`;
- zero hidden-information, unknown-as-zero, owner-overlap, stale,
  duplicate-advancement, or unemittable-route evidence.

Passing every gate conditionally authorizes one isolated implementation from
the exact parent.  Failing any gate stops the hypothesis as
`RARE_NARROW/NO_ACTIONABLE_BOUNDARY`; thresholds may not be relaxed.

Any later implementation must pass the established immutable Silver200 plus
adjacent560, exact 760-row gate and its frozen strength/seat/block/trace floors.
