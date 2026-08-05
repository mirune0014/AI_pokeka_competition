# Archaludon rollout Q v1

This directory is a Codex-local Luna Max workspace. Its nested
`.codex/config.toml` overrides the repository defaults only when the Codex
working directory is this directory or a descendant:

- primary model: `gpt-5.6-luna`
- reasoning effort: `max`
- spawned-agent default: `gpt-5.6-luna` + `max`
- named subagent: `archaludon_rollout_q_v1_luna_max`

Start Codex with this directory as the working directory, for example:

```powershell
Set-Location research/experiments/archaludon_rollout_q_v1
codex
```

Starting Codex at the repository root does not activate this nested layer,
because the closest active `.codex/config.toml` is then the repository-level
one. Likewise, an explicit command-line or spawn-time model override takes
precedence over defaults; do not use one here if Luna Max is required.

## Experiment surface

The implementation in this directory is the isolated Rollout-Q v1 expert
iteration. Formal Archaludon directories are inputs only. Generated traces,
branch results, datasets, checkpoints, and reports go under
`_local_generated/archaludon_rollout_q_v1/`.

Use the repository virtual environment on Windows:

```powershell
.\.venv-ptcg\Scripts\python.exe -m research.experiments.archaludon_rollout_q_v1.rollout_q.cli collect-source --round 0
.\.venv-ptcg\Scripts\python.exe -m research.experiments.archaludon_rollout_q_v1.rollout_q.cli build-tasks --round 0
.\.venv-ptcg\Scripts\python.exe -m research.experiments.archaludon_rollout_q_v1.rollout_q.cli run-branches --round 0 --shard-count 16 --shard-index 0
.\.venv-ptcg\Scripts\python.exe -m research.experiments.archaludon_rollout_q_v1.rollout_q.cli merge-results --round 0 --shard-count 16
.\.venv-ptcg\Scripts\python.exe -m research.experiments.archaludon_rollout_q_v1.rollout_q.cli build-dataset --through-round 0
.\.venv-ptcg\Scripts\python.exe -m research.experiments.archaludon_rollout_q_v1.rollout_q.cli train --through-round 0
.\.venv-ptcg\Scripts\python.exe -m research.experiments.archaludon_rollout_q_v1.rollout_q.cli evaluate --round 0
.\.venv-ptcg\Scripts\python.exe -m research.experiments.archaludon_rollout_q_v1.rollout_q.cli report --round 0
```

Workers are independent file writers. Run the same fixed shard count on each
machine and give each worker a distinct shard index. Existing task IDs in a
shard are skipped on restart. The `run-round` command assumes all branch
shards have already completed.

The eight prescribed test files are under `tests/`; no formal submission
artifact imports the learned policy.
