# Rule5 fixed160 minimal numerical audit

## Verdict

**Supplied fixed160 acceptance checks: PASS.** The independently recomputed outcome is exactly neutral: baseline **100-60 (62.50%)**, candidate **100-60 (62.50%)**, delta **0/160 = 0.00 pp**, with **0 gains / 0 regressions / 160 ties**. This is compatibility evidence, not evidence of a strength improvement.

The practical paired effect is 0.00 pp. With no discordant pair, exact McNemar `p=1.0`; a conservative 95% bound obtained from the two-sided Clopper-Pearson upper bound on the unseen discordance rate is **[-2.28, +2.28] pp**. Thus neither a meaningful improvement nor a regression is demonstrated.

## Independent CSV recomputation

Win derivation was seat-specific and did not reuse a player-0 counter: for both baseline and candidate, `win = (result == 0)` in seat/player 0 and `win = (result == 1)` in seat/player 1. All 160 recomputed values agree with the stored `*_win` columns.

The schedule key was `(panel, opponent, seat, seed)`, where `panel` is the raw subdirectory. There are **160 rows, 160 unique keys, 0 duplicate keys**. Every row satisfies `seed = seed_base + game`; paired baseline/candidate schedule equality is exact.

| Opponent | Seat / policy player | Games | Baseline W-L | Candidate W-L | Candidate rate | Delta | G/R/T |
|---|---:|---:|---:|---:|---:|---:|---:|
| historical_silver | 0 | 20 | 11-9 | 11-9 | 55.0% | 0.0 pp | 0/0/20 |
| historical_silver | 1 | 20 | 9-11 | 9-11 | 45.0% | 0.0 pp | 0/0/20 |
| alakazam_capbloo_gold | 0 | 20 | 16-4 | 16-4 | 80.0% | 0.0 pp | 0/0/20 |
| alakazam_capbloo_gold | 1 | 20 | 13-7 | 13-7 | 65.0% | 0.0 pp | 0/0/20 |
| arch_peak | 0 | 20 | 6-14 | 6-14 | **30.0%** | 0.0 pp | 0/0/20 |
| arch_peak | 1 | 20 | 14-6 | 14-6 | 70.0% | 0.0 pp | 0/0/20 |
| marnie_kazuki_live | 0 | 20 | 14-6 | 14-6 | 70.0% | 0.0 pp | 0/0/20 |
| marnie_kazuki_live | 1 | 20 | 17-3 | 17-3 | 85.0% | 0.0 pp | 0/0/20 |

Aggregate seat split is baseline=candidate **47/80 (58.75%)** as player 0 and **53/80 (66.25%)** as player 1. Candidate-minus-baseline delta is zero in both seats and every individual seed. Absolute strength nevertheless has material seat sensitivity: the inherited `arch_peak` floor is **30% in player 0 versus 70% in player 1**. No recurring candidate-specific floor was introduced; this severe absolute cell is unchanged and must not be hidden by the 62.5% aggregate.

Baseline and candidate results are identical on all 160 rows. Decision counts are also identical on 159/160 rows; the sole deterministic behavioral divergence is `historical_silver`, player 1, seed `271828192` (baseline 78 versus candidate 76 steps), with both winning. No trace-level causal claim is made.

## Runner-report and gate checks

- Both `report.json` files have `valid=true`, empty `invalid_reasons`, and independently matching aggregates.
- Duplicate-control report fields are zero in both panels: **0 total mismatches**. The authorized four-file scope did not include baseline_a/b raw rows, so this audit verifies the checked runner's report field rather than rereading those rows.
- Fault checks visible in scope pass: 0 invalid result values, 0 stored-win derivation mismatches, 0 seed-formula mismatches. Shadow summary has 0 invalid actions and 0 exceptions.
- Shadow evidence: 4,262 callbacks, 2 rule5-attributed action differences, both `DIRECT_EXACT_CURRENT_WIN`; `all_differences_allowed=true` and `all_differences_rule5=true`. Together with the fixed160 decision-count divergence, observed rule activity is nonzero.
- `gains >= regressions`: **0 >= 0**, pass. Every opponent/seat candidate count equals baseline, so the `baseline - 3 games` floor passes in all eight cells.
- No clearly harmful first difference is present in the supplied compact classification. Deep trace comparison was intentionally not performed.

Gate interpretation assumption: “natural fires > 0” means observed rule-attributed action/behavior differences. Under that supplied operational definition it passes (shadow differences=2; fixed160 behavioral divergence=1). The separate shadow field `natural_starts=0` is not treated as the gate counter; if the gate instead literally targets that field, the dormant check would fail and must be re-specified.

One source replay is listed as malformed in the shadow summary, while invalid actions and exceptions are zero. Per the supplied gate, the excluded malformed source is not counted as a candidate execution fault.

## Identities and reproducibility

Parent-supplied immutable identities (accepted without rereading outside the authorized scope):

- Spec: `autonomous_gold_20260715/evaluation_specs/archaludon_historical_silver_single_resolver_salvage_rule5_trial_v1/fixed160_spec.json`, SHA-256 `B9D6BEAC707B51C79D9EA42E5C00FCE0E4C85D8FA0F4A119EC39ACA032BAF258`.
- Baseline: `autonomous_gold_20260715/candidates/archaludon_historical_silver_single_resolver_salvage_rule4_trial_v1/main.py`, SHA-256 `F6B6266D870D3F134544A91616C27673620557D149C0496CC2034E7674F010D9`.
- Candidate: `autonomous_gold_20260715/candidates/archaludon_historical_silver_single_resolver_salvage_rule5_trial_v1/main.py`, SHA-256 `D966E455E5110F9D5616195AEAAC8663E6A92F310DAFC4B7F79E4D37149A9C62`.
- Deck SHA-256 `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`; runner-tree digest `4A89277BA250B25CA849B3868BEF80A268D36881A20E0CA9CD3698396E056B82`.

Independently hashed inputs:

- `fixed160_raw/historical_silver/paired_results.csv`: `AE03C48F2C2895645AE8D5564A3E280BEB2AD9C3F5F84760637ACB321DEF57B0`
- `fixed160_raw/historical_silver/report.json`: `37706612165C1E2D80C3485C70D0AC571CF6F7148EA79C96B342390A376B7315`
- `fixed160_raw/adjacent_population/paired_results.csv`: `F6B2596699ABB1CE767EF35B39A38A75DB4F2229DCED2132F8BFE4D9A6CA771E`
- `fixed160_raw/adjacent_population/report.json`: `AF692679EE949E2D6B72A3EE1283361A1F6A1A5C7A1DFEB16FF6F7D639BBCCE4`
- `implementation/.../shadow_summary.json`: `3C24F89CDD5E509BCB2455CD1BC019BB5CFB75CA1A89F2B206B9D1ACB256CE71`

Recalculation: parse both CSVs; derive each win with `int(result) == int(seat)`; group by opponent and seat; classify each pair as gain, regression, or tie; assert key uniqueness, seed formula, and stored-win equality; compare recomputed aggregates with each JSON report. No simulation, matrix expansion, source edit, or trace comparison was performed.
