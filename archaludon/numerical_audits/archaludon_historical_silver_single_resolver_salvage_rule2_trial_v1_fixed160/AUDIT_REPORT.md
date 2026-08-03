# Rule 2 fixed160 independent numerical audit

## Recommendation

**DEFER-DORMANT under the stage contract.**

The candidate is mechanically clean and outcome-identical to the accepted Rule
1 parent, but Rule 2 did not activate once.  The fixed160 contains **160/160
byte-identical candidate/parent traces**.  Together with the supplied
root-verified shadow result of **0 differences over 4,262 callbacks**, the
combined natural-start count is zero.  The frozen requirement therefore says
to record the implementation but **not integrate it and not broaden its
conditions**.

This is not a strength rejection: the rule had no evaluated behavioral effect.

## Frozen identity and execution validity

- Requirements SHA-256:
  `24282FA6A0EF91D936E2E5B2AAD725904EF3223FCFBDF9BEEA16C62C726038C9`.
- Immutable fixed160 spec SHA-256:
  `7EF9D7F5074EC6ADD7DE04A78D2B521792B5DDD9E3815A00E0394B4DEA642036`.
- Accepted Rule 1 parent `main.py`:
  `153D8461FB66927DB9731CBE614B71FF5398B8EAE8980AE0BB4D46ADD0E8792A`.
- Rule 2 candidate `main.py`:
  `D2BC5FCC82A5A507B7C5CC9FEDAAC4ED6EA0BE1622EBE99EFC74B6E6A926FC62`.
- Both decks:
  `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`.
- All verification, engine, checked-runner, and adjacent-opponent hashes bound
  by the immutable spec independently match.
- Raw runner ledger: 512 files, SHA-256
  `8D3C52ADF49F2D36DCE2E3D50033E75306C981B7915443DE413FB598024F1F29`
  (match).  Its formula is SHA-256 over the UTF-8 concatenation of sorted
  `UPPERCASE_FILE_SHA256 + two spaces + relative POSIX path + LF` records.
- Independent secondary portable ledger over sorted
  `relative/path<TAB>bytes<TAB>file_sha256<LF>` records:
  `069FE7C45B2CDA7723117F1FE8C5AE5EB1FC428A80352B5E782884DC398DA691`.

Exactly **160 unique `(panel, opponent, seat, seed)` keys** reconstruct and
equal the immutable schedule.  All 24 manifest commands exited zero, used the
frozen seeded engine, `.venv-rl/Scripts/python.exe`, the checked battle runner,
correct player placement, 20 seeds per cell, and `--max-steps 1000`.

Execution health is clean:

- start faults: 0;
- action errors: 0;
- populated exception fields: 0;
- invalid results: 0;
- max-step hits: 0;
- malformed or step-count-invalid traces: 0; and
- checked-runner aggregate/row discrepancies: 0.

The identical-policy duplicate control is baseline A versus baseline B in the
same role, opponent, and seed.  It matches **160/160** on result, decision
count, all non-trace summary fields, and trace bytes.  The Historical-Silver
panel is accepted Rule 1 versus exact Historical-Silver, so its opposite-seat
runs are not incorrectly treated as an identical-policy control.

Policy mapping is explicit: at seat 0 the tested policy is agent A/player 0
and wins iff `result == 0`; at seat 1 it is agent B/player 1 and wins iff
`result == 1`.

## Paired result

| Quantity | Rule 1 parent | Rule 2 candidate | Paired result |
|---|---:|---:|---:|
| Wins-losses | 100-60 | 100-60 | 0 wins |
| Rate | 62.50% | 62.50% | 0.00 pp |
| Gains / regressions / ties | - | - | 0 / 0 / 160 |

Exact McNemar `p = 1.0`.  Every observed paired delta and every panel/seed
cluster delta is zero, so the empirical clustered 95% interval is `[0, 0]`.
This degenerate sample interval is not proof of population identity.  As a
finite-sample sensitivity bound, zero discordances in 160 gives a conservative
95% net-effect magnitude envelope of **±1.8549 percentage points**.

## Buckets and absolute floors

| Opponent | Parent | Candidate | Delta | Candidate seat 0 | Candidate seat 1 |
|---|---:|---:|---:|---:|---:|
| Historical-Silver | 20/40 (50.0%) | 20/40 (50.0%) | 0 | 11/20 | 9/20 |
| Arch Peak | 20/40 (50.0%) | 20/40 (50.0%) | 0 | **6/20** | 14/20 |
| Alakazam Capbloo Gold | 29/40 (72.5%) | 29/40 (72.5%) | 0 | 16/20 | 13/20 |
| Marnie Kazuki Live | 31/40 (77.5%) | 31/40 (77.5%) | 0 | 14/20 | 17/20 |

Seat totals are 47/80 (58.75%) at seat 0 and 53/80 (66.25%) at seat 1 for
both policies.  The aggregate hides an existing **Arch Peak seat-0 floor of
6/20 (30%)**; Rule 2 neither causes nor repairs it.  The mirror seat-1 label is
9/20 (45%).  Each panel has 20 seed clusters, and every cluster has net delta
zero.

## Rule 2 coverage and gate disposition

| Check | Result |
|---|---|
| Frozen hashes and raw ledger | PASS |
| 160 unique keys and exact schedule | PASS |
| Duplicate summary/result/step equality | PASS (160/160) |
| Duplicate trace equality | PASS (160/160) |
| Execution and trace health | PASS (all zero faults) |
| Candidate versus parent trace equality | 160/160 identical |
| Paired gains at least regressions | PASS (0 >= 0) |
| No seat or opponent at least 3 wins below parent | PASS (all deltas 0) |
| Minimum one natural Rule 2 start | **FAIL (0)** |
| Shadow plus fixed160 combined natural starts | **0** |
| Dormancy rule | **APPLIES: record, do not integrate, do not widen** |

Accordingly, **DEFER-DORMANT** is the only contract-consistent recommendation.
`ACCEPT` would incorrectly integrate an unexercised rule; `REJECT` would
incorrectly claim evidence of harm.

## Reproducibility

Calculator:

`autonomous_gold_20260715/numerical_audits/archaludon_historical_silver_single_resolver_salvage_rule2_trial_v1_fixed160/audit_rule2_fixed160.py`

Calculator SHA-256:
`E86674BE3022B6A370A703D71229EB6CC2F865CCE7AA907A9D815BF6E8A6A76B`.

Run from the repository root:

```powershell
.venv-rl\Scripts\python.exe autonomous_gold_20260715\numerical_audits\archaludon_historical_silver_single_resolver_salvage_rule2_trial_v1_fixed160\audit_rule2_fixed160.py
```

Raw root:

`autonomous_gold_20260715/evaluations/archaludon_historical_silver_single_resolver_salvage_rule2_trial_v1/fixed160_raw`

Panel hashes:

| Panel | Manifest | Paired rows | Cell summary | Report |
|---|---|---|---|---|
| Historical-Silver | `A779DF95135068C37934D5D8758ABE68AD000796D790A58A4C6D189A1D9F17C0` | `6B17B59C959A1420103E927F22532F67E333D6B57CB3E5B66F594D6CAFACC676` | `BD30AEA1526B09FAE2147F5DE0D072AB56BCC0546E2B6485E5A938090F89A1F4` | `37706612165C1E2D80C3485C70D0AC571CF6F7148EA79C96B342390A376B7315` |
| Adjacent population | `30A7AF636A09D61079643900B6BBFF3580CAFE02DB7800022B18D0778F4356CE` | `F6B2596699ABB1CE767EF35B39A38A75DB4F2229DCED2132F8BFE4D9A6CA771E` | `BAF347F4C437B5028B053CC2601A2562DCCBD4EEC053E225505EB42258B0E96C` | `AF692679EE949E2D6B72A3EE1283361A1F6A1A5C7A1DFEB16FF6F7D639BBCCE4` |

Assumptions are limited to the root-supplied shadow count and the frozen
scope.  No simulation was run or expanded, and no source, deck, schedule,
specification, or raw runner result was modified.
