# Sol-Ultra numerical audit - return relevance census v1

## Verdict

**FAIL.  Required decision: `STOP__RETURN_UNKNOWN_NOT_ONE_ACTIONABLE_BOUNDED_CAUSE`.**

`RELEVANCE_BOUND_PUBLIC_RETURN_COMPLETENESS_V1` does not meet the frozen
implement gates.  At the independent-turn level the shadow converts only 5 of
75 independent targeted turns from baseline `RETURN_UNKNOWN` to fully exact (5 gains, 0
losses), versus the required 24 turns.  It produces 0 hard plan-ranking
differences, 0 predicted legal first-action differences, and 0 qualifying hard
layer differences.  The bounded family also reaches only 37 earliest
independent callbacks (33 containing unique exact provenance), versus 40
required.

The positive exactness delta is not evidence of policy strength: it never
changes a hard ranking or predicted first action in this census.  No source edit,
candidate implementation, promotion, or Kaggle action is authorized.

## Frozen scope, artifacts, and assumptions

- Contract:
  `STRATEGY_SELECTION_RETURN_RELEVANCE_V1.md`, SHA-256
  `B4ED651CD03D033FCCEDDA481A2D8636C41F328E7C3A8814C2844BF5AE710731`.
- Baseline parent:
  `autonomous_gold_20260715/candidates/archaludon_purpose_first_pokegear_boss_transaction_v1/main.py`,
  SHA-256
  `558EE5DB29E001428B0D59813613FABEE8E15B96E422746C104BDFAB4DC22DB6`.
- There is no separate candidate source.  Baseline and shadow are paired calls
  to the same parent through
  `freeze_pre_edit_return_relevance_cause_census.py`, with local-no-route
  suppression disabled/enabled.  Runner SHA-256:
  `E6F65CFE8DCC247988EE86A56DBB60C2102973F3E4C6345579ECB38F7ACBEFC0`.
- Raw cause rows:
  `pre_edit_return_relevance_cause_census_raw/cause_rows.csv`, SHA-256
  `78C16DDBFE1BA27BB9701781CDFFF011719ECA8BBFC0CD4EB397453AB30ED2DA`.
- Raw shadow rows:
  `pre_edit_return_relevance_cause_census_raw/shadow_plan_rows.csv`, SHA-256
  `72C30B7D76BB8D5E2032208575007F5B26701A5D47C63378F6FA47E7F4585ADA`.
- Runner summary (comparison only, not numeric authority):
  `pre_edit_return_relevance_cause_census_raw/summary.json`, SHA-256
  `6AB7D5EC7D02E4C490A71B7A4FABF01F2753FE1F9A0A0BDD5694DF5AC0195999`.
- An independent callback has decoded `pre_call_owners == {}`, following the
  frozen workflow's prior independent-callback rule.  An independent turn is
  `(replay, seat, turn)` with at least one such callback; its evidence row is
  the minimum numeric `step` among those callbacks.  One raw target turn has no
  independent callback and is excluded.  A cause is counted once per
  independent turn.  A blocker has exact provenance only when
  `matched_event_count == 1` and its source, zone, metadata, tier, and sequence
  fields are present.
- A fully exact turn requires every persisted attack alternative at every
  targeted callback in that turn to be `EXACT`.  In these rows the looser
  "any-alternative exact" definition happens to give the same 5 turns.
- Null `predicted_first_roles` means no predicted role, not an unemittable role.
- This is a state census, not a battle schedule.  It has no `result`, opponent,
  engine-seed, or player-A/player-B columns.  W-L, policy-to-player mapping,
  battle seat deltas, seed sensitivity, and identical-policy controls are not
  applicable.  The applicable duplicate control is exact raw-key uniqueness;
  no separate duplicate-run artifact was supplied.

## Reproducible calculation

All repository Python reads used `.venv-rl\Scripts\python.exe` and did not call
the agent or rerun the census.  SHA-256 was recomputed from file bytes.  The
207-entry manifest and source replay JSON were read directly to reconstruct the
selectable callback keys.

The persisted keys and groupings were recomputed as follows:

```text
cause_key  = (replay, seat, step, snapshot_sha256, attack_id, blocker_index)
shadow_key = (replay, seat, step, snapshot_sha256, attack_id)
turn_key   = (replay, seat, turn)
independent_callback = (json(pre_call_owners) == {})
earliest(turn_key) = minimum(step among independent_callback rows)

exact_turn = all(shadow_status == "EXACT" for every row in turn_key)
hard_turn  = any(first_hard_difference is nonempty in turn_key)
pred_turn  = any(predicted_first_difference == True in turn_key)
```

For the paired exactness effect, each target turn is baseline-unknown by
construction.  The estimate is therefore `(shadow exact - baseline exact) / 75
= 5/75`.  A replay-cluster percentile bootstrap (48 replay clusters, 200,000
resamples, seed `20260801`) gives a descriptive 95% interval of
**+1.47 to +13.75 percentage points** around the observed **+6.67 pp**.  The
corpus is frozen and opportunity-selected, so this interval is not a strength
or generalization claim.

## Integrity recomputation

| Check | Independent result | Audit status |
|---|---:|---|
| Manifest replays / replay-seat pairs | 207 / 209, all unique as specified | Pass |
| Manifest replay hash mismatches | 0 | Pass |
| Selectable callback rows / unique full keys | 25,880 / 25,880 | Pass |
| Callback keys by seat | seat 0: 13,709; seat 1: 12,171 | Pass |
| Frozen target callbacks / attack alternatives | 225 / 254 | Pass |
| Target callbacks by alternative count | 196 with one; 29 with two | Pass |
| Shadow full keys | 254 / 254 unique | Pass |
| Cause full keys | 819 / 819 unique | Pass |
| Shadow target-set or snapshot mismatch vs frozen Jumbo rows | 0 | Pass |
| Cause sequence mismatch vs each raw `baseline_unsupported` list | 0 | Pass |
| Target-row baseline status | 254/254 `RETURN_UNKNOWN` | Pass |
| Target-row parent validity / nonempty error lists | 254/254 valid; 0 errors | Pass for persisted targets |
| Full 25,880-call parent-action validity | Only aggregate `summary.json` says 0 invalid; no per-call ledger was persisted | Not independently auditable |

The persisted target rows are internally complete and uniquely keyed.  The
full-call validity subgate is not independently reproducible from the raw CSVs:
the CSVs contain the 225 targets, not all 25,880 parent calls.  A read-only replay
scan proves the callback total and key uniqueness but cannot prove the parent
action returned at each omitted callback without rerunning, which this audit did
not do.

## Cause coverage and exact provenance

The raw targets contain 76 turn keys in 49 replays.  One singleton callback has
nonempty `pre_call_owners`, leaving 75 independent target turns in 48 replays.
Forty-five independent turns contain multiple targeted callbacks (2 to 18
callbacks), so counting rows or all callbacks as independent would be invalid.

| Cause class | Rows | Union turns / replays | Earliest independent turns (seat 0 / seat 1) / replays | Earliest independent turns containing a unique-provenance row (seat 0 / seat 1) / replays |
|---|---:|---:|---:|---:|
| `EXACT_LOCAL_NO_ROUTE` | 240 | 39 / 31 | 37 (18 / 19) / 30 | 33 (15 / 18) / 28 |
| `GLOBAL_TARGET_OR_UNCERTAIN_EFFECT_SCOPE` | 517 | 59 / 36 | 57 (31 / 26) / 35 | 30 (16 / 14) / 26 |
| `REACHABLE_FREE_PROMOTION_OR_RETREAT` | 18 | 11 / 10 | 8 (3 / 5) / 7 | 8 (3 / 5) / 7 |
| `REACHABLE_PUBLIC_EVOLUTION_OR_SWITCH` | 1 | 1 / 1 | 1 (1 / 0) / 1 | 0 (0 / 0) / 0 |
| `REACHABLE_READY_NOW` | 43 | 12 / 10 | 12 (8 / 4) / 10 | 12 (8 / 4) / 10 |
| `REACHABLE_AFTER_ONE_ATTACHMENT` | 0 | 0 / 0 | 0 (0 / 0) / 0 | 0 (0 / 0) / 0 |
| `POST_ACTION_PROJECTION_OR_CALLBACK` | 0 | 0 / 0 | 0 (0 / 0) / 0 | 0 (0 / 0) / 0 |
| `BACKUP_OR_NONUNIQUE_REPLY_FAILURE` | 0 | 0 / 0 | 0 (0 / 0) / 0 | 0 (0 / 0) / 0 |

The runner's 39-turn bounded-cause count is the union over every callback in a
turn.  Selecting the minimum raw callback gives 38; applying the contract's
owner-empty independent-callback rule gives 37.  Counting only rows with an
exact one-event provenance gives an optimistic upper bound of 33 turns (a turn
qualifies here if it contains at least one such row).  All variants miss the
40-turn threshold; seat and replay breadth alone do pass.

Blocker matching is not exact:

- 469/819 rows (57.26%) have exactly one matched event;
- 263/819 (32.11%) have multiple matched events;
- 87/819 (10.62%) have no matched event;
- consequently 350/819 (42.74%) have no single source identity or complete
  per-route metadata in the direct columns.

Within `EXACT_LOCAL_NO_ROUTE`, 179 rows are unique and suppression-eligible,
while 61 are ambiguous (52 match two events and 9 match three).  Within
`GLOBAL_TARGET_OR_UNCERTAIN_EFFECT_SCOPE`, 229 are unique, 202 ambiguous, and
86 unmatched.  The sole public-evolution/switch row is unmatched.

For all 469 uniquely matched rows, the persisted card metadata parses, its
`card_id` matches `source_id`, and attack/skill text hashes are present.  That
does not repair the other 350 rows.  In addition, neither CSV schema preserves
the contract-required **current attack payment/allocation**; it records only
ready attack IDs and possible one-attachment IDs/types.  Thus the required
"every blocker assigned exactly once with exact metadata provenance" gate
fails independently of the downstream count gates.

This exposes an optimistic runner defect: `summary.json` reports
`blocker_assignment: true` because its implementation checks only that the row
count matches and every row contains an allowed enum.  It does not require
`matched_event_count == 1`, complete provenance, or current-payment evidence,
despite separately reporting 263 ambiguous and 87 unmatched rows.

## Shadow exactness, decisions, and floors

| Frozen gate | Recomputed result | Requirement | Result |
|---|---:|---:|---|
| Bounded cause, earliest independent | 37 turns, both seats, 30 replays | >=40 turns, both seats, >=15 replays | **Fail** |
| Bounded cause containing exact provenance | at most 33 turns, both seats, 28 replays | same | **Fail** |
| Fully exact | 5 turns, both seats, 5 replays | >=24 turns, both seats, >=12 replays | **Fail** |
| Hard plan-ranking differences | 0 turns, 0 seats, 0 replays | >=12 turns, both seats, >=8 replays | **Fail** |
| Predicted legal first-action differences | 0 turns, 0 seats, 0 replays | >=8 turns, both seats, >=6 replays | **Fail** |
| Qualifying first-hard layer classes | 0 classes; no first-hard layers | >=3 differences in at least 2 classes | **Fail** |
| Root `GOOD_CAUSAL` marks | no predicted differences; raw status is `PENDING` | every predicted difference marked | Not an authorization |

The exactness transition is 13/254 attack alternatives and 13/225 callbacks,
but those collapse to only 5/75 independent turns (6.67%).  There are 5 paired
turn gains and 0 losses.  All alternatives in those five turns are exact, so
the five-turn figure is not an any-vs-all artifact.  Seat splits are:

- seat 0: 3/40 turns exact (7.50%);
- seat 1: 2/35 turns exact (5.71%), the absolute seat floor.

The recurring floor is severe: 241/254 raw alternatives (94.88%) and 70/75
independent turns (93.33%) remain `RETURN_UNKNOWN`.  The global/uncertain family alone accounts
for 517/819 blocker rows and 58 earliest turns.  No favorable aggregate should
hide the 0 hard differences and 0 action differences.

The 13 exact alternative rows change seven compact fields from unknown to
known (`certain_return_prizes`, `certain_terminal_reply`,
`chosen_public_reply`, `current_attacker_survival`,
`next_turn_payable_attack`, `exact_backup_ready`, and
`exact_backup_next_prizes`).  Current KO/prize values do not change.  These
field exactifications are not hard lexicographic differences and cannot be
credited toward the two-layer gate.

## Suppression and qualitative safeguards

The raw shadow rows contain 272 suppressed route-event instances: 116
`READY_NOW` and 156 `ONE_ORDINARY_ATTACH`, across both seats.  Internal raw
checks find:

- 0 suppressed events with nonempty `analysis.relevant`;
- 0 with non-exact route analysis, unsafe local scope, a non-`None` original
  route, false eligibility/suppression flags, or missing source/target identity;
- 0 one-attachment events with a payable attack ID or nonempty Basic Energy
  type set.

Thus **zero relevant-route suppression is supported by the runner's own route
analysis columns**, and no positive hidden-Energy assumption is visible there.
It is not an independent card-semantics proof because current payments are not
persisted.

All 13 exact alternative rows (5 turns) assert an exact
`no_exact_public_attack_reply`, zero return prizes, and current-attacker
survival.  Six of the 13 rows, spanning two of the five earliest turns, also
contain at least one ambiguously matched blocker.  The raw files contain no
independent reply oracle, so the required zero-false-terminal-certificate claim
cannot be certified numerically; it remains a root qualitative check.  There
are no predicted roles at all, hence 0 observed unemittable predicted roles but
also no emittability opportunity.

## Final recommendation

Reject the hypothesis at this frozen gate.  The result is not borderline:
provenance is incomplete, the bounded family misses even before provenance is
required, exact coverage is 5 versus 24 turns, and every decision-impact gate
is zero.  Retain the parent unchanged and apply the contract's fixed stop
decision without relaxing thresholds or expanding the matrix.
