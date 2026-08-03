# Comparison B: v0 versus runtime-certified v1 fix5

## Purpose

This specification freezes the paired comparison of
`alakazam_newdeck_v0_port` and
`alakazam_newdeck_v1_package_runtime_certified_fix5`.

Both versions use the same selected 60-card deck. The measured difference is
the operational effect of the nine-slot adaptation rules and their strict
transactions. It is not a deck-list effect and does not isolate individual
card causality.

Every earlier v1 candidate and Comparison B output is superseded. In
particular, fix4 is `SUPERSEDED_FORMAL_RUNTIME_FAULT`. No earlier row may be
reused or pooled.

## Frozen provenance

- Repository commit at branch start:
  `54f09edb2b3f6dd2def7c2c49efde16dfeda97c9`
- Branch: `codex/alakazam-staged-development`
- Fix5 contract SHA-256:
  `5270AD22162ADDD81963E99CF459F40FE1C1D62259E501BB199D53A547CE8D20`
- Engine:
  `analysis_outputs/cynthia_v9_vs_v11_poffin_role_selection_20260713/seeded_engine`
- Engine tree SHA-256:
  `466638706BD5C6915E25D1B3CB9E3D966390FBC263F4ED3153108E29C0194FFF`
- Python:
  `C:\Users\amuam\project\AI_pokeka_competition\.venv-rl\Scripts\python.exe`
  (`3.11.6`)
- Paired runner SHA-256:
  `5EC25C98F2777FF61DE2DBD0A03A08519A7FEA4B2B4C510B5B8895BC2000E000`
- Battle runner SHA-256:
  `E1ABA0151CDAEE425B858511AA760CE5C5647D555DDEFBD69D7319C29C5B773B`
- Combiner SHA-256:
  `CABFB6ECB500EF1395B05EDB5A9775193B8A13578E3EDF35C0CED04214175C77`
- Metric runner SHA-256:
  `BCC98229B23C86FC5EB248D3F1E254337008FF4E85BD85224B3B3D6F570F1EEA`
- Metric summarizer SHA-256:
  `1679DCFFEF79D72A69A8CD49B6EA9A056A88FE120F75639B77740FA65EFF8A03`

## Versions

### Baseline

- Source:
  `alakazam_staged_20260729/versions/alakazam_newdeck_v0_port`
- Adapter:
  `alakazam_staged_20260729/eval_adapters/alakazam_newdeck_v0_port`
- Policy closure SHA-256:
  `D9ADBC03054AB1D2FFD1E1955D734DB1D14DA74C9D1088249A271F98EBCECD46`
- Adapter `main.py` SHA-256:
  `C38C357D28CB4E8401815220E385B5542B385B7AB2984719E30DBAF9503CC2AC`

### Candidate

- Source:
  `alakazam_staged_20260729/versions/alakazam_newdeck_v1_package_runtime_certified_fix5`
- Adapter:
  `alakazam_staged_20260729/eval_adapters/alakazam_newdeck_v1_package_runtime_certified_fix5`
- Policy closure SHA-256:
  `5FFA8776CA95E16C7030C55B5682DE42BA21C06964C790A3D6312B60FBAA5009`
- Planner SHA-256:
  `80A9B0F88A04591D4174B21AFCC5C9019A4EFCEC02E8F9C2D1576DCFC0FC044B`
- Adapter `main.py` SHA-256:
  `426F1BBB71583A691CBF39A07FA8A042CB0AB0600EB43F22F9E4DBD247E5AAEC`
- Unit tests: `146/146`

Both versions have:

- raw deck SHA-256:
  `F598F5E578D0440C96DC0492EAECF2E19739B7A23225BE57114A724EF7D0FB94`;
- normalized deck hash:
  `4414e8995e50c7a00d4b6aa7d9229f63c1dff5261643ec7cd86c4e329113ed69`.

Policy closure covers top-level non-test Python files, top-level `deck.csv`,
and `runtime/main.py`. Relative paths are sorted lexically. Each row is
`path + NUL + uppercase file SHA-256 + NUL + byte size + LF`; the UTF-8
concatenation is SHA-256 hashed.

## Opponents

| Label | Path |
| --- | --- |
| `marnie` | `meta_agents/marnie_sota_live_85033057_simple` |
| `cynthia` | `meta_agents/cynthia_garchomp_nasuo445_v80_legal_complete_role_cycle` |
| `alakazam_mirror` | `meta_agents/alakazam_oselcoun_live_85035844_simple` |
| `rocket_mewtwo_spidops_proxy` | `meta_agents/rocket_mewtwo_spidops_kashiwashira_20260703_simple` |
| `kangaskhan_crustle` | `meta_agents/kangaskhan_crustle_mpgaming_v13_backupkang_two_growline` |
| `historical_silver` | `analysis_outputs/reference_agents/historical_silver_archaludon_54495224` |
| `direct_frozen` | `alakazam_staged_20260729/eval_adapters/alakazam_800_frozen` |

The Rocket opponent is a Mewtwo/Spidops proxy, not the exact public
Mewtwo ex/Ariados list.

## Immutable schedule

- Seed bases:
  `202608500`, `202608510`, `202608520`, `202608530`, `202608540`
- Games per opponent, seed base, and seat: `10`
- Seats: `0`, `1`
- Max steps: `1000`
- Total: `7 × 50 × 2 = 700` paired rows
- Expected manifest rows: `210`
- Expected child summaries: `2,100`
- Expected paired schedule SHA-256:
  `619BA954971C33FDC698810A58DF1E2C0786FFF16B6A0CCD2715DC33B04FD076`
- Expected manifest schedule SHA-256:
  `9277E7463E1372FCE8095BD86A79FA35EC616177034CBEA7894BCBC5419AAAB3`

## Fresh outputs

- Panels:
  `alakazam_staged_20260729/evaluations/comparison_b_runtime_certified_fix5_panels`
- Combined:
  `alakazam_staged_20260729/evaluations/comparison_b_runtime_certified_fix5_combined`
- Comparison name:
  `comparison_b_v0_vs_v1_runtime_certified_fix5`

Each of 35 `(seed_base, opponent)` panels uses the checked
`tools/run_seeded_paired_suite.py` with both seats, ten games per seat, and up
to three identical-command retries. A failed attempt is preserved and never
pooled. The first `report.valid=true` attempt is canonical. Any panel without a
valid attempt blocks the entire comparison.

## Prerequisite hard gate

Before the first panel starts, all of the following fresh fix5 evidence must
pass:

1. 146/146 unit and mutation tests;
2. all 80 known-fault replay games;
3. all 140 smoke games;
4. all 700 formal safety games;
5. exact callback and transaction pairing;
6. zero invalid action, exception, timeout, max-step, pending transaction,
   duplicate-control violation, structural fault, unknown removed-card route,
   first-legal fallback, candidate-owned fallback, transaction abort, and
   irreversible fault.

Failure blocks Comparison B regardless of any partial win result.

## Comparison hard gate

- exactly 700 unique `(opponent, seat, seed)` rows;
- exact baseline/candidate schedule equality;
- 35 selected valid panels and 210 manifest rows;
- child exit code, action error, max-step, timeout, unstarted, invalid winner,
  and baseline duplicate mismatch counts all zero;
- checked rows and formal metric rows agree exactly on candidate schedule,
  result, and steps;
- candidate-owned generic and first-legal fallback counts are zero.

## Required analysis

Report overall, opponent, seat, seed-base, paired gain/loss, discordant pairs,
and the exact two-sided paired sign-test p-value.

Also report first attack, attack gaps with and without terminal tails, post-KO
continuity, maximum consecutive attacks, hand size at attack, Powerful Hand
counters, KO-threshold misses, second-line creation, added-card
exposure/play, removed-card hits, fallback, safety, and decision-time metrics.

Event-denominator metrics are descriptive unless an exact paired event
definition exists. Do not call their raw difference a causal effect.
