# Archaludon Rollout-Q Expert Iteration v1

This directory is explicitly authorized as an isolated research experiment.
It may train and evaluate a Rollout-Q model, but learned behavior must not be
copied into or imported by the formal Archaludon deliverables.

Formal paths that are immutable for this experiment:

- `archaludon/final/`
- `archaludon/baseline/`
- `archaludon/strategy/`
- `archaludon/packages/`
- `archive/submissions/`

Implementation and generated outputs are confined to this directory and
`_local_generated/archaludon_rollout_q_v1/`. No PPO, PCGrad, BC, DAgger,
search APIs, adversarial file tests, or receipt hash chains are implemented
here. The only runtime override is the fail-closed Rollout-Q policy defined by
the experiment specification.
