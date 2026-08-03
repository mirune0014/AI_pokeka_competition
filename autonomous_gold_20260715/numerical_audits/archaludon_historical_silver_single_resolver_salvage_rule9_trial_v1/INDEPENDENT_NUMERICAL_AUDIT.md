# Independent numerical audit — Rule 9 fixed160

Audit date: 2026-08-03 JST  
Scope: completed immutable raw outputs only; no simulation was run and no source, deck, schedule, checkpoint, or raw result was changed.

## Outcome

**Evaluation integrity: usable for deterministic parity evidence. Stage decision: FAIL / `DEFER-DORMANT`; do not integrate Rule 9.**

The independently recomputed comparison is an exact tie: Rule 5 baseline **100-60 (62.50%)** and Rule 9 candidate **100-60 (62.50%)**, paired **G/R/T = 0/0/160**, observed change **0 wins / 0.00 pp**. All 160 candidate traces are byte-identical to their paired baseline traces. This is no evidence of a statistically or practically meaningful improvement.

The activity gate does not pass. The raw runner did not persist Rule 9's in-memory owner telemetry or activity counters. Consequently, trace equality must **not** be interpreted as zero entry starts: a Rule 9 start emits the same Gear action as its parent. An exhaustive trace scan found no qualifying natural complete Gear -> revealed Boss -> bound target -> same attack transaction. Thus the required `minimum_complete_boss_hit_transactions = 1` is unmet (**0 proven**), and starts/hits cannot be certified. Numerical parity cannot substitute for this mechanism-coverage gate.

## Frozen identity and raw artifacts

All 28 hash-addressed inputs referenced by the effective overlay/base specification independently matched, including the engine, checked runners, opponents, strategy, verification, policies, and decks.

| Artifact | SHA-256 |
|---|---|
| `autonomous_gold_20260715/evaluation_specs/archaludon_historical_silver_single_resolver_salvage_rule9_trial_v1/fixed160_spec.json` | `DC4F17D354374B3CA048CB1DEA3EDAAED1CBB9AAC7FE5063DD5956AB75CCDE4B` |
| Rule 5 baseline `autonomous_gold_20260715/candidates/archaludon_historical_silver_single_resolver_salvage_rule5_trial_v1/main.py` | `D966E455E5110F9D5616195AEAAC8663E6A92F310DAFC4B7F79E4D37149A9C62` |
| Rule 9 candidate `autonomous_gold_20260715/candidates/archaludon_historical_silver_single_resolver_salvage_rule9_trial_v1/main.py` | `FC2ACC8F1AA08AC32D85B20001E420D9D036853B117FF11539D985D99B7395D0` |
| Both policy decks | `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A` |

Raw root: `autonomous_gold_20260715/evaluations/archaludon_historical_silver_single_resolver_salvage_rule9_trial_v1/fixed160_raw`

| Raw artifact | SHA-256 |
|---|---|
| `historical_silver/paired_results.csv` | `79110266032FF39C63EE3142E72FE228DBC82DF5BBE3BFDB397D8E20FF3FBA22` |
| `historical_silver/manifest.jsonl` | `2DED90E926B22A51F5218905D9F6A0BD3F892605419AFD52A9DAEC4528C83191` |
| `historical_silver/cell_summary.csv` | `BD30AEA1526B09FAE2147F5DE0D072AB56BCC0546E2B6485E5A938090F89A1F4` |
| `historical_silver/report.json` | `37706612165C1E2D80C3485C70D0AC571CF6F7148EA79C96B342390A376B7315` |
| `adjacent_population/paired_results.csv` | `F6B2596699ABB1CE767EF35B39A38A75DB4F2229DCED2132F8BFE4D9A6CA771E` |
| `adjacent_population/manifest.jsonl` | `769C0A445E4225BF91CD95758B4753B4AC62C084FE796040765CC9F6D7391CE0` |
| `adjacent_population/cell_summary.csv` | `BAF347F4C437B5028B053CC2601A2562DCCBD4EEC053E225505EB42258B0E96C` |
| `adjacent_population/report.json` | `AF692679EE949E2D6B72A3EE1283361A1F6A1A5C7A1DFEB16FF6F7D639BBCCE4` |

For compact whole-panel integrity, I also calculated SHA-256 over sorted UTF-8 rows `relative_posix_path<TAB>file_sha256<LF>` for every file in each raw panel: historical Silver **130 files / 24,379,241 bytes**, digest `FA32FC5D34A42E89E3F38F267F802EF743BA18C8471251BEF1A5413DAC36B4A6`; adjacent population **382 files / 65,184,224 bytes**, digest `459A09B9515F3806951855215561C399805AF2438A90FF37C4D975595C4B0671`.

## Command deviation

The parent-requested outer prefix was `py -3.11 -B`; the execution operator instead used `.venv-rl\Scripts\python.exe -B` for the same Rule 9 `run_fixed160.py --execute` wrapper. This exact outer invocation is not stored in the raw manifests, so the discrepancy statement comes from the immutable handoff and is recorded rather than silently omitted.

This is a procedural deviation, but it does **not** invalidate these persisted results:

- the used virtual-environment interpreter currently identifies as **Python 3.11.6** (current executable SHA-256 `4BDDD834FB6FC274CC20FA7CBFAA6E9B5ADE6309429EB96A635538DBA5D4A3AE`), matching the requested Python 3.11 line;
- the frozen base specification itself names `.venv-rl/Scripts/python.exe` for repository battle commands;
- all **24/24** persisted inner manifest commands use the absolute `.venv-rl\Scripts\python.exe`, include `--engine-seed`, and exited 0;
- all 28 frozen file checks, the exact 160-key schedule, duplicate controls, and handed-off paired-result hashes independently match.

The manifests establish the interpreters and arguments of the actual battle subprocesses, which are the result-producing commands. The outer-launch deviation therefore does not change the audited matrix or engine seeding.

## Schedule, execution, and duplicate controls

The policy/player mapping was applied directly from raw `result`, which is the winning player index:

- seat 0: tested policy is agent A / player 0; win iff `result == 0`;
- seat 1: tested policy is agent B / player 1; win iff `result == 1`.

No player-0 counter was reused for player-1 rows.

- Schedule key: `(panel, opponent, seat, seed)`.
- Expected/observed unique keys: **160/160**; duplicates 0, missing 0, extra 0.
- `seed == seed_base + game`: **160/160**.
- Baseline A, baseline B, and candidate each cover exactly the same 160 keys.
- Persisted win-column disagreements with seat-relative recomputation: **0/320 fields**.
- Paired CSV result/step disagreements with source summaries: **0**.
- Manifest subprocesses: **24**, nonzero exits 0; all use seeded engine execution.
- Summary records: **480** (160 per role); `started=false` 0, action errors 0, max-step hits 0, nonterminal results 0.
- Identical-policy duplicate control, on every bucket/seat/seed: result and decision count **160/160 exact**; checked summary tuple `(seed,result,steps,turn,action_errors,hit_max_steps)` **160/160 exact**; trace bytes **160/160 exact**.
- Candidate versus baseline: summaries excluding the role-specific trace pathname **160/160 exact**; trace bytes **160/160 exact**; action-difference games 0 and action-difference callbacks 0.

The process-level execution gates pass. One coverage limitation remains: the candidate catches its own wrapper exceptions and records `wrapper_exception:*` only in `_last_telemetry`, which this runner does not serialize. Therefore “zero caught internal Rule 9 wrapper exceptions in fixed160” is **not directly proven** by the raw format; zero exits/action errors and parity traces do not distinguish a dormant rule from a fail-closed caught exception. The supplied separate shadow result reports 30,977 callbacks and Rule 9 faults 0, but that is shadow evidence, not a persisted fixed160 counter.

## Independently recomputed comparison

| Bucket | N | Baseline W-L / rate | Candidate W-L / rate | Delta | G/R/T |
|---|---:|---:|---:|---:|---:|
| Historical Silver | 40 | 20-20 / 50.00% | 20-20 / 50.00% | 0 / 0.00 pp | 0/0/40 |
| Adjacent population | 120 | 80-40 / 66.67% | 80-40 / 66.67% | 0 / 0.00 pp | 0/0/120 |
| **Aggregate** | **160** | **100-60 / 62.50%** | **100-60 / 62.50%** | **0 / 0.00 pp** | **0/0/160** |

| Opponent / seat | N | Baseline | Candidate | Delta |
|---|---:|---:|---:|---:|
| Historical Silver / 0 | 20 | 11-9 / 55% | 11-9 / 55% | 0 |
| Historical Silver / 1 | 20 | 9-11 / 45% | 9-11 / 45% | 0 |
| Arch Peak / 0 | 20 | 6-14 / **30%** | 6-14 / **30%** | 0 |
| Arch Peak / 1 | 20 | 14-6 / 70% | 14-6 / 70% | 0 |
| Alakazam Capbloo Gold / 0 | 20 | 16-4 / 80% | 16-4 / 80% | 0 |
| Alakazam Capbloo Gold / 1 | 20 | 13-7 / 65% | 13-7 / 65% | 0 |
| Marnie Kazuki Live / 0 | 20 | 14-6 / 70% | 14-6 / 70% | 0 |
| Marnie Kazuki Live / 1 | 20 | 17-3 / 85% | 17-3 / 85% | 0 |

Opponent totals are Historical Silver 20/40 (50%), Arch Peak 20/40 (50%), Alakazam 29/40 (72.5%), and Marnie 31/40 (77.5%) for both policies. Overall seat totals are seat 0 **47/80 (58.75%)** and seat 1 **53/80 (66.25%)**, a 7.5 pp absolute seat split shared by both policies.

The severe absolute floor is **Arch Peak seat 0: 6/20 (30%)**, hidden by the opposite-seat 14/20 (70%) and the 50% opponent average. It recurs unchanged in baseline and candidate. The matrix has only one seed base per panel/bucket, so recurrence across independent seed blocks cannot be established; claiming recovery from this average would be unjustified. The next-lowest cell is Historical Silver seat 1 at 45%.

Every one of the 160 paired keys has zero candidate delta. Across the 20 exact Historical-Silver seeds, each two-seat stratum is 50%; across the 20 adjacent seed values, the absolute candidate rate ranges 33.33%-83.33% over six games per seed, while paired delta remains 0 for every seed. There is only one base seed per panel, so between-seed-base sensitivity is not estimable.

### Paired uncertainty and effect size

There are no discordant pairs. Rather than report the degenerate paired bootstrap `[0,0]` as certainty, I bounded the probability of any paired discordance. For `0/160`, the two-sided 95% exact Clopper-Pearson upper bound is

`u = 1 - 0.025^(1/160) = 0.0227917495`.

Because the magnitude of the net paired win-rate difference cannot exceed the discordance probability, a conservative 95% paired interval for the change is **[-2.28, +2.28] pp**. Observed practical effect is exactly **0.00 pp**. The data therefore support behavioral parity on this schedule, not a meaningful improvement.

## Rule 9 activity audit

The raw schema contains no `rule9_start`, hit, miss, completion, abort, fault, owner, proposal, or `_last_telemetry` field. The trace files contain observations and emitted actions only. Across **8,881 candidate-policy callbacks**, all candidate actions and full traces equal baseline.

The scan found **236** candidate-owned Gear reveal prompts: 125 reveals contained at least one Boss and 111 contained no Boss. All 236 reveal actions were nonempty. Boss moved immediately from LOOKING to hand in 76 cases. These are ordinary observable Gear/Boss events and cannot be attributed to Rule 9 because the parent traces are identical; in particular, an entry start and even a Boss selection can coincide with the parent semantic action.

No Rule 9 miss-empty emission was observed: all 111 no-Boss reveal actions were nonempty. Starts and Boss hits remain **unknown, with 0 proven**, rather than proven zero.

An ordered same-turn scan found six physical Gear -> Boss -> switch -> Metal Defender patterns. Three contain intervening unrelated parent actions and therefore cannot be the bounded Rule 9 continuation. The other three are transaction-shaped but fail a necessary entry certificate:

- Historical Silver, seat 0, game 4, seed `271828186`: own prizes 2; opponent Bench is Cinderace at 110 HP (KO but one prize) plus Archaludon ex at 300 HP (two prizes but not KO by Metal Defender 220).
- Historical Silver, seat 0, game 13, seed `271828195`: own prizes 5; no single visible Bench target can take all five.
- Arch Peak, seat 0, game 12, seed `271958325`: own prizes 2; opponent Bench is Archaludon ex at 300 HP plus Duraludon at 130 HP, again giving “two prizes but not KO” versus “KO but one prize.”

The three intervening-action shapes likewise have own-prize/target states incompatible with the certificate (Historical Silver seat 1 seed `271828197`, own prizes 3 and only a 130-HP Duraludon Bench; Arch Peak seat 0 seed `271958329`, own prizes 3 and two 130-HP Duraludon; Marnie seat 1 seed `271958325`, own prizes 5).

Accordingly, the raw data establish **0 proven natural complete transactions**. They do not establish that internal entry starts were exactly zero. This is precisely the distinction required by the frozen same-action entry design.

## Gate decision

| Acceptance check | Result |
|---|---|
| Frozen hashes and exact 160-key schedule | PASS |
| Duplicate summary and byte-trace equality, all cells | PASS, 160/160 |
| Exits, starts, action errors, max steps, terminal results | PASS at runner/process level |
| Fixed160 caught internal wrapper exceptions | NOT OBSERVABLE in persisted schema |
| Candidate at least 100/160 | PASS exactly, 100/160 |
| Paired gains at least regressions | PASS only as tie, 0 >= 0 |
| Historical-Silver anchor non-worse | PASS as tie, 20/40 versus 20/40 |
| Seat/opponent/cell regression limits | PASS, every delta 0 |
| Harmful/unclassified trace differences | PASS, no trace differences |
| At least one natural start and one per seat | FAIL as evidence gate: 0 proven; actual entry count unavailable |
| At least one complete natural Boss-hit transaction | **FAIL: 0 proven, required 1** |

The conditional `dormant_if_shadow_plus_fixed160_starts = 0` cannot be evaluated as an exact counter sum because fixed160 starts were not serialized. That missing value is not imputed as zero. Nevertheless, the independent adoption requirement is at least one **proven complete** natural transaction, and that requirement fails. The correct bounded outcome is therefore **`DEFER-DORMANT` / reject integration**, without widening the rule or expanding the matrix.

## Reproducible calculation and assumptions

The audit used `.venv-rl\Scripts\python.exe` with Python's standard `csv`, `json`, `hashlib`, and `pathlib` modules, read-only. Core definitions were:

```text
key = (panel, opponent, int(seat), int(seed))
baseline_win  = int(int(baseline_result)  == int(seat))
candidate_win = int(int(candidate_result) == int(seat))
G = count(candidate_win == 1 and baseline_win == 0)
R = count(candidate_win == 0 and baseline_win == 1)
T = N - G - R
duplicate tuple = (seed, result, steps, turn, action_errors, hit_max_steps)
```

Expected keys were generated directly from the frozen base panels, opponents, both seats, `games_per_seat = 20`, and `seed = seed_base + game`, then compared as sets with each role's summary keys. Trace equality used raw byte comparison; action differences additionally parsed every JSONL row. Group totals were recomputed from `result`, never trusted from the runner aggregates. The uncertainty bound used the formula shown above.

Assumptions are limited to: (1) the audited files are the immutable artifacts identified by the hashes in this report; (2) `run_local_battle.py`'s documented `result` is the winning player index; (3) all terminal results are 0 or 1, as verified; (4) the supplied 30,977-callback shadow counters are separate parent evidence and are not treated as fixed160 telemetry; and (5) action traces can establish emitted behavior but cannot reveal an unpersisted in-memory Rule 9 owner when its action equals the parent.
