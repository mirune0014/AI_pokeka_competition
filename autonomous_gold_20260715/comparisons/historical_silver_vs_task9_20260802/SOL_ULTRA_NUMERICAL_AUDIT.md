# Sol-Ultra numerical audit: Historical Silver vs Task 6 / Task 9

Audit date: 2026-08-03 JST  
Scope: completed `fixed760` raw outputs only. The preserved failed-layout directory is excluded and is not evidence.

## Recommendation

**Runner validity: PASS. Historical-Silver replacement: FAIL for both Task 6 and Task 9. Task 7–9 aggregate repair of Task 6: FAIL (no net repair).**

Historical Silver independently reconstructs to **478-282 (62.89%)**. Task 6 and Task 9 each reconstruct to **368-392 (48.42%)**, a practically large **-110 wins / -14.47 percentage-point** regression. The primary same-seed-cluster bootstrap 95% intervals are `[-17.11, -11.71] pp` for Task 6 and `[-17.24, -11.84] pp` for Task 9; neither is compatible with parity.

Directly, Task 9 versus Task 6 is **368-392 versus 368-392**, with **42 gains, 42 regressions, and 676 ties**: `0.00 pp`, primary 95% CI `[-2.24, +2.37] pp`, exact McNemar `p=1.0`. Task 9 moves three net wins from the adjacent population to the Historical-Silver mirror and five net wins from seat 1 to seat 0, but it does not improve the total. Numerically, Task 6 was already severely degraded and Tasks 7–9 reshuffled, rather than repaired, that degradation.

The immutable specification explicitly says this diagnostic is not a promotion gate, and no separate numerical promotion threshold was supplied. Even without such a threshold, both candidates fail the requested replacement decision because their aggregate loss is large, precise, recurring across seed quartiles, and accompanied by severe matchup floors.

## Evidence validity and assumptions

- Immutable spec SHA-256: `8C7F2C3BD994966EE7E004B35C698E3E006E7416E9BC801C5ECDFA23ED3E970E` (match).
- Historical-Silver, Task 6, Task 9, common deck, seeded engine, paired runner, and battle runner all match the frozen hashes. The exact artifact hashes are recorded below.
- Task 6: 760 raw schedule keys, 760 unique; Task 9: 760 raw schedule keys, 760 unique; exact `(panel, opponent, seat, seed)` set equality, with zero one-sided keys.
- Both suites have 48 manifest runs, all exit code 0 and all using `.venv-rl/Scripts/python.exe`, the checked battle runner, `--engine-seed`, and `--max-steps 1000`.
- Both suites have zero start faults, action errors, exception fields, invalid results, and max-step hits.
- Duplicate baseline controls match **760/760 in each suite** on the checked runner tuple `(seed, result, steps, turn, action_errors, hit_max_steps)`. They also match 760/760 on every non-trace summary field. Thus result and decision-count (`steps`) equality are exact.
- Cross-suite Historical-Silver baseline outputs match **760/760** on both the checked runner tuple and every non-trace summary field.
- Independently reconstructed rows match all four checked `paired_results.csv` files and all four `report.json` validity/aggregate fields with zero discrepancies.
- Policy mapping is explicit: at seat 0 the policy is agent A/player 0 and wins iff `result == 0`; at seat 1 it is agent B/player 1 and wins iff `result == 1`. No player-0 counter is reused for seat-1 runs.
- The audited identical-policy control is the Historical-Silver mirror. Its seat-labelled baseline commands produce the same full game tuple for **100/100 seeds**. Player 0 wins 58 and player 1 wins 42. The apparent baseline `58%-42%` seat split is therefore the complementary result of the identical games, not evidence that one copy of the same policy is stronger. Candidate seat deltas are always interpreted with this control in view.
- `G/R/T` below means right-policy gain (left loss/right win), regression (left win/right loss), and tie. The two-sided exact McNemar/binomial test conditions on `G+R` and treats schedule rows as pairs. Because engine seeds are reused across seats/opponents, the primary uncertainty interval is a deterministic 100,000-replicate paired percentile bootstrap over whole engine-seed clusters, stratified by panel (100 mirror seeds and 40 adjacent-population seeds).
- “Conditional exact CI” maps the Clopper-Pearson interval for the gain share among discordants back to the net paired delta while holding the observed discordant fraction fixed. It is a secondary interval; the seed-cluster interval is primary.
- Results are conditional on the frozen opponents, seats, and seed blocks. Numerical movement alone is not causal evidence that a Task 7–9 rule changed a state; that requires the separate same-determinization action-difference/replay audit.

## Aggregate paired comparison

| Comparison (left -> right) | Left W-L / rate | Right W-L / rate | G/R/T | Delta | Seed-cluster 95% CI | Conditional exact 95% CI | Exact p |
|---|---:|---:|---:|---:|---:|---:|---:|
| Silver -> Task 6 | 478-282 / 62.89% | 368-392 / 48.42% | 37/147/576 | -110 / -14.47 pp | [-17.11, -11.71] pp | [-17.15, -11.31] pp | 1.02e-16 |
| Silver -> Task 9 | 478-282 / 62.89% | 368-392 / 48.42% | 44/154/562 | -110 / -14.47 pp | [-17.24, -11.84] pp | [-17.38, -11.12] pp | 1.67e-15 |
| Task 6 -> Task 9 | 368-392 / 48.42% | 368-392 / 48.42% | 42/42/676 | 0 / 0.00 pp | [-2.24, +2.37] pp | [-2.46, +2.46] pp | 1.0 |

The positive deltas in isolated buckets below do not overturn the aggregate result. Task 6's only opponent-level positive delta versus Silver is Kang/Crustle (`+2/80`, exact `p=.727`), which is tiny and uncertain. Task 9 has no positive opponent-level delta versus Silver.

## Panel totals

| Comparison | Panel | Left wins | Right wins | Rates (L -> R) | G/R/T | Delta | Seed-cluster 95% CI | Exact p |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| Silver -> Task 6 | Historical-Silver mirror (n=200) | 100 | 36 | 50.00% -> 18.00% | 15/79/106 | -32.00 pp | [-37.00, -27.00] | 1.15e-11 |
| Silver -> Task 6 | Adjacent population (n=560) | 378 | 332 | 67.50% -> 59.29% | 22/68/470 | -8.21 pp | [-11.43, -5.00] | 1.25e-6 |
| Silver -> Task 9 | Historical-Silver mirror (n=200) | 100 | 39 | 50.00% -> 19.50% | 14/75/111 | -30.50 pp | [-35.50, -25.50] | 3.01e-11 |
| Silver -> Task 9 | Adjacent population (n=560) | 378 | 329 | 67.50% -> 58.75% | 30/79/451 | -8.75 pp | [-11.96, -5.54] | 2.96e-6 |
| Task 6 -> Task 9 | Historical-Silver mirror (n=200) | 36 | 39 | 18.00% -> 19.50% | 16/13/171 | +1.50 pp | [-3.50, +7.00] | .711 |
| Task 6 -> Task 9 | Adjacent population (n=560) | 332 | 329 | 59.29% -> 58.75% | 26/29/505 | -0.54 pp | [-3.04, +1.96] | .788 |

Task 9's mirror gain is small, uncertain, and exactly offset (in win count) by its adjacent-population loss. It is not a practical repair.

## Opponent totals and absolute floors

Each adjacent opponent has `n=80`; the mirror has `n=200`. Entries are `wins/rate; delta vs left; G/R; exact p`.

| Opponent | Historical Silver | Task 6 vs Silver | Task 9 vs Silver | Task 9 vs Task 6 |
|---|---:|---:|---:|---:|
| historical_silver | 100 / 50.00% | 36 / 18.00%; -32.00 pp; 15/79; 1.15e-11 | 39 / 19.50%; -30.50 pp; 14/75; 3.01e-11 | +1.50 pp; 16/13; .711 |
| arch_peak | 39 / 48.75% | 13 / 16.25%; -32.50 pp; 4/30; 6.16e-6 | 11 / 13.75%; -35.00 pp; 4/32; 1.94e-6 | -2.50 pp; 1/3; .625 |
| arch_shumpei | 40 / 50.00% | 27 / 33.75%; -16.25 pp; 5/18; .0106 | 31 / 38.75%; -11.25 pp; 8/17; .108 | +5.00 pp; 9/5; .424 |
| alakazam_capbloo_gold | 62 / 77.50% | 61 / 76.25%; -1.25 pp; 3/4; 1.0 | 59 / 73.75%; -3.75 pp; 4/7; .549 | -2.50 pp; 2/4; .688 |
| cynthia_v23 | 67 / 83.75% | 65 / 81.25%; -2.50 pp; 2/4; .688 | 61 / 76.25%; -7.50 pp; 1/7; .0703 | -5.00 pp; 1/5; .219 |
| kang_crustle | 28 / 35.00% | 30 / 37.50%; +2.50 pp; 5/3; .727 | 27 / 33.75%; -1.25 pp; 8/9; 1.0 | -3.75 pp; 6/9; .607 |
| marnie_kazuki_live | 68 / 85.00% | 64 / 80.00%; -5.00 pp; 2/6; .289 | 68 / 85.00%; 0.00 pp; 4/4; 1.0 | +5.00 pp; 6/2; .289 |
| mega_lucario_public | 74 / 92.50% | 72 / 90.00%; -2.50 pp; 1/3; .625 | 72 / 90.00%; -2.50 pp; 1/3; .625 | 0.00 pp; 1/1; 1.0 |

Recurring severe floors hidden by the aggregate:

- **Arch Peak is catastrophic and worsens:** Task 6 is 13-67 (16.25%), split 9/40 (22.5%) in seat 0 and 4/40 (10.0%) in seat 1. Task 9 is 11-69 (13.75%), split 8/40 (20.0%) and **3/40 (7.5%)**.
- **The exact Historical-Silver anchor remains catastrophic:** Task 6 is 18% in both policy seats; Task 9 is 21% in seat 0 and 18% in seat 1. These are not small aggregate fluctuations.
- Arch Shumpei is another recurring low absolute bucket: Task 6 is 32.5%/35.0% by seat; Task 9 is 37.5%/40.0%. Task 9's `+5 pp` opponent gain is uncertain and leaves a poor absolute floor.
- Task 9 introduces or deepens adjacent seat floors: Cynthia seat 1 falls 34 -> 30 (`85% -> 75%`, direct 0 gains/4 regressions, exact `p=.125`); Kang/Crustle seat 1 falls 15 -> 11 (`37.5% -> 27.5%`, 3/7, `p=.344`).

## Seat totals and sensitivity

| Comparison | Policy seat | Left wins/rate | Right wins/rate | G/R/T | Delta | Exact p |
|---|---:|---:|---:|---:|---:|---:|
| Silver -> Task 6 | 0 (agent A/player 0) | 243/380, 63.95% | 187/380, 49.21% | 19/75/286 | -14.74 pp | 4.82e-9 |
| Silver -> Task 6 | 1 (agent B/player 1) | 235/380, 61.84% | 181/380, 47.63% | 18/72/290 | -14.21 pp | 8.07e-9 |
| Silver -> Task 9 | 0 (agent A/player 0) | 243/380, 63.95% | 192/380, 50.53% | 22/73/285 | -13.42 pp | 1.46e-7 |
| Silver -> Task 9 | 1 (agent B/player 1) | 235/380, 61.84% | 176/380, 46.32% | 22/81/277 | -15.53 pp | 4.07e-9 |
| Task 6 -> Task 9 | 0 | 187/380, 49.21% | 192/380, 50.53% | 21/16/343 | +1.32 pp | .511 |
| Task 6 -> Task 9 | 1 | 181/380, 47.63% | 176/380, 46.32% | 21/26/333 | -1.32 pp | .560 |

Task 9's five-win seat-0 increase and five-win seat-1 decrease exactly cancel. Neither direct seat movement is distinguishable from zero. The identical-policy mirror control's 58/42 result also prevents treating an unadjusted seat split as policy strength.

## Seed sensitivity

`P/Z/N` counts seed clusters with positive, zero, or negative net paired delta. Quartiles are consecutive game offsets within each frozen seed block; values are paired deltas in percentage points.

| Comparison | Panel | P/Z/N | Cluster net range | Q1 | Q2 | Q3 | Q4 |
|---|---|---:|---:|---:|---:|---:|---:|
| Silver -> Task 6 | mirror, 100 clusters | 2/32/66 | -1..+1 | -36.00 | -34.00 | -20.00 | -38.00 |
| Silver -> Task 6 | adjacent, 40 clusters | 4/6/30 | -4..+3 | -7.14 | -11.43 | -10.00 | -4.29 |
| Silver -> Task 9 | mirror, 100 clusters | 1/37/62 | -1..+1 | -38.00 | -30.00 | -24.00 | -30.00 |
| Silver -> Task 9 | adjacent, 40 clusters | 3/11/26 | -5..+2 | -5.71 | -12.86 | -9.29 | -7.14 |
| Task 6 -> Task 9 | mirror, 100 clusters | 14/74/12 | -1..+2 | -2.00 | +4.00 | -4.00 | +8.00 |
| Task 6 -> Task 9 | adjacent, 40 clusters | 14/10/16 | -2..+2 | +1.43 | -1.43 | +0.71 | -2.86 |

Both candidates regress versus Silver in every seed quartile of both panels. In contrast, Task 9 versus Task 6 changes sign across quartiles and has a zero-centred cluster interval. That is redistribution/seed sensitivity, not stable repair.

## Complete discordant-key ledger

Every paired gain and regression is encoded below. A key is `(panel, opponent, seat, seed_base + offset)`. `G` is a right-policy gain, `R` a right-policy regression, ranges are inclusive, and `-` means none. This compact ledger is exhaustive; ties are omitted.

<details>
<summary>Historical Silver -> Task 6 (37 gains, 147 regressions)</summary>

```text
adjacent_population|alakazam_capbloo_gold|seat0; base=271958313; G=31,35; R=10,14
adjacent_population|alakazam_capbloo_gold|seat1; base=271958313; G=3; R=33-34
adjacent_population|arch_peak|seat0; base=271958313; G=0,16-17,19; R=5-7,11,18,23,25-26,28-30,32,36,39
adjacent_population|arch_peak|seat1; base=271958313; G=-; R=0-1,3-4,9-10,12,16-17,19,22,24,33-35,38
adjacent_population|arch_shumpei|seat0; base=271958313; G=21-22,32,38; R=2,5,9-10,16-17,27-28
adjacent_population|arch_shumpei|seat1; base=271958313; G=37; R=1,5,11,16,23,25-26,28,31-32
adjacent_population|cynthia_v23|seat0; base=271958313; G=-; R=35,38
adjacent_population|cynthia_v23|seat1; base=271958313; G=3,37; R=12,23
adjacent_population|kang_crustle|seat0; base=271958313; G=26; R=20
adjacent_population|kang_crustle|seat1; base=271958313; G=3,29,32,35; R=0,22
adjacent_population|marnie_kazuki_live|seat0; base=271958313; G=3; R=30
adjacent_population|marnie_kazuki_live|seat1; base=271958313; G=35; R=1,10,16,23,26
adjacent_population|mega_lucario_public|seat0; base=271958313; G=1; R=9
adjacent_population|mega_lucario_public|seat1; base=271958313; G=-; R=11,15
historical_silver|historical_silver|seat0; base=271828182; G=10,12,32,49,62-63; R=0,2-4,13,15-16,19,21,23-24,27-29,31,33-34,36,40,44,46,48,51,53,56,59,61,64-66,68,71,74-75,79-81,85,88-91,93-94,96,98
historical_silver|historical_silver|seat1; base=271828182; G=5,36,58-59,61,71,80,89,91; R=1,6,8-12,17-18,22,26,30,32,35,38,41,45,47,49,62-63,67,70,73,76,82-84,86-87,92,95,97
```
</details>

<details>
<summary>Historical Silver -> Task 9 (44 gains, 154 regressions)</summary>

```text
adjacent_population|alakazam_capbloo_gold|seat0; base=271958313; G=31,35; R=0,10,18,34
adjacent_population|alakazam_capbloo_gold|seat1; base=271958313; G=3,19; R=20,33-34
adjacent_population|arch_peak|seat0; base=271958313; G=0,17,19,24; R=5-7,11,18,21,23,25-26,28-30,32,36,39
adjacent_population|arch_peak|seat1; base=271958313; G=-; R=0-1,3-4,9-10,12,14,16-17,19,22,24,33-35,38
adjacent_population|arch_shumpei|seat0; base=271958313; G=21-23,32; R=5,9-10,16-17,28
adjacent_population|arch_shumpei|seat1; base=271958313; G=4,24,30,37; R=1,7,10-11,15,23,25-26,31-32,38
adjacent_population|cynthia_v23|seat0; base=271958313; G=-; R=25,35
adjacent_population|cynthia_v23|seat1; base=271958313; G=3; R=6,10,12,23,26
adjacent_population|kang_crustle|seat0; base=271958313; G=25-26,29,39; R=20,34,37
adjacent_population|kang_crustle|seat1; base=271958313; G=5,12,32,35; R=15-16,22-24,31
adjacent_population|marnie_kazuki_live|seat0; base=271958313; G=3,23; R=21
adjacent_population|marnie_kazuki_live|seat1; base=271958313; G=17,35; R=16,26,36
adjacent_population|mega_lucario_public|seat0; base=271958313; G=1; R=-
adjacent_population|mega_lucario_public|seat1; base=271958313; G=-; R=8,11,15
historical_silver|historical_silver|seat0; base=271828182; G=6,10,41,49,63; R=0,2-4,7,13,15-16,21,23-24,27-29,31,34,36,40,44,46,48,51,53,55-56,58,61,64-66,68,71,74-75,79-80,85,89,91,93-94,96
historical_silver|historical_silver|seat1; base=271828182; G=28,51,53,58,61,65,71,80,91; R=1,6,8-12,17-18,22,26,30,32,38,43,45,47,49,52,62-63,67,69-70,73,76,82-83,86-87,92,95,97
```
</details>

<details>
<summary>Task 6 -> Task 9 (42 gains, 42 regressions)</summary>

```text
adjacent_population|alakazam_capbloo_gold|seat0; base=271958313; G=14; R=0,18,34
adjacent_population|alakazam_capbloo_gold|seat1; base=271958313; G=19; R=20
adjacent_population|arch_peak|seat0; base=271958313; G=24; R=16,21
adjacent_population|arch_peak|seat1; base=271958313; G=-; R=14
adjacent_population|arch_shumpei|seat0; base=271958313; G=2,23,27; R=38
adjacent_population|arch_shumpei|seat1; base=271958313; G=4-5,16,24,28,30; R=7,10,15,38
adjacent_population|cynthia_v23|seat0; base=271958313; G=38; R=25
adjacent_population|cynthia_v23|seat1; base=271958313; G=-; R=6,10,26,37
adjacent_population|kang_crustle|seat0; base=271958313; G=25,29,39; R=34,37
adjacent_population|kang_crustle|seat1; base=271958313; G=0,5,12; R=3,15-16,23-24,29,31
adjacent_population|marnie_kazuki_live|seat0; base=271958313; G=23,30; R=21
adjacent_population|marnie_kazuki_live|seat1; base=271958313; G=1,10,17,23; R=36
adjacent_population|mega_lucario_public|seat0; base=271958313; G=9; R=-
adjacent_population|mega_lucario_public|seat1; base=271958313; G=-; R=8
historical_silver|historical_silver|seat0; base=271828182; G=6,19,33,41,59,81,88,90,98; R=7,12,32,55,58,62
historical_silver|historical_silver|seat1; base=271828182; G=28,35,41,51,53,65,84; R=5,36,43,52,59,69,89
```
</details>

## Reproducibility, raw paths, and hashes

Independent calculator:

```powershell
.venv-rl\Scripts\python.exe autonomous_gold_20260715\comparisons\historical_silver_vs_task9_20260802\SOL_ULTRA_NUMERICAL_AUDIT_CALC.py
```

Calculator SHA-256: `EB2DCAFAC4E99A1B6823F2A36A9B4B134AC44AC1124FB93153FA5ED23C3A757C`.

The raw-tree digest is `SHA256(UTF-8 sorted relative/path<TAB>bytes<TAB>file_sha256<LF>)`, covering every raw file without altering it.

| Raw output | Files | Raw-tree SHA-256 |
|---|---:|---|
| `.../fixed760_task6_raw` | 56 | `F9E5F8C9B0CEA61CE2A16970947B2CC6E0E39B8F05582A50C56B55E9A8E45153` |
| `.../fixed760_task9_raw` | 56 | `AC8B3F9CE656807A9E0D332CE186FBD03130605BAB15FC7A548C22AAD581886E` |

Full paths are:

- `autonomous_gold_20260715/comparisons/historical_silver_vs_task9_20260802/fixed760_task6_raw`
- `autonomous_gold_20260715/comparisons/historical_silver_vs_task9_20260802/fixed760_task9_raw`

| Suite/panel | Manifest SHA-256 | `paired_results.csv` SHA-256 | `report.json` SHA-256 | Panel-tree SHA-256 |
|---|---|---|---|---|
| Task 6 / historical_silver | `4835FFDECBDFB6E98DE564967E83346A391F4A9F11D8DD1B53EF0CB35EA54331` | `114FBACD0F5084F26F81EC4D4B8B1C2FFAA1A1AB5C14D2F095215DBD0390FE33` | `53FF89F5A4EFD11E61543DDCDA1A5CCF9CA595AAF572AF9854447411CF733AE0` | `1358CCEF02B8F9ADD737C2B9F32BE02C385BA5B1D459B8046F47089B96F1FD85` |
| Task 6 / adjacent_population | `5055BBFAF896DC5524AC8F0954FD232FDC6CF5F9630D668A2F00C9C19325775C` | `01E563EFFC241C58FAB76FCA2F47E7452D710AAD1BE97C4D8E13578AC684DFFC` | `C6BAA1032662BB2AF6278CFFA9CF176299B15C684D9B3F4E464612EC9BBB1E1B` | `C501BB108212117782FBADD52FFE82444D8828D27F76029AE93532D0668B00D3` |
| Task 9 / historical_silver | `A06506018F7F68E2AD1FE478F5D09B1F784B32EA762D067688D897979D71FDC6` | `B958D395B00C4D280231CEC6EEB1315CA6DD820280DC37495DE239686A2EA980` | `07EA6F23A33F7832A74B961DA92362B6DADF9C6CC756912A1FF66AC505A8D20C` | `EC2487BAA2225B7ACC1C1C1245AB41435E491A12420CDF127D5B53AAA65A7CD1` |
| Task 9 / adjacent_population | `6A87AD1F1942F00182609AF95A934049A6C710A3AA9C409424771E9CBC5A2DC2` | `DF5304D2688C0C3DC7F4E1A2CD1308C6B6FAC561010BF3B711DD29B939A683AF` | `26522D7521B051EB71D09B4BC3595188B00971F6CAC820BAE5D3551FCEC8146C` | `85CD890A7B415C79CBE8D0F99147F677EBA7ACD6033FEFDFEFCAE6C22C8BA46A` |

Frozen artifact hashes independently verified:

- Historical-Silver `main.py`: `F4B578453C9D953BE94885144DD50E05DBA4510DF3340BE27ADE07495896046E`
- Task 6 `main.py`: `99EE7BF5E6E6D61D863EF1D131232F90DCE36A3CFDF032AF6E534DECA79B2756`
- Task 9 `main.py`: `0A9F0052095257B08CC5C5ABACAA0E912D7E02A9842145B48E2192A6F50ED4AE`
- All three `deck.csv`: `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`
- Seeded `cg/cg.dll`: `0C6153F9206366F2588E5C601AB086EA997A66E80E4FEB6D95635B2987C9929B`
- `run_seeded_paired_suite.py`: `5EC25C98F2777FF61DE2DBD0A03A08519A7FEA4B2B4C510B5B8895BC2000E000`
- `run_local_battle.py`: `03881BA796D1D8D3A095067684E8D0F5B069EF40AC0B543420896157F0431F2A`

Only after the independent calculation was complete, it was cross-checked against `ROOT_RECOMPUTE_FIXED760.json` SHA-256 `78D8C2E3A948EFCC3C047E8DCE064B9D89CF728307AA3D034027867B265B4C15`. All **609** shared aggregate count fields agree, and its 84 direct Task-6/Task-9 discordant keys exactly equal the independently reconstructed set. This agreement is a cross-check, not the source of the numbers above.

## Acceptance-check disposition

| Check | Result |
|---|---|
| Frozen artifact hashes and immutable schedule | PASS |
| 760 unique keys per candidate and exact schedule equality | PASS |
| Duplicate controls exact on every key, including result and decision count | PASS (760/760 for each candidate) |
| Baseline deterministic across both suites | PASS (760/760) |
| Exit/start/action/exception/max-step health | PASS (all zero faults) |
| Task 7–9 repaired Task 6 | FAIL: 42 gains equal 42 regressions; 0.00 pp, CI crosses zero |
| Task 6 can replace Historical Silver | FAIL: -14.47 pp overall with severe mirror/Arch-Peak floors |
| Task 9 can replace Historical Silver | FAIL: -14.47 pp overall; no aggregate repair and several shifted regressions |

No traces are pasted, no simulations were added, and no source, deck, schedule, or raw runner output was modified.
