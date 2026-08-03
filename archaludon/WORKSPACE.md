# Archaludon Workspace

This directory is the permanent workspace for the deterministic Archaludon
agent. The improvement loop began on 2026-07-15, but the directory name is
stable and no longer tied to that start date.

## Canonical entry points

- Formal Archaludon result:
  `final/archaludon_historical_silver_single_resolver_salvage_v1/`
- Historical-Silver strength anchor:
  `baseline/historical_silver_archaludon_54495224/`
- Final integration requirements and checkpoint:
  `strategy/archaludon_historical_silver_single_resolver_salvage_v1/`
- Independent final numerical audit:
  `numerical_audits/archaludon_historical_silver_single_resolver_salvage_v1/`

The formal result accepts Rules 1, 4, and 5. Other numbered rule directories
are trials, rejections, or dormant implementations unless their own judgment
explicitly says otherwise. Directory recency is not an adoption signal.

## Isolation policy

- Existing repository files are read-only inputs and strength anchors.
- All new source variants live under `candidates/`.
- All fetched public evidence and replay snapshots live under `evidence/`.
- All local evaluation outputs live under `evaluations/`.
- All packaged Kaggle submissions live under `packages/`.
- Decisions, immutable comparison specifications, and promotion records live
  under `decisions/`.
- No learned action ranker, behavior cloning, replay-derived opponent proxy, or
  residual RL is permitted. The active path is deterministic rule-based play.

## Navigation order

1. Start from `final/` and the checkpoint above.
2. Read the matching `strategy/` contract.
3. Read the matching `numerical_audits/` and `root_verification/` evidence.
4. Open raw `evaluations/` or `live/` data only when reproducing a specific
   claim.

Alakazam has its own workspace at `../alakazam/`.
RL and imitation-learning experiments are archived at `../research/experiments/` and
are not part of this workspace's active path.
