# v4 C2–C5 strategy-judge binding amendment

Date: 2026-07-30

This amendment is binding on every implementation and evaluation derived from
the following frozen specifications.  The original files remain immutable.

| Stage | Frozen specification | SHA-256 |
|---|---|---|
| C2 | `v4_c2_next_attacker_distance_shadow_fix4_immutable_spec.md` | `096AC9F8C968A5BE645ECE87119241B1965C9110433E4872721881F16956FFE9` |
| C3 | `v4_c3_public_survival_bench0_fix5_immutable_spec.md` | `1585C9FC7BEB326E2F496AC8B35D99E5B75A976F0F69C7A8B7492671E7B73B5F` |
| C4 | `v4_c4_wall_shadow_fix6_immutable_spec.md` | `F6BFEA318FC245543BDB8043D4FF0E8D60CD9A476403FA3E52993EF35CB2859B` |
| C5 | `v4_c5_strict_wall_action_fix7_decision_contract.md` | `E62135D0D430715D4AD4B955723870D544E5BD02426AAFF7117CAF62A8218F46` |

## 1. Separate projected states

C3 must calculate two independent projected states:

- `PARENT_POST_STATE`: the exact public state after the parent's proposed
  `ATTACK` or `END`.
- `CANDIDATE_POST_STATE`: the exact public state after playing the candidate
  Basic and then executing the same parent attack.

The board-out threat must remain certified in both projections.  If the parent
attack removes, switches, disables, or otherwise changes the threatening
attacker, and the continuation cannot be projected exactly, C3 retains the
parent action.

C4 and C5 must calculate two different projections:

- `EXPOSE_STATE`: the exact public state after the parent promotion, Run Away,
  or Trading Places choice exposes the protected line.
- `WALL_STATE`: the exact public state after the wall alternative.

Threat to the protected line is certified only in `EXPOSE_STATE`.  Wall
survival, public bypass, opponent refusal, progress, and release are certified
only in `WALL_STATE`.  A current-state value must not be reused as either
projection.

## 2. UNKNOWN dominates unproven IMPOSSIBLE

C2 route reduction is:

```text
if any route is CERTIFIED:
    CERTIFIED
else if any route is POSSIBLE:
    POSSIBLE
else if any plausible route is unresolved or unsupported:
    UNKNOWN
else:
    IMPOSSIBLE
```

`IMPOSSIBLE` requires complete enumeration of every supported route.  Numeric
ordering must never prefer `IMPOSSIBLE` to unresolved `UNKNOWN`.  The same
taint rule applies when recomputing a line after removal and when deriving
`UNKNOWN_IMPORTANCE`.

## 3. Deterministic Run Away draw value

Successful Run Away with at least three cards in deck produces an exact
hand-count increase of three.  Powerful Hand therefore gains a certified
`+60` before subtracting any deterministic card expenditures in the projected
route.

Unknown identities of the three cards cannot certify evolution, search, or
switch routes.  They do not make the hand-count damage unknown.

Run Away outranks a strict wall only when an exact projected route:

1. wins the game immediately;
2. KOs the current repeatable threat; or
3. achieves an explicitly certified safe prize exchange.

A merely legal damaging attack is insufficient.  Before suppressing Run Away,
all exact post-Run-Away promotion choices must be evaluated, including another
certified wall.

## 4. Premium Power Pro multiplicity

Card ID `1141` must have a frozen, source-backed multiplicity rule before C3
or wall-survival code relies on a cap.

- `evidenced_policy_cap` is the largest supported damage based on same-battle
  public evidence and exact public archetype evidence.  C3 may use it only for
  its chance-based board-out comparison.
- `safety_cap` is the largest damage from every legally stackable supported
  boost still possible from public information.  If this cannot be bounded
  exactly, it is `UNKNOWN`.

`CERTIFIED_REUSABLE_WALL` requires `wall_hp > safety_cap`.  It must not use the
smaller policy cap.  If several copies of `1141` can legally stack, one
evidenced `+30` is not a survival certificate.

Until the multiplicity audit is complete, all affected reusable-wall
certificates fail closed.

## 5. Non-rolling refusal and release witnesses

Only a current-hand C2 `CERTIFIED` route may prove refusal progress or safe
release.  An ordinary draw/search whose contents are unknown remains
`POSSIBLE`.

At wall entry, freeze:

```text
hold_deadline = entry_turn + initial_certified_turn_delay
```

The deadline never rolls forward.  Protected-line distance must strictly
improve on each held turn; otherwise the strict certificate expires.  Safe
release is evaluated from the exact projected post-attack board and opponent
continuation, not merely from the existence of a completed Alakazam.

## 6. Single-change stage boundaries

- If C3's action-changing candidate is rejected, C4 may inherit only a
  side-effect-free analyzer whose C3 action gate is provably disabled.
- C5 action points A, B, and C are implemented and evaluated one at a time.
- Combining accepted action points creates a new candidate requiring
  pairwise transaction fixtures and the full immutable evaluation.
- Run Away suppression at action point B must account for any enabled
  post-Run-Away promotion behavior from action point A.
- `PRESERVE_CHANCE_WALL` remains shadow-only in every C5 candidate.

## 7. Reusable versus sacrifice wall

Reusable-wall class does not automatically dominate sacrifice-wall class.
Dominance is certified only if the reusable wall:

1. survives `safety_cap`;
2. needs no more hold turns;
3. has a certified release;
4. loses no terminal or current-threat-KO conversion; and
5. has no worse public bypass or final-Prize outcome.

Without this proof, compare both candidates explicitly and retain the parent
action when the ordering is not certified.

## 8. Required trace additions

The combined analyzer trace must include:

```text
parent_post_fingerprint
candidate_post_fingerprint
expose_state_fingerprint
wall_state_fingerprint
certified_draw_count
certified_draw_damage_delta
premium_power_pro_multiplicity
evidenced_policy_cap
safety_cap
hold_entry_turn
hold_deadline
distance_progress_by_turn
```

## 9. Required focused fixtures

In addition to each frozen specification's fixtures:

1. Parent attack removes the threat, so C3 does not bench.
2. Exact Run Away draw three gives `+60` and converts Powerful Hand into a
   current-threat KO.
3. A non-KO damaging attack does not outrank a strict wall.
4. Threat is certified in `EXPOSE_STATE` while survival is certified in
   `WALL_STATE`.
5. The hold deadline does not roll.
6. C5 action points A and B compose correctly at Run Away and promotion.
7. Stackable and non-stackable `1141` semantics use different caps.

## 10. Episode-specific expectations

For episode `88843743`:

- Before Run Away, Dudunsparce's survival is logged but Run Away is not
  suppressed by C3.
- Hilda remains the parent choice at the next public state.
- At the later Bench-0 state, Shaymin is inserted only if
  `PARENT_POST_STATE` and `CANDIDATE_POST_STATE` both retain the public
  board-out threat and the parent attack remains exactly unchanged.

For episode `88844273`, all four fixed public observations remain mandatory
fixtures.  No replay identity, episode ID, opponent name, or hidden card is an
allowed production trigger.
