# Sparse residual policy RL

This package learns small, visible-state corrections to an existing rule agent.
Zero weights use the rule ordering; training only samples from the top-N baseline
candidates and always returns the same number of option indices as the rule agent.

Run local training (do not use a Kaggle archive as `--baseline`; extract it first):

```powershell
python rl_ptcg/train_reinforce.py --engine-dir analysis_outputs/rl_policy_value/seeded_engine --baseline submission_archaludon_current_purecopy --opponent arch=submission_archaludon_current_purecopy --epochs 5 --games-per-epoch 8 --seed 7 --top-n 4 --learning-rate 0.01 --temperature 1.0 --output-dir rl_runs/example
```

For policy comparisons and terminal-reward optimization, build and use the
seeded local engine. The stock `BattleStart` ignores Python seeds and uses
`std::random_device`, so it is not suitable for paired A/B evaluation.

```powershell
powershell -ExecutionPolicy Bypass -File tools/build_seeded_engine.ps1
python -m rl_ptcg.train_cem --engine-dir analysis_outputs/rl_policy_value/seeded_engine ...
```

The seeded DLL is a local evaluation artifact. Submission archives continue to
use the competition-provided runtime binaries.

Build an immutable submission copy:

```powershell
python rl_ptcg/build_submission.py --baseline submission_archaludon.tar.gz --weights rl_runs/example/weights.json --top-n 3 --residual-cap 0.35 --output-dir rl_runs/submission --archive rl_runs/submission.tar.gz
```

Verify an empty-weight build against the exact baseline action-by-action:

```powershell
python rl_ptcg/verify_zero_equivalence.py --engine-dir submission_archaludon --baseline path/to/extracted_baseline --residual path/to/zero_weight_build --opponent meta_agents/alakazam_psychic_public_simple --games 4 --seed 7000
```

`residual_policy.py` extracts sparse features only from the current observation,
baseline callbacks, and selected options. It uses Plackett-Luce sampling without
replacement during training and deterministic argmax for inference. The trainer
uses terminal win/loss/draw reward plus prize-difference shaping, a moving baseline
per opponent, L2 decay, and bounded weights. It loads fresh Python agent modules
for every game, but the native engine remains process-global, so games are run
sequentially. This is a deliberately conservative policy layer, not a full state
value learner; it cannot recover from baseline actions absent from the top-N pool.
Unselected negative-score options are excluded from exploration, and the learned
logit correction is capped. Use `--weights PATH` with `--evaluate` to evaluate a
checkpoint, or without `--evaluate` to resume training from it.
The default `--feature-scope matchup` updates only matchup-conditioned features,
so a correction learned against one recognized archetype does not alter another.
Use `filter_weights.py` to keep only matchup namespaces that pass holdout gates;
this is also how corrections for the baseline's broad `generic` bucket are
removed before packaging.
