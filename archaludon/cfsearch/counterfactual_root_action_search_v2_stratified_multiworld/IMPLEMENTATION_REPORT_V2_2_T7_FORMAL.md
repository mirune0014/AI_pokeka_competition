# Counterfactual root-action search V2.2: formal T7 report

Date: 2026-08-16 (JST)

## Scope and invariants

This is a diagnostic-only continuation of the accepted Historical-Silver
Archaludon parent. The parent agent and deck are not modified, no candidate
agent is produced, and no Kaggle submission is made. Hidden engine state is
kept inside the seeded engine; root generation and alternative predicates use
only the retained public observation and semantic action set.

Accepted parent:

- agent SHA-256: `506E1A75062EE22BEE550C303C74D44A141EF6F8A6AD0DB6AEADBD9211085CB6`
- deck SHA-256: `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`

## Trace-preserving fixed760

The normalized public-hash run completed all 760 scheduled games (16 cells,
both seats, eight opponent families) with 84,529 callback rows, 760 retained
trace files, no action errors, no max-step hits, and no orchestrator failures.
The only observation normalization removes the volatile `search_begin_input`
field; all other public fields remain hashed and recorded.

The exact schedule output is under:

`_local_generated/analysis_outputs/archaludon_counterfactual_root_action_search_v2_stratified_multiworld/v2_2_fixed760_trace_normalized_public_hash/`

The parent-only run is a parity/trace artifact, not a candidate win-rate
comparison.

## Formal realized T7 discovery

From the retained traces, 6,073 public energy-eligible roots were found. The
deterministic discovery selection contains 64 roots, 36 distinct games, all
eight opponent families, and both policy seats. For every selected root the
parent branch and each alternative branch were run in the same seeded world
and resumed with the parent policy after the single root replacement.

Root/branch output:

`_local_generated/analysis_outputs/archaludon_counterfactual_root_action_search_v2_stratified_multiworld/t7_formal_discovery64_v22_normalized/`

Independent raw-row recomputation agrees with the runner report:

| check | value |
|---|---:|
| parent rows | 64 |
| alternative rows | 108 |
| valid comparable alternatives | 108 |
| root/public-prefix mismatches | 0 |
| action errors | 0 |
| max-step hits | 0 |
| gains | 8 |
| regressions | 9 |
| net | -1 |

The discovery gate therefore does not support a T7 candidate (`net < 3` and
regressions exceed the provisional limit). The result is recorded for
classification only; no T7 rule is promoted or implemented.

The formal aggregate is split by T7 class, target role, opponent family,
seat, and turn/prize bucket in `t7_formal_discovery64_v22_normalized/aggregate/`.
The largest negative concentration is early Active-to-Bench (T7A: 3 gains,
6 regressions); Bench-to-Active is net positive (3 gains, 2 regressions).
Historical-Silver itself is net -2 in this small discovery slice (0 gains,
2 regressions), so this is not evidence for changing the accepted parent.

## Earlier diagnostic findings

The synthetic T13 bank remains diagnostic-only: 2 distinct roots and 2 games,
with no opponent-family coverage and mixed outcomes. It is not a formal rule
hypothesis. T1 and T6 remain on hold pending a separate realized-world
predicate; no negative synthetic result is treated as a permanent rejection.

## Reproducibility hashes

The raw formal report is `t7_formal_discovery64_v22_normalized/report.json`
(SHA-256 `72F537FBFB5D1164F35150F4A93F4E4FC897097AF542B738C7B4426C762D72CB`).
The raw branch ledger is `branch_results.jsonl` (SHA-256
`AA7FE5E4086157C52B578A199DBD09A0195A34FE73C3CBE4BA456804BF129376`).
The selected-root ledger is `t7_formal_roots_v22_normalized/discovery64_roots.jsonl`
(SHA-256 `3D0A0DC1AB5EC9C8C2F7E374494E1E42DFED3CFBFA90FE0305AE49B45881E90E`).
The classified aggregate is `aggregate/REPORT.json` (SHA-256
`0C48BFC8465C6B2C822BBA9CD41B0DFDA1E0D8F0EB6AD3D7E0A9346C7C39BD85`).

