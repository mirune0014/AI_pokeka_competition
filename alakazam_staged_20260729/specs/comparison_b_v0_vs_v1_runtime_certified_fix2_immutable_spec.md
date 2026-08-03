# Comparison B: v0 versus runtime-certified v1 fix2

## Purpose and interpretation

This specification freezes the paired evaluation of
`alakazam_newdeck_v0_port` against
`alakazam_newdeck_v1_package_runtime_certified_fix2`.
Both versions use the same selected 60-card deck. The measured difference is
therefore the operational effect of the nine-slot adaptation rules and their
strict runtime transactions, not a deck-list effect.

The earlier runtime-certified candidate and its smoke output are retained as
`SUPERSEDED_LIVE_RUNTIME_FAULT`. The superseded smoke completed all 140 games
but contained 36 strict-verifier faults: 35 Enhanced Hammer child-envelope
faults and one evolved-target KO-order fault.

## Frozen inputs

- Repository commit at branch start:
  `54f09edb2b3f6dd2def7c2c49efde16dfeda97c9`
- Runtime-completion contract SHA-256:
  `304F9945BE90D2716083B39137AD83521FE6EB2B3FBA031ADA727B0B6677F3FE`
- Original runtime fixture amendment SHA-256:
  `60FB4284E1854C63AA6CB7A8CF6EBDB26F2FCD3F17D3055B90A41E305EAD26B3`
- Live-smoke fix2 amendment SHA-256:
  `36A94C32748C8B0260B3B3DE3B1A1C964292ED0B301B608B0B3DB07909662CCA`
- Superseded smoke manifest SHA-256:
  `B5F800A35622B63291D13AF2C7219A4B42688E57C5C576D7457A535D3699866B`
- Engine:
  `analysis_outputs/cynthia_v9_vs_v11_poffin_role_selection_20260713/seeded_engine`
- Engine source/runtime tree SHA-256:
  `466638706BD5C6915E25D1B3CB9E3D966390FBC263F4ED3153108E29C0194FFF`
- Engine tree file count: `11`
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

- Baseline path:
  `alakazam_staged_20260729/versions/alakazam_newdeck_v0_port`
- Baseline adapter:
  `alakazam_staged_20260729/eval_adapters/alakazam_newdeck_v0_port`
- Baseline policy closure SHA-256:
  `D9ADBC03054AB1D2FFD1E1955D734DB1D14DA74C9D1088249A271F98EBCECD46`
- Candidate path:
  `alakazam_staged_20260729/versions/alakazam_newdeck_v1_package_runtime_certified_fix2`
- Candidate adapter:
  `alakazam_staged_20260729/eval_adapters/alakazam_newdeck_v1_package_runtime_certified_fix2`
- Candidate policy closure SHA-256:
  `10A92A25FCDDEAE1792701B8B8013C835311D460A27A400618129618090CC6D7`
- Candidate planner SHA-256:
  `18FEE0C19FCC38E4DDF94EF4BF1293ECD6C6E714790089F5DBAA33FA7B2915BF`
- Candidate unit tests: `124/124`
- Shared raw deck SHA-256:
  `F598F5E578D0440C96DC0492EAECF2E19739B7A23225BE57114A724EF7D0FB94`
- Shared normalized deck hash:
  `4414e8995e50c7a00d4b6aa7d9229f63c1dff5261643ec7cd86c4e329113ed69`
- Both adapter `main.py` SHA-256:
  `C38C357D28CB4E8401815220E385B5542B385B7AB2984719E30DBAF9503CC2AC`

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

The Rocket opponent is a Mewtwo/Spidops proxy, not an exact
Mewtwo ex/Ariados list.

## Immutable schedule

- Seed bases: `202608500`, `202608510`, `202608520`, `202608530`,
  `202608540`
- Games per opponent, seed base, and seat: `10`
- Seats: `0`, `1`
- Max steps: `1000`
- Total: 7 opponents × 50 seeds × 2 seats = `700` paired rows
- Expected manifest rows: `210`
- Expected child summaries: `2100`
- Expected paired schedule SHA-256:
  `619BA954971C33FDC698810A58DF1E2C0786FFF16B6A0CCD2715DC33B04FD076`
- Expected manifest schedule SHA-256:
  `9277E7463E1372FCE8095BD86A79FA35EC616177034CBEA7894BCBC5419AAAB3`

## Fresh outputs

- Smoke:
  `alakazam_staged_20260729/metrics/smoke_v1_runtime_certified_fix2_seed202608500`
- Panels:
  `alakazam_staged_20260729/evaluations/comparison_b_runtime_certified_fix2_panels`
- Combined:
  `alakazam_staged_20260729/evaluations/comparison_b_runtime_certified_fix2_combined`
- Formal metrics:
  `alakazam_staged_20260729/metrics/formal_v1_runtime_certified_fix2_7opp_50seed`
- Formal metric summary:
  `alakazam_staged_20260729/metrics/formal_v1_runtime_certified_fix2_7opp_50seed_summary`
- Comparison name:
  `comparison_b_v0_vs_v1_runtime_certified_fix2`

No existing attempt directory may be reused or overwritten.

## Hard gates

Before the full schedule:

- all source and candidate tests pass;
- deck bytes and bound hashes match this specification;
- the nine candidate-function ASTs and both precedence chains are unchanged
  from the approved v1 source;
- fresh smoke has all blocks complete and all callbacks structurally valid;
- fresh smoke has zero invalid action, uncaught exception, timeout, max-step,
  first-legal fallback, `V1_TRANSACTION_ABORT`, and
  `V1_IRREVERSIBLE_ABORT_FAULT`;
- every removed-card classification is `KNOWN`;
- every fired candidate transaction completes without calling the inherited
  delegate while it owns a child prompt.

For the full result:

- exactly 700 unique `(opponent, seat, seed)` rows;
- exact baseline/candidate schedule equality;
- child exit code, action error, max-step, timeout, unstarted, invalid winner,
  and baseline duplicate mismatch counts are all zero;
- checked rows and formal metric rows agree exactly on schedule, result, and
  steps;
- transaction starts equal transaction completions, with zero abort/fault;
- generic and first-legal fallback rates are zero for candidate-owned routes.

Failure of a hard gate makes Comparison B a failure regardless of win rate and
blocks v2 implementation.

## Required analysis

Report overall, opponent, seat, seed-base, paired gain/loss, and exact
discordant-pair p-value. Also report first attack, attack gaps, post-KO
continuity, consecutive attacks, hand size at attack, Powerful Hand counters,
second-line creation, added-card exposure/play, removed-card hits, fallback,
safety, and decision-time metrics. Do not interpret aggregate post-KO changes
as paired causal effects when event denominators differ by policy.
