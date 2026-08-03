## Material Passport

- Origin Skill: academic-research-suite / experiment-agent
- Origin Mode: validate
- Origin Date: 2026-08-03 JST
- Verification Status: ANALYZED
- Version Label: rule3_parent_prefix_fixed760_numerical_audit_v1

# Rule 3 parent-prefix fixed760 numerical audit

## Result

**Fixed-schedule outcome retention and execution safety pass; strength gain is not demonstrated.** This is a numerical finding only, not an adoption decision.

The direct parent and Rule 3 candidate both independently reconstruct to **480-280 / 63.16%** over 760 keys. There are **0 gains, 0 regressions, and 760 result ties**, so the observed paired effect is exactly `0 wins / 0.00 pp`; exact McNemar `p=1.0`. With no discordant result, that test is uninformative about improvement. Any paired bootstrap of these observed outcome deltas is also degenerate at `[0,0]`; this records exact equality on the frozen keys, not equivalence on unseen states.

Candidate-parent terminal/game summaries match `760/760`, but byte traces match only **755/760**. The five changed traces have identical result and step count; their qualitative first differences are deliberately not interpreted here.

## Inputs and validity

- Rule 3 spec: `autonomous_gold_20260715/evaluation_specs/archaludon_historical_silver_single_resolver_salvage_rule3_parent_prefix_v1/fixed760_spec.json`
  - SHA-256 `AD0C31C9DF83ADD924D30129A3A99961CFA10F89019731C6CFC61BEBBB02B4D8` (match).
- Direct parent: `autonomous_gold_20260715/final/archaludon_historical_silver_single_resolver_salvage_v1/main.py`
  - SHA-256 `D966E455E5110F9D5616195AEAAC8663E6A92F310DAFC4B7F79E4D37149A9C62` (match).
- Candidate: `autonomous_gold_20260715/candidates/archaludon_historical_silver_single_resolver_salvage_rule3_repair_v2/main.py`
  - SHA-256 `4287A616E1611F5697964D9F4065978EED1CEA72CDB48C9F63F1430D69106C35` (match).
- Both decks: SHA-256 `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A` (match).
- Hash-pinned schedule base: SHA-256 `49B89DDAEDF6745A7ADD203602DA457BDDE912B2B7F4F18FAA3C2955780BC75D` (match).
- All 36 checked hashes—specifications, policies/decks, engine files, runners/wrapper, strategy/verification documents, and opponents—match.

Policy-to-player mapping was reconstructed from each manifest: at seat 0 the tested policy is agent A/player 0 and wins iff `result == 0`; at seat 1 it is agent B/player 1 and wins iff `result == 1`.

| Validation item | Independent result |
|---|---:|
| Paired rows | 760 |
| Unique parent-A / parent-B / candidate keys | 760 / 760 / 760 |
| Exact `(panel, opponent, seat, seed)` schedule equality | yes |
| Manifest runs / nonzero exits | 48 / 0 |
| Summary rows across all three roles | 2,280 |
| Start faults / action errors / exceptions / explicit faults | 0 / 0 / 0 / 0 |
| Invalid results / max-step hits | 0 / 0 |
| Duplicate parent A/B checked-summary matches | 760/760 |
| Duplicate parent A/B full non-trace-summary matches | 760/760 |
| Duplicate parent A/B byte-trace matches | 760/760 |
| Parent/candidate checked game-tuple matches | 760/760 |
| Parent/candidate full non-trace-summary matches | 760/760 |
| Parent/candidate byte-trace matches | **755/760** |
| Raw-to-`paired_results.csv`/`report.json` discrepancies | 0 |

The duplicate parent A/B runs are the required identical-policy control. Their result and decision count (`steps`), all other checked summary fields, and trace bytes match on every key before any seat comparison is interpreted.

## Aggregate, panel, and seat totals

| Slice | Games | Parent W-L/rate | Candidate W-L/rate | Gains/regressions/ties | Delta |
|---|---:|---:|---:|---:|---:|
| Overall | 760 | 480-280 / 63.16% | 480-280 / 63.16% | 0/0/760 | 0 |
| Historical-Silver mirror | 200 | 100-100 / 50.00% | 100-100 / 50.00% | 0/0/200 | 0 |
| Adjacent population | 560 | 380-180 / 67.86% | 380-180 / 67.86% | 0/0/560 | 0 |
| Policy seat 0 (agent A/player 0) | 380 | 245-135 / 64.47% | 245-135 / 64.47% | 0/0/380 | 0 |
| Policy seat 1 (agent B/player 1) | 380 | 235-145 / 61.84% | 235-145 / 61.84% | 0/0/380 | 0 |

The mirror's seat cells are 58/100 at player 0 and 42/100 at player 1 for both policies. Candidate-minus-parent is zero in both seats; the raw 58/42 split is not used as evidence of candidate strength.

## Opponent and opponent-seat cells

Every entry is identical for parent and candidate; every cell has zero gains and zero regressions.

| Opponent | Total W/n (rate) | Seat 0 W/40 | Seat 1 W/40 |
|---|---:|---:|---:|
| historical_silver | 100/200 (50.00%) | 58/100 | 42/100 |
| arch_peak | 39/80 (48.75%) | 19 | 20 |
| arch_shumpei | 39/80 (48.75%) | 17 | 22 |
| alakazam_capbloo_gold | 62/80 (77.50%) | 32 | 30 |
| marnie_kazuki_live | 68/80 (85.00%) | 32 | 36 |
| mega_lucario_public | 74/80 (92.50%) | 37 | 37 |
| kang_crustle | 31/80 (38.75%) | 17 | 14 |
| cynthia_v23 | 67/80 (83.75%) | 33 | 34 |

Absolute floors are preserved, not improved: the Historical-Silver mirror is 50.00%; the adjacent-panel rate is 67.86%; the lowest adjacent opponent is Kang/Crustle at `31/80 = 38.75%`, and its seat-1 cell is the lowest adjacent cell at `14/40 = 35.00%`.

## Candidate-parent trace differences

The following are the complete five byte-unequal trace keys. `result` is the winning player index; `policy outcome` uses the policy's actual seat. Parent and candidate have the same result and steps on each row.

| Panel/opponent | Seat | Seed | Result / policy outcome | Steps | Parent bytes -> candidate bytes |
|---|---:|---:|---:|---:|---:|
| adjacent / cynthia_v23 | 0 | 271958313 | 0 / win | 134 | 231,958 -> 231,848 |
| adjacent / cynthia_v23 | 1 | 271958330 | 1 / win | 123 | 205,258 -> 205,059 |
| adjacent / marnie_kazuki_live | 1 | 271958346 | 1 / win | 125 | 199,274 -> 199,274 |
| mirror / historical_silver | 0 | 271828212 | 1 / loss | 149 | 250,981 -> 250,860 |
| mirror / historical_silver | 0 | 271828275 | 0 / win | 85 | 137,383 -> 137,272 |

Trace SHA-256 pairs, in the same order:

```text
83AA1D6239F3A40667AC9935CEE1880AB80BE91CE48605E973DF7D82F6991410 -> 9387B97756E3C32AF38C915BBFADACF9FC6802AA8BE1861B92F8E0D92E4A0CEF
C17A0ED4F291AEA5F4BC21E11FC6ED35FDA1656BD6F4AB731530AD87C9040A8C -> 0A3DC1FA2477E8166BCD59A8D6D2481059BE2A7925C6B99E895B6F446F699372
29924B2126DC5030CFBF0BF0EEB272DC31CC18C94F1C8963DE6D585DBD47D641 -> 8EFA9FB345878066989D9BD2A0DFE24B5FB62B73F354D19DDD15067CF16C6BEA
CC2A60DB53D8360A37A956155D241113336A0418A519E184D6BD825C1A71A2A4 -> 417F5C738447D168652F7572C48734CDC568521B1D9165D56BD58BEE84747504
8EC13C27A4B45DF2717E557E1F042139C27B90A2789DD0B87176A695FC4CF794 -> AA5F6849360C3BDD2F3770D0C8806F4870B0321894D4D524922AA7642834501B
```

This is evidence of five behavioral differences with no fixed-schedule result change. It is neither a numerical regression nor proof of safety in those changed positions. The controlling verification document requires separate inspection before adoption; this report makes no qualitative claim about them.

## Gate disposition

The Rule 3 spec literally contains `"gates": {}`. To avoid inventing thresholds, this audit separately reports (a) the fixed760 subset explicitly stated by its hash-pinned verification document and (b) all gates in the hash-pinned `schedule_base` specification.

- **Rule 3 fixed760 retention/safety subset: PASS.** Candidate wins `480 >= 478`; gains `0 >= 0` regressions; mirror `100 >= 98`; seat drops `0/0 <= 2`; every adjacent-opponent drop is `0 <= 5`; schedule, duplicate controls, and all execution-health gates pass.
- **All inherited schedule-base entries: 14/15 pass.** The sole failure is `strengthened_candidate_wins_minimum`: `480 < 486` by six wins. `strengthened_both_seats_nonworse` passes only by exact equality.
- **Strength gain: not shown.** The candidate adds zero wins, has zero paired gains, improves no opponent or seat cell, and fails the 486-win strengthened threshold.
- **Full behavior identity: not shown.** Candidate-parent trace equality is 755/760, although fixed-schedule outcomes and terminal summaries are identical.

This distinguishes strong non-regression evidence on the frozen outcomes from absent strength evidence. Passing `0 gains >= 0 regressions` is a retention gate, not evidence that the candidate is stronger.

## Statistical warnings and fallacy scan

- Overall confidence is **SOLID for the raw fixed-schedule arithmetic and execution/duplicate checks**, but **CAUTION for extrapolated safety or strength claims** because five traces differ and there is no positive paired effect.
- Multiple comparison correction is immaterial here: all 16 opponent-seat deltas are exactly zero and no cell-level discovery claim is made.
- The sample is a frozen selected opponent/seed panel; rates should not be generalized to an unrestricted meta population.
- Exact `p=1.0` with zero discordants must not be reframed as proof of equivalence or proof that the amendment has no effect.

Fallacy scan coverage: **11/11**. Simpson reversal: absent (aggregate and every cell delta are zero); ecological inference: avoided; Berkson/selection: selected-panel limitation noted; collider bias: no covariate adjustment; base-rate neglect: absolute W/n reported; regression to mean: paired immutable schedule, no pre/post claim; survivorship: no missing keys/faulted games; look-elsewhere: all cells reported; garden of forking paths: frozen schedule and the empty/local versus inherited gate distinction disclosed; correlation/causation and reverse causality: no causal interpretation made.

## Reproducibility and raw hashes

Recalculation command:

```powershell
.venv-rl\Scripts\python.exe autonomous_gold_20260715\analysis_outputs\ptcg_local_evaluator_rule3_parent_prefix_v1_fixed760\CALC.py
```

`CALC.py` SHA-256: `C78E769C5B881C883291A27EEA46CA4E4099A47760A1FF42689A674BB2A7457D`.

Raw root: `autonomous_gold_20260715/evaluations/archaludon_historical_silver_single_resolver_salvage_rule3_repair_v2/fixed760_parent_prefix_v1_raw`

- Files / bytes: `2,336 / 418,214,813`.
- Raw-tree SHA-256: `6C3D892097C394CFDBDFC992E0480577F0D085C5D5FB6F99303FAE5AB0A4A9EB`.
- Tree definition: `SHA256(UTF-8 sorted relative/path<TAB>bytes<TAB>file_sha256<LF>)`.

| Panel | Manifest SHA-256 | `paired_results.csv` SHA-256 | `report.json` SHA-256 |
|---|---|---|---|
| historical_silver | `DA2BDDDFB8837BC1C321B3CA2FBFBE2AF94E08C733112D00C3AA4282E8A0E906` | `D45BB63A6B2ECE6CB51BCC80B7F01B78528AF77E84A8617442F4AC07C43726C2` | `F54D80C469309306C2558E9F92F4ED26A8832BBEE4A906A827F0FCA22B96A48B` |
| adjacent_population | `75577E155466CF45161F9102C9B9454FCEFCA3C7D423ABDCF5C4439590DDC7EE` | `447C08F4377C7FC9F9EC0DDA8117B243C89989281ACFA0F18E038C3CE353C2A1` | `1029FD3FF4A4342ADD2FF147861A67032B11AFEA631D1D63446308A0954B389B` |

No simulation was rerun, no trace first difference was interpreted, and no candidate, source, deck, schedule, or raw result file was modified. Experimental rerun reproducibility is therefore marked `ANALYZED`, not `VERIFIED`.
