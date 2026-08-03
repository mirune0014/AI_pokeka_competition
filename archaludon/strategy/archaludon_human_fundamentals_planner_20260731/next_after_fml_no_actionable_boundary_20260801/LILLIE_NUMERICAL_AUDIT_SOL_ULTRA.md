# Purpose-bound Lillie v1 pre-edit numerical audit

## Decision

**FAIL / STOP BEFORE IMPLEMENTATION.** The frozen census reproduces 346 uniquely
deduplicated actionable and predicted `PLAY_LILLIE` turns, but it contains
**0 `HOLD_LILLIE` turns and 0 protected HOLD roles**. Therefore it fails two
non-relaxable gates in `STRATEGY_SELECTION_LILLIE_V1.md`: at least three HOLD
turns with both seats represented, and at least two distinct protected HOLD
roles. Per the frozen contract, the disposition is
`RARE_NARROW/NO_ACTIONABLE_BOUNDARY`. This audit does not select another
hypothesis.

This is a pre-edit replay census, not a candidate-versus-baseline battle
evaluation. W-L, win rate, paired gain/loss, confidence interval, seed
sensitivity, and battle duplicate-control results are not applicable. No
policy-strength inference is made from the positive PLAY count.

## Frozen artifacts

All supplied hashes matched the files read on 2026-08-01.

| Artifact | SHA-256 |
|---|---|
| `pre_edit_lillie_actionability_census_raw/opportunity_rows.csv` | `42AEBFFF013023C3C90567FD1A69D6EF1BE224B3C377B2BFDFD7E8E74411B73C` |
| `pre_edit_lillie_actionability_census_raw/summary.json` | `847E96B39EBFF6B8202B489B0552CA2B84727FE5B0D3E7310CDDED537055781E` |
| `STRATEGY_SELECTION_LILLIE_V1.md` | `B77AAB1F5033E4827CA31B338388E49AB7E3A23C0ABB2E6385CA93C23FED2797` |
| frozen parent `autonomous_gold_20260715/candidates/archaludon_purpose_first_pokegear_boss_transaction_v1/main.py` | `558EE5DB29E001428B0D59813613FABEE8E15B96E422746C104BDFAB4DC22DB6` |
| frozen parent `deck.csv` | `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A` |
| `next_after_metal_allocation_fail_20260801/night_stretcher_callback_census_raw/source_manifest.json` | `90A512D5C9AE5EAD8DF92F370C32716959EC0929F9465451E7BB0926DBEB5A68` |
| `freeze_pre_edit_lillie_actionability_census.py` | `EFBD7B11D2C3D61454AAABB3FA4AF3989F68943EE99BFEED1D35EA5D30D08DED` |

The immutable replay schedule is the 207-entry source manifest. The runner
output directory is
`pre_edit_lillie_actionability_census_raw`. No runner or simulation was
re-executed, and no matrix was expanded.

## Definitions and assumptions

- A raw row key is exactly `(replay, seat, step, turn, snapshot_sha256)`, as in
  the frozen runner.
- A unique-turn key is exactly `(replay, seat, turn)`.
- `strict purpose` is the union of rows whose direction is `PLAY_LILLIE`,
  `HOLD_LILLIE`, or `APPROVE_PARENT_LILLIE`.
- `actionable` is `PLAY_LILLIE` or `HOLD_LILLIE` with
  `uniquely_emittable == True`; `predicted` is
  `predicted_first_difference == True`.
- Direction categories are mutually exclusive per callback row, but not per
  unique turn. A turn can contain several MAIN callbacks with different board
  states and directions. Direction-specific unique-turn counts therefore
  overlap and must not be summed.
- `LogType.PLAY == 10` was independently read from the frozen parent's bundled
  `cg` API. Historical PLAY coverage was recomputed from replay logs, not from
  the CSV flag.
- The frozen CSV contains parent validity only for the 1,889 Lillie-opportunity
  callbacks. It proves zero invalid parent actions in those rows. The global
  zero across all 25,880 calls is a frozen runner-summary result and was not
  regenerated, because doing so would rerun the parent census.
- `GOOD_CAUSAL` is a qualitative root-audit label. The raw schema has no causal
  audit field; this numerical audit does not invent one.

## Integrity recomputation

| Check | Independent result | Status |
|---|---:|---|
| Manifest entries | 207 unique replay names | PASS |
| Target seats | 209 total: seat 0 = 108, seat 1 = 101 | PASS |
| Replay files missing / SHA mismatches / step-count mismatches | 0 / 0 / 0 across all 207 entries | PASS |
| Select callbacks matching the runner admission rule | 25,880 | PASS |
| Invalid parent actions in opportunity CSV | 0 / 1,889 | PASS |
| Global invalid parent actions | frozen summary = 0 / 25,880 | PASS on frozen runner evidence; not independently rerun |
| Manifest mismatches | 0 independently | PASS |
| Historical Lillie PLAY turns | 256 turns, 153 replays, seats 0 and 1; 128 turns per seat | PASS |
| Historical flag binding | 256 flagged turns; 0 missing, 0 extra | PASS |
| Raw row keys | 1,889 / 1,889 unique; 0 duplicate key instances | PASS |
| `(replay, seat, step)` callback bindings | 1,889 / 1,889 unique | PASS |
| Replay/seat/step/turn/snapshot bindings to source replays | 0 mismatches | PASS |
| Exact Lillie metadata | card 1227, exact name and one exact skill text; metadata SHA `205F3708DC5361350F18790354FD6E91A87C91EFA19099C5809E5CA5979667F4` | PASS |
| Count transform on all rows | 0 violations of draw, shuffle, post-hand, post-deck, or deck sufficiency equations | PASS |

The historical count is specifically the 256 unique turns carrying log type
10. Other log types mentioning card 1227 were excluded, as required.

## Deduplicated census counts

| Scope | Raw rows | Unique turns | Replays | Seat 0 turns | Seat 1 turns | Seats |
|---|---:|---:|---:|---:|---:|---|
| All Lillie-opportunity rows | 1,889 | 646 | 181 | 331 | 315 | 0, 1 |
| Strict purposes, union | 862 | 408 | 167 | 213 | 195 | 0, 1 |
| Actionable, union | 691 | 346 | 157 | 180 | 166 | 0, 1 |
| Predicted first difference | 691 | 346 | 157 | 180 | 166 | 0, 1 |
| `PLAY_LILLIE` | 691 | 346 | 157 | 180 | 166 | 0, 1 |
| `HOLD_LILLIE` | 0 | 0 | 0 | 0 | 0 | none |
| `APPROVE_PARENT_LILLIE` | 171 | 171 | 125 | 83 | 88 | 0, 1 |
| `EQUAL` | 519 | 289 | 136 | 158 | 131 | 0, 1 |
| `REJECT` | 508 | 187 | 85 | 92 | 95 | 0, 1 |

The strict-purpose union is 408 rather than `346 + 171` because 109 turns
contain both a PLAY callback and an APPROVE callback. The counts reproduce the
frozen summary exactly where the summary reports them.

Purpose breakdown:

| Purpose | Raw rows | Unique turns | Replays | Seat 0 turns | Seat 1 turns |
|---|---:|---:|---:|---:|---:|
| `HAND_RENEWAL` | 755 | 346 | 164 | 186 | 160 |
| `DECKOUT_MARGIN` | 107 | 65 | 43 | 28 | 37 |
| HOLD/protected or return-survival purpose | 0 | 0 | 0 | 0 | 0 |

Three turns contain both strict purposes at different callbacks, so the two
purpose turn counts also must not be summed. Within actionable PLAY rows,
`HAND_RENEWAL` contributes 592 rows / 288 turns / 150 replays and
`DECKOUT_MARGIN` contributes 99 rows / 59 turns / 40 replays; one PLAY turn
contains both purposes at different callbacks.

Rejection categories:

| Rejection | Raw rows | Unique turns | Replays | Seat 0 turns | Seat 1 turns |
|---|---:|---:|---:|---:|---:|
| `lillie_first_role_not_unique` | 491 | 173 | 80 | 84 | 89 |
| `live_owner_collision` | 17 | 14 | 11 | 8 | 6 |

## Duplicate callback audit

Row-key uniqueness does not imply turn- or state-level independence:

- 483 of 646 unique turns have more than one Lillie-opportunity callback.
- The 1,889 rows contain 1,243 callbacks beyond the 646 unique-turn keys; the
  maximum is 25 callbacks in one turn.
- PLAY has 691 rows but 346 unique turns, so 345 repeated PLAY callbacks are
  excluded from gate evidence. There are 173 turns with multiple PLAY rows.
- 295 turns contain conflicting directions across callbacks. Of the 346 turns
  containing PLAY, only 92 are PLAY-only across all opportunity callbacks;
  254 also contain APPROVE, EQUAL, or REJECT. Those 92 stable PLAY turns cover
  63 replays and both seats (44 seat 0, 48 seat 1).
- There are 112 exact repeated-snapshot instances across 17 turns even after
  considering `snapshot_sha256`; actionable PLAY contains 41 such instances
  across 6 turns. The maximum identical snapshot repetition is 18.
- Largest turn-level callback repetitions are:
  `episode_88724889_replay.json`, seat 0, turn 4: 25 callbacks (24 PLAY, 1
  EQUAL); `episode_88293552_replay.json`, seat 1, turn 5: 20 callbacks (19
  PLAY, 1 EQUAL); and `episode_87654847_replay.json`, seat 1, turn 6: 19
  callbacks (1 PLAY, 18 EQUAL).

Only unique-turn counts are used against the frozen thresholds. The duplicate
audit does not rescue or worsen the decisive zero-HOLD failure.

## Actionable-row semantic invariants

All 691 actionable rows are PLAY rows; there are no HOLD rows to audit.

| Required invariant over actionable rows | Violations |
|---|---:|
| Unique current Lillie role and non-null emittable candidate role | 0 |
| Candidate role present in the same row's current Lillie option roles | 0 |
| Live owner overlap | 0 |
| Rejection attached to an actionable row | 0 |
| Hidden-card identity or redrawn-card benefit used in first difference/queue | 0 |
| Unknown count treated as zero or inexact/insufficient count transform | 0 |
| Protected physical serial displaced | 0 |
| Stale or unavailable candidate route | 0 |
| Missing first hard difference | 0 |
| Empty or incomplete alternative queue | 0 |
| Queue serial/counts inconsistent with current option and exact transform | 0 |

More specifically, every actionable queue is one exact `PLAY_LILLIE` item
whose serial is present in the same callback and whose `draw_count`,
`post_hand_count`, and `post_deck_count` equal the independently recomputed
values. Every non-played hand resource is recorded as `DECK_UNKNOWN`; none is
assumed to be redrawn. Every actionable benefit is a positive exact hand-count
or deck-count change. No `RETURN_SURVIVAL` rows occur.

These row-level checks pass, but they cannot satisfy the separate requirement
to demonstrate an emittable HOLD alternative and protected route, because the
census contains no HOLD evidence.

## Frozen gate comparison

| Frozen requirement | Observed | Result |
|---|---|---|
| 207 manifest entries; 209 target seats | 207; 209 | PASS |
| Exactly 25,880 parent calls; zero invalid actions and manifest mismatches | 25,880; summary global invalid = 0; independent manifest mismatch = 0 | PASS on frozen runner evidence |
| Exactly 256 historical Lillie PLAY turns, both seats | 256; seats 0 and 1 | PASS |
| Unique row keys and exact metadata | 0 duplicate keys; exact metadata | PASS |
| At least 40 strict-purpose turns, both seats, at least 20 replays | 408; both; 167 | PASS |
| At least 20 actionable turns, both seats, at least 10 replays | 346; both; 157 | PASS |
| At least 12 predicted first differences, both seats, at least 8 replays | 346; both; 157 | PASS |
| At least 3 PLAY and 3 HOLD turns; each direction in both seats | PLAY 346/both; HOLD 0/no seats | **FAIL** |
| HOLD covers at least 2 protected roles | 0 roles | **FAIL** |
| Every predicted difference root-audited `GOOD_CAUSAL` | No audit field/output supplied; not inferred | NOT DEMONSTRATED |
| Zero hidden-draw, unknown-as-zero, owner-overlap, stale-role, or unemittable-alternative violations among actionable evidence | 0 violations in 691 actionable rows | PASS |

Because all gates must pass and two numerical gates definitively fail, the
candidate implementation is not authorized regardless of the unresolved
qualitative `GOOD_CAUSAL` audit.

## Reproducible calculation

All repository Python reads used `.venv-rl\Scripts\python.exe`. The core count
recomputation is:

```python
import csv, json
from collections import Counter, defaultdict
from pathlib import Path

root = Path(r"C:\Users\amuam\project\AI_pokeka_competition")
base = root / "autonomous_gold_20260715/strategy/archaludon_human_fundamentals_planner_20260731/next_after_fml_no_actionable_boundary_20260801"
csv_path = base / "pre_edit_lillie_actionability_census_raw/opportunity_rows.csv"
rows = list(csv.DictReader(csv_path.open(newline="", encoding="utf-8")))

row_key = lambda r: (
    r["replay"], int(r["seat"]), int(r["step"]), int(r["turn"]),
    r["snapshot_sha256"],
)
turn_key = lambda r: (r["replay"], int(r["seat"]), int(r["turn"]))
truth = lambda x: x == "True"

def stats(selected):
    keys = {turn_key(r) for r in selected}
    return {
        "rows": len(selected),
        "turns": len(keys),
        "replays": len({k[0] for k in keys}),
        "seats": sorted({k[1] for k in keys}),
        "seat_turns": {s: sum(k[1] == s for k in keys) for s in (0, 1)},
    }

assert len(rows) == 1889
assert len({row_key(r) for r in rows}) == len(rows)
strict = [r for r in rows if r["direction"] in {
    "PLAY_LILLIE", "HOLD_LILLIE", "APPROVE_PARENT_LILLIE"
}]
actionable = [r for r in rows if r["direction"] in {
    "PLAY_LILLIE", "HOLD_LILLIE"
} and truth(r["uniquely_emittable"])]
predicted = [r for r in rows if truth(r["predicted_first_difference"])]
print(stats(strict), stats(actionable), stats(predicted))
for direction in (
    "PLAY_LILLIE", "HOLD_LILLIE", "APPROVE_PARENT_LILLIE", "EQUAL", "REJECT"
):
    print(direction, stats([r for r in rows if r["direction"] == direction]))

groups = defaultdict(list)
for row in rows:
    groups[turn_key(row)].append(row)
print("turns", len(groups))
print("multi_callback_turns", sum(len(v) > 1 for v in groups.values()))
print("excess_callbacks", len(rows) - len(groups))
print("direction_conflicts", sum(
    len({r["direction"] for r in v}) > 1 for v in groups.values()
))
print("rejections", Counter(r["rejection_reason"] for r in rows
                            if r["rejection_reason"]))
```

Artifact hashes were recomputed with PowerShell `Get-FileHash -Algorithm
SHA256`. Manifest verification additionally rehashed all 207 replay files,
checked manifest step counts, counted callbacks using
`current.yourIndex == seat and select is not None`, recomputed each raw
observation's canonical sorted-JSON SHA-256, and compared every CSV
replay/seat/step/turn/snapshot binding. Exact-effect assertions applied to all
1,889 rows were:

```text
draw_count = 8 if prize_count == 6 else 6
shuffle_count = hand_count - 1
post_hand_count = draw_count
post_deck_count = deck_count + shuffle_count - draw_count
deck_count + shuffle_count >= draw_count
```
