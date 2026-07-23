# Autonomous Gold Workspace

This directory is the isolated workspace for the autonomous rule-based agent
improvement loop started on 2026-07-15.

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

