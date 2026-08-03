# Independent numerical audit: Rule 8 fixed160

Audit date: 2026-08-03 (Asia/Tokyo)

## Decision

**DEFER-DORMANT. Do not integrate, promote, or widen Rule 8.**

The completed frozen run is internally valid on every persisted schedule,
duplicate-control, result, and runner-health check. It provides no strength
improvement: Rule 5 and Rule 8 are both **100-60 (62.500%)**, the paired
candidate-minus-baseline effect is **0 wins / 0.000 percentage points**, and
paired gains/regressions/ties are **0/0/160**.

The controlling activity gate does not pass. The independently root-confirmed
shadow had 30,977 callbacks, zero natural Rule 8 starts, and zero differences.
Fixed160 has zero serialized action differences across all 8,881 callbacks
controlled by the candidate policy (seat 0: 4,252; seat 1: 4,629). Under the
frozen Rule 8 contract, every natural start necessarily changes the Rule 5
parent action from `ATTACK 223` to `ATTACK 224`; therefore the observable
fixed160 natural-start count is zero and shadow plus fixed160 is **0 + 0 = 0**.
That satisfies the explicit `dormant_if_shadow_plus_fixed160_starts == 0`
condition and fails `minimum_natural_starts == 1`.

Dedicated Rule 8 internal telemetry was **not persisted** by this runner. That
missing field is kept separate below from the measured zero action-difference
count.

## Frozen identity and raw evidence

All hashes below were independently recomputed from disk.

| Artifact | SHA-256 |
|---|---|
| `autonomous_gold_20260715/evaluation_specs/archaludon_historical_silver_single_resolver_salvage_rule8_trial_v1/fixed160_spec.json` | `F791EA0BB0CF7A4A09F1D089B0AD80D5BE06F4C2E99C0780F63515166EB78B4A` |
| schedule base `autonomous_gold_20260715/evaluation_specs/archaludon_historical_silver_single_resolver_salvage_v1_rule1/fixed160_spec.json` | `E2B8986663A43A7F6F52888E487F39B8D059CDCDDF441A3E87D8C093DF15274C` |
| Rule 5 baseline `autonomous_gold_20260715/candidates/archaludon_historical_silver_single_resolver_salvage_rule5_trial_v1/main.py` | `D966E455E5110F9D5616195AEAAC8663E6A92F310DAFC4B7F79E4D37149A9C62` |
| Rule 8 candidate `autonomous_gold_20260715/candidates/archaludon_historical_silver_single_resolver_salvage_rule8_trial_v1/main.py` | `B0BD42D71617EEA041AFCF54F84B9C92FD894A2A3A6BD1CCAD95645CD1952507` |
| baseline and candidate `deck.csv` (each) | `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A` |
| `fixed160_raw/historical_silver/paired_results.csv` | `79110266032FF39C63EE3142E72FE228DBC82DF5BBE3BFDB397D8E20FF3FBA22` |
| `fixed160_raw/adjacent_population/paired_results.csv` | `F6B2596699ABB1CE767EF35B39A38A75DB4F2229DCED2132F8BFE4D9A6CA771E` |
| `fixed160_raw/historical_silver/manifest.jsonl` | `91F1706FC38A09AE48EEB79221C2EC8A158234CB3128EDD2F2E9644767AD7C10` |
| `fixed160_raw/adjacent_population/manifest.jsonl` | `BC5C28D7168E9BD640D5B571A07EB6FC823DA30383EAA699E834AE3F5E767F22` |
| `fixed160_raw/historical_silver/report.json` | `37706612165C1E2D80C3485C70D0AC571CF6F7148EA79C96B342390A376B7315` |
| `fixed160_raw/adjacent_population/report.json` | `AF692679EE949E2D6B72A3EE1283361A1F6A1A5C7A1DFEB16FF6F7D639BBCCE4` |

Raw root:
`autonomous_gold_20260715/evaluations/archaludon_historical_silver_single_resolver_salvage_rule8_trial_v1/fixed160_raw`

For a compact checksum of the complete raw corpus, 512 files totaling
89,563,502 bytes were sorted by POSIX relative path. For each file the audit
hashed `relative_path + NUL + uppercase_file_sha256 + LF`, concatenated those
records, and SHA-256 hashed the result. The resulting raw-tree digest is
`547144C999FEDE90FD6F22AA631FD2B7355C9CC294766C36BCBE0F6C80CD9C27`.
The corpus contains 4 CSV, 506 JSONL, and 2 JSON files.

## Reproducible calculation

The audit was run from the repository root with
`.venv-rl\Scripts\python.exe` and Python standard-library CSV/JSON/hash
parsing only. No simulation was run and no raw artifact was written.

For every canonical paired row:

```text
key           = (panel, opponent, int(seat), int(seed))
baseline_win  = int(int(baseline_result)  == int(seat))
candidate_win = int(int(candidate_result) == int(seat))
d             = candidate_win - baseline_win
gain          = int(d == +1)
regression    = int(d == -1)
tie           = int(d ==  0)
```

The policy/player mapping was audited before interpreting seat splits:

- `seat == 0`: the tested policy is agent A / player 0; a win is
  `result == 0`.
- `seat == 1`: the tested policy is agent B / player 1; a win is
  `result == 1`.

The expected key set was regenerated from the frozen schedule base: each
specified panel/opponent, both seats, and the 20 seeds
`seed_base + game`, `game = 0..19`. Each role's summaries (`baseline_a`,
`baseline_b`, and `candidate`) were independently keyed the same way and
compared with both the expected set and the paired CSV rows.

For duplicate control, each baseline-A record was paired with baseline-B by
panel/opponent/seat/seed and exact equality was required for `result`, `steps`,
`started`, `action_errors`, `hit_max_steps`, and trace bytes. Candidate traces
were also aligned with baseline A by `(game, step, player)` and their serialized
actions were compared. `steps` equaled the JSONL trace-line count in every
game for every role.

## Independently recomputed results

### Aggregate and panels

| Scope | n | Rule 5 W-L (rate) | Rule 8 W-L (rate) | Delta wins / pp | G/R/T |
|---|---:|---:|---:|---:|---:|
| All fixed160 | 160 | 100-60 (62.500%) | 100-60 (62.500%) | 0 / 0.000 | 0/0/160 |
| Historical Silver | 40 | 20-20 (50.000%) | 20-20 (50.000%) | 0 / 0.000 | 0/0/40 |
| Adjacent population | 120 | 80-40 (66.667%) | 80-40 (66.667%) | 0 / 0.000 | 0/0/120 |

### Opponents and seats

| Bucket | n | Rule 5 W-L (rate) | Rule 8 W-L (rate) | Delta wins / pp |
|---|---:|---:|---:|---:|
| `historical_silver` | 40 | 20-20 (50.000%) | 20-20 (50.000%) | 0 / 0.000 |
| `arch_peak` | 40 | 20-20 (50.000%) | 20-20 (50.000%) | 0 / 0.000 |
| `alakazam_capbloo_gold` | 40 | 29-11 (72.500%) | 29-11 (72.500%) | 0 / 0.000 |
| `marnie_kazuki_live` | 40 | 31-9 (77.500%) | 31-9 (77.500%) | 0 / 0.000 |
| seat 0 / agent A | 80 | 47-33 (58.750%) | 47-33 (58.750%) | 0 / 0.000 |
| seat 1 / agent B | 80 | 53-27 (66.250%) | 53-27 (66.250%) | 0 / 0.000 |

The aggregate absolute seat split is +7.500 percentage points for seat 1,
identically for Rule 5 and Rule 8. It is an environment/opponent interaction,
not candidate gain.

### Absolute cell floors

| Opponent | Seat | n | Rule 5 W-L (rate) | Rule 8 W-L (rate) | Delta wins / pp |
|---|---:|---:|---:|---:|---:|
| `historical_silver` | 0 | 20 | 11-9 (55.000%) | 11-9 (55.000%) | 0 / 0.000 |
| `historical_silver` | 1 | 20 | 9-11 (45.000%) | 9-11 (45.000%) | 0 / 0.000 |
| `arch_peak` | 0 | 20 | 6-14 (30.000%) | 6-14 (30.000%) | 0 / 0.000 |
| `arch_peak` | 1 | 20 | 14-6 (70.000%) | 14-6 (70.000%) | 0 / 0.000 |
| `alakazam_capbloo_gold` | 0 | 20 | 16-4 (80.000%) | 16-4 (80.000%) | 0 / 0.000 |
| `alakazam_capbloo_gold` | 1 | 20 | 13-7 (65.000%) | 13-7 (65.000%) | 0 / 0.000 |
| `marnie_kazuki_live` | 0 | 20 | 14-6 (70.000%) | 14-6 (70.000%) | 0 / 0.000 |
| `marnie_kazuki_live` | 1 | 20 | 17-3 (85.000%) | 17-3 (85.000%) | 0 / 0.000 |

The 62.500% aggregate hides a severe recurring Archaludon-anchor weakness:
both `historical_silver` and `arch_peak` are only 50.000% overall, and the
absolute floor is **30.000% against `arch_peak` in seat 0**. The `arch_peak`
seat gap is 40.000 points. Rule 8 neither causes a regression nor repairs this
floor; every cell is exactly neutral.

### Seed sensitivity

- At every one of the 160 individual schedule keys, paired delta is zero.
- At every one of the 40 actual engine-seed values, paired delta is zero.
- Grouping common game offsets 0..19 across all eight opponent/seat cells,
  absolute win rates range from 37.500% (offset 9, 3/8) to 75.000% (eight
  offsets, 6/8); population SD is 11.859 points. This is descriptive absolute
  seed variation shared exactly by both policies, not candidate sensitivity.
- Adjacent-population actual-seed rates range from 33.333% to 83.333% over six
  cells per seed. Historical-Silver actual-seed rates are 50.000% over two
  seats per seed. These small per-seed denominators are not strength estimates.

## Paired uncertainty and practical effect

The matched-pair differences are all zero: 0 candidate-only wins, 0
baseline-only wins, and 160 concordant pairs. The exact McNemar/sign comparison
has no discordant pairs (conventionally `p = 1.0`; its conditional odds ratio
is not identifiable). This is no evidence of either statistical or practical
improvement.

To avoid reporting the empirical paired-bootstrap degeneracy `[0, 0]` as if it
were population certainty, let `q` be the probability that a future matched
pair is discordant. With 0 discordances in 160 pairs, the exact one-sided 95%
binomial upper bound is:

```text
q_upper = 1 - 0.05 ** (1 / 160) = 0.0185491341
```

Because the net paired rate difference satisfies `|delta| <= q`, a conservative
95% interval is **[-1.855, +1.855] percentage points** if these scheduled rows
are treated as a sample from a target seed distribution. The observed fixed
schedule effect itself is exactly 0.000 points. Corresponding conservative
bounds are +/-7.216 points for each 40-game opponent bucket and +/-13.911
points for each 20-game seat/opponent cell. None supports a meaningful positive
effect, and no positive aggregate delta exists to interpret.

## Integrity, duplicate control, and execution health

| Check | Independent result | Gate |
|---|---:|---:|
| canonical paired rows | 160 | PASS |
| unique `(panel, opponent, seat, seed)` keys | 160; 0 duplicates | PASS |
| expected versus observed key set | 0 missing; 0 unexpected | PASS |
| game/seed and seed-base mismatches | 0 | PASS |
| recomputed versus stored `baseline_win` mismatches | 0 | PASS |
| recomputed versus stored `candidate_win` mismatches | 0 | PASS |
| per-role schedule set | 160/160 exact for each of three roles | PASS |
| manifest commands | 24; all use `.venv-rl`, `--engine-seed`, 20 games, max 1,000 | PASS |
| nonzero process exits | 0/24 | PASS |
| summary records | 480/480 present and JSON-readable | PASS |
| start faults / invalid results | 0 / 0 | PASS |
| action errors / max-step hits | 0 / 0 | PASS |
| explicit summary exception keys or exception strings | 0 / 0 | PASS (runner-observable) |
| baseline-A versus baseline-B result mismatches | 0/160 | PASS |
| baseline-A versus baseline-B decision-count mismatches | 0/160 | PASS |
| baseline-A versus baseline-B byte-trace mismatches | 0/160 | PASS |
| candidate versus baseline result/step CSV-summary mismatches | 0/160 | PASS |
| candidate versus baseline byte-trace mismatches | 0/160 | PASS |
| trace key/length mismatches | 0 / 0 | PASS |
| candidate versus baseline serialized action differences | 0/17,859 total callbacks; 0/8,881 candidate-policy callbacks | PASS/neutral |
| paired gains at least regressions | 0 >= 0 | PASS/neutral |
| seat/opponent regression floor | worst delta 0 wins | PASS |
| Rule 8 natural-start minimum | observable fixed160 0; combined shadow+fixed160 0 | **FAIL: DORMANT** |

The identical-policy control was audited before any seat delta was interpreted.
All 160 baseline-A/baseline-B games match in result, decision count, and raw
trace bytes. Baseline A, baseline B, and candidate each total 17,859 decisions,
and each game's `steps` equals its trace-line count.

## Telemetry distinction and assumptions

Measured zeroes:

- Fixed160 serialized action differences are zero over 17,859 aligned trace
  callbacks and zero over the 8,881 callbacks belonging to the tested policy.
- Candidate/baseline result, step, and trace-byte differences are zero in all
  160 games.
- Runner exits, starts, invalid results, action errors, explicit exception
  records/strings, and max-step hits are zero on the persisted artifacts.

Missing telemetry, not asserted as a direct zero counter:

- The summaries, reports, and traces contain no persisted `rule_id`,
  `selected_source`, `proposal_semantic`, `proof_gates`, `rejection_reason`, or
  equivalent Rule 8 telemetry record. The audit found zero records containing
  those fields; this means the direct fixed160 natural-start counter is absent.
- For the same reason, the candidate's internally caught
  `wrapper_exception:*` rejection-reason counter is not independently available.
  The runner-observable exception count is zero, but a separate internal caught
  exception count must not be relabeled as measured zero.

The zero fixed160 natural-start conclusion is an explicit contract inference,
not a hidden telemetry count: the frozen source hash and activation contract
permit a Rule 8 start only when it returns `ATTACK 224` instead of the parent
`ATTACK 223`. Exact action and trace equality therefore exclude any natural
start in these 160 games. The shadow fact (30,977 callbacks, zero starts, zero
differences) was supplied as independently root-confirmed evidence and was not
recomputed from fixed160 files.

The uncertainty interval assumes the fixed keys can be viewed as sampled
matched pairs from a target seed distribution; it does not change the exact
fixed-schedule result. No claim of strength is inferred from the neutral
aggregate, and the matrix must not be widened to search for an activation.

