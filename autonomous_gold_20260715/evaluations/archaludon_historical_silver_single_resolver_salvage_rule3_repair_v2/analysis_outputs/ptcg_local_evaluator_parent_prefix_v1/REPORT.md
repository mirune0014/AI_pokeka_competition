# Rule 3 parent-prefix v1 fixed160 independent numerical audit

## Decision

**PASS for the fixed160 numerical, determinism, and execution-safety gates.** Baseline and candidate are both **100-60 (62.50%)**. The paired result is **0 gains / 0 regressions / 160 ties**, and candidate versus baseline A is byte-trace-identical on **160/160** schedule keys. The observed practical effect is exactly **0 wins / 0.00 percentage points**. This is retention evidence, not evidence of a statistically or practically meaningful strength improvement.

This fixed160 panel has **no natural Rule 3 start**. Consequently, it cannot establish Rule 3 efficacy or strength; that evidence must come from the separately frozen natural-seed verification, not from a positive aggregate delta here (there is none). The linked verification contains two natural starts, one in each seat: Active-prefix seed `271958323` (seat 1, `result=1`, therefore a tested-policy win) and Turbo seed `271958324` (seat 0, `result=1`, therefore a tested-policy loss). Both are candidate/parent trace-identical and complete Rule 3 without an irreversible-abort fault. Thus the Active seed is the separate win-restoration evidence; the Turbo seed is transaction/physical-copy preservation evidence, not a win.

## Frozen scope and policy/player mapping

- Candidate: `autonomous_gold_20260715/candidates/archaludon_historical_silver_single_resolver_salvage_rule3_repair_v2/main.py`, SHA-256 `4287A616E1611F5697964D9F4065978EED1CEA72CDB48C9F63F1430D69106C35`.
- Baseline/parent: `autonomous_gold_20260715/final/archaludon_historical_silver_single_resolver_salvage_v1/main.py`, SHA-256 `D966E455E5110F9D5616195AEAAC8663E6A92F310DAFC4B7F79E4D37149A9C62`.
- Candidate and baseline deck SHA-256: `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`.
- Immutable controlling spec: `autonomous_gold_20260715/evaluation_specs/archaludon_historical_silver_single_resolver_salvage_rule3_parent_prefix_v1/fixed160_spec.json`, SHA-256 `433DC2102AB5C6AFEBBC2253EAC3506E25D7651602DDE5E4032AA754D82018D9`.
- Referenced schedule base: `autonomous_gold_20260715/evaluation_specs/archaludon_historical_silver_single_resolver_salvage_v1_rule1/fixed160_spec.json`, SHA-256 `E2B8986663A43A7F6F52888E487F39B8D059CDCDDF441A3E87D8C093DF15274C`.
- Raw output root: `autonomous_gold_20260715/evaluations/archaludon_historical_silver_single_resolver_salvage_rule3_repair_v2/fixed160_parent_prefix_v1_raw`.
- The candidate, parent, decks, schedule/base specs, strategy amendment, linked pre-fixed160 verification, all three runner files, all seeded-engine files, Historical-Silver, and the three adjacent opponents independently matched their frozen hashes.

`run_local_battle.py` reports the winning **player index**. The manifests confirm that for `seat=0` the tested policy is agent A/player 0 and wins iff `result==0`; for `seat=1` it is agent B/player 1 and wins iff `result==1`. Applying `policy_win = int(result == seat)` independently reproduced all 160 stored baseline and candidate win flags. No player-0 counter was reused for seat-1 rows.

## Schedule and raw-row reconstruction

The expected schedule was reconstructed as the Cartesian expansion of each frozen panel's opponents, both seats, and games `0..19`, with `seed = seed_base + game`.

- Paired CSV rows: `40 historical_silver + 120 adjacent_population = 160`.
- Unique logical `(panel, opponent, seat, seed)` keys: `160/160`.
- Duplicate / missing / unexpected keys: `0 / 0 / 0`.
- Incorrect `game` or `seed_base` metadata: `0`.
- Baseline-A, baseline-B, and candidate summary schedules: each exactly `160` unique expected keys, with exact three-way schedule equality.
- Paired CSV versus baseline-A/candidate raw summaries: `160/160` result and step-count matches for each role.
- Stored versus independently recomputed win flags: `160/160` for each policy.

The two panel CSVs do not physically store a `panel` column; `panel` is deterministically derived from the containing immutable panel directory. This is the only normalization used to form the required logical key.

## Aggregate, panels, seats, and opponents

| Bucket | Baseline W-L (rate) | Candidate W-L (rate) | Delta | Gains / regressions / ties |
|---|---:|---:|---:|---:|
| All, 160 | 100-60 (62.50%) | 100-60 (62.50%) | 0 (0.00 pp) | 0 / 0 / 160 |
| Historical-Silver panel, 40 | 20-20 (50.00%) | 20-20 (50.00%) | 0 | 0 / 0 / 40 |
| Adjacent-population panel, 120 | 80-40 (66.67%) | 80-40 (66.67%) | 0 | 0 / 0 / 120 |
| Seat 0, 80 | 47-33 (58.75%) | 47-33 (58.75%) | 0 | 0 / 0 / 80 |
| Seat 1, 80 | 53-27 (66.25%) | 53-27 (66.25%) | 0 | 0 / 0 / 80 |
| Historical Silver, 40 | 20-20 (50.00%) | 20-20 (50.00%) | 0 | 0 / 0 / 40 |
| Arch Peak, 40 | 20-20 (50.00%) | 20-20 (50.00%) | 0 | 0 / 0 / 40 |
| Alakazam capbloo Gold, 40 | 29-11 (72.50%) | 29-11 (72.50%) | 0 | 0 / 0 / 40 |
| Marnie kazuki live, 40 | 31-9 (77.50%) | 31-9 (77.50%) | 0 | 0 / 0 / 40 |

Every opponent-by-seat cell is also unchanged:

| Opponent / seat | Baseline W-L | Candidate W-L | Rate | Delta | Gains / regressions / ties |
|---|---:|---:|---:|---:|---:|
| Historical Silver / 0 | 11-9 | 11-9 | 55.00% | 0 | 0 / 0 / 20 |
| Historical Silver / 1 | 9-11 | 9-11 | 45.00% | 0 | 0 / 0 / 20 |
| Arch Peak / 0 | 6-14 | 6-14 | **30.00%** | 0 | 0 / 0 / 20 |
| Arch Peak / 1 | 14-6 | 14-6 | 70.00% | 0 | 0 / 0 / 20 |
| Alakazam capbloo Gold / 0 | 16-4 | 16-4 | 80.00% | 0 | 0 / 0 / 20 |
| Alakazam capbloo Gold / 1 | 13-7 | 13-7 | 65.00% | 0 | 0 / 0 / 20 |
| Marnie kazuki live / 0 | 14-6 | 14-6 | 70.00% | 0 | 0 / 0 / 20 |
| Marnie kazuki live / 1 | 17-3 | 17-3 | 85.00% | 0 | 0 / 0 / 20 |

The persistent severe absolute floor hidden by the 62.50% aggregate is **Arch Peak in seat 0 at 6-14 (30.00%)**; the same opponent is 14-6 (70.00%) in seat 1, a 40-point seat swing. Historical Silver in seat 1 remains a secondary floor at 9-11 (45.00%). These floors recur identically in parent and candidate; they are not new regressions, but the aggregate must not be read as uniformly strong play.

Overall seat 1 exceeds seat 0 by 7.50 points (66.25% versus 58.75%). By opponent, the seat-1 minus seat-0 gaps are Historical Silver `-10`, Arch Peak `+40`, Alakazam `-15`, and Marnie `+15` percentage points. There is absolute seat sensitivity, but no candidate-relative seat sensitivity because every paired delta is zero.

## Paired uncertainty and seed sensitivity

- McNemar discordant counts: gains `b=0`, regressions `c=0`; exact two-sided p-value `1.0`.
- Observed total discordance: `0/160`.
- Exact one-sided 95% Clopper-Pearson upper bound for total discordance: `1 - 0.05^(1/160) = 0.0185491341` or **1.8549%**.
- Since `|P(gain)-P(regression)| <= P(discordance)`, a conservative paired 95% effect bound is **[-1.8549 pp, +1.8549 pp]**.

The empirical paired standard error is zero only because all observed pair differences are zero; the exact discordance bound avoids treating this finite sample as proof of exact population equivalence. The point estimate and practical effect are zero, so this panel supports neither statistical nor practical improvement.

For seed sensitivity, equal game offsets were compared across the two panel seed bases. Candidate wins out of eight schedule cells at offsets `0..19` are:

`[6, 4, 6, 4, 6, 6, 5, 5, 4, 3, 4, 5, 4, 6, 6, 6, 6, 4, 5, 5] / 8`.

Absolute rates therefore range from `3/8 = 37.50%` to `6/8 = 75.00%`. Every offset has gains/regressions `0/0` and net delta zero, so there is absolute seed variation but no candidate-relative seed sensitivity in this schedule.

## Duplicate control, trace audit, and execution safety

- Manifest commands: `24/24` exited zero; every command used the frozen `.venv-rl` interpreter, checked battle runner, checked seeded engine, `--engine-seed`, 20 games, and max steps 1000, with the tested policy on the correct player for its seat.
- Raw summary rows: `480 = 160 baseline A + 160 baseline B + 160 candidate`.
- Started normally: `480/480`; start faults `0`.
- Action-error games / total action errors: `0 / 0`.
- Invalid results / max-step hits: `0 / 0`.
- Explicit exception records, nonzero exits, missing/malformed summaries, or missing traces: `0`.
- Identical-policy duplicate baseline A versus baseline B: result matches `160/160`, decision-count (`steps`) matches `160/160`, byte-trace SHA-256 matches `160/160`; any-field duplicate mismatches `0`.
- Candidate versus baseline A: result matches `160/160`, step-count matches `160/160`, byte-trace SHA-256 matches `160/160`; differences: **none**.

The SHA-256 inventory of all 480 trace files is `0D265A5C2F1B15F5EBC5FC0C3D34D645A16CCD0D5703C9AF190C9377BD8A2344`; the 24-summary inventory is `A62FBA5ACB4A25FA178B2FBB5A74B00207A38E8C62B18261D9EB91272EF60D84`. Each inventory hashes the UTF-8 concatenation of sorted `relative_path<TAB>file_sha256<LF>` records.

For the specifically requested 160-key candidate comparison, the pair inventory SHA-256 is `DE9C33BC143F5B518D79C70101CF1A5DC4BE1D0FF8EBE4532EAC591EF0EBAEE8`. It hashes sorted UTF-8 records `panel|opponent|seat|seed|baseline_a_trace_sha256|candidate_trace_sha256<LF>`. The identical-policy baseline-A/baseline-B pair inventory has the same digest because all three trace hashes agree on every key. No differing key exists to list.

## Acceptance checks

The controlling spec references the immutable base schedule. I treat the base numerical/safety gates as inherited and the controlling spec's natural-start values as the explicit override (`minimum_natural_starts=2`, `minimum_starts_per_seat=1`).

| Check | Independently observed result | Decision |
|---|---:|---:|
| Unique schedule keys | 160 expected = 160 unique; no missing/unexpected | PASS |
| Exact three-role schedules | 160/160 keys for baseline A, baseline B, candidate | PASS |
| Baseline duplicate result/decision equality | 160/160 and 160/160 | PASS |
| Baseline duplicate byte-trace equality | 160/160 | PASS |
| Candidate versus baseline trace comparison | 160/160 equal; 0 differences | PASS |
| Execution/start/action/exception/max-step faults | 0 / 0 / 0 / 0 / 0 | PASS |
| Paired gains at least regressions | 0 >= 0 | PASS |
| Maximum regression in any seat bucket | 0 wins (allowed at most 2) | PASS |
| Maximum regression in any opponent bucket | 0 wins (allowed at most 2) | PASS |
| Natural-start coverage | Fixed160: 0; linked frozen verification: 2 starts, one per seat | PASS only via separate verification |

Accordingly, the fixed160 run is valid and passes the supplied retention/safety checks. The recommendation is **PASS as a safety gate**, while explicitly **rejecting any claim that fixed160 itself demonstrates added strength**.

## Raw evidence hashes

| Raw file under `fixed160_parent_prefix_v1_raw` | SHA-256 |
|---|---|
| `historical_silver/paired_results.csv` | `79110266032FF39C63EE3142E72FE228DBC82DF5BBE3BFDB397D8E20FF3FBA22` |
| `historical_silver/manifest.jsonl` | `BAD2514F9137E3A8B6FA7F8C54EA003D24C9CF4FE7492840FB5183B13F3B3FB3` |
| `historical_silver/cell_summary.csv` | `BD30AEA1526B09FAE2147F5DE0D072AB56BCC0546E2B6485E5A938090F89A1F4` |
| `historical_silver/report.json` | `37706612165C1E2D80C3485C70D0AC571CF6F7148EA79C96B342390A376B7315` |
| `adjacent_population/paired_results.csv` | `F6B2596699ABB1CE767EF35B39A38A75DB4F2229DCED2132F8BFE4D9A6CA771E` |
| `adjacent_population/manifest.jsonl` | `172E18B5C9F95F0FE1D2B644D816B8C22500BBBF472CFDE1AA2AB1231CB247DC` |
| `adjacent_population/cell_summary.csv` | `BAF347F4C437B5028B053CC2601A2562DCCBD4EEC053E225505EB42258B0E96C` |
| `adjacent_population/report.json` | `AF692679EE949E2D6B72A3EE1283361A1F6A1A5C7A1DFEB16FF6F7D639BBCCE4` |

The separate natural-start source is `autonomous_gold_20260715/root_verification/archaludon_historical_silver_single_resolver_salvage_rule3_parent_prefix_v1_20260803/ROOT_PRE_FIXED160_VERIFICATION.md`, SHA-256 `34B1CFD0E78A1ADB6ABC99FA24704689B04C60235CBA3BD414B9FA372104E8CF`. Its Active/Turbo telemetry hashes are respectively `A774A2E911B3AE41008164E26A7F6E4941E2F1DD7460FC75CA2709347E5CCA84` and `0465D6DE920483A6859A000D695B5F1DC888411233748ED4738BF7521E5D3B76`; direct reads give owned-or-complete callback counts `20/10`, completions `1/1`, and irreversible-abort faults `0/0`.

## Reproducibility assumptions and calculation

1. `panel` is the immutable containing panel directory, because it is absent from each partitioned paired CSV.
2. A tested-policy win is `int(result == seat)`, per the manifest-verified policy/player placement.
3. A gain is `(baseline_win, candidate_win)=(0,1)`; a regression is `(1,0)`; all other pairs are ties.
4. `steps` is the runner's per-game decision count used by the duplicate-control gate; byte equality is independently checked with SHA-256 of each trace file.
5. Seed sensitivity is grouped by `game = seed - seed_base`, because the two frozen panels have different seed bases.
6. The fixed160 raw files contain no Rule 3 telemetry. The zero-natural-start fact is a supplied/frozen scope fact and is not inferred merely from trace identity; natural-start counts are sourced only from the separately hashed pre-fixed160 telemetry.
7. No simulations were run and no source, deck, spec, schedule, or raw result file was modified. All calculations above were recomputed read-only from the frozen specs, manifests, paired CSVs, summary rows, and trace bytes.
