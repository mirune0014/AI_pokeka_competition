# Immutable comparison: Historical-Silver vs cumulative Task 6 / Task 9

Frozen by Root on 2026-08-02 JST before execution. This comparison diagnoses
whether the cumulative human-fundamentals wrappers displaced the exact
historical-Silver Archaludon policy. It is not a promotion gate and it does not
authorize source edits or a Kaggle write.

## Policies

All three policies use the same exact `deck.csv` SHA-256
`08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`.

- Baseline / exact historical-Silver:
  `analysis_outputs/reference_agents/historical_silver_archaludon_54495224`
  - `main.py` SHA-256:
    `F4B578453C9D953BE94885144DD50E05DBA4510DF3340BE27ADE07495896046E`
  - bytes: `53,448`
- Cumulative Task 6:
  `autonomous_gold_20260715/candidates/archaludon_public_ultra_ball_declared_complete_route_transaction_v1`
  - `main.py` SHA-256:
    `99EE7BF5E6E6D61D863EF1D131232F90DCE36A3CFDF032AF6E534DECA79B2756`
  - bytes: `1,207,886`
- Cumulative Task 9:
  `autonomous_gold_20260715/candidates/archaludon_public_prize_race_threat_control_t9_v1`
  - `main.py` SHA-256:
    `0A9F0052095257B08CC5C5ABACAA0E912D7E02A9842145B48E2192A6F50ED4AE`
  - bytes: `1,374,663`

Task 8 remains the formal rollback for the isolated Task 9 overlay, but the
comparison baseline in this audit is exact historical-Silver.

## Engine and checked runners

- Python: `.venv-rl/Scripts/python.exe`
- Engine:
  `analysis_outputs/cynthia_v9_vs_v11_poffin_role_selection_20260713/seeded_engine`
- Engine `cg/cg.dll` SHA-256:
  `0C6153F9206366F2588E5C601AB086EA997A66E80E4FEB6D95635B2987C9929B`
- Checked paired runner: `tools/run_seeded_paired_suite.py`
  - SHA-256:
    `5EC25C98F2777FF61DE2DBD0A03A08519A7FEA4B2B4C510B5B8895BC2000E000`
- Checked battle runner: `tools/run_local_battle.py`
  - SHA-256:
    `03881BA796D1D8D3A095067684E8D0F5B069EF40AC0B543420896157F0431F2A`

The checked paired runner must execute baseline control A, baseline control B,
and the candidate for every schedule cell. It must not be modified and no
custom aggregate may replace its `paired_results.csv` and `report.json`.

## Fixed schedule for each candidate

Each candidate receives the exact same 760 `(panel, opponent, seat, seed)`
keys. Both policy seats are included.

### Historical-Silver mirror anchor

- opponent:
  `historical_silver=analysis_outputs/reference_agents/historical_silver_archaludon_54495224`
- games per seat: `100`
- seed base: `271828182`
- expected paired rows: `200`

### Adjacent complete-agent population

- games per seat and opponent: `40`
- seed base: `271958313`
- expected paired rows: `560`
- opponents:
  - `arch_peak=submission_archaludon_gtmidguard_lucariobev_crustledeckguard_archattach_ruleinline_20260710`
  - `arch_shumpei=meta_agents/archaludon_shumpei_current_v3`
  - `alakazam_capbloo_gold=meta_agents/alakazam_capbloo_gold_85357128_simple`
  - `marnie_kazuki_live=meta_agents/marnie_kazuki_live_85083586_simple`
  - `mega_lucario_public=meta_agents/mega_lucario_public_simple`
  - `kang_crustle=meta_agents/kangaskhan_crustle_mpgaming_v23_heal_role_missing160_guard`
  - `cynthia_v23=meta_agents/cynthia_garchomp_nasuo445_v23_allcall_before_evolve`

Maximum steps are `1000`. Engine-seeded execution is mandatory. Expected
total paired rows are `760` for Task 6 and separately `760` for Task 9.

## Destinations

- Task 6 raw:
  `autonomous_gold_20260715/comparisons/historical_silver_vs_task9_20260802/fixed760_task6_raw`
- Task 9 raw:
  `autonomous_gold_20260715/comparisons/historical_silver_vs_task9_20260802/fixed760_task9_raw`

Destinations are new and immutable after successful completion. Refuse to
overwrite a pre-existing nonempty destination.

## Replay first-difference corpus

Use the already frozen Task 9 shadow corpus definition:

- all 46 paths in
  `autonomous_gold_20260715/live/55155015/analysis_20260802/refresh`;
- the first 32 of 207 paths by SHA-256 of filename in
  `autonomous_gold_20260715/live/55070349/refresh_20260729_1241/shadow_corpus_196_prior_plus_11_new`.

The source snapshot SHA-256 is
`B88C25BC8F26F959F85D00D27FD7B148D22034D71B2588DF73AAF8C8E0B15004`.
The existing Task 9 shadow JSON is
`autonomous_gold_20260715/implementation/archaludon_public_prize_race_threat_control_t9_v1/replay_shadow_results.json`,
SHA-256
`81EA74F57CCC90AC75FFE89A8AA3B7E1780C1B16BC101EFED20C5C740A4A8C14`.
There are 77 readable replays and one malformed current file. Do not interpret
the factual suffix after a first counterfactual action difference.

The replay comparison must compute both boundaries separately:

1. historical-Silver -> Task 6;
2. Task 6 -> Task 9;
3. historical-Silver -> Task 9.

For every first difference record the episode, correct seat, step, public
state, recorded action, left/right action semantics, cumulative rule/owner that
won arbitration, and whether the displaced historical action had an immediate
attack, setup, recovery, draw, evolution, attachment, gust, or conservation
purpose. Replay outcomes are not action labels.

## Required validation and interpretation

- exactly `760` unique schedule keys per candidate;
- exact schedule equality between Task 6 and Task 9 comparisons;
- duplicate controls `760/760` per candidate;
- zero start faults, action errors, exceptions, and max-step hits;
- Root independently recomputes wins from result and policy seat;
- report overall, panel, opponent, and seat totals;
- list every paired gain and regression;
- rerun discordant keys with traces and inspect their first action divergence;
- distinguish `Task 6 already degraded` from `Task 7-9 repaired/degraded`;
- do not infer causal strength from score movement without an action difference.

Numerical interpretation belongs to a Sol-Ultra evaluator. Qualitative replay
diagnosis belongs to a Sol-Ultra replay analyst. Root verifies all
submission-critical counts and synthesizes the final diagnosis.
