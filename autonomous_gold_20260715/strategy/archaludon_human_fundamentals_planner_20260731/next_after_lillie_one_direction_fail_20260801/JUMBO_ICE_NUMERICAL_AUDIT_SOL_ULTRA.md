# Jumbo Ice Cream v1 pre-edit numerical audit

## Decision

**FAIL / STRICT STOP BEFORE IMPLEMENTATION.** Under the frozen contract's
required earliest-independent-callback rule, the census has 19 strict
two-world turns, **0 actionable turns, 0 predicted first differences, 0
`PLAY_ICE`, and 0 `HOLD_ICE`**. It therefore fails every numerical
actionability floor except seat/replay coverage within the strict subset. The
required disposition is `RARE_NARROW/NO_ACTIONABLE_BOUNDARY`; the frozen
thresholds must not be relaxed and no Jumbo candidate is conditionally
authorized.

This is a pre-edit replay census, not a candidate-versus-baseline battle
evaluation. W-L, win rate, paired uncertainty, seat/seed battle sensitivity,
and battle duplicate controls are not applicable, and no policy-strength
claim is made from any positive callback count.

## Frozen artifacts

All hashes were independently recomputed from the files read on 2026-08-01.

| Artifact | SHA-256 |
|---|---|
| `pre_edit_jumbo_ice_cream_actionability_census_raw/opportunity_rows.csv` | `093573F0C9D5E47EF6EA5E8277E6DD137078D06C07FC20BF8241606B14CCB1D9` |
| `pre_edit_jumbo_ice_cream_actionability_census_raw/summary.json` | `BB38450572DD285FEDAD3B79616CDEE22A0A32AC626111038605CE2239EF085C` |
| `STRATEGY_SELECTION_JUMBO_ICE_CREAM_V1.md` | `53E50964F76F2CB16A6F67D1276D93DEE86991CFB07C1464D6EC9E1B3F3DEADF` |
| `freeze_pre_edit_jumbo_ice_cream_actionability_census.py` | `3441E6DFA25140E9C70CABB58E9F36CF3DF76FCD25B3B36311590FA83CF9EF8B` |
| frozen parent `main.py` | `558EE5DB29E001428B0D59813613FABEE8E15B96E422746C104BDFAB4DC22DB6` |
| frozen parent `deck.csv` | `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A` |
| source manifest | `90A512D5C9AE5EAD8DF92F370C32716959EC0929F9465451E7BB0926DBEB5A68` |

The immutable schedule is the 207-entry source manifest and its 209 target
seats. The runner output directory is
`pre_edit_jumbo_ice_cream_actionability_census_raw`. No census, battle, or
simulation was rerun or expanded, and no runner output was altered.

## Definitions and assumptions

- A raw key is `(replay, seat, step, turn, snapshot_sha256)`.
- A turn key is `(replay, seat, turn)`.
- An independent callback is a row with decoded `owner_state == {}`. For each
  turn, gate evidence is the minimum-step independent callback only. One of
  159 opportunity turns has no independent callback and is excluded.
- A strict classification has a non-null same-row world comparison and an
  output direction in `PLAY_ICE`, `HOLD_ICE`, `APPROVE_PARENT_ICE`, or
  `EQUAL`.
- Actionable means output direction `PLAY_ICE` or `HOLD_ICE` with
  `uniquely_emittable == True`; predicted means
  `predicted_first_difference == True`.
- Purpose floors are counted only on those actionable earliest rows, matching
  the runner's intended purpose-set admission.
- The summary's global invalid-action count is frozen-runner evidence. This
  audit independently checked the 483 recorded parent actions and their
  current option-role bindings, but did not call the parent agent 25,880
  times again.
- `GOOD_CAUSAL` is a root qualitative label. The supplied schema contains no
  such audit field, so it is not inferred.

## Integrity recomputation

| Check | Independent result | Status |
|---|---:|---|
| Manifest entries / unique replay names | 207 / 207 | PASS |
| Target seats | 209 total: seat 0 = 108, seat 1 = 101 | PASS |
| Missing replay / replay-hash / step-count mismatch | 0 / 0 / 0 | PASS |
| Select callbacks matching runner admission | 25,880: seat 0 = 13,709, seat 1 = 12,171 | PASS |
| Invalid actions in CSV / global frozen summary | 0 / 483; 0 / 25,880 | PASS on stated evidence |
| Physical Jumbo PLAY records / unique turns | 92 / 82 | PASS |
| Historical turn coverage | 68 replays; seat 0 = 35 turns, seat 1 = 47 | PASS |
| CSV historical-flag mismatches | 0 / 483 | PASS |
| Raw rows / unique raw keys | 483 / 483; duplicates = 0 | PASS |
| Replay/seat/step/turn/snapshot binding mismatches | 0 / 483 | PASS |
| Exact Jumbo metadata | card 1147, exact name and skill text; metadata SHA `4AF7D9412473B3898465BADD4FEC450ADBC3C2B08AFCD0DA5775265D19F67E20` | PASS |
| Current legal Jumbo role/serial bindings | 0 mismatches; 386 rows have 1 option, 94 have 2, 3 have 3 | PASS |
| Actual engine attack-option bindings | 0 mismatches; 360 rows expose attack 253, 123 expose attacks 223 and 224 | PASS |
| Active HP/Energy/effective-heal equations | 0 violations; every row is damaged and has at least 3 Energy | PASS |

The replay log control used exact `LogType.PLAY == 10`; other log types were
not counted. Effective heal was independently recomputed as
`min(80, max(0, max_hp - hp))`.

## Callback deduplication and census counts

The 483 rows cover 159 turns in 95 replays (85 seat-0 turns, 74 seat-1
turns). Ninety-two turns have multiple opportunity callbacks, yielding 324
callbacks beyond one per turn; the maximum is 21. Five turns contain
conflicting output directions. There are also 45 repeated-snapshot callbacks
across 7 turns. Row-key uniqueness therefore does not establish independent
turn evidence.

The frozen summary uses a set union over **any** qualifying callback in a turn;
it does not select the earliest independent callback. Its reported union and
the contract-correct result are:

| Scope | Frozen any-callback union | Earliest independent callback |
|---|---:|---:|
| Strict turns / replays / seats | 20 / 18 / both | **19 / 17 / both** (seat 0 = 9, seat 1 = 10) |
| Actionable turns / replays / seats | 1 / 1 / seat 1 | **0 / 0 / none** |
| Predicted turns / replays / seats | 1 / 1 / seat 1 | **0 / 0 / none** |
| `PLAY_ICE` | 1 | **0** |
| `HOLD_ICE` | 0 | **0** |
| `APPROVE_PARENT_ICE` | 5 | **2** |
| `EQUAL` | 19 | **17** |
| `REJECT` | 140 | **139** |

The sole raw `PLAY_ICE` is
`episode_88293552_replay.json`, seat 1, turn 9, step 84. The same turn's
earliest independent callback is step 83 and is `EQUAL`; step 85 is
`APPROVE_PARENT_ICE`. Thus the raw PLAY callback is not independent gate
evidence.

Among all 54 raw comparable rows, independently reconstructed world
comparisons are 40 `EQUAL`, 8 heal-disfavored, and 6 heal-favored. All 8
heal-disfavored comparisons become output `EQUAL` because the parent did not
select Jumbo; none supplies the contract's required emittable `HOLD_ICE`
alternative. On earliest independent rows, the underlying comparisons are 16
equal, 1 heal-disfavored, and 2 heal-favored, but the two heal-favored rows are
parent approvals. Consequently both actionable purpose counts are zero.

## Rejections and the 423-row question

Raw rejection categories reproduce exactly:

| Rejection | Rows | Unique turns | Replays | Seat-turn coverage |
|---|---:|---:|---:|---|
| `no_heal:no_fully_rankable_plan` | 423 | 138 | 82 | seat 0 = 75, seat 1 = 63 |
| `no_heal:multiple_nondominated_best_plans` | 2 | 2 | 1 | seat 0 only |
| `live_owner_collision` | 4 | 4 | 4 | both seats |

**The 423 rows are not produced by a `plan_layers` runner defect.** Every one
contains zero retained exact no-heal plans; no exact plan was present and then
dropped because of a mistaken field test.

- 225 rows (254 exposed attack alternatives) report only
  `RETURN_UNKNOWN`. Rehydrating those stored observations through the frozen
  deterministic plan helper reproduced all 254 statuses. Each has exactly the
  same five uncertified fields:
  `certain_terminal_reply`, `certain_return_prizes`,
  `current_attacker_survival`, `next_turn_payable_attack`, and
  `exact_backup_ready`. This is factual absence of a complete exact public
  return/backup certificate in the frozen planner, not unknown-as-zero.
- 198 rows (277 attack alternatives) report only `unavailable`. Frozen-code
  diagnostics split these into 128 rows / 173 alternatives with an
  unsupported public stadium and 70 rows / 104 alternatives whose current
  combat oracle is unknown because of unsupported public skills/tools. These
  fail before a return/backup plan exists.

Therefore “missing exact return/backup fields” precisely describes the 225
`RETURN_UNKNOWN` rows, while the other 198 are earlier exact-plan coverage
failures. Both are mandated conservative `REJECT` outcomes under the frozen
contract's incomplete-graph/unsupported-effect rule. The separate runner
defect is only the summary's any-callback turn aggregation; correcting that
aggregation worsens actionability from 1 to 0 and cannot authorize an edit.

The two nondominated rejections each contain two exact no-heal plans tied at
every hard layer. Choosing either would violate the unique-plan requirement.

## Owner and route invariants

- All 4 nonempty owner rows are exactly the 4 `live_owner_collision`
  rejections; none emits a candidate role, queue, actionable flag, or
  predicted difference. All carry `_cum_active_transaction_owner` and
  `_cum_owner_meta`; one also carries `_h6_transaction`.
- All 6 emitted play routes (5 parent approvals and 1 raw PLAY) bind the same
  row's selected minimum Jumbo serial, then the same row's chosen exact attack
  ID and current engine attack role. Violations: 0.
- Accepted/rejected direction semantics, selected-world uniqueness,
  first-hard-layer reconstruction, current option membership, queue shape,
  parent-role binding, and stale/unemittable route checks have 0 violations.
- No `HOLD_ICE` queue exists. Rejected unknowns and owner collisions are not
  used as actionable evidence.

## Frozen mandatory gate

| Requirement | Contract-correct observed value | Result |
|---|---:|---|
| 207/209 corpus; 25,880 calls; zero invalid/mismatch | 207 / 209 / 25,880; zero | PASS on stated evidence |
| 92 physical plays; 82 turns; both seats | 92 / 82; both | PASS |
| Unique raw keys; exact metadata and actual attack options | 0 duplicates; 0 option/metadata mismatches | PASS |
| At least 24 strict turns, both seats, at least 12 replays | **19**, both seats, 17 replays | **FAIL** |
| At least 16 uniquely emittable actionable turns, both seats, at least 8 replays | **0**, no seats, 0 replays | **FAIL** |
| At least 10 predicted first differences, both seats, at least 6 replays | **0**, no seats, 0 replays | **FAIL** |
| At least 3 PLAY and 3 HOLD; each in both seats | **0 PLAY / 0 HOLD** | **FAIL** |
| At least 3 `SURVIVAL_OR_PRIZE_CLOCK` and 3 `RAGING_HAMMER_KO_PRESERVATION` actionable turns | **0 / 0** | **FAIL** |
| Every predicted difference root-audited `GOOD_CAUSAL` | No supplied audit field; sole later raw prediction not demonstrated | NOT DEMONSTRATED |
| Zero forbidden evidence in admitted actionable routes | 0 admitted routes and 0 route violations; unknown/owner cases rejected | PASS, vacuous |

Because every gate must pass, the numerical failures require an unconditional
pre-edit STOP regardless of the unresolved qualitative audit.

## Reproducible calculation

All repository Python reads used `.venv-rl\Scripts\python.exe`. The core CSV
calculation was:

```python
import csv, json
from collections import defaultdict
from pathlib import Path

rows = list(csv.DictReader(Path(CSV_PATH).open(encoding="utf-8", newline="")))
row_key = lambda r: (
    r["replay"], int(r["seat"]), int(r["step"]), int(r["turn"]),
    r["snapshot_sha256"],
)
turn_key = lambda r: (r["replay"], int(r["seat"]), int(r["turn"]))

assert len(rows) == 483
assert len({row_key(r) for r in rows}) == 483

groups = defaultdict(list)
for row in rows:
    groups[turn_key(row)].append(row)

earliest = {}
for key, group in groups.items():
    independent = [r for r in group if json.loads(r["owner_state"]) == {}]
    if independent:
        earliest[key] = min(independent, key=lambda r: int(r["step"]))

strict = [r for r in earliest.values() if r["direction"] in {
    "PLAY_ICE", "HOLD_ICE", "APPROVE_PARENT_ICE", "EQUAL"
} and r["first_hard_difference"] not in ("", "null")]
actionable = [r for r in earliest.values() if r["direction"] in {
    "PLAY_ICE", "HOLD_ICE"
} and r["uniquely_emittable"] == "True"]
predicted = [r for r in earliest.values()
             if r["predicted_first_difference"] == "True"]

assert (len(strict), len(actionable), len(predicted)) == (19, 0, 0)
assert sum(r["direction"] == "PLAY_ICE" for r in earliest.values()) == 0
assert sum(r["direction"] == "HOLD_ICE" for r in earliest.values()) == 0
```

Manifest verification separately rehashed all 207 replay files, checked
manifest step counts, counted callbacks using
`current.yourIndex == seat and select is not None`, reconstructed sorted-JSON
snapshot hashes, and recomputed log controls. Frozen-code diagnostics only
rehydrated the already-recorded 423 observations to identify deterministic
plan rejection causes; they did not advance games or create new result rows.
