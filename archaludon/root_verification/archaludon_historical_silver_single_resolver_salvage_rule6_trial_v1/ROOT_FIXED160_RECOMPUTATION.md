# Rule 6 fixed160 root recomputation

Date: 2026-08-03 JST

## Frozen inputs

- Spec SHA-256: `4BE2C65E3F28D403664769E50C0F1078BCC4A1BBAD134222ACDBA60AC24BD3BF`
- Baseline Rule 5 SHA-256: `D966E455E5110F9D5616195AEAAC8663E6A92F310DAFC4B7F79E4D37149A9C62`
- Candidate Rule 6 SHA-256: `02180DB5EA65356FA85301D7978EF088725FCA241B84EE68B29E102B77655164`
- Shared deck SHA-256: `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`
- Raw tree digest: `393A162DE440DB52CE5E8A29C0B2AE9B5576A409F771722C6335B99CE49A4C66`

## Numerical result

The two paired CSVs contain exactly 160 unique `(opponent, seat, seed)` keys with exact baseline/candidate schedule equality.

| Cell | Games | Baseline wins | Candidate wins | Delta |
| --- | ---: | ---: | ---: | ---: |
| Historical-Silver, seat 0 | 20 | 11 | 11 | 0 |
| Historical-Silver, seat 1 | 20 | 9 | 9 | 0 |
| Alakazam, seat 0 | 20 | 16 | 16 | 0 |
| Alakazam, seat 1 | 20 | 13 | 13 | 0 |
| Arch Peak, seat 0 | 20 | 6 | 6 | 0 |
| Arch Peak, seat 1 | 20 | 14 | 14 | 0 |
| Marnie, seat 0 | 20 | 14 | 14 | 0 |
| Marnie, seat 1 | 20 | 17 | 17 | 0 |
| **Total** | **160** | **100** | **100** | **0** |

- Paired gains/regressions/ties: `0/0/160`.
- Action errors, exceptions/start faults, max-step hits, duplicate mismatches: 0.
- Baseline/candidate step-count differences: 0.
- Fixed160 Rule 6 attributable action differences or transaction markers: 0.

## Coverage result

The replay shadow has one Rule 6 start and one `POKE_PAD_DURALUDON_TARGET` difference, but the recorded continuation follows the parent's different physical Duraludon serial. It therefore contains zero ready completions and zero whiff completions. Fixed160 adds zero Rule 6 starts, differences, ready completions, or whiffs.

Combined observed coverage is:

- starts/differences: 1;
- complete ready transactions: 0;
- complete whiff transactions: 0.

The candidate passes all numerical retention and execution-safety gates. It fails the frozen coverage gate `minimum_completed_or_whiff_transactions=1`. The strategy explicitly classifies a natural start with neither a completed ready route nor a completed whiff as `REJECT`, not `DEFER-DORMANT`. Conditions must not be widened and the accepted parent must remain Rule 5.

Final judgment remains subject to the independent numerical audit and Sol-Ultra rule-level decision.
