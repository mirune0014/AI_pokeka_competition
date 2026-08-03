# Hero's Cape arbitration v1 — independent numerical audit

## Decision

**FAIL.** The immutable pre-edit gate does not pass. The required decision is:

`STOP__PARENT_CAPE_NOT_ONE_BROAD_ACTIONABLE_BOUNDARY`

The census has enough natural support and predicted action differences, but only 13/40 complete independent comparisons, 13/20 classifiable turns, 0/3 `RETARGET_CAPE` turns, and 0/3 survival/Prize/continuity boundaries. All 13 predicted differences are one-sided `VETO_TO_ATTACK` results whose first and only hard-vector difference is the resource ledger. No successor, edit, simulation, package, or submission is authorized by this audit.

## Audit scope and reproducible definitions

This is a deterministic replay census, not a candidate-versus-baseline battle evaluation. There is no pre-edit candidate, player mapping, paired win interval, seeded duplicate battle control, or seat-relative win counter to audit. I did not rerun or expand the census. The exact parent is `archaludon_purpose_first_pokegear_boss_transaction_v1/main.py`, SHA-256 `558EE5DB29E001428B0D59813613FABEE8E15B96E422746C104BDFAB4DC22DB6`; its deck SHA-256 is `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`.

The row-level reconstruction used:

- callback key = `(replay, seat, step, turn, snapshot_sha256)`;
- turn key = `(replay, seat, turn)`;
- independent row = the earliest row in a turn with `activation_boundary == True`;
- scope-qualified clear turn = independent parent-Cape turn with `clear_owner_boundary == True`, at least one legal Cape role, and at least one legal attack role;
- complete/classifiable/predicted exactly as the frozen contract requires: complete target worlds; then non-deferred and emittable; then predicted role unequal to parent role;
- world key = callback key plus `(world_kind, cape_target_serial, attack_id)`.

The CSV omits an explicit `independent` column, but reconstruction is unambiguous: 119 callback rows form 116 turn keys; 115 turns have one row, and only `episode_88643491`, seat 0, turn 8 repeats (steps 77–80). Step 77 is the sole activation row and steps 78–80 have `activation_boundary == False`. This yields exactly 116 independent parent-Cape turns.

## Independently recomputed fixed gates

| Fixed check | Recomputed evidence | Result |
|---|---:|:---:|
| Corpus integrity | 207/207 unique replays; 209/209 unique replay-seat targets (seat 0: 108, seat 1: 101); 25,880/25,880 callable observations; 25,880 unique raw keys; 0 manifest/hash mismatch; all 119 persisted callbacks map exactly to their source snapshots | PASS* |
| Natural support | 103 scope-qualified clear turns/replays, both seats (seat 0: 56, seat 1: 47), versus ≥40 turns and ≥20 replays | PASS |
| Earliest-independent complete comparisons | 13 turns/replays, both seats (5/8), versus ≥40 | **FAIL** |
| Classifiable and emittable | 13 turns, 13 replays, both seats (5/8), versus ≥20 turns and ≥12 replays | **FAIL** |
| Predicted first-action differences | 13 turns, 13 replays, both seats (5/8), versus ≥12 turns and ≥8 replays | PASS |
| Both directions | `VETO_TO_ATTACK` 13 (seat 0: 5, seat 1: 8); `RETARGET_CAPE` 0 | **FAIL** |
| Repeated mechanisms | finish/no-purpose label 13; survival/Prize/continuity 0 | **FAIL** |
| Qualitative safety | 13/13 legal current attack roles, owner-clear, exact, non-identity-targeting, and emittable; however 0/13 persisted `GOOD_CAUSAL` labels and the summary remains `PENDING` | **NOT SATISFIED** |

`PASS*` is limited to what can be independently reconstructed. The source corpus verifies replay, seat, call, raw-key, snapshot, and manifest integrity. All 119 persisted parent-Cape rows have valid legal parent roles and the exact Cape metadata hash `28C60B5A46C39088C6BD88657B2D3016AABB4CFAD1FE9CBDCD624BBD0019E9A6`. The output does not persist the other 25,761 parent results, so `invalid_parent_actions == 0` over all calls is summary-only rather than row-reproducible. This provenance gap cannot change the overall failure.

## Row and world integrity

- Callback rows: 119, all unique; 116 independent turns; 113 owner-clear turns. Every row has context/min/max `0/1/1`, `predicted_emittable == True`, matching Cape metadata, and `errors == []`.
- Scope correction: 10 of the 113 owner-clear turns have no legal attack role. The contract's trigger requires an actual current attack, leaving 103 scope-qualified clear turns.
- World rows: 415, all unique and non-orphaned: 118 `ATTACK_NOW` and 297 `CAPE_THEN_ATTACK`. Every expected attack and target×attack row is present; no extra row exists.
- Every Cape world uses a unique visible target role, starts with an empty Tool slot, installs the same physical Cape, and changes both HP and maximum HP by exactly +100. Target IDs represented are 169 (162 rows), 190 (85), 666 (48), and 840 (2).
- World plans: 58 exact rows and 357 incomplete rows. The 357 carry `plan_not_exact`; status is `RETURN_UNKNOWN` for 247 and blank for 110. At callback level, reasons are 100 `incomplete_target_worlds`, 6 `live_owner_or_nonboundary`, and 13 `attack_strictly_dominates_every_cape_world`.
- Only 13 independent callbacks are complete. All 13 are classifiable, emittable, predicted differences, and `VETO_TO_ATTACK`; no complete `APPROVE_PARENT_CAPE` or `RETARGET_CAPE` row exists.

## The 13 predicted differences

All rows below have `current_win == False`, `next_payable_attack == True`, an exact plan, a legal/emittable attack role, and first hard difference `POST_ACTION_THEN_POST_REPLY_RESOURCES`. `—` means the exact plan has no selected public return route, not an unknown plan.

| Episode | Seat / turn / step | Cape targets | Attack | Current damage / KO / Prize | Return damage / KO / Prize | Survives / backup |
|---|---:|---:|---:|---:|---:|---:|
| 87651381 | 1 / 13 / 91 | 2 | 253 | 190 / T / 2 | 20 / F / 0 | T / F |
| 87661127 | 1 / 7 / 72 | 4 | 253 | 190 / F / 0 | 240 / T / 2 | F / T |
| 87662159 | 0 / 6 / 55 | 4 | 253 | 220 / F / 0 | 300 / T / 2 | F / T |
| 87773965 | 0 / 2 / 14 | 2 | 223 | 0 / F / 0 | 0 / F / 0 | T / F |
| 87899857 | 1 / 6 / 57 | 3 | 965 | 50 / T / 1 | — | T / F |
| 87911959 | 1 / 6 / 62 | 4 | 253 | 220 / F / 0 | 180 / F / 0 | T / T |
| 87952737 | 0 / 4 / 27 | 1 | 253 | 220 / T / 1 | 30 / F / 0 | T / F |
| 88191793 | 0 / 12 / 127 | 1 | 253 | 220 / T / 1 | — | T / F |
| 88293552 | 1 / 15 / 124 | 2 | 253 | 190 / T / 2 | 190 / F / 0 | T / F |
| 88425777 | 0 / 2 / 13 | 2 | 965 | 100 / F / 0 | 0 / F / 0 | T / F |
| 88457867 | 1 / 2 / 27 | 3 | 223 | 30 / F / 0 | — | T / F |
| 88660007 | 1 / 5 / 39 | 2 | 253 | 220 / T / 1 | 50 / F / 0 | T / F |
| 88680842 | 1 / 2 / 13 | 1 | 223 | 30 / F / 0 | 0 / F / 0 | T / F |

Numerically, these attacks comprise 6 KOs and 7 non-KOs; Prize yields are 0×7, 1×4, and 2×2; none is an exact current win. Attack IDs are 223×3, 253×8, and 965×2. Eleven attackers survive; two are KO'd on the public reply; three have an exact ready backup. In all 13 histories the observed subsequent Cape attachment target equals the parent's selected target.

Structurally, the 13 callbacks expand to 31 Cape-target comparisons (target counts per callback: 1×3, 2×5, 3×2, 4×3). For all 31:

- every KO, Prize, win, return, survival, promotion, payable-attack, and backup field is identical between `ATTACK_NOW` and the matching `CAPE_THEN_ATTACK` world;
- the five earlier hard-vector layers are identical;
- the only differing hard-vector layer is `POST_ACTION_THEN_POST_REPLY_RESOURCES`;
- the physical Cape ledger row changes from `HAND_READY` to `ATTACHED_AND_RECOVERABLE` in both post-action and post-reply ledgers;
- after removing Cape-specific bookkeeping, 29/31 pairs are otherwise identical; two active-target worlds additionally put that same Cape serial in `certainly_lost_serials` on reply.

Therefore **all 13 predicted differences are resource-ledger-only**. This is not a CSV join accident: the frozen comparator explicitly ranks `HAND_READY` above `ATTACHED_AND_RECOVERABLE`. But it is one conservation-ordering mechanism, not independent evidence of a KO, Prize, survival, or continuity boundary. The runner mechanically labels every VETO as `FINISH_OR_NO_PURPOSE_CONSERVATION`; the label itself is not a separate causal certificate.

## Aggregation and auditability defects

1. `summary.json` reports 113 natural-support turns, but 10 lack any legal attack and violate the frozen trigger. The scope-correct count is 103. The threshold still passes, so this bug does not alter the final decision.
2. The callback CSV omits the required `independent` marker. The current 116-turn reconstruction is nevertheless exact and unambiguous for the reasons above.
3. Boundary labels are direction-driven rather than independently proven: every VETO is unconditionally called finish/no-purpose; every retarget would be called survival/Prize/continuity even if its first difference were resources; an approve compares the winning plan with itself, so its first difference becomes a semantic tie. Current data contain no complete retarget or approve, so correcting this cannot rescue the gate.
4. The helper can return a non-`None` error tuple during role extraction, while the runner counts every non-`None` result as valid and never populates the persisted `errors` list. Thus the aggregate zero-invalid-parent claim is not fully independently auditable.
5. World uniqueness is not asserted by the runner, but the completed raw output has 415/415 unique composite world keys and exact expected coverage.

## Immutable artifacts

- Contract: `STRATEGY_SELECTION_HERO_CAPE_ARBITRATION_V1.md` — `C973A81410538E176CEA41FEDB53A9D03D117255CBB67576B25C82D7A1E244B9`
- Execution specification: `EXECUTION_SPEC_HERO_CAPE_ARBITRATION_V1.md` — `81DA814E2284A4A04932A96C8B02A6F1A14E5C402947FFCDF47206A347DCADD7`
- Frozen runner: `freeze_pre_edit_parent_initiated_hero_cape_census.py` — `C7A0E150E2CCF6F17EECA76108577F4EA5E863CBBED353B551E84524838823B8`
- Raw callback ledger: `pre_edit_parent_initiated_hero_cape_census_raw/callback_rows.csv` — `DE4554312ADBDF177DEABEBFB6956D1E946814770EAD31A024DE72519D97533A`
- Raw target-world ledger: `pre_edit_parent_initiated_hero_cape_census_raw/target_world_rows.csv` — `9BFC462EE352EA8E672C13D0F969BD1F0F19AA579A723E5B5911867FA474A68F`
- Raw runner summary: `pre_edit_parent_initiated_hero_cape_census_raw/summary.json` — `E5A713193D7BACCF197C8EC7066923853C4CEE7FFAAF44A1A74779BE18EE597A`
- Source manifest: `next_after_metal_allocation_fail_20260801/night_stretcher_callback_census_raw/source_manifest.json` — `90A512D5C9AE5EAD8DF92F370C32716959EC0929F9465451E7BB0926DBEB5A68`

## Assumptions

- The parent-provided statement that deterministic execution completed is accepted; no separate exit-code/stdout artifact was supplied or found.
- Empty exact return-route fields are treated as no selected public reply route, while `RETURN_UNKNOWN` rows remain incomplete and cannot contribute to complete/classifiable counts.
- No threshold is relaxed, no later callback substitutes for an earlier independent callback, and no unapproved bucket or simulation is added.
