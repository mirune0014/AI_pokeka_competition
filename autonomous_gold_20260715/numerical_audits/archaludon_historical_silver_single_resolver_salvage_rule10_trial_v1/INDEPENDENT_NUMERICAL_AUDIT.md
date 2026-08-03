# Independent numerical audit — Rule 10 fixed160

## Decision

The completed fixed160 execution is **valid**, but Rule 10 is **not adoptable**.
Baseline and candidate are exactly tied at 100-60 (62.5%), with paired
gains/regressions/ties of 0/0/160 and a practical effect of 0.0 percentage
points. All candidate traces are byte-identical to the corresponding baseline
traces. Because a Rule 10 entry necessarily changes the parent's registered
ATTACK action into a Full Metal Lab PLAY action, this proves zero fixed160
starts and therefore zero complete fixed160 FML-to-same-attack transactions.
The hash-verified replay shadow likewise has 30,977 callbacks but
starts/completions/aborts/faults of 0/0/0/0. The frozen requirement of at least
one complete natural transaction fails.

**Recommendation: FAIL adoption; DEFER-DORMANT.** Preserve Rule 5. Do not infer
strength from the aggregate rate, integrate Rule 10, or widen its entry gates.

## Frozen identity and raw evidence

- Rule 10 spec:
  autonomous_gold_20260715/evaluation_specs/archaludon_historical_silver_single_resolver_salvage_rule10_trial_v1/fixed160_spec.json
  — SHA-256 B647B547DCB377F156ED24B32AA0B77A0CDA7BB9618DDBE5FF7E11D006A02EE0.
- Inherited schedule spec:
  autonomous_gold_20260715/evaluation_specs/archaludon_historical_silver_single_resolver_salvage_v1_rule1/fixed160_spec.json
  — SHA-256 E2B8986663A43A7F6F52888E487F39B8D059CDCDDF441A3E87D8C093DF15274C.
- Baseline Rule 5 main.py — SHA-256
  D966E455E5110F9D5616195AEAAC8663E6A92F310DAFC4B7F79E4D37149A9C62.
- Candidate Rule 10 main.py — SHA-256
  2C9249F74CA37429DECEA4801E736E13085E50C19956BB0C75176B9D6759245A.
- Both decks — SHA-256
  08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A.
- Raw root:
  autonomous_gold_20260715/evaluations/archaludon_historical_silver_single_resolver_salvage_rule10_trial_v1/fixed160_raw
  — 512 files, 89,564,043 bytes, deterministic tree SHA-256
  9B872C03A6D21192BAED22FA0E865600EE70B75B248694A99E3377C5951A92DC.
- Historical-Silver raw panel — 130 files, 24,379,412 bytes, tree SHA-256
  F165518859743A9A26CC27393D217522C43B679F4E6DEE0803857B1F9D3EB053.
- Adjacent-population raw panel — 382 files, 65,184,631 bytes, tree SHA-256
  8D239505481FB80415B83B979024516DF82969A216DB2C1D9BA91239BD17567A.

The tree digest is reproducible: for every file in sorted POSIX-relative-path
order, calculate the uppercase file SHA-256 and hash the concatenation of
relative path, NUL, file SHA-256, and LF.

| Raw file | SHA-256 |
|---|---|
| historical_silver/manifest.jsonl | 628F8166906FC2759349079585E52BB2840E9F79943D0D20CDD8544D8C70E73A |
| historical_silver/paired_results.csv | 79110266032FF39C63EE3142E72FE228DBC82DF5BBE3BFDB397D8E20FF3FBA22 |
| historical_silver/cell_summary.csv | BD30AEA1526B09FAE2147F5DE0D072AB56BCC0546E2B6485E5A938090F89A1F4 |
| historical_silver/report.json | 37706612165C1E2D80C3485C70D0AC571CF6F7148EA79C96B342390A376B7315 |
| adjacent_population/manifest.jsonl | B02FF09E493DA8A14CE46C787C3547F8DD9DD506CA45EA51B09148407A3C7D83 |
| adjacent_population/paired_results.csv | F6B2596699ABB1CE767EF35B39A38A75DB4F2229DCED2132F8BFE4D9A6CA771E |
| adjacent_population/cell_summary.csv | BAF347F4C437B5028B053CC2601A2562DCCBD4EEC053E225505EB42258B0E96C |
| adjacent_population/report.json | AF692679EE949E2D6B72A3EE1283361A1F6A1A5C7A1DFEB16FF6F7D639BBCCE4 |

## Reproducible calculation and integrity checks

The exact key is (panel, opponent, seat, seed). For seat 0, the evaluated
policy is agent A/player 0 and a win is result == 0. For seat 1, it is agent
B/player 1 and a win is result == 1. Baseline and candidate wins were
recomputed separately from each role's raw summary result; no player-0 counter
was reused for player-1 runs. A gain is candidate_win=1 and baseline_win=0; a
regression is the reverse; otherwise the pair is tied.

- The expected schedule has 160 keys and 40 distinct numeric seeds:
  271828182-271828201 and 271958313-271958332. Baseline A, duplicate baseline
  B, and candidate each have exactly 160 rows, 160 unique keys, zero duplicate
  keys, zero missing keys, and zero extra keys. Their key sets exactly equal
  the frozen schedule.
- The two stored paired CSVs contain 160 rows and 160 unique exact keys. Against
  the raw summaries, stored baseline/candidate result mismatches, win
  mismatches, step mismatches, game mismatches, and seed-base mismatches are all
  zero. Stored cell summaries and reports also have zero aggregate mismatches.
- All 24 manifest commands exited 0, used .venv-rl/Scripts/python.exe,
  run_local_battle.py with --engine-seed, 20 games, and max_steps=1000.
  Manifest sequence duplicates are zero.
- The 480 raw summary rows all started, all have binary results, and contain
  zero action errors and zero max-step hits. Thus start faults, nonzero exits,
  and observed uncaught execution exceptions are zero.
- Baseline A versus baseline B: result differences 0/160, decision-count
  differences 0/160, normalized-summary differences 0/160, and byte-trace
  differences 0/160. This satisfies the mandatory duplicate control exactly.
- Candidate versus baseline A: result differences 0/160, decision-count
  differences 0/160, normalized-summary differences 0/160, and byte-trace
  differences 0/160. Candidate also matches baseline B in all 160 byte traces.
  All 480 trace files exist, and every trace line count equals its summary step
  count.
- Each role has 17,859 total steps: mean 111.619, median 125, range 17-165.
  Baseline/candidate step delta is exactly zero on every key.

## Independently recomputed results

Aggregate baseline: **100-60, 62.5%**. Aggregate candidate: **100-60,
62.5%**. Paired delta: **0 wins, 0.0 pp**. G/R/T: **0/0/160**.

| Opponent and seat | Baseline | Candidate | Candidate delta | Absolute floor |
|---|---:|---:|---:|---:|
| historical_silver, player 0 | 11/20 (55%) | 11/20 (55%) | 0 (0 pp) | 9 losses |
| historical_silver, player 1 | 9/20 (45%) | 9/20 (45%) | 0 (0 pp) | 11 losses |
| arch_peak, player 0 | 6/20 (30%) | 6/20 (30%) | 0 (0 pp) | 14 losses |
| arch_peak, player 1 | 14/20 (70%) | 14/20 (70%) | 0 (0 pp) | 6 losses |
| alakazam_capbloo_gold, player 0 | 16/20 (80%) | 16/20 (80%) | 0 (0 pp) | 4 losses |
| alakazam_capbloo_gold, player 1 | 13/20 (65%) | 13/20 (65%) | 0 (0 pp) | 7 losses |
| marnie_kazuki_live, player 0 | 14/20 (70%) | 14/20 (70%) | 0 (0 pp) | 6 losses |
| marnie_kazuki_live, player 1 | 17/20 (85%) | 17/20 (85%) | 0 (0 pp) | 3 losses |

Opponent aggregates are historical_silver 20/40 (50%), arch_peak 20/40
(50%), alakazam_capbloo_gold 29/40 (72.5%), and marnie_kazuki_live 31/40
(77.5%), with zero candidate delta in every opponent bucket. Aggregate player
0 is 47/80 (58.75%); aggregate player 1 is 53/80 (66.25%). Candidate-baseline
seat deltas are both zero, while the shared absolute player-1 advantage is 7.5
pp.

The 62.5% average hides a recurring severe floor: arch_peak/player 0 is only
30% across 20 seeds, losing 14 times, while the opposite seat is 70% (a 40 pp
seat split). Historical-Silver/player 1 is another sub-50% floor at 45% over
20 seeds. Cell rates span 30%-85%, a 55 pp range. These floors belong equally
to Rule 5 and Rule 10; Rule 10 did not repair them.

Candidate-minus-baseline delta is zero on every one of the 160 exact seed keys
and after aggregation over each of the 40 numeric seeds. Pooled game-offset
rates vary from 37.5% to 75% (n=8 per offset), but candidate and baseline move
identically. With only one seed base per panel/opponent composition, that
absolute variation is confounded and cannot be attributed to Rule 10.

## Paired uncertainty and effect size

There are zero discordant pairs, so the observed paired difference is exactly
0.0 pp and exact McNemar evidence contains no direction of improvement. For a
nondegenerate uncertainty statement, the exact two-sided 95% Clopper-Pearson
interval for the probability of any discordance after observing 0/160 is
0%-2.279%. Since the absolute paired mean difference cannot exceed the
discordance probability, this induces a conservative paired-delta bound of
**-2.279 pp to +2.279 pp**. The candidate's absolute 62.5% rate has a Wilson
95% interval of 54.79%-69.63%, but that unpaired absolute interval is not
evidence of improvement.

The practical effect is zero wins, zero changed outcomes, zero changed
decision counts, and zero changed trace bytes. This is neither statistically
nor practically meaningful improvement.

## Natural mechanism gate and acceptance checks

The fixed160 traces prove zero Rule 10 starts: the inspected implementation's
start path stores FML_EMITTED and returns the bound FML PLAY in place of the
parent ATTACK, which would necessarily change that trace action. With 160/160
candidate traces byte-identical to baseline, fixed160 has starts/completions of
0/0 and no possible Rule 10 lifecycle abort or owner fault.

The independent shadow artifacts are:

- autonomous_gold_20260715/implementation/archaludon_historical_silver_single_resolver_salvage_rule10_trial_v1/shadow_summary.json
  — SHA-256 10CFB7339BB130D51267F96A8351CB3A8E0718E578887DDBFBA6A25BE50DEA46;
- shadow_activity_events.json and shadow_differences.json — each SHA-256
  4F53CDA18C2BAA0C0354BB5F9A3ECBE5ED12AB4D8E11BA873C2F11161202B945.

The shadow reports 252 readable replays, one documented malformed replay,
30,977 callbacks, zero action/first differences, and activity
starts/completions/aborts/faults of 0/0/0/0. Combined natural starts and
complete transactions across shadow plus fixed160 remain 0 and 0.

| Frozen check | Result |
|---|---|
| Candidate at least 100/160 | PASS, exactly 100/160 |
| Paired gains at least regressions | PASS but vacuous, 0 = 0 |
| Historical-Silver non-worse | PASS, 20/40 = 20/40 |
| No opponent-seat regression of -3 or worse | PASS, all cell deltas 0 |
| No aggregate-seat regression of -2 or worse | PASS, both seat deltas 0 |
| Exact schedule and duplicate equality | PASS |
| Zero execution/start/action/max-step faults | PASS |
| Zero harmful or unclassified first differences | PASS, no differences |
| At least one natural Rule 10 start | **FAIL, 0** |
| At least one complete natural FML-to-same-attack transaction | **FAIL, 0** |

Numerical safety is therefore neutral and valid, but the mechanism is dormant
and unevidenced. The failed natural-completion gate controls the final adoption
decision.

## Assumptions and scope

1. The frozen wrapper inherits the hashed fixed160 schedule and changes only
   the declared baseline/candidate/output/gates; that reference hash matched.
2. Results are interpreted only as winning player indices. All 480 raw results
   were 0 or 1; there were no draws or unresolved games.
3. Byte-identical candidate/baseline traces imply zero Rule 10 starts only
   because the verified Rule 10 entry action is necessarily FML PLAY rather
   than the parent's ATTACK. No claim is made about which fail-closed entry
   predicate caused dormancy.
4. Shadow counts come from the hash-verified supplied shadow artifacts; the
   single malformed replay is not treated as mechanism evidence.
5. The paired uncertainty bound treats the 160 frozen keys as paired
   observations and makes no claim that opponent buckets or seeds are iid.
6. No simulation was run or expanded. Candidate, decks, specs, and raw runner
   outputs were read only.
