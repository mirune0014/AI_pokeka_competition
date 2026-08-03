# Alakazam Run Away Draw Actual Capacity v3 — Strategy Selection

Date: 2026-07-17  
Role: `ptcg_sol_ultra_worker` strategy judge  
Decision: **SELECT exactly one v3 hypothesis**

## Hypothesis

The v2 overlay is sound only when the public deck has capacity to realize its fixed three-card draw premise. Require `deck_count >= 3` before applying the `h+3` hit-bound and cost certificate. This is a public, deterministic, stateless mechanics guard; it contains no opponent, seat, seed, or replay exception.

## Exact implementation boundary

Clone frozen v2 source SHA-256 `8E61C70D7BC0136E724C6A2283833DF78CDA39508835CBB9A5BEBDE46CA8CE3B` into a new isolated v3 candidate. In the score-1550 Run Away Draw overlay predicate in `main.py` (v2 lines 871–880), add only:

```python
and deck_count >= 3
```

Place it beside `and safe_draws >= 3` and before `_hit_bound_reduced(op_active_hp, hand_size, 3)` is used. `deck_count` must be the existing public `my_state.deckCount` value. Do not alter `_hit_bound_reduced`, `_run_away_draw_cost_certified`, `safe_draws`, the original score-30000 exact-KO rule, option ordering, helpers, deck, runtime, or any other behavior.

Do not replace the guard with `min(3, deck_count)` or create one- or two-draw certificates: those would expand the hypothesis rather than repair it.

## Pre-proof

The frozen broad traces contain 46 first divergences: 45 had `deckCount >= 5` and actually drew exactly three cards; the sole short-draw branch had `deckCount == 1`. The guard is therefore expected to preserve the 45 certified branches and suppress only `reference/known/marnie_sota/p1/2026071583`. This is a pre-proof and not promotion evidence; the expected `+10` combined result after removing that one gain must be executed and recomputed.

## Required freeze and verification

Before execution, freeze source, runtime, deck, engine, schedules, output schema, and hashes.

1. Focused fixtures must prove that deck counts 0, 1, and 2 suppress only the score-1550 overlay even when `safe_draws == 999`; deck count 3 permits it when every other predicate holds. Compile/import, legal 60-card deck, determinism, action validity, and both-seat packaged smoke remain mandatory.
2. Rerun the exact frozen 33-key Phase-0 parent/v3 schedule. Require all prior six eligible gains and all 15 control wins to remain sound, with no new first divergence outside the intended guard. Add the sole deck-one anomaly as an explicit capacity-suppression fixture; its first v3 action must match the parent Powerful Hand action.
3. Rerun the v3 candidate on every key of the full frozen broad schedules. Frozen parent rows may be reused only after re-verifying their hashes and exact schedule equality; v2 candidate rows may not serve as v3 result evidence. Require v3 to match v2 on the 1,439 expected unaffected paired keys and to match the parent at the anomaly, or investigate and reject any mismatch.
4. Recompute all frozen broad Gates 1–8 without changing thresholds. Review every gain and regression trace again. Every score-1550 first divergence must have public `deckCount >= 3` and an observed first Run Away Draw count of exactly three.
5. Obtain a fresh Sol-Ultra numerical audit and final Sol-Ultra adoption judgment. Only a passing final judgment may authorize packaging or Kaggle submission.

No source change, battle execution, package, or Kaggle write is authorized by this selection document itself.
