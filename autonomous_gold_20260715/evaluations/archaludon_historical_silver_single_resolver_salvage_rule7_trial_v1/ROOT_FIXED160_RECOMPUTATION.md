# Root recomputation: Rule 7 fixed160

## Frozen comparison

- Overlay spec SHA:
  `3B60AE8008D6ED8977B9703AFD070F99618E13E9AB521AA6B52E241F2F28245E`.
- Baseline Rule 5 SHA:
  `D966E455E5110F9D5616195AEAAC8663E6A92F310DAFC4B7F79E4D37149A9C62`.
- Candidate Rule 7 SHA:
  `9C2D5935364C0940967D48D85E2690EC386569143CD922186A31C716C5391BC1`.
- The checked runner completed both frozen panels with exit code zero.

## Independent root counts

Root imported the two raw `paired_results.csv` files and recomputed all wins
from their `baseline_win` and `candidate_win` columns.

- Exact rows: 160.
- Unique `(panel, opponent, seat, seed)` keys: 160; duplicates: 0.
- Baseline wins: 100/160.
- Candidate wins: 98/160.
- Paired gain/regression/tie: 3/5/152.
- All 160 baseline A/B duplicate controls agree on seed, result, and steps.
- Across all 480 baseline-A, baseline-B, and candidate summary rows: zero start
  faults, action errors, and max-step hits.
- Checked reports both state `valid=true` and duplicate mismatch zero.

Cell counts:

| Opponent | Seat | Baseline | Candidate | Gain | Regression |
|---|---:|---:|---:|---:|---:|
| Historical-Silver | 0 | 11/20 | 11/20 | 0 | 0 |
| Historical-Silver | 1 | 9/20 | 8/20 | 1 | 2 |
| Arch Peak | 0 | 6/20 | 8/20 | 2 | 0 |
| Arch Peak | 1 | 14/20 | 12/20 | 0 | 2 |
| Alakazam | 0 | 16/20 | 15/20 | 0 | 1 |
| Alakazam | 1 | 13/20 | 13/20 | 0 | 0 |
| Marnie | 0 | 14/20 | 14/20 | 0 | 0 |
| Marnie | 1 | 17/20 | 17/20 | 0 | 0 |

The stage gate `paired gains >= paired regressions` fails: `3 < 5`.
Historical-Silver also declines by one win overall.  Aggregated by tested seat,
seat 0 moves `47 -> 48`, while seat 1 moves `53 -> 50`.  The seat-1 decline of
three wins separately fails the rule that a whole seat may not fall three or
more wins below the parent.  No individual opponent/seat cell declines by
three, but that does not repair either failed gate.

## First-difference audit

Root compared every baseline-A and candidate trace until the first differing
row.  Thirty-three games differ: 23 first differences are Turbo Flare target
choices (`ATTACH_FROM`), and 10 are Turbo Flare Energy-set choices
(`ATTACH_TO`).  Every first difference is inside Rule 7; no non-Turbo first
difference was found.

The eight outcome-discordant keys are:

| Result | Opponent | Seat | Seed | First difference |
|---|---|---:|---:|---|
| gain | Historical-Silver | 1 | 271828182 | select 2 rather than 3 Energy, stopping Duraludon at exact 3 |
| gain | Arch Peak | 0 | 271958316 | choose the other otherwise equal zero-Energy Duraludon |
| gain | Arch Peak | 0 | 271958329 | choose the other otherwise equal zero-Energy Duraludon |
| regression | Historical-Silver | 1 | 271828183 | move one remainder Energy between otherwise equal Duraludon |
| regression | Historical-Silver | 1 | 271828191 | choose the other otherwise equal zero-Energy Duraludon |
| regression | Arch Peak | 1 | 271958314 | select 2 rather than 3 Energy, stopping Duraludon at exact 3 |
| regression | Arch Peak | 1 | 271958329 | select 2 rather than 3 Energy, stopping Duraludon at exact 3 |
| regression | Alakazam | 0 | 271958317 | choose the other otherwise equal zero-Energy Duraludon |

Thus the numerical failure is mechanism-attributable.  Several discordances
come from serial tie-breaking between publicly equivalent Duraludon rather than
from a certified strategic improvement.  Stopping the fourth Energy is
interpretable, but on this frozen schedule it has one gain and two regressions.

Raw report hashes:

- Historical-Silver `paired_results.csv`:
  `E020E22D717C815020186E30AD7DA1B5718BF62551944ABBB4EEA6F66B709567`;
- Historical-Silver `report.json`:
  `8414DE19B0AD66E27914AB3377D83448854AEDA4EAFAC544EB2358492062E9C2`;
- adjacent `paired_results.csv`:
  `EEC61025F3EA87952A9EAA12B3FD4B4B60DFDD8324CD6304FA19DECF82259CA2`;
- adjacent `report.json`:
  `2EF29FF6B255A5CD401AFF733C35A34691E32F97ADD007665862D39C4DA13C45`.

## Root numerical conclusion

Rule 7 fails the frozen stage gate.  Under the requirements, it must not be
repaired by stacking a compensating rule and must not become the next parent.
The accepted parent therefore remains Rule 5, subject to the independent
numerical audit and final strategy judgment agreeing with this recomputation.
