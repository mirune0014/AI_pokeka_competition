# AI Pokeka Competition

Working repository for the Kaggle `pokemon-tcg-ai-battle` simulation competition.

## Current Local Champion

- Archive: `submission_archaludon_gtmidguard_lucariobev_crustledeckguard.tar.gz`
- Strategy: Archaludon ex / Cinderace metal-tempo rule-based agent
- Selection basis: this submitted family reached roughly 1045 on the public
  ladder and remains the regression baseline for local meta suites.

## Reinforcement Learning

`rl_ptcg/` contains a dependency-free sparse REINFORCE residual policy,
training CLI, safety filter, zero-weight equivalence verifier, and immutable
submission builder. The original rule chooser remains the legality and error
fallback.

The first local RL cycle did not produce a checkpoint that consistently beat
the rule champion on expanded holdouts. Experimental archives are retained
under `analysis_outputs/rl_work/candidates`, but none is currently recommended
for Kaggle submission. See `docs/residual_rl_plan_2026-07-10.md` for results and
acceptance gates.

See `docs/ptcg_competition_notes.md` for Discussion/Code notes and strategy rationale.
See `docs/analysis_environment.md` for local behavior checks, matchup tests, and public episode analysis.
