# Rule 1 fixed160 independent numerical audit

## Assessment

**PASS against every supplied frozen Rule 1 fixed160 acceptance check.**

This is a non-destruction/mechanism pass, not evidence of increased strength.
Historical-Silver and the candidate both independently reconstruct to
**100-60 (62.50%)**. The paired result is **0 gains, 0 regressions, 160 ties**,
or `0 wins / 0.00 percentage points`; exact McNemar `p = 1.0`. Rule 1 did
activate naturally 28 times and all 28 activations were outcome ties. The
candidate therefore has a real, correctly bounded mechanism but no observed
practical or statistical improvement on this schedule.

## Frozen identity and execution validity

- Immutable spec SHA-256:
  `E2B8986663A43A7F6F52888E487F39B8D059CDCDDF441A3E87D8C093DF15274C`
  (match).
- Raw-run ledger SHA-256:
  `DB612879410B9FE53AF97B33A33212CD80C3FD24FEAD8184DA224F805616C6DD`
  over 512 files (match).
- Exact Historical-Silver `main.py`:
  `F4B578453C9D953BE94885144DD50E05DBA4510DF3340BE27ADE07495896046E`
  (match). The candidate's stored parent has the same hash.
- Candidate `main.py`:
  `153D8461FB66927DB9731CBE614B71FF5398B8EAE8980AE0BB4D46ADD0E8792A`
  (match).
- Both policy decks:
  `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`
  (match).
- All frozen strategy, verification, opponent, seeded-engine, checked-runner,
  and trace-wrapper hashes in the immutable spec also match.
- Exactly 160 unique `(panel, opponent, seat, seed)` keys reconstruct, equal
  the immutable expected key set, and are exactly equal between baseline and
  candidate. The panel name is supplied structurally by the immutable panel
  directory because the checked runner writes one CSV per panel.
- All 24 manifest commands exited zero and used
  `.venv-rl/Scripts/python.exe`, the checked local-battle runner,
  `--engine-seed`, the frozen engine, correct seat mapping, 20 games, and
  `--max-steps 1000`.
- Across all 480 role-game summaries: zero start faults, action errors,
  populated exception fields, invalid results, or max-step hits. All traces
  parse, have one row per reported decision step, and have no step-index
  faults.
- Independently reconstructed rows match both `paired_results.csv` files,
  both `cell_summary.csv` files, and both runner reports with zero discrepancy.

Policy mapping is explicit: at seat 0 the tested policy is agent A/player 0
and wins iff `result == 0`; at seat 1 it is agent B/player 1 and wins iff
`result == 1`. No player-0 counter is reused for seat-1 runs.

The identical-policy control was audited before interpreting seat movement.
In the Historical-Silver mirror, exact Silver is both players. The two
seat-labelled baseline runs match on every non-trace summary field and on
trace bytes for **20/20** seeds. Those same games contain 11 player-0 wins and
9 player-1 wins, so the apparent `11/9` seat split is complementary labeling
of identical games, not a policy-strength difference.

The duplicate baseline A/B controls match **160/160** on the checked tuple
`(seed, result, steps, turn, action_errors, hit_max_steps)`, on every non-trace
summary field, and byte-for-byte on all 160 traces. In particular, result and
decision-count equality are exact on every key.

## Paired effect and uncertainty

| Quantity | Historical-Silver | Candidate | Paired result |
|---|---:|---:|---:|
| Wins-losses | 100-60 | 100-60 | 0 wins |
| Rate | 62.50% | 62.50% | 0.00 pp |
| Gains / regressions / ties | - | - | 0 / 0 / 160 |
| Both-win / both-loss | - | - | 100 / 60 |

The primary paired empirical interval resamples whole engine-seed clusters
within panel because each adjacent seed is reused across opponents and seats.
Every observed row and every one of the 40 seed clusters has net delta zero,
so every possible empirical resample is also zero: **95% interval
`[0.00, 0.00] pp`**. This degenerate empirical interval is descriptive of the
frozen sample and is not proof of population identity.

As a finite-sample sensitivity bound, zero discordant rows in 160 gives the
one-sided 95% Clopper-Pearson upper bound
`1 - 0.05^(1/160) = 1.8549%` on discordance. Since absolute net paired effect
cannot exceed discordance, a conservative exact magnitude envelope is
**`[-1.855, +1.855] pp`**. Neither interval supports a positive strength
claim; the point effect is exactly zero.

## Rule 1 mechanism

Candidate and baseline trace bytes differ in 28 games; the other 132 are
byte-identical. All 28 same-determinization first differences satisfy the
mechanism before their outcomes are considered:

- identical pre-action trace observation;
- turn 0, candidate player, `SETUP_BENCH_POKEMON`;
- exact Silver action `[]` versus one legal candidate option;
- visible Duraludon in hand;
- same-callback Cinderace-to-Active commitment; and
- later visible Cinderace Active plus exactly one Duraludon on the candidate
  Bench, while the empty-action baseline has no Duraludon there.

There are zero off-surface or malformed first differences and zero mechanism
faults. Natural starts are **28 total**, split **11 at seat 0** and **17 at
seat 1**:

| Opponent | Seat 0 starts | Seat 1 starts | Total | Outcome G/R/T |
|---|---:|---:|---:|---:|
| Historical-Silver | 5 | 3 | 8 | 0/0/8 |
| Arch Peak | 2 | 4 | 6 | 0/0/6 |
| Alakazam Capbloo Gold | 2 | 5 | 7 | 0/0/7 |
| Marnie Kazuki Live | 2 | 5 | 7 | 0/0/7 |
| **Total** | **11** | **17** | **28** | **0/0/28** |

Thus the start gate is not being inferred from score: it is established from
the retained action/state traces, and those traced starts changed no winner.

## Buckets, floors, and sensitivity

Every panel, opponent, seat, and seed-quartile delta is zero.

| Opponent | Baseline W-L / rate | Candidate W-L / rate | Delta | Candidate seat 0 | Candidate seat 1 |
|---|---:|---:|---:|---:|---:|
| Historical-Silver | 20-20 / 50.00% | 20-20 / 50.00% | 0 | 11/20, 55% | 9/20, 45% |
| Arch Peak | 20-20 / 50.00% | 20-20 / 50.00% | 0 | **6/20, 30%** | 14/20, 70% |
| Alakazam Capbloo Gold | 29-11 / 72.50% | 29-11 / 72.50% | 0 | 16/20, 80% | 13/20, 65% |
| Marnie Kazuki Live | 31-9 / 77.50% | 31-9 / 77.50% | 0 | 14/20, 70% | 17/20, 85% |

The aggregate hides a severe recurring absolute floor: **Arch Peak seat 0 is
6-14 (30%)** for both policies. Rule 1 neither causes nor repairs it. The next
lowest seat cell is the mirror seat-1 label at 45%, which must be read with the
identical-policy control above.

| Policy seat | Baseline | Candidate | Delta | G/R/T |
|---|---:|---:|---:|---:|
| 0 (agent A/player 0) | 47-33 / 58.75% | 47-33 / 58.75% | 0 | 0/0/80 |
| 1 (agent B/player 1) | 53-27 / 66.25% | 53-27 / 66.25% | 0 | 0/0/80 |

Seed-cluster net-delta counts are `positive/zero/negative = 0/20/0` in each
panel, with delta range `0..0`. Absolute adjacent-population rates by
consecutive five-seed quartile are `70.00%, 60.00%, 66.67%, 70.00%`; the
Historical-Silver mirror is 50.00% in every quartile. Candidate and baseline
are identical in every quartile. Adjacent absolute wins range from 2 to 5 per
six-row seed cluster, while the identical-policy mirror is exactly one win per
two-row seed cluster.

## Acceptance-check disposition

| Frozen check | Result |
|---|---|
| Spec, source, deck, engine, runner, opponent, and raw hashes | PASS |
| 160 unique keys and exact baseline/candidate schedule equality | PASS |
| Duplicate summaries exact, including result and decision count | PASS (160/160) |
| Duplicate traces byte-identical | PASS (160/160) |
| Exit/start/action/exception/result/max-step/trace faults | PASS (all zero) |
| Natural starts at least 4 | PASS (28) |
| At least one start in each seat | PASS (11 / 17) |
| Paired gains at least regressions | PASS (0 >= 0) |
| No seat or opponent at least 3 wins below parent | PASS (all deltas 0) |
| Every candidate first difference has exact Rule 1 mechanism | PASS (28/28) |
| **Overall frozen Rule 1 fixed160 gate** | **PASS** |

The numerical recommendation is therefore **PASS this specific frozen Rule 1
fixed160 gate**, with the explicit qualification that the practical effect is
neutral and no strength increase was observed. This audit makes no judgment
about any later rule.

## Reproducibility and raw paths

Run:

```powershell
.venv-rl\Scripts\python.exe autonomous_gold_20260715\numerical_audits\archaludon_historical_silver_single_resolver_salvage_v1_rule1_fixed160\audit_rule1_fixed160.py
```

Calculator SHA-256:
`C3FA172BF10C7424C676321984C4A897F6F49C50808609E0F66C13174C41B7CF`.

Raw root:

`C:\Users\amuam\project\AI_pokeka_competition\autonomous_gold_20260715\evaluations\archaludon_historical_silver_single_resolver_salvage_v1\rule1_fixed160_raw`

The parent-supplied run-ledger digest is reproduced exactly as SHA-256 over
the UTF-8 LF-joined (no terminal LF) lines
`UPPERCASE_FILE_SHA256 + two spaces + absolute Windows FullName`, after
PowerShell FullName sorting. Its preimage is 163,647 bytes and its digest is
`DB612879410B9FE53AF97B33A33212CD80C3FD24FEAD8184DA224F805616C6DD`.
Because that identity is absolute-path-bound, the calculator also reports a
portable digest over sorted
`relative/path<TAB>bytes<TAB>UPPERCASE_FILE_SHA256<LF>` lines:
`B9D89566125FED05298666CA8F63B54196140760D9CA8F6CF108EE88EFA98C31`.

| Raw panel | Files | Portable panel-tree SHA-256 | Manifest SHA-256 | `paired_results.csv` SHA-256 | `report.json` SHA-256 |
|---|---:|---|---|---|---|
| `historical_silver` | 130 | `E87620F743A2E5F1C48E7E1B4CA09DC05E4360DC95DB6D1172DA65B9902D5239` | `F42C7A1BDF470596149CE9E8F14D2741C161248C689CD23E09E7FF7B28AA3CA6` | `C11077639865CABFC58ECE42697324E3C3D70B5443D4F8FA511D4C4504F891E8` | `37706612165C1E2D80C3485C70D0AC571CF6F7148EA79C96B342390A376B7315` |
| `adjacent_population` | 382 | `6DD32313A30B2548DF97FC3C64ED1DC04E839354C212BA6518ABFB1D98156D55` | `A1BD9A0B54C9C48B3A61555A22A5A7B20834A28B689530A117A0CE3B4A668C55` | `0EAA7B9A5E4EA0A0780DBB57ABC39DD3132A4E698F78E56D50F4119484FA0F9E` | `AF692679EE949E2D6B72A3EE1283361A1F6A1A5C7A1DFEB16FF6F7D639BBCCE4` |

## Assumptions

1. The immutable panel directory is the authoritative structural `panel`
   field for each checked-runner CSV row.
2. Winner index is interpreted relative to the tested policy's actual player
   mapping, as stated above.
3. Schedule rows are paired only on exact immutable keys; no missing or extra
   row is imputed.
4. A natural start requires the complete trace mechanism predicate above; a
   score or changed trace length alone is insufficient.
5. Statistical statements are conditional on these frozen opponents, seats,
   and seed blocks. The cluster-empirical interval is degenerate because the
   observed paired delta is identically zero, while the exact envelope is a
   conservative finite-sample sensitivity bound.
6. A positive aggregate delta alone would not imply strength. Here there is no
   positive delta at all, and the 30% Arch-Peak seat floor remains explicit.

No simulation was run or expanded, no full trace is pasted, and no source,
deck, schedule, specification, or raw runner output was modified.
