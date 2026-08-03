# Neutralization Zone numerical audit (Sol Ultra)

## Decision

**FAIL — `STOP__INSUFFICIENT_NATURAL_SEMANTIC_COVERAGE`.** Only the integrity and zone-turn gates pass. The affected-certificate, hard-difference, predicted-difference, four-example-class, and identity-diversity gates fail under the frozen thresholds. No candidate edit is authorized.

This is a read-only semantic census, not a paired battle evaluation. Win/loss rates, player mapping, seed/seat sensitivity, uncertainty intervals, and duplicate battle controls are therefore not applicable; no simulations or agent calls were run for this audit.

## Inputs and raw-completeness judgment

All supplied hashes independently match:

- `STRATEGY_SELECTION_NEUTRALIZATION_ZONE_V1.md`: `7E4863D0B02F5F1B379D0EFEAF5D92F9D02484815E05A589BAF3B26106E5AD7C`
- `freeze_pre_edit_neutralization_zone_semantic_census.py`: `02D7903428EED9410CC444801A855CDBF5F17803A39596C384302EE7E50034CC`
- `pre_edit_neutralization_zone_semantic_census_raw/gap_identity_rows.csv`: `9C96B147F9C341E409602B004E76996ABA2D9948864FA474C87C8AB4AE8D7FE7`
- `pre_edit_neutralization_zone_semantic_census_raw/opportunity_rows.csv`: `FD8E4CC64FE295C77B7B66AA89EBC277BE8FE506BBB7A1943032A612DF25A0B6`
- `pre_edit_neutralization_zone_semantic_census_raw/summary.json`: `C1D2511A57B707DF89901F56E37AE359D4335A946E167553E8540DB93A05A5F7`

The raw outputs are complete despite the reported process exit code 1. Both CSVs and the JSON parse to EOF with their exact schemas; there are 423/423 unique gap keys and 40/40 unique opportunity raw keys and turn keys, with no malformed embedded JSON. Every emitted row's replay, seat, step, turn, replay hash where present, and snapshot hash matches the immutable corpus. The runner closes both CSVs and writes `summary.json` before its final stdout `print`; therefore a CP932 `UnicodeEncodeError` at that final print cannot truncate the already closed files.

Independent manifest/corpus traversal, without executing the policy, reproduces 207 unique replays, 209 target seats, 25,880 selectable parent-call positions, 25,880 unique raw keys, zero duplicate raw keys, zero replay-hash mismatches, and zero declared-step mismatches. The summary's `invalid_parent_actions = 0` is not fully recoverable from the emitted CSV schema: only the 40 emitted opportunities expose `parent_valid`, and all 40 are true. Thus that one integrity value is runner/summary-attested rather than independently row-auditable across the other 25,840 calls. This limitation cannot turn the recommendation from FAIL to PASS; a nonzero value would only add another failure.

The exact parent hash also matches `558EE5DB29E001428B0D59813613FABEE8E15B96E422746C104BDFAB4DC22DB6`. A read-only catalog load independently confirms card ID 1247, card and sole skill name `Neutralization Zone`, and normalized text hash `cf3fb44117e74c1fc5ac792a4721cd1ea345a1caa0a861931a59a46a842fd877`.

## Reproducible calculation

CSV rows were parsed with `csv.DictReader`; JSON-valued cells were parsed with `json.loads`. Corpus snapshots were canonicalized with `json.dumps(raw, ensure_ascii=False, sort_keys=True)` and SHA-256, matching the runner for JSON-native values. The independent keys were:

- raw key: `(replay, seat, step, turn, snapshot_sha256)`;
- zone turn: `(replay, seat, turn)` when the selectable observation has exactly one Stadium with ID 1247 and a non-null serial;
- affected certificate: `(replay, seat, turn, scope, source_serial, attack_id, target_serial)` for `prevented == true`;
- hard difference: nonempty `first_hard_difference` by unique zone-turn key;
- predicted difference: `predicted_first_difference == true` by unique zone-turn key.

Example classes were recomputed from each row's `affected_certificates`, not trusted from `example_counts`: prevented events count as `EX_OR_MEGA_DAMAGE_PREVENTED`; positive `NON_RULE_BOX_SOURCE` and `RULE_BOX_TARGET` events count in their respective classes; the runner's public-return classifier counts a prevented scope other than `CURRENT` or `BENCH`. Recomputed row classes, blocked/protected ID cells, aggregate summary values, and every stored numeric-gate Boolean agree exactly with the raw rows under those runner definitions.

## Gap taxonomy and Stadium partition

The 423 gap rows reproduce exactly: `RETURN_UNKNOWN = 225`, `UNSUPPORTED_STADIUM = 128`, and `UNSUPPORTED_SKILL_TOOL = 70`. All 423 source snapshots match, all keys are unique, and every `attack_alternative_count` equals the decoded error count.

The 128 Stadium rows partition exactly as follows:

| Card ID | Exact name | Normalized text SHA-256 | Rows |
|---:|---|---|---:|
| 1259 | Spikemuth Gym | `602783d7a8c06461af5df9e87ba7831178fc7001352a8fb19d7dd909e50ee258` | 60 |
| 1247 | Neutralization Zone | `cf3fb44117e74c1fc5ac792a4721cd1ea345a1caa0a861931a59a46a842fd877` | 36 |
| 1257 | Team Rocket's Factory | `bfbb02ba4d372ca0f75a5d230765afe43d8aab57069c3ff552362e5b06d2c8ce` | 17 |
| 1252 | Gravity Mountain | `0c6a7efe7fa3c18f67a642887b664e0715edd00e078b1a24464c6e1fd9342295` | 6 |
| 1266 | Nighttime Mine | `0a420e41475097553586efda1eef52b21525c67df1b0fbc199e42e5718cb5856` | 5 |
| 1256 | Team Rocket's Watchtower | `ee82827ea811c91865701e4ce9a99a1f75e4b8277b2721cad940053aac656717` | 2 |
| 1254 | Levincia | `8f4c3dfa5196d74d3a42f7b0b8eae18a87fe84fa74dd538ebfa0baf55a9b209c` | 1 |
| 1260 | Risky Ruins | `d3e043bf7e85b0be3a1fb50cf225a8ba38d1481518cfec36c767be5f5b9c29e7` | 1 |

## Frozen-gate recomputation

| Gate | Frozen requirement | Independent observation | Result |
|---|---|---|---|
| Integrity | exactly 207 replays, 209 seats, 25,880 calls; zero manifest mismatch, duplicate key, invalid action | `207 / 209 / 25,880`; mismatches `0`, duplicate keys `0`, summary invalid actions `0` (40/40 emitted rows directly valid) | PASS |
| Zone turns | at least 40 turns, both seats, at least 12 replays | **71 turns / seats `[0,1]` / 16 replays** | PASS |
| Affected certificates | at least 24 keys, both seats, at least 8 replays | **10 keys / 6 turns / seats `[0,1]` / 3 replays** | FAIL |
| Hard plan-ranking differences | at least 12 turns, both seats, at least 6 replays | **0 turns / seats `[]` / 0 replays** | FAIL |
| Predicted first-action differences | at least 8 turns, both seats, at least 4 replays | **0 turns / seats `[]` / 0 replays** | FAIL |
| Four example classes | at least 3 of each | prevented ex/Mega-ex `10`; non-ex remains legal `73`; Rule-Box target unprotected **`0`**; runner-classified public return `6` | FAIL |
| Identity diversity | at least 2 blocked sources and 4 protected targets | **1 blocked ID `[190]`; 2 protected IDs `[741,743]`** | FAIL |

The runner's 71 zone-turn keys arise from 621 selectable Zone-visible calls. The emitted earliest activation-boundary MAIN table contains 40 unique turns across 15 replays and both seats; all 40 have `activation_boundary = true`, `pre_call_owners = {}`, MAIN context, and a valid parent action. Of the other 31 Zone-visible turns, 20 have no raw MAIN call and 11 have a MAIN call but do not satisfy the frozen activation/no-owner emission condition. Reclassifying or rerunning those turns would expand/change the frozen census, not correct an emitted-row arithmetic error.

All 10 runner-defined affected keys are attack 253 from blocked source ID 190 (`Archaludon ex`, `ex=true`, `megaEx=false`) into protected non-Rule-Box IDs 741 (`Abra`) or 743 (`Alakazam`). The identity counts are therefore genuinely one and two, not missing distinct IDs hidden by aggregation. All 40 selected-plan fields are null: selection reasons are 38 `v2_plan_unsupported_or_incomparable`, one `v2_plan_ledger_or_public_reply_unknown`, and one `no_hard_lexicographic_improvement`. This directly supports both zero-difference results; 10 rows record the non-exception diagnostic `no_actual_attack_option`.

## Schema/counting sensitivity

Two defects make the stored coverage more optimistic, not less:

1. All six events counted as `PUBLIC_RETURN_DAMAGE_PREVENTED` have ambiguous scope `CURRENT_OR_RETURN`; there are **zero** explicit `RETURN` events. The strategy's requirement is exact public-return damage prevention, so the strict supported count is 0 rather than 6.
2. Four turns record the same source/attack/target certificate once as `CURRENT` and once as `CURRENT_OR_RETURN`. The frozen affected key includes `scope`, producing 10 keys; collapsing scope to the six physical replay-seat-turn/source/attack/target combinations yields **6**, not a larger count.

There are no affected-key collisions with different event payloads, no within-row duplicate event payloads, no Bench prevented events, no Rule-Box-target events, and no raw/summary discrepancy that could supply missing hard or predicted differences or new identities. Consequently no defensible schema or event-count correction can turn this FAIL into PASS. Only a newly approved, redesigned census could examine excluded states, and that would not be an audit of this immutable output.

## Assumptions

- The reported CP932 exception occurred only at the runner's final stdout print, as stated by the parent; file ordering and complete parse/provenance checks independently support that account.
- The frozen runner definitions govern the primary counts. The stricter explicit-`RETURN` and scope-collapsed figures are reported as sensitivity checks and do not relax any threshold.
- `invalid_parent_actions = 0` outside the 40 emitted opportunities is accepted only as the immutable runner/summary result because the raw schema does not emit all parent-call actions.
- Root qualitative `GOOD_CAUSAL` review remains pending, but with zero predicted first-action differences and multiple independent numeric failures it cannot rescue the gate.
