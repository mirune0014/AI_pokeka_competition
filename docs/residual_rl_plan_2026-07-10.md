# Residual RL plan for the PTCG agent

## Objective

Improve the strongest submitted Archaludon rule agent without removing its
legality checks, matchup guards, or deterministic fallback behavior. The first
RL stage learns only a bounded residual score over legal options. Zero learned
weights must reproduce the original rule policy.

## Baseline

- Canonical archive:
  `submission_archaludon_gtmidguard_lucariobev_crustledeckguard.tar.gz`
- SHA-256:
  `69BC01010FA2963781E6CD18CBA4773E0372127763DBB7AAF5E2081E1A156809`
- Kaggle history: this family reached approximately 1045 before later rating
  fluctuation. It is preferred over the public 1072 sample because it contains
  the accumulated matchup and safety guards used by our submitted trajectory.
- Local training-set baseline, seed base 310000: 22/28 wins, 0 errors.
- Local holdout baseline, seed base 410000: 23/28 wins, 0 errors.

The local mimics are useful regression tests, not unbiased estimates of Kaggle
ladder strength. In particular, the high aggregate rate leaves little room for
learning and makes per-bucket regressions more important than the mean alone.

## Policy design

For each legal option, compute:

`final_score = rule_score + clip(rl_scale * dot(weights, features), -cap, cap)`

The rule score remains responsible for hard exclusions and deck-specific
strategy. The residual policy may only reorder a conservative top-k candidate
set. Multi-select count constraints are still handled by the baseline chooser.
Any feature, model, or inference error returns the baseline action.

The initial implementation uses sparse hashed/categorical features and a
dependency-free linear softmax policy. This is intentional: local simulation is
currently limited by the native game engine rather than matrix throughput, and
the final Kaggle agent should not depend on PyTorch at inference time.

## Training protocol

- Algorithm: episodic REINFORCE with an exponential moving reward baseline.
- Reward: terminal win/loss, with only a small bounded prize differential term.
- Seats: alternate player 0 and player 1.
- Sampling: fixed weighted meta pool; keep deterministic validation seeds out of
  training.
- Checkpoints: evaluate each epoch and retain a champion only when the aggregate
  score improves without a material protected-bucket regression.
- Reproducibility: record seed, opponent, seat, result, policy decisions, and
  weight checksum for every episode.

## Opponent split

Training buckets:

- `alakazam_psychic_public_simple`
- `submission_marnie_grimmsnarl`
- `dragapult_live_simple`
- `mega_lucario_public_simple`
- `starmie_public_simple`
- `great_tusk_crustle_public`
- `archaludon_public`

Holdout buckets:

- `alakazam_noor_live_84982062_simple`
- `marnie_kazuki_live_85083586_simple`
- `dragapult_rojiomote_live_85060632_simple`
- `mega_lucario_hamu_live_85060465_simple`
- `starmie_windecks_84743054_simple`
- `great_tusk_evan2_live_85029139_simple`
- `archaludon_victorvv_live_85044984_simple`

## Acceptance gates

1. Zero-weight policy matches baseline actions on recorded traces.
2. No engine, action, import, or packaging errors.
3. Training-set gain is not accompanied by more than one net holdout loss.
4. Protected strengths into Starmie, Great Tusk, and Mega Lucario do not regress
   materially.
5. Candidate archive contains exactly one 60-card deck and a deterministic,
   dependency-free inference path.
6. A Kaggle submission is made only after local fixed-seed and unseen-seed tests
   pass; ladder evidence is then collected for at least 20-40 public games.

## Compute plan

Stage 1 runs locally on CPU even though an RTX 4070 is available: sparse linear
updates are cheap and native simulator calls dominate runtime. Stage 2 can use
the local GPU or a Kaggle GPU notebook for batched policy/value networks,
card/deck embeddings, or search-guided training after the residual pipeline has
produced reliable trajectories. GPU use should be justified by measured model
compute, not enabled by default.

The downloaded competition engine and data remain Competition Use Only. Do not
publish or redistribute them in a Kaggle Notebook or dataset.

## Local experiment results

The infrastructure passed its safety gates, but no learned checkpoint passed the
strength gate in this first cycle.

- Empty weights matched the canonical rule agent for all 747 checked decisions
  across Alakazam, Marnie, and Archaludon games.
- A matchup-pruned candidate also matched 908/908 decisions in intentionally
  unchanged Marnie, Alakazam, Great Tusk, and Cynthia buckets.
- The first matchup-scoped checkpoint (`m841e1`) tied the baseline at 96/112 on
  one train confirmation and scored 96/112 versus 89/112 on its initial
  holdout. On the broader 18-deck live suite it fell to 119/144 versus the
  baseline's 124/144, so it was rejected.
- Pruning that checkpoint to Archaludon, Lucario, and Starmie scored 109/144
  versus 108/144, but regressed Toru Archaludon from 11/16 to 6/16. It was
  rejected.
- Pruning to Lucario and Starmie first scored 184/192 versus 175/192. A larger
  independent confirmation reversed the result: 343/384 versus the baseline's
  357/384. It was rejected.
- A second, more diverse curriculum added public-state interaction features and
  trained on 12 live/public variants. Its best full checkpoints remained below
  baseline: at best 68/96 versus 70/96 on training variants and 67/88 versus
  72/88 on held-out variants.

Therefore the accepted champion remains the canonical rule archive. Learned
archives under `analysis_outputs/rl_work/candidates` are experiment artifacts,
not submission recommendations. The next RL cycle should use a validation-aware
optimizer and substantially more paired or process-controlled simulation before
any Kaggle submission.
