# Rule 3 fixed160 Sol-Ultra numerical audit

## Decision

**REJECT.** Rule 3 fails the frozen stage gate. The independently recomputed result is `100/160 -> 99/160`, with paired gains / regressions / ties `0 / 1 / 159`. Therefore `paired gains >= paired regressions` is false (`0 >= 1`). The sole regression is mechanism-first and the observed transaction does not complete its declared evolve/energy/attack route.

Do not integrate, patch, or widen this rule. Return to the accepted Rule 1 parent, preserving this trial only as a rejected implementation record.

## Frozen inputs and raw evidence

- Requirements SHA-256: `24282FA6A0EF91D936E2E5B2AAD725904EF3223FCFBDF9BEEA16C62C726038C9`
- Rule 3 overlay spec SHA-256: `BDB2B72162A2CED3BF99547E713C33E4A87670A0A3151074117F6A29E45EE95B`
- Inherited schedule SHA-256: `E2B8986663A43A7F6F52888E487F39B8D059CDCDDF441A3E87D8C093DF15274C`
- Baseline Rule 1 `main.py`: `153D8461FB66927DB9731CBE614B71FF5398B8EAE8980AE0BB4D46ADD0E8792A`
- Candidate `main.py`: `3F05F353B868307E91A38FA62ED460D4BFB9A82B85400E2D98B3DBB5CE67A0FC`
- Candidate Rule 3 helper: `2015A4E589D2AE428A151AF50520C160CED7E1B1926D5599A2B35EB0CC6CEA61`
- Candidate deck: `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`
- Runner script SHA-256: `063784175D20984660947DCCBE632B103EE175455D537542527A5E9BA9F2AC1C`
- Raw output root: `autonomous_gold_20260715/evaluations/archaludon_historical_silver_single_resolver_salvage_rule3_trial_v1/fixed160_raw`
- Raw tree SHA-256: `24885F5E21D43C2A87F717BD83E80777BF6CEAB006B2CE97EBF8760C8099E638`
- Historical paired CSV SHA-256: `6B17B59C959A1420103E927F22532F67E333D6B57CB3E5B66F594D6CAFACC676`
- Adjacent paired CSV SHA-256: `DC99EC2AE6BA026A5646C990AD40C2D1F9DF4CB2275B6812E5A0A3D6511FC198`
- Historical report SHA-256: `37706612165C1E2D80C3485C70D0AC571CF6F7148EA79C96B342390A376B7315`
- Adjacent report SHA-256: `4D14EC8543DB70C66FD460F374538EFDDB91849551FBFA45B9BF4B389C465666`
- Root recomputation SHA-256: `EA8747FF43A3618A6F39D76682CAD2D0D70031D5C3F1966A23CD56062413F0EA`
- Reproducible calculator: `audit_rule3_fixed160.py`

## Schedule, player mapping, and validity

I recomputed each policy win from `result == seat`: `result == 0` for the tested policy in player 0 and `result == 1` for the tested policy in player 1. I did not reuse a player-0 counter for player-1 rows.

- Exact schedule: `160/160` unique `(panel, opponent, seat, seed)` keys; duplicate keys `0`.
- Reported-vs-recomputed win-column mismatches: `0`.
- Historical-Silver mirror: 20 seeds in each seat, 40 keys.
- Arch Peak, Alakazam, and Marnie: 20 seeds in each seat for each opponent, 120 keys.
- Baseline duplicate control: `160/160` per-game `result`, `steps`, and `context_counts` identical; mismatches `0`.
- All 18 runner commands exited `0`.
- Across 480 baseline-A / baseline-B / candidate summary rows: start faults `0`, max-step hits `0`, action errors `0`.
- Both runner `report.json` files say `valid: true` and `duplicate_mismatch_count: 0`.

## Independently recomputed result

| Bucket | Games | Rule 1 | Rule 3 | Delta | Gains | Regressions |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| All | 160 | 100 (62.50%) | 99 (61.875%) | -1 | 0 | 1 |
| Historical-Silver mirror | 40 | 20 (50.0%) | 20 (50.0%) | 0 | 0 | 0 |
| Arch Peak | 40 | 20 (50.0%) | 19 (47.5%) | -1 | 0 | 1 |
| Alakazam | 40 | 29 (72.5%) | 29 (72.5%) | 0 | 0 | 0 |
| Marnie | 40 | 31 (77.5%) | 31 (77.5%) | 0 | 0 | 0 |
| Seat 0 | 80 | 47 (58.75%) | 46 (57.5%) | -1 | 0 | 1 |
| Seat 1 | 80 | 53 (66.25%) | 53 (66.25%) | 0 | 0 | 0 |

Paired ties are `159/160`. The paired effect is `-0.625` percentage points. An exact empirical paired bootstrap, whose observed distribution is one `-1` and 159 zeroes, gives a 95% interval of `[-1.875 pp, 0 pp]`. The two-sided exact sign-test value is `p = 1.0`. Thus the numerical decrease is small and not evidence of a general strength difference, but it still fails the precommitted deterministic gate and coincides with a trace-proven mechanism regression.

## First-difference and transaction audit

Exactly three games have a candidate-parent action difference; the other `157/160` are action-identical. All three changed games are the same seed and seat—`271958318`, seat 0—against Arch Peak, Alakazam, and Marnie. This is strong seed/seat concentration rather than broad coverage.

For all three starts:

1. The first difference is an Ultra Ball discard prompt (`context 8`, effect card `1121`) from an identical visible state.
2. Parent action is `[0, 2]`; candidate action is `[2, 0]`. Both select the same card-ID multiset, two Basic Metal Energy (`[8, 8]`), so the first card-ID-level cost is equivalent.
3. The next Ultra Ball search differs: parent `[0]`, candidate `[6]` or `[7]`. Both reveal an Archaludon ex (`190`) in hand, but a different legal deck option is selected.
4. The candidate then does **not** emit the declared immediate Archaludon evolution. The next main action returns to the same parent-selected Explorer's Guidance route. No `EVOLVE` log occurs before that Explorer resolution.
5. Because the different search option has perturbed the deck state, Explorer reveals different cards. In the regression against Arch Peak, the parent reveal is `[169,169,8,190,8,8]`; the candidate reveal is `[666,169,1121,190,1152,8]`. The parent subsequently obtains another Duraludon while the candidate must use a different recovery/development line.

The action-observable fixed160 count is therefore **3 natural Rule 3 starts and 0 completed declared transactions**. The runner did not persist the candidate's private `_last_telemetry` or option serials, so a completely parent-identical hidden start cannot be distinguished from ordinary parent play. This limitation does not weaken the rejection: every action-observable start fails to complete, one produces the only paired regression, and none produces a gain.

The sole outcome flip is:

- panel `adjacent_population`
- opponent `arch_peak`
- seat `0`
- game `5`
- seed `271958318`
- Rule 1 parent: win (`result 0`, 133 steps)
- Rule 3 candidate: loss (`result 1`, 131 steps)

Because the pre-difference state is identical, the candidate differs only through Rule 3, and the deterministic continuation flips the result, this is a clear harmful mechanism-first difference. It is not safe to dismiss the first reordered pair as cosmetic: the following searched option and deck-dependent reveal diverge, while the transaction owner fails to carry the promised route to evolution and attack.

## Frozen-gate recommendation

- Minimum observable natural starts (`>=1`): **PASS** (`3`).
- Dormant classification: **not applicable**.
- Mechanical validity and duplicate controls: **PASS**.
- No seat/opponent decline of 3 wins: **PASS** (worst `-1`).
- Paired gains at least regressions: **FAIL** (`0 < 1`).
- Zero clearly harmful first differences: **FAIL** (`1`).
- Complete-route requirement at observed starts: **FAIL** (`0/3`).

Final stage-gate recommendation: **REJECT Rule 3 and restore Rule 1 as the accepted parent.**
