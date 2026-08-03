# Public secured-attack search-purpose guard: numerical census audit

## Decision

`STOP__PUBLIC_SECURED_ATTACK_SEARCH_GUARD_NOT_BROADLY_ACTIONABLE`

Implementation is **not authorized**.  The immutable actionability thresholds
were applied without reduction.  Even before qualitative review, the census
misses the eligible-surface, predicted-difference, and per-search-family
difference gates.  In addition, the raw contract fields contradict the
`PURPOSE_HOLD` / `predicted_difference=False` labels on 67 rows, so the literal
parent-equal-control requirement is not evidenced by those rows.

No qualitative replay analysis was performed because the numerical gate already
fails.  No source, deck, schedule, raw output, package, or external state was
changed.

## Scope and assumptions

- This is the deterministic pre-edit census defined by
  `EXECUTION_SPEC_PUBLIC_SECURED_ATTACK_SEARCH_GUARD_V1.md`, not a baseline vs.
  candidate battle evaluation.  A candidate does not yet exist.  Battle-result
  seat mapping, duplicate battle controls, W-L rates, paired uncertainty, and
  effect sizes are therefore not applicable.
- The only executable policy is the formal parent at
  `autonomous_gold_20260715/candidates/archaludon_purpose_first_pokegear_boss_transaction_v1/main.py`;
  its bound deck is the adjacent `deck.csv`.
- The parent designated the frozen run complete.  All five expected files exist
  and match the supplied hashes.  An operator exit-code/stdout/elapsed-time log
  is not part of the raw directory, so it was not independently audited and the
  census was not rerun.
- The global `invalid_parent_actions=0` value over all 25,880 parent calls exists
  only as a checked-runner scalar in `summary.json`.  Independently, all 601
  retained parent-search rows have `parent_valid=True`.  Recomputing the global
  action-validity scalar would require invoking the policy again, which this
  audit was not authorized to do.  The final STOP does not depend on that scalar.
- The raw CSVs retain one representative after retry deduplication.  Raw replay
  occurrences independently reproduce the retry counts, while equality of
  stateful owner/contract fields on omitted representatives retains the frozen
  runner's halt-on-mismatch provenance.

## Reproducible calculation

All calculations used Python 3.11.6 through
`.venv-rl\Scripts\python.exe`, the standard `csv`, `json`, `hashlib`, and
`collections` modules, and read-only access to the frozen CSV/JSON files and
the 207 manifest-bound replay JSON files.  `summary.json` was compared only
after the row selections below were calculated.

1. Hash each file as uppercase SHA-256 of its bytes.
2. For each manifest replay and target seat, select a source callback exactly
   when `observation.current.yourIndex == seat` and `observation.select` is not
   null.  Hash the loaded observation as SHA-256 of
   `json.dumps(observation, ensure_ascii=False, sort_keys=True)` and define the
   raw key as `(replay, seat, step, turn, snapshot_sha256)`.
3. Define the orientation output key as
   `(replay_sha256, seat, "ORIENTATION", snapshot_sha256)` and the parent-search
   output key as
   `(replay_sha256, seat, "PARENT_SEARCH", snapshot_sha256)`.
4. Parse a CSV boolean as true only when its text is exactly `True`.  Define a
   turn key as `(replay, seat, turn)`.
5. `classifiable := classifiable=True`;
   `predicted := predicted_difference=True`;
   runner-labelled purposeful control :=
   `classification="PURPOSE_HOLD" and classifiable=True`; and owner control :=
   `classification="OWNER_HOLD"`.
6. Independently test the literal parent-equal requirement with both
   `parent_action == contract_action` and
   `parent_semantic == contract_semantic`.  Also test that
   `predicted_difference` equals semantic inequality on every retained row.

## Hash and source integrity

Every supplied and execution-spec-bound hash matched:

| Artifact | SHA-256 |
|---|---|
| strategy | `6D98BF4300BC059F1E7E7B9EA31FD98CBCE15CA68510DBF168F2DB26A2F7E69A` |
| execution specification | `4D5FEEDCAA4735992445779E8368BFEE060AB7BF0AFC5DB962A0CDBC31D7EE77` |
| formal parent `main.py` | `558EE5DB29E001428B0D59813613FABEE8E15B96E422746C104BDFAB4DC22DB6` |
| formal parent `deck.csv` | `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A` |
| source manifest | `90A512D5C9AE5EAD8DF92F370C32716959EC0929F9465451E7BB0926DBEB5A68` |
| checked helper | `3441E6DFA25140E9C70CABB58E9F36CF3DF76FCD25B3B36311590FA83CF9EF8B` |
| first-Turbo stop report | `7277B8ECD82C577CF775CCF2C058DACAAA01435F00A9A99B9041C1889B21F458` |
| TODO | `8AE7B706CF5BE4E3EF659A10CEB4F8C5E516E67BECDA4421173AF06567BB1224` |
| acceptance matrix | `F273C043D4C479F15CC464600B14D51823BECF55D4AF22F68A0B8971F166A386` |
| action-frequency report | `9A440FA409161153F8801354884FD66EC88DE522B14D5067D23ADDCBA0804ECC` |
| effect-gap report | `253F8CB535DFF70F561E93EA57066E3C5E563DCE9735F91AF56AF327A714D3D1` |
| frozen census runner | `A60CDB559DBC0BC6B985654B3BCDC499F2C6D712F7795526D7DC190EE77803F8` |

Raw directory:

`C:\Users\amuam\project\AI_pokeka_competition\autonomous_gold_20260715\strategy\archaludon_human_fundamentals_planner_20260731\next_after_first_turbo_no_actionable_boundary_20260801\pre_edit_search_purpose_guard_census_raw`

| Raw file | Data rows / entries | SHA-256 |
|---|---:|---|
| `orientation_rows.csv` | 2,017 | `87045C92E614054024FEACACAEA92E8485DF4299BC7F26C445696ECF9FE159A7` |
| `search_guard_callback_rows.csv` | 601 | `4996A46D1C221B230D99A6C0E0C21156179489E74935CB7F3A92826C8193A008` |
| `predicted_first_differences.csv` | 4 | `5603076F28701487112A057D20C9FDD5FD9E149E3F83BDD3D981127B5D59AA5A` |
| `source_manifest.json` | 207 | `90A512D5C9AE5EAD8DF92F370C32716959EC0929F9465451E7BB0926DBEB5A68` |
| `summary.json` | one object | `76B38A7E269FE2C2C2D32091949D025B3948A127C66930A0A4BE09D2A0AA2FCC` |

Manifest/source replay recomputation:

- 207 unique replay names and hashes; 209 unique target replay-seat keys
  (seat 0: 108; seat 1: 101).
- 0 missing replay files, 0 replay-hash mismatches, and 0 manifest step-count
  mismatches.
- 25,880 selectable source callbacks and 25,880 unique raw keys: exact
  reproduction.
- Output keys: 2,017/2,017 unique orientation keys, 601/601 unique
  parent-search keys, and 4/4 unique predicted-file keys.  Every CSV row maps
  exactly to its manifest replay, seat, step, turn, turn-action count, and
  snapshot hash; mismatches: 0.
- `predicted_first_differences.csv` is row-field/order equivalent to filtering
  the 601 callback rows on `predicted_difference=True`.

## Orientation and callback census

The previously reported orientation surface is reproduced exactly:

- **2,017** unique orientation snapshots, **636** turn keys, **180** replays,
  seats `{0,1}`.
- By seat: 1,265 rows / 350 turns for seat 0; 752 rows / 286 turns for seat 1.
- Search options: 307 Pad-only rows, 1,507 Ultra-only rows, and 203 rows with
  both families.
- Formal-parent selection inside this attack-plus-search orientation surface:
  Pad 262, Ultra 185, and non-search 1,570.

The formal-parent search census is not the historical recorded-action frequency
table; the frozen runner calls the current formal parent and does not imitate
the replay action.  Its exact counts are:

| Surface | Rows | Turn keys | Replays | Seat 0 rows | Seat 1 rows | Pad rows | Ultra rows |
|---|---:|---:|---:|---:|---:|---:|---:|
| all parent-search callbacks | 601 | 477 | 192 | 321 | 280 | 371 | 230 |
| classifiable | 71 | 54 | 36 | 47 | 24 | 37 | 34 |
| flagged predicted differences | 4 | 3 | 3 | 1 | 3 | 3 | 1 |
| runner-labelled classifiable `PURPOSE_HOLD` | 67 | 51 | 35 | 46 | 21 | 34 | 33 |
| owner controls | 41 | 33 | 31 | 21 | 20 | 38 | 3 |

Family-by-seat row splits are: parent-search Pad `198/173` and Ultra `123/107`;
classifiable Pad `25/12` and Ultra `22/12`; labelled purposeful Pad `25/9`
and Ultra `21/12`; owner Pad `19/19` and Ultra `2/1`, where each pair is
`seat 0 / seat 1`.

Flagged prediction categories:

- `POKE_PAD_NO_PURPOSE_ATTACK`: 3 rows, 2 turns, 2 replays, seat 1 only.
- `ULTRA_NO_PURPOSE_ATTACK`: 1 row, 1 turn, 1 replay, seat 0 only.
- `ULTRA_UNSAFE_RESERVE_ATTACK`: 0.

Thus four flagged rows occupy three turn keys because two distinct snapshots
occur on one turn; this is not an output-key duplicate.

## Purpose and owner controls

The frozen summary's label-based selection finds 67 classifiable
`PURPOSE_HOLD` rows across 51 turns, 35 replays, both seats, and both search
families.  There are another two nonclassifiable `PURPOSE_HOLD` rows, both
rejected as `backup_readiness_unknown`.

However, all 67 classifiable `PURPOSE_HOLD` rows have both a different
`contract_action` and a different `contract_semantic` from the parent while
their `predicted_difference` flag is false.  Therefore:

- runner-labelled purposeful controls: 67;
- literal exact-parent-action controls among them: **0**;
- literal exact-parent-semantic controls among them: **0**;
- false `predicted_difference=False` flags relative to the recorded contract
  semantic: **67**.

The frozen summary does not test this invariant.  It counts
`classification == PURPOSE_HOLD and classifiable=True` and reports the
purposeful-control gate as true.  That reproduces the summary's algorithm, but
it does not satisfy the strategy's literal requirement for parent-equal
controls.  The 67 contradictory rows cannot be silently credited either as
controls or as actionable predictions.

All 41 owner controls are exact-parent by both action and semantic.  They cover
31 replays, both seats, and both families.  Owner creation after the one parent
call is: `_pfc_search_watch` on 38 rows, `_cum_active_transaction_owner` plus
`_h6_transaction` on 2, and `_cum_active_transaction_owner` plus
`_h3_transaction` on 1.  All start with an empty pre-owner set.  These 41
pre/post transitions are recorded owner controls, not mismatches; owner flag
and `OWNER_HOLD` equivalence mismatches are both 0.

## Classifications and rejection reasons

Classifications over all 601 parent-search rows:

| Classification | Count | Pad | Ultra |
|---|---:|---:|---:|
| `ATTACK_UNKNOWN_HOLD` | 487 | 296 | 191 |
| `OWNER_HOLD` | 41 | 38 | 3 |
| `PURPOSE_HOLD` | 69 | 34 | 35 |
| `POKE_PAD_NO_PURPOSE_ATTACK` | 3 | 3 | 0 |
| `ULTRA_NO_PURPOSE_ATTACK` | 1 | 0 | 1 |

All rejection-reason counts:

| Rejection reason | Count |
|---|---:|
| none | 4 |
| `attack_certificate_unknown` | 86 |
| `backup_readiness_unknown` | 2 |
| `multiple_incomparable_nonko_attacks` | 1 |
| `no_payable_attack` | 123 |
| `nonko_successor_unknown` | 30 |
| `owner_live` | 41 |
| `reply_graph_unknown` | 247 |
| `unfinished_productive_main_action` | 19 |
| `visible_role_deficit:EVOLUTION_SEARCH_PURPOSE` | 7 |
| `visible_role_deficit:EVOLUTION_SEARCH_PURPOSE,NO_INDEPENDENT_EVOLUTION_CHASSIS,NO_READY_BACKUP,ONE_POKEMON_LOSS_RISK` | 2 |
| `visible_role_deficit:EVOLUTION_SEARCH_PURPOSE,NO_READY_BACKUP` | 3 |
| `visible_role_deficit:EVOLUTION_SEARCH_PURPOSE,ONE_PRIZE_WALL_PURPOSE` | 1 |
| `visible_role_deficit:NO_INDEPENDENT_EVOLUTION_CHASSIS` | 1 |
| `visible_role_deficit:NO_INDEPENDENT_EVOLUTION_CHASSIS,NO_READY_BACKUP,ONE_POKEMON_LOSS_RISK` | 4 |
| `visible_role_deficit:NO_INDEPENDENT_EVOLUTION_CHASSIS,NO_READY_BACKUP,ONE_POKEMON_LOSS_RISK,ONE_PRIZE_WALL_PURPOSE` | 3 |
| `visible_role_deficit:NO_INDEPENDENT_EVOLUTION_CHASSIS,NO_READY_BACKUP,ONE_POKEMON_LOSS_RISK,POST_TURBO_LINE_PURPOSE` | 11 |
| `visible_role_deficit:NO_READY_BACKUP` | 15 |
| `visible_role_deficit:NO_READY_BACKUP,ONE_PRIZE_WALL_PURPOSE` | 1 |

## Violations and retries

The runner-enumerated violation counters are independently reproduced for the
four flagged predictions: invalid contract actions 0, hidden-information flags
0, owner collisions 0, semantic-copy noise 0, non-MAIN predictions 0, and
prediction errors 0.  The checked-runner global invalid-parent scalar is 0.

Across all 601 retained callback rows: invalid parent flags 0, invalid contract
flags 0, error rows 0, hidden-information flags 0, non-MAIN contexts 0,
non-unique selected search roles 0, inexact public-effect flags 0, and retained
`duplicate_retry=True` flags 0.  The frozen classifier receives no replay name
or target-seat parameter and records no opponent-archetype, opponent-deck, or
replay-ID predicate.  It does use the bound deck's public card IDs for the
specified board-role and protected-reserve checks.

The additional uncounted data-contract violation is the 67 false negative
`predicted_difference` flags described above.  In total, the recorded
`contract_semantic` differs from `parent_semantic` on 71 rows, whereas only four
are flagged and exported as predictions.

Retry facts:

- The 2,017 orientation keys map to 2,322 source replay occurrences: 1,968 keys
  occur once and 49 occur more than once, producing exactly **305** collapsed
  orientation retries.  Repeated-key multiplicities are
  `2:9, 3:2, 4:3, 5:5, 6:4, 7:8, 8:4, 9:1, 10:2, 12:3, 13:3, 14:1, 15:3, 18:1`
  (`multiplicity:key-count`).
- The 601 parent-search keys map to 601 source occurrences, so callback retries
  collapsed are **0**.
- Source-row snapshot mismatches are 0.  The completed frozen runner would halt
  on a nonidentical orientation or parent-search retry; no stale nonidentical
  retry is present in the retained outputs.

## Immutable gate audit

| Gate | Exact requirement | Recomputed evidence | Result |
|---|---|---|---|
| bound integrity | exact hashes; 207 replays; 209 seats; 25,880 calls; unique keys; zero listed integrity errors | hashes exact; 207; 209; 25,880/25,880 unique; manifest/output-key mismatches 0; retained invalid parents 0; global runner scalar 0 | PASS under frozen integrity definition |
| orientation reproduction | reproduce or explain the suggested surface | 2,017 snapshots; 636 turns; 180 replays; seats `{0,1}` | PASS |
| eligible surface | at least 80 classifiable turns, 50 replays, both seats | 71 rows; **54 turns**; **36 replays**; both seats | **FAIL** |
| predicted differences | at least 24 rows and 24 turns, 16 replays, both seats | **4 rows**; **3 turns**; **3 replays**; both seats | **FAIL** |
| zero-discard Pad differences | at least 8 | **3** | **FAIL** |
| discard-cost Ultra differences | at least 8 no-purpose or unsafe-reserve | **1** (`NO_PURPOSE` 1, `UNSAFE_RESERVE` 0) | **FAIL** |
| purposeful controls, frozen label test | at least 24, at least 16 replays, both families | 67 labels; 35 replays; both families | PASS only under summary's label-only test |
| purposeful parent-equal controls, literal strategy test | at least 24 exact-parent controls, at least 16 replays, both families | **0** exact-parent actions and **0** exact-parent semantics among the 67 labelled rows | **FAIL / raw contract inconsistency** |
| inherited-owner controls | present | 41 exact-parent controls; 31 replays; both families and seats | PASS |
| enumerated zero violations | every frozen-summary violation counter zero | all seven summary counters zero | PASS |
| contract/flag consistency | a recorded predicted-difference flag must match recorded semantic inequality | **67 mismatches** | **FAIL / omitted by summary** |
| root qualitative labels | every predicted difference `GOOD_CAUSAL`; sampled holds `CORRECT_HOLD` | not reached; numeric gate already fails | NOT RUN |

The frozen `summary.json` gate booleans are exactly reproduced under its own
definitions: integrity `true`, eligible surface `false`, predicted differences
`false`, both search families `false`, purposeful controls `true`, inherited
owner controls `true`, and zero enumerated violations `true`; aggregate numeric
gate `false`.  Applying the stricter literal strategy wording additionally
fails purposeful parent equality and exposes the 67-row contract/flag
inconsistency.  Both readings require the same immutable STOP decision.
