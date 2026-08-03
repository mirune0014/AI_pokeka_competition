# First-Turbo Public Exact Role Fill V1 — numerical census audit

## Decision

**FAIL — STOP__FIRST_TURBO_EXACT_ROLE_FILL_NOT_ACTIONABLE**

The frozen immediate-difference floor fails without threshold relaxation:
10 semantic first-action differences over 10 transactions and 10 replays were
observed, versus required floors of 24 differences, 16 transactions, and 12
replays. Both seats are represented, but that does not cure the three failed
count floors. Numerical evidence therefore does **not** permit implementation.

There is also a raw-provenance mismatch: the supplied expected transaction CSV
hash is a 62-character value and does not equal the actual 64-character SHA256.
The calculations below identify and use the actual file explicitly; this
mismatch was not silently repaired.

Root GOOD_CAUSAL classification was not performed in this numerical-only audit
and remains pending. It cannot rescue the already failed numeric floor.

## Scope, provenance, and assumptions

- This is the completed pre-edit census, not a candidate-versus-baseline battle
  evaluation. No candidate exists under the frozen PRE_EDIT_CENSUS_ONLY status.
  W-L, policy-to-player mapping, paired uncertainty, battle duplicate controls,
  matchup buckets, and seat/seed performance are therefore not applicable.
- No source, deck, schedule, runner output, raw result, package, or submission
  was changed. No simulation was run or expanded.
- Strategy:
  C:\Users\amuam\project\AI_pokeka_competition\autonomous_gold_20260715\strategy\archaludon_human_fundamentals_planner_20260731\next_after_opening_timing_fail_20260801\first_turbo_public_exact_role_fill_v1\STRATEGY_SELECTION_FIRST_TURBO_PUBLIC_EXACT_ROLE_FILL_V1.md
  — SHA256 E3E6C7BBA58DB125FCF2594FD0EA3A2DE826563DDE5B96DD95682BB213C0389D.
- Retry execution specification:
  C:\Users\amuam\project\AI_pokeka_competition\autonomous_gold_20260715\strategy\archaludon_human_fundamentals_planner_20260731\next_after_opening_timing_fail_20260801\first_turbo_public_exact_role_fill_v1\EXECUTION_SPEC_FIRST_TURBO_PUBLIC_EXACT_ROLE_FILL_V1_RETRY1.md
  — SHA256 09A9038B12432E80031E13BE8BA608BE287FBFE1FF6C8819658E8CF00BFA97D9.
- The formal parent main.py, deck.csv, source manifest, checked helper, prior
  stop reports, attempt-1 runner/spec/failure record, and retry-1 runner all
  match the hashes bound in the retry specification. The retry-1 runner hash is
  558EF4BEBEE3A213886F98F7E1F0452F61090953A0DD61291B03C958C02E471B.
- Replay identity is the manifest SHA256. A transaction key is
  (replay, seat, turn, source_serial). A retained semantic callback key is
  (replay_sha256, seat, stage, snapshot_sha256). Empty error and rejection
  cells mean no recorded error or rejection.
- The global invalid-parent counter over all 25,880 selectable calls is present
  only in the checksum-bound summary (zero); the persisted first-Turbo CSV rows
  independently contain zero invalid parent or contract actions.

Raw directory:

C:\Users\amuam\project\AI_pokeka_competition\autonomous_gold_20260715\strategy\archaludon_human_fundamentals_planner_20260731\next_after_opening_timing_fail_20260801\first_turbo_public_exact_role_fill_v1\pre_edit_first_turbo_exact_role_fill_census_retry1_raw

| Raw file | Actual SHA256 | Supplied expected hash status |
|---|---|---|
| first_turbo_callback_rows.csv | FED101B77BD55E9BFE9E25C17AC63F2E2693CCFA05EDFFCC56C3C92B9D70EE49 | MATCH |
| first_turbo_transaction_rows.csv | F8516840B8700DDD2D2E78AE350D2A5B2EDC316BBC1BE094C8A61BC05E8F9A34 | **MISMATCH** — supplied value F8516840B8700DDD2D78AE350D2A5B2EDC316BBC1BE094C8A61BC05E8F9A34 has 62 hex characters |
| predicted_first_differences.csv | 55CCD26BD89C833416F6C14C23DE8FB0ADF32ED3DDDCA63193A5C5FA5E2A7BC1 | MATCH |
| source_manifest.json | 90A512D5C9AE5EAD8DF92F370C32716959EC0929F9465451E7BB0926DBEB5A68 | MATCH |
| summary.json | 4F520F733D2620CABBEB7F1EF0A123521F6307FDE108DD64BA3E82EDE3347D2A | MATCH |

Four of five supplied raw hashes match. The transaction hash mismatch is a
provenance blocker. The row calculations in this report apply only to the
actual transaction file with SHA256
F8516840B8700DDD2D2E78AE350D2A5B2EDC316BBC1BE094C8A61BC05E8F9A34.

## Reproducible calculation

1. Enumerate the copied manifest and the bound corpus; verify every replay
   filename, file SHA256, and declared step count.
2. For every manifest target seat, count a selectable parent call exactly when
   observation.current.yourIndex equals the seat and observation.select is not
   null. Form the raw key
   (replay, seat, step_index, turn, SHA256(canonical observation)).
3. Parse the three CSVs with UTF-8 and exact True/False conversion. Recompute
   all key cardinalities and counters directly from rows. Verify that the
   predicted-difference ledger is an exact row multiset match to the
   predicted_difference=True callback subset.
4. Join callbacks to transactions on
   (replay, seat, turn, effect_serial/source_serial) and independently match
   every declared callback_rows and target_rows count.
5. For each retained callback snapshot, count identical occurrences in the
   corpus. Retry excess is the sum of max(0, occurrence_count - 1).
6. Apply the frozen thresholds literally; no continuity correction, inferred
   causal label, or threshold adjustment is used.

## Independently recomputed integrity

| Check | Result |
|---|---:|
| Corpus JSON files / manifest entries | 207 / 207 |
| Unique replay names / hashes | 207 / 207 |
| Missing, extra, hash-mismatched, or step-mismatched replays | 0 / 0 / 0 / 0 |
| Target seats / unique replay-seat pairs | 209 / 209 |
| Manifest seat split | seat 0: 108; seat 1: 101 |
| Selectable parent calls / unique raw keys | 25,880 / 25,880 |
| Duplicate raw keys | 0 |
| Retained callback rows / unique semantic callback keys | 1,132 / 1,132 |
| Transaction rows / unique transaction keys | 133 / 133 |
| Difference-ledger rows / unique difference keys | 10 / 10 |
| Unknown replay/hash/seat references in any CSV | 0 |
| Callback-to-transaction count disagreements | 0 |
| Summary errors / manifest mismatches / global invalid-parent count | [] / 0 / 0 |

Retry audit: all 1,132 retained callback snapshots were found in the corpus.
They occurred 1,621 times, so 489 exact-snapshot retry occurrences were
collapsed across 42 repeated keys. All 489 were ATTACH_FROM retries; ATTACH_TO
retry excess was zero. Maximum multiplicity was 44. This exactly reproduces
the summary retry count. There were zero non-identical/stale retry
disagreements: the hash-verified retry runner makes such disagreement fatal,
the execution completed, and the raw error list is empty.

## Census counts

| Population | Callbacks | Transactions | Replays | Seat 0 / seat 1 |
|---|---:|---:|---:|---:|
| Natural first-Turbo | 1,132 | 133 | 133 | transactions 76 / 57 |
| Predicted semantic difference | 10 | 10 | 10 | 6 / 4 |
| Parent-equal controls | 1,122 | 123 | 123 | transactions 70 / 53; callbacks 868 / 254 |

All 10 predicted differences are immediate ATTACH_TO differences and the
difference ledger exactly equals that callback subset. All 10 are
OVERFILL_AVOIDANCE with direction REDUCE_ENERGY_COUNT: eight reduce the
semantic Energy selection from 3 to 0, and two reduce it from 3 to 2. There
are zero EXACT_COST_FILL or RETARGET_EXACT_ROLE_FILL differences.

Classification and direction counts are:

- Transactions: PARENT_EQUAL 123; OVERFILL_AVOIDANCE 10.
- Transaction directions: PARENT_EQUAL 123; REDUCE_ENERGY_COUNT 10.
- Callbacks: PARENT_EQUAL 1,122; OVERFILL_AVOIDANCE 10.
- Callback directions: PARENT_EQUAL 1,122; REDUCE_ENERGY_COUNT 10.
- Stages: ATTACH_TO 133; ATTACH_FROM 999.
- Nonblank callback errors: 0. Nonblank transaction rejection reasons: 0.

Every transaction has exact metadata, an exact Bench snapshot, clear ownership,
no H3 owner, and valid parent and contract actions. Row-level violation counts
are all zero:

- invalid parent actions: 0 callback rows, 0 transactions, 0 predicted rows;
- invalid contract actions: 0 callback rows, 0 transactions, 0 predicted rows;
- hidden-information use: 0;
- H3 changes: 0;
- owner collisions among predicted changes: 0;
- non-Turbo changes: 0 (all are confirmed first Turbo, effect 666, ATTACH_TO);
- semantic-copy noise: 0 (every predicted semantic cardinality changes);
- duplicate raw, callback, transaction, or difference keys: 0;
- stale/non-identical retries: 0.

## Frozen implement/stop gate

| Gate | Frozen requirement | Observed | Result |
|---|---|---|---|
| Raw provenance precondition | every parent-supplied expected raw hash matches | transaction CSV expected hash is malformed and differs from actual | **FAIL** |
| Integrity | exactly 207 replays, 209 target seats, 25,880 calls; zero mismatches, duplicate keys, invalid parent actions | 207; 209; 25,880 unique; all listed violations zero | PASS |
| Natural support | at least 80 transactions, 64 replays, both seats | 133 transactions; 133 replays; seats {0,1} | PASS |
| Immediate semantic differences | at least 24 differences over at least 16 transactions, 12 replays, both seats | 10 differences; 10 transactions; 10 replays; seats {0,1} | **FAIL** |
| Exact-fill or overfill evidence | at least 8 differences | 10, all overfill avoidance | PASS |
| Parent-equal negative controls | at least 24 controls over at least 16 transactions, both seats | 1,122 callback controls over 123 transactions; seats {0,1} | PASS |
| Zero prohibited violations | all listed counts zero | all zero | PASS |
| Root causal audit | every predicted difference GOOD_CAUSAL | pending; outside numerical scope | NOT ASSESSED |

The failed difference floor is short by 14 differences, 6 transactions, and 2
replays. The raw-provenance precondition also fails. Under the immutable rule
that any failed floor stops the hypothesis, the required recommendation is:

**STOP__FIRST_TURBO_EXACT_ROLE_FILL_NOT_ACTIONABLE**

Passing integrity, controls, and the combined exact-fill/overfill count does not
authorize implementation and is not evidence of strength.
