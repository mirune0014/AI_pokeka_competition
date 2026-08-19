# Archaludon rollout Q v1 local Codex policy

This file applies only to this directory and its descendants. The repository
root `AGENTS.md` is still authoritative; these rules only specialize Codex
model routing for this experiment directory.

## Model routing

- When Codex is started with this directory as its working directory, use
  `gpt-5.6-luna` with `model_reasoning_effort = 'max'`.
- Spawn only the named role
  `archaludon_rollout_q_v1_luna_max` for work in this subtree.
- Do not select `ptcg_sol_ultra_worker`, `ptcg_candidate_worker`, `worker`,
  `explorer`, or any other model/role for this subtree.
- Do not pass an explicit model override that conflicts with the local
  `.codex/config.toml`.

The actual model pin is in `.codex/config.toml` and
`.codex/agents/luna_max.toml`; keep those files in sync if this scope is
renamed.
