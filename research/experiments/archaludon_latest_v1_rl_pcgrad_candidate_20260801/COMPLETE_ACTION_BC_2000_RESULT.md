# Complete-action BC 2000 result

The 2026-08-02 complete-action behavior-cloning experiment is complete and
rejected. The deterministic `iteration004` agent remains the retained
baseline. The three BC checkpoints are preserved locally only as negative
experimental evidence and are not deployment, PPO-reference, or Kaggle
candidates.

## Verified fixed evaluation

| Arm | Wins / games | Win rate | Delta from iteration004 |
|---|---:|---:|---:|
| `complete_bc_seed2026080211` | 241 / 320 | 75.3125% | -6.2500 pp |
| `complete_bc_seed2026080212` | 229 / 320 | 71.5625% | -10.0000 pp |
| `complete_bc_seed2026080213` | 248 / 320 | 77.5000% | -4.0625 pp |
| `iteration004` | 261 / 320 | 81.5625% | baseline |

Root recomputation and an independent Sol-Ultra numerical audit agreed with
the checked aggregate with zero numerical discrepancies:

- 48 summaries, 48 receipts, and 48 deployment-audit streams;
- 960 unique `(arm, opponent, seat, seed)` schedule keys;
- zero action errors and zero max-step hits;
- 49,893 audited decisions, 138 safety fallbacks, and 3 model timeouts;
- all three validation top-1 rates were below the 98% gate;
- Historical-Silver was the recurring floor: pooled BC 33.33% versus the
  57.5% baseline, a -24.17 pp delta.

No baseline per-game rows or duplicate-control outputs were available, so a
promotion-grade paired interval and duplicate equality check were not
auditable. This missing evidence cannot rescue acceptance given the repeated
absolute and anchor regressions.

## Tracked evidence

- [`COMPLETE_ACTION_BC_2000_RESULT.json`](COMPLETE_ACTION_BC_2000_RESULT.json)
  is the checked fixed-evaluation aggregate. SHA-256:
  `69CE2A6414B645F29007040C4100AB1625B21D6CB5279418925BCdda7C53753B`.
- [`COMPLETE_ACTION_BC_2000_COMPARISON_SPEC.json`](COMPLETE_ACTION_BC_2000_COMPARISON_SPEC.json)
  records the immutable inputs, corrected raw manifest, schedule, and audit
  requirements. SHA-256:
  `29D2EBAB3F6A1BF706B04596D625EC8C78055F88476AD3F3EA829FDD582DC572`.

The 3.38 GiB rollout, dataset, raw evaluation, checkpoints, dependency ZIP,
and the failed-path backup remain ignored local artifacts under
`analysis_outputs/` or other ignored paths. They are intentionally not stored
in Git.
