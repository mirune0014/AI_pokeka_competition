# Immutable Rule 1 replay-shadow specification

## Policies

- Left: `analysis_outputs/reference_agents/historical_silver_archaludon_54495224`
  - `main.py` SHA-256: `F4B578453C9D953BE94885144DD50E05DBA4510DF3340BE27ADE07495896046E`
  - `deck.csv` SHA-256: `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`
- Right: `autonomous_gold_20260715/candidates/archaludon_historical_silver_single_resolver_salvage_v1`
  - `main.py` SHA-256: `153D8461FB66927DB9731CBE614B71FF5398B8EAE8980AE0BB4D46ADD0E8792A`
  - exact parent SHA-256: `F4B578453C9D953BE94885144DD50E05DBA4510DF3340BE27ADE07495896046E`
  - `deck.csv` SHA-256: `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`

## Corpus

- All 46 paths matching
  `autonomous_gold_20260715/live/55155015/analysis_20260802/refresh/episode_*_replay.json`.
- The same deterministic 32-file historical sample used by the frozen
  Silver/Task9 comparison: sort all 207 paths below by
  `sha256(path.name)` and take the first 32:
  `autonomous_gold_20260715/live/55070349/refresh_20260729_1241/shadow_corpus_196_prior_plus_11_new/episode_*_replay.json`.
- Ordered corpus snapshot SHA-256:
  `B88C25BC8F26F959F85D00D27FD7B148D22034D71B2588DF73AAF8C8E0B15004`.
- One known malformed current file may fail JSON decoding. It remains in the
  manifest and is not silently replaced.

## Checked executor

- `tools/compare_replay_agent_actions.py`
- SHA-256: `A449CDB2783F2B8CDF34373BFB9A6097BE724143150EE174C570EBB3C657EE46`
- Python: `py -3.11 -B`
- Engine: `analysis_outputs/cynthia_v9_vs_v11_poffin_role_selection_20260713/seeded_engine`
- Write one raw JSON report per replay to
  `implementation/archaludon_historical_silver_single_resolver_salvage_v1/shadow_raw`.
- Do not aggregate or interpret in the execution operator.

## Root acceptance checks

- Exactly 77 readable reports and one explicit malformed-input record.
- Zero invalid option positions from either agent.
- Every first difference is `SETUP_BENCH_POKEMON`, parent `[]`, candidate one
  own-hand Duraludon with minimum visible serial, after a Cinderace Active
  selection in the same replay/seat.
- No Active-Duraludon setup may produce a Rule 1 difference.
- No report may contain more than one candidate Duraludon in the setup action.
- Replays do not prove retry permutation; focused fixtures remain authoritative
  for that invariant.
