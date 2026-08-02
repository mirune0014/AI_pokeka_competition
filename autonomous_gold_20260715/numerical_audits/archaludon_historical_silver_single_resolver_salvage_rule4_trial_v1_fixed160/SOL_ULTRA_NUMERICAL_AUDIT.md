# Rule 4 fixed160 Sol-Ultra numerical audit

## Material Passport

- Origin Skill: experiment-agent
- Origin Mode: validate
- Origin Date: 2026-08-03
- Verification Status: ANALYZED
- Version Label: rule4_fixed160_audit_v1

## Recommendation

**ACCEPT against the frozen Rule 4 stage gates.** This is a stage-gate acceptance, not evidence of a strength improvement. Rule 4 and the accepted Rule 1 parent are byte/action-identical in all 160 evaluated games: both finish `100-60` (`62.50%`), with paired gains/regressions/ties `0/0/160`. The supplied shadow contributes two valid natural starts, so combined activation is `2` and the explicit zero-start dormancy condition does not apply.

The coverage assumption is explicit: the Rule 4 overlay's minimum-one-start gate is applied to `shadow + fixed160`, matching its explicit combined-start dormancy gate. The two shadow suffixes are counterfactual replays, so their zero confirmations are completion-unobservable, not failed transactions.

## Frozen identity and raw validity

- Overlay specification: `3649FFDDEF35ADCE6A50EBC8F1BE581E9E4780426D4FF8AA5271F8A2912A9D7A`
- Inherited schedule: `E2B8986663A43A7F6F52888E487F39B8D059CDCDDF441A3E87D8C093DF15274C`
- Strategy selection: `136526EB9D2435A7E5822D3A6EE106078267365EDFB5801DCDE15A7737F7A269`
- Root verification: `192C5D9146BA5E16FEE61411FB6C402E213841B92F151666FE8A89367E70BDB8`
- Rule 1 baseline `main.py`: `153D8461FB66927DB9731CBE614B71FF5398B8EAE8980AE0BB4D46ADD0E8792A`
- Rule 4 candidate `main.py`: `F6B6266D870D3F134544A91616C27673620557D149C0496CC2034E7674F010D9`
- Both decks: `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`
- Raw root: `autonomous_gold_20260715/evaluations/archaludon_historical_silver_single_resolver_salvage_rule4_trial_v1/fixed160_raw`
- Raw tree: 512 files, 89,571,349 bytes, digest `82CE2B713417F754D13BCF8B2EC9C682AA0EFEC930EBB14FA19D0D4BA68782E1`

The raw digest is `SHA256(UTF-8 sorted relative/path|bytes|UPPERCASE_file_sha256<LF>)`.

Exactly `160/160` unique `(panel, opponent, seat, seed)` keys equal the immutable schedule. Policy mapping is explicit: seat 0 is agent A/player 0 and wins iff `result == 0`; seat 1 is agent B/player 1 and wins iff `result == 1`.

All 24 manifest commands exited zero. Across 480 summary rows: start faults `0`, action errors `0`, populated exception fields `0`, invalid results `0`, max-step hits `0`, and trace-integrity faults `0`. Baseline-A versus identical-policy baseline-B matches `160/160` for result, decision count, complete non-trace summary, and trace bytes. Both checked reports are valid and independently reconstructed CSV/report values have zero discrepancies.

## Independently recomputed comparison

| Bucket | Games | Rule 1 | Rule 4 | Delta | G/R/T |
| --- | ---: | ---: | ---: | ---: | ---: |
| All | 160 | 100 (62.50%) | 100 (62.50%) | 0 | 0/0/160 |
| Historical-Silver | 40 | 20 (50.0%) | 20 (50.0%) | 0 | 0/0/40 |
| Arch Peak | 40 | 20 (50.0%) | 20 (50.0%) | 0 | 0/0/40 |
| Alakazam | 40 | 29 (72.5%) | 29 (72.5%) | 0 | 0/0/40 |
| Marnie | 40 | 31 (77.5%) | 31 (77.5%) | 0 | 0/0/40 |
| Seat 0 | 80 | 47 (58.75%) | 47 (58.75%) | 0 | 0/0/80 |
| Seat 1 | 80 | 53 (66.25%) | 53 (66.25%) | 0 | 0/0/80 |

Every candidate-parent trace is byte-identical, so the complete fixed160 first-action-difference ledger is empty. Fixed160 natural starts/completed/failed transactions are `0/0/0`; mechanism-first losses and clearly harmful changed actions are both zero.

The paired seed-cluster empirical 95% interval is `[0, 0]` and exact McNemar `p = 1.0`. Because every observed delta is zero, this interval is degenerate and does not prove population identity. A conservative zero-discordance sensitivity envelope is `[-1.8549 pp, +1.8549 pp]`. No practically or statistically meaningful improvement is observed.

All 20 seed clusters in each panel have delta zero. Absolute strength remains seat-sensitive: seat 1 exceeds seat 0 by `6.25 pp`. The aggregate hides the recurring Arch Peak seat-0 floor of `6/20 (30%)`; Historical-Silver seat 1 is also below half at `9/20 (45%)`. Rule 4 neither causes nor repairs either floor.

## Rule 4 route and transaction audit

The shadow hashes match: summary `B37F5162A12F25B9C179DF7E891FC3410621F1FAA59A83D4B2FB5D2AB3C3D594`; differences `AFF84E8BE667B9D36834DA00356BE5C755C5965D3E13C321E38C0F1EFBC02718`.

| Replay | Seat/step | Parent | Candidate route | Receipt status |
| --- | --- | --- | --- | --- |
| `89279065` | 1 / 41 | exact Lillie serial 108 | `BENCH_EVOLUTION_BEFORE_LILLIE`, Archaludon ex 68 onto Duraludon 66 | unobservable after counterfactual divergence |
| `89283885` | 1 / 34 | exact Lillie serial 107 | `BENCH_EVOLUTION_BEFORE_LILLIE`, non-ex Archaludon 91 onto Duraludon 64 | unobservable after counterfactual divergence |

Both are among the four permitted classes, both have one exact physical parent Lillie, and neither emits HOLD/END. Shadow natural starts/completed/failed/unobservable are `2/0/0/2`. Focused poststate verification, rather than the counterfactual replay suffix, is the authority for receipt/clear behavior.

## Gate disposition

- Frozen hashes/raw tree, exact schedule, runner reconstruction: **PASS**
- Duplicate summary/result/decision-count/byte-trace controls: **PASS (160/160)**
- Execution, action, exception, max-step, trace faults: **PASS (all zero)**
- Allowed first differences and exact parent Lillie: **PASS (2/2 shadow; no fixed160 differences)**
- Combined minimum natural starts: **PASS (2 >= 1)**
- Dormancy: **does not apply (2 != 0)**
- Paired gains at least regressions: **PASS (0 >= 0)**
- No seat/opponent decline of three wins: **PASS (all deltas zero)**
- No mechanism-first loss or clearly harmful action: **PASS (zero)**

Fallacy scan coverage is `11/11`: no aggregate/subgroup reversal exists because every paired delta is zero; the material caution is selection/generalization. Strength is not inferred from the aggregate tie or from two shadow activations.

Reproducible calculator: `audit_rule4_fixed160.py`. No source, deck, schedule, specification, shadow evidence, or raw runner output was modified, and no simulation was run or expanded.
