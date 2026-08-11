# Archaludon Multi-Determinization Search-Q v1

This experiment reuses the immutable Round 0 source traces, branch points,
and candidate identities from `archaludon_rollout_q_v1`. It evaluates each
candidate under paired, deterministic hidden-state samples and fits an
expected terminal-reward model. Generated files belong under
`_local_generated/archaludon_multideterminization_q_v1` and are deliberately
not part of the formal Archaludon agent.

The implementation uses the seeded engine's public `cg.api` search wrapper.
It does not generate new source battles and does not modify the existing
Rollout-Q, groupwise, source-trace, task, or branch-result artifacts.
