# COUNTERFACTUAL_ROOT_ACTION_SEARCH_V2_STRATIFIED_MULTIWORLD

This directory is an external diagnostic experiment.  It does **not** modify,
wrap, promote, or package the accepted Historical-Silver Archaludon parent.
It also does not submit to Kaggle.

## Frozen GPT PRO direction

- Keep the accepted parent byte-identical and treat all counterfactual gains as
  hypotheses only; do not turn them into a rule yet.
- Classify each root on two independent axes: one primary action
  transformation (`T1_ATTACK_TO_DEVELOP` through `T13_OTHER`) and any
  callback-visible context tags (`C_*`). `energy_target` is an eligibility
  diagnostic, not an exclusive stratum.
- Use at least 32 discovery roots and 16 untouched fresh holdout roots when
  available, plus a reserve. Shortfalls remain explicit and are never filled
  with invented or hidden-information states. Calibration roots are excluded.
- Run parent/alternative branches in multiple worlds that are consistent with
  the public observation.  World cards are engine placeholders only and never
  reach the policy callback.
- The primary outcome is terminal win/loss/draw.  Prize, board, and next-attack
  fields are diagnostics and cannot be optimized as a proxy objective.
- Discovery and holdout are separate.  No condition or rule may be tuned on
  holdout rows.
- ROOT_VALID is deliberately small: normalized public observation, semantic
  option set, parent action, and forced-action legality. Skip an individual
  bad root/branch. Stop globally only for ROOT_VALID below 70%, invalid forced
  actions above 0.5%, action errors above 1%, world-count validation failures
  above 5%, hidden-information leakage, or parent mutation. Energy sparsity is
  reported and does not stop the experiment.
- A later adoption experiment would require holdout confirmation and fixed760
  parent-safety gates.  This experiment itself never adopts a rule.

## Explicit non-goals

No RL, MCTS, learned rankers, behavior cloning, Gold-action imitation,
replay-derived opponent-policy proxy, hidden hand reconstruction, or new agent
logic is used here.  The experiment is a measurement tool only.
