# Fixed760 independent numerical audit

## Material Passport

- Origin Skill: experiment-agent
- Origin Mode: validate
- Origin Date: 2026-08-01
- Verification Status: ANALYZED
- Version Label: fixed760_audit_v1

## Decision

**PASS all supplied fixed760 gates; PASS parent-retention/non-regression; no evidence of a strength gain.** The candidate and direct parent each score **476-284 (62.6316%)**, with paired **gain 0 / regression 0 / tie 760** and zero delta in every panel/opponent/seat cell. The candidate does change behavior: 45/760 candidate traces differ, and the first difference in all 45 is a direct tested-policy action. Every changed game was already a win under both policies and the candidate merely ended it sooner. This is mechanism activation and execution shortening, not terminal strength improvement.

The historical-Silver anchor is preserved at 100-100 (50.0%), and the adjacent panel is preserved at 376-184 (67.1429%). The adjacent average hides a recurring severe floor against `kang_crustle`: 14/40 (35.0%) in seat 0 and 13/40 (32.5%) in seat 1. Thus adjacent **non-regression** passes, but the inherited Kang/Crustle weakness remains unresolved.

## Immutable inputs and raw provenance

| Item | Path | SHA-256 |
|---|---|---|
| Spec | `autonomous_gold_20260715/evaluation_specs/archaludon_explorer_certified_attack_deadline_productive_prefix_v1/fixed760_spec.json` | `22CBACA72FCD23D0909C205D8EF05FF3E8630998F687A2A054AAE937EC0E492F` |
| Direct parent `main.py` | `autonomous_gold_20260715/candidates/archaludon_purpose_first_pokegear_boss_transaction_v1/main.py` | `558EE5DB29E001428B0D59813613FABEE8E15B96E422746C104BDFAB4DC22DB6` |
| Candidate `main.py` | `autonomous_gold_20260715/candidates/archaludon_explorer_certified_attack_deadline_productive_prefix_v1/main.py` | `E19A2CBF2C0F9626D8530263CB13750568F8C7B9739F4A3E9E43B9EDF4B44669` |
| Both decks | respective candidate directories, `deck.csv` | `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A` |
| Raw root | `autonomous_gold_20260715/evaluations/archaludon_explorer_certified_attack_deadline_productive_prefix_v1/fixed760_raw_20260801` | tree digest `8564E557F09E43C878C0C20A42C005B3F1F24B19C15570616B0E3FDB9246720B` |

The raw tree contains 2,336 files and 420,620,452 bytes. It was unchanged in file set, sizes, and mtimes during hashing. The tree digest is SHA-256 over each sorted relative POSIX path, NUL, its binary file SHA-256, and LF.

| Raw file | SHA-256 |
|---|---|
| `historical_silver/paired_results.csv` | `6B2F26D9E2ACD9DCD2FE4D0B24DF99465F0473BDF912F1805247A1647AE41B63` |
| `historical_silver/manifest.jsonl` | `765D6E984ACD9DCA3E0F980A708B6EA72B0C95C189B2A9216B1624C07B4DE103` |
| `historical_silver/cell_summary.csv` | `0985D11F49C067E5AAFC0961691C96852CF89B66CC2F147E14759C8332597CB8` |
| `historical_silver/report.json` | `84D12047BC9BFC4034B281AAC4BD87F5362EC386AF913C95F59015542F65771F` |
| `adjacent_population/paired_results.csv` | `8C120673577452D6906DBE0793763FECC1465AB6D42FC15028FE233E49A4F8B7` |
| `adjacent_population/manifest.jsonl` | `709E2B80CA0F5A90521FB2A2423C4469BD243F5C0FFB35F51D2E4D847710E95B` |
| `adjacent_population/cell_summary.csv` | `716DB8F6302316BD013C114B5F899DA8E55C4490701C75F7893B3066F27CEA25` |
| `adjacent_population/report.json` | `A53021D823037EF54DA26226BF47822367B3A54786F850795A5FB22316E2640C` |

Every expected spec-bound source, deck, runner, engine file, and adjacent opponent hash matches. The historical-Silver files currently hash to `F4B578453C9D953BE94885144DD50E05DBA4510DF3340BE27ADE07495896046E` (`main.py`) and `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A` (`deck.csv`), but the immutable spec does not provide expected hashes for that panel opponent; this is a provenance limitation, not a supplied numerical gate.

## Reproducible calculation and integrity checks

Run from repository root:

```powershell
.venv-rl\Scripts\python.exe autonomous_gold_20260715\numerical_audits\archaludon_explorer_certified_attack_deadline_productive_prefix_v1_20260801\audit_fixed760.py
```

The calculation reads the paired CSVs, all 48 manifest commands, all 2,280 summary rows, and all preserved traces. It independently derives wins from `result`: in seat 0 the policy is agent A/player 0 and wins iff `result == 0`; in seat 1 it is agent B/player 1 and wins iff `result == 1`. Manifest commands confirm this mapping and use `.venv-rl\Scripts\python.exe`, `run_local_battle.py`, and `--engine-seed`.

- Logical rows and unique `(panel, opponent, seat, seed)` keys: 760/760; no duplicates, missing keys, or extras.
- Baseline-A, baseline-B, candidate, CSV, and spec schedules: exact equality, 760 keys each.
- Independently recomputed CSV-field discrepancies: 0. Runner report/cell-summary discrepancies: 0.
- Duplicate control: 760/760 exact runner `GAME_FIELDS`, 760/760 results, 760/760 decision counts, and 760/760 byte-identical traces.
- Execution: 48/48 manifest exits zero; 2,280/2,280 starts successful; action errors 0; explicit exceptions/nonzero-exit proxy 0; max-step hits 0; missing traces 0; trace-line/step mismatches 0.

The physical paired CSV files omit the literal `panel` column named by `required_output_schema`. This audit materializes `panel` from the immutable spec-declared partition directory (`historical_silver` or `adjacent_population`), yielding the complete required logical schema. A reader requiring a literal column should record this as a physical-schema caveat; the partition value is unique and does not alter or ambiguate any schedule key.

## Independently recomputed outcomes

| Bucket | Parent W-L | Candidate W-L | Both rates | Gain / regression / tie | Delta | Conservative paired 95% bound |
|---|---:|---:|---:|---:|---:|---:|
| All | 476-284 | 476-284 | 62.6316% | 0 / 0 / 760 | 0.000 pp | [-0.393, +0.393] pp |
| Historical Silver | 100-100 | 100-100 | 50.0000% | 0 / 0 / 200 | 0.000 pp | [-1.487, +1.487] pp |
| Adjacent population | 376-184 | 376-184 | 67.1429% | 0 / 0 / 560 | 0.000 pp | [-0.534, +0.534] pp |

The aggregate absolute-rate Wilson 95% interval is 59.137%-65.999% for either policy. McNemar's exact two-sided p-value is 1.0 because there are no discordant terminal pairs. The matched odds ratio is not identifiable (0/0 discordants), so it is not used.

| Panel/opponent | Parent = candidate | Delta | Paired 95% bound |
|---|---:|---:|---:|
| historical_silver / historical_silver | 100/200 = 50.00% | 0.00 pp | ±1.487 pp |
| adjacent / alakazam_capbloo_gold | 61/80 = 76.25% | 0.00 pp | ±3.675 pp |
| adjacent / arch_peak | 39/80 = 48.75% | 0.00 pp | ±3.675 pp |
| adjacent / arch_shumpei | 41/80 = 51.25% | 0.00 pp | ±3.675 pp |
| adjacent / cynthia_v23 | 66/80 = 82.50% | 0.00 pp | ±3.675 pp |
| adjacent / kang_crustle | 27/80 = 33.75% | 0.00 pp | ±3.675 pp |
| adjacent / marnie_kazuki_live | 68/80 = 85.00% | 0.00 pp | ±3.675 pp |
| adjacent / mega_lucario_public | 74/80 = 92.50% | 0.00 pp | ±3.675 pp |

Every cell delta below is exactly zero; each 40-game adjacent cell has a conservative paired bound of ±7.216 pp, and each 100-game historical cell ±2.951 pp.

| Opponent | Seat 0 parent = candidate | Seat 1 parent = candidate |
|---|---:|---:|
| historical_silver | 57/100 = 57.0% | 43/100 = 43.0% |
| alakazam_capbloo_gold | 32/40 = 80.0% | 29/40 = 72.5% |
| arch_peak | 20/40 = 50.0% | 19/40 = 47.5% |
| arch_shumpei | 19/40 = 47.5% | 22/40 = 55.0% |
| cynthia_v23 | 32/40 = 80.0% | 34/40 = 85.0% |
| kang_crustle | 14/40 = 35.0% | 13/40 = 32.5% |
| marnie_kazuki_live | 33/40 = 82.5% | 35/40 = 87.5% |
| mega_lucario_public | 37/40 = 92.5% | 37/40 = 92.5% |

Across panels, seat 0 is 244/380 (64.21%) and seat 1 is 232/380 (61.05%), a 3.16 pp absolute seat split shared identically by parent and candidate. Comparative seed sensitivity is zero: the paired delta is 0 for every one of the 100 historical and 40 adjacent engine seeds (range 0, SD 0). Absolute seed-group rates vary from 0%-100% in historical two-game seed groups and 42.86%-85.71% in adjacent fourteen-game seed groups; those small-group ranges are descriptive, not candidate effects.

## Behavioral activation versus strength

- Candidate trace identical to parent: 715/760; different: 45/760 (5.92%).
- In all 45 differing traces, the first differing record is the tested policy's own action (44 at context 0, one at context 8), so this is direct behavioral activation rather than downstream opponent divergence.
- Decision counts differ in exactly the same 45 games. Candidate is shorter in 45, longer in 0, and total decisions fall from 83,452 to 83,336: -116 decisions (-0.139%; mean -2.58 per activated game).
- All 45 activated games are wins for both parent and candidate. Terminal results remain equal in all 760 games.

Therefore the change has a small measured execution-efficiency effect inside already-won games, but **terminal practical effect size is exactly 0.000 percentage points on the fixed schedule**. The trace establishes that the candidate acts differently; it does not, by itself, name which source-level condition fired. No strength conclusion is inferred from the shorter terminal shadow.

## Floors, regressions, and acceptance gates

Using `<40%` only as a descriptive severe-floor flag (not a supplied gate), `kang_crustle` is severe in both seats and is the recurring floor hidden by the 67.14% adjacent average. Other sub-50% cells are historical-Silver seat 1 (43.0%), `arch_peak` seat 1 (47.5%), and `arch_shumpei` seat 0 (47.5%). No cell regresses relative to the parent.

| Supplied gate | Required | Observed | Result |
|---|---:|---:|---|
| Unique schedule keys | 760 | 760 | PASS |
| Duplicate summary matches | 760 | 760 | PASS |
| Duplicate byte-trace matches | 760 | 760 | PASS |
| Execution faults | 0 | 0 | PASS |
| Start faults | 0 | 0 | PASS |
| Action errors | 0 | 0 | PASS |
| Exceptions | 0 | 0 | PASS |
| Max-step hits | 0 | 0 | PASS |
| Regressing panel/opponent/seat cells | 0 | 0 | PASS |

Recommendation against the supplied checks: **PASS**. Recommendation for interpretation: the candidate is eligible for retention if the criterion is safe behavioral activation plus exact preservation of the direct parent's absolute and adjacent results. This evaluation does **not** justify a claim of statistical or practical strength improvement and should not be used alone as promotion evidence. The unresolved Kang/Crustle floor should remain explicit in any adoption decision.

## Uncertainty, assumptions, and fallacy scan

The audited schedule is deterministic, so its observed delta is exactly zero. For a population-style uncertainty statement, this report treats matched schedule keys as exchangeable and bounds the probability of any unseen discordance. With zero discordances in `n` pairs, the exact one-sided 95% Clopper-Pearson upper bound is `q_U = 1 - 0.05^(1/n)`; because the absolute paired risk difference cannot exceed `q`, the aggregate conservative interval is ±0.393 pp. This is a paired interval, not two independent binomial intervals. It does not guarantee transfer to new opponents, decks, engine versions, or non-exchangeable seeds.

Assumptions: partition directory is the logical `panel`; runner exceptions would appear as nonzero manifest exit or explicit exception record; a step is one recorded decision; traces contain every runner-recorded action; no result is generalized outside the approved matrix; `<40%` is descriptive only; no numeric minimum absolute-rate gate was supplied, so “retention” is interpreted as no loss versus the direct parent.

Fallacy scan coverage: **11/11**.

| Fallacy | Audit finding |
|---|---|
| Simpson's paradox | No delta reversal: every aggregate and subgroup delta is zero. Absolute averaging does hide the Kang/Crustle floor, which is reported. |
| Ecological fallacy | No claim about unseen individual games or global metagame strength is made from panel aggregates. |
| Berkson's paradox | The approved opponent panel is curated; generalization beyond it is explicitly limited. |
| Collider bias | No covariate adjustment or conditioned causal model is used. |
| Base-rate neglect | Not a diagnostic-classification analysis; W-L denominators and panel composition are explicit. |
| Regression to the mean | Identical paired controls, not an extreme-selected pre/post comparison; no recovery claim is made. |
| Survivorship bias | All 760 scheduled keys and all three 2,280 runs are present; no failed games were dropped. |
| Look-elsewhere effect | Immutable buckets are all reported. Per-cell observations are not promoted as corrected significance claims. |
| Garden of forking paths | Spec and schedule hash are fixed; the severe-floor threshold is clearly marked post hoc/descriptive. |
| Correlation implies causation | The paired intervention supports on-schedule behavioral attribution, not broader strength causation. |
| Reverse causality | Not applicable to the deterministic paired policy intervention; no directional observational claim is made. |
