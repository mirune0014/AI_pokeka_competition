# GPT Pro strategy review - 2026-07-11

## Adopted diagnosis

The primary bottleneck is the mismatch between the local opponent-policy
distribution and the Kaggle upper-ladder distribution. The next bottleneck is
the support and capacity limit of the current sparse residual: top-three rule
actions, a linear score, and residual cap `0.12` cannot represent a strategic
switch when the useful action is outside that set.

The existing linear residual remains the champion prior, fallback, and safety
baseline. Further checkpoint, CEM, turn-bucket, and feature-weight searches are
closed except for runtime fixes or calibration against a new model.

## Immediate experiment

Before implementing a neural ranker, run a 512-state public-belief teacher
reproducibility pilot.

State mix:

- 50% Alakazam, Archaludon mirror, and Mega Lucario;
- 25% neutral matchups;
- 25% current strong-matchup anti-regression states;
- both seats and policy-family holdouts;
- meaningful decisions plus a 20% uniform sample.

For each state, compare complete candidate actions against the baseline action
on the same public-belief particles. Use two independent teacher batches,
terminal utility, multiple opponent policies, and observation-only continuation
policies. Preserve paired results by particle and opponent-policy group rather
than counting action branches as independent samples.

Initial success gates:

- high-margin top-action agreement at least 70% across independent batches;
- advantage-sign agreement at least 80%;
- search-gated policy at least +2 win-rate points overall, or +4 points over
  the weak-matchup aggregate;
- strong-matchup regression at most 1 to 1.5 points;
- at least 5% of positive-LCB overrides outside the rule top three.

Do not train a neural ranker if 64 particles, two independent batches,
opponent-policy population, terminal-only utility, and an unknown-deck component
still produce less than 60% teacher ranking agreement, or if the 90% upper
confidence bound on oracle gain is below one point.

## Submission gate

Small local action fixes are not Kaggle candidates. A future submission should
normally require:

- at least +1.5 win-rate points on blind external seeds;
- positive one-sided 90% lower confidence bound;
- leave-one-policy-family-out non-regression;
- no action errors or max-step regression;
- no strong-matchup loss larger than 1.5 points;
- reproduction across more than one seed window.

The queued `2-2` mirror Boss guard improved `559/1200` to `563/1200`, but four
discordant improvements are not strong enough for a Kaggle slot under this
gate. It remains an internal ablation only.

## Evidence from the first opponent-policy ensemble

Loss `85370349` exposed a turn-two Explorer choice. A public-belief rollout
against one local Lucario policy initially made an Ultra Ball line look better.
An independent 128-particle check rejected `Metal Energy + Ultra Ball`.

A second proposal, `Archaludon ex + Ultra Ball`, appeared non-negative across
four Lucario rollout policies and had aggregate paired delta `+0.0234` over 256
particles, although its lower bound remained slightly negative. The exact
replay action was implemented and changed no non-Lucario controls.

The authoritative seeded game screen then rejected it:

- eight Lucario policies, both seats, 320 games;
- duplicate baseline controls exact;
- baseline `295/320`, candidate `293/320`;
- Akira `-1`, public `-1`, other buckets neutral;
- all regressions occurred in seat one;
- zero action errors and zero max-step games.

This is direct evidence that a root rollout teacher can be optimistic even
after hidden-state sampling and a small opponent-policy ensemble. Continuation
policy, population weighting, and teacher stability must be validated before
distillation. A plausible replay action is not a substitute for end-to-end
paired games.

## Implemented foundations

- `label_replay_rollout.py --replay-step` enables focused high-particle checks.
- `choose_with_rollout` can evaluate a Cartesian product of hidden-deck
  hypotheses and opponent-policy modules, using the worst scenario as a safety
  gate.
- `label_replay_rollout.py --opponent-agent` is repeatable for policy ensembles.
- focused rollout and replay-label tests pass.

The next implementation should add state sampling/canonicalization, complete
candidate-action coverage, independent teacher-batch reporting, policy-group
and hidden-particle variance decomposition, and oracle-headroom evaluation.

## Public-belief teacher pilot results

The pilot infrastructure now supports deterministic public-state sampling,
complete legal-action enumeration, two independent batches, multiple opponent
policies, multiple deck hypotheses, multiple continuation policies, paired
particle outcomes, episode-cluster bootstrap, and explicit failure reporting.
All 101 RL unit tests pass.

The exact-replay-deck pilot was optimistic. On 32 frozen states with three
nearest opponent policies and four particles per policy, top-action agreement
was `62.5%`, advantage-sign agreement was `82.69%`, and mean oracle advantage
was `15.89` points. This is an upper bound because the teacher knows the exact
opponent deck from the completed replay.

The leakage-free pilot selects deck and policy hypotheses from publicly
visible opponent cards only. If no catalog deck contains all visible cards,
it repairs an unobserved part of a nearby deck to create a compatible unknown
variant. It evaluates the Cartesian product of three deck hypotheses, three
opponent policies, and two own continuation policies. The two continuation
policies are the current residual agent and the prior rule-inline champion.

At four particles per scenario:

- 8-state smoke: top-action agreement `87.5%`, sign agreement `84.62%`;
- 32-state pilot: top-action agreement `56.25%`, sign agreement `78.54%`;
- high-margin states: `3/3` top-action agreement;
- mean oracle advantage: `13.02` points;
- episode-bootstrap one-sided 90% lower bound: `6.05` points;
- positive-LCB complete actions outside the rule top-three support in both
  batches: `2/32`, or `6.25%`.

The 32-state result narrowly misses the 80% sign-agreement gate and has too few
high-margin states to train a ranker yet. It nevertheless passes the 5%
outside-top-three headroom test. The next step is not another sparse linear
search. It is to improve teacher calibration and expand the frozen pilot,
retaining only positive-LCB labels that reproduce across batches. A neural
ranker remains gated on a larger stable sample.

A support split localizes the instability:

- 15 states fully supported by real catalog decks: sign agreement `85.71%`,
  overall top-action agreement `66.67%`, high-margin agreement `2/2`;
- 17 states requiring at least one synthetic unknown variant: sign agreement
  `71.96%`, overall top-action agreement `47.06%`, high-margin agreement `1/1`.

The immediate safe architecture is therefore a selective teacher/ranker. It
may override the rule agent only when the public cards admit real catalog deck
hypotheses and the cross-batch action advantage has a positive lower bound.
Unsupported states fall back to the frozen rule/residual champion. Synthetic
unknown variants remain useful for diagnosing distribution shift, but they
must not produce training targets or live overrides until their prior weights
are calibrated.

Operational bugs found and fixed during the pilot were: submission agents
without `choose_options`, dataclass-versus-dict observation conversion,
partial-state success reporting, duplicate deck hypotheses causing unbalanced
scenario counts, and non-serializable continuation paths in manifests. These
are relevant to any reusable local Search API teacher.

## Supported 64-state stop decision

Filtering the frozen 512-state pool left 244 states whose public cards were
fully supported by real catalog decks. A stratified 64-state set retained the
50/25/25 weak/strong/neutral mix. At four particles per deck x opponent-policy
x continuation-policy scenario, all 128 state-batches completed:

- top-action agreement `54.69%`;
- advantage-sign agreement `79.74%`;
- high-margin top agreement `2/2`;
- positive-LCB actions outside rule top three `5/64` (`7.81%`);
- mean oracle advantage `9.00` points, lower-90 `6.48` points.

Only six states retained the same positive-LCB action across both batches,
four outside the top-three support. This is insufficient for a neural ranker,
and the sign gate remains strictly below 80%. The teacher route is paused, not
declared valueless. Stable labels are preserved in
`analysis_outputs/teacher_pilot_supported64_pop3_cont2_p4_v1/stable_positive_lcb_labels.jsonl`.
The next experiment is factorial deck headroom under the frozen policy.

## Exploratory Kaggle submission policy

The strict +1.5 blind-point gate now distinguishes champion promotion from
live probes. When two mature submissions remain below 1000, a locally valid,
informative probe may be submitted to obtain real opponent-distribution logs.
A result around or below 700 may be replaced early after basic diagnosis.
Execution errors still require diagnosis before another slot.

Under this policy, the narrow mirror candidate was submitted as Kaggle id
`54570077` at 20:36 JST. Its local evidence remains `559/1200 -> 563/1200`,
six mirror policy buckets nonnegative, and zero action/max-step errors. It is a
live information probe, not a promoted champion.

The submission passed validation and began public play `2-0`, reaching score
`752.9`. It is above the user's roughly-700 early replacement line, so the
probe remains active while the first public sample accumulates.

The mirror probe later reached five public games at `3-2`, but score fell to
`668.0`; no mirror matchup had occurred. A factorial deck candidate had by then
passed stronger local evidence, so the probe was replaced.

The selected deck swap adds Relicanth `57` and removes one of three Night
Stretchers `1097`. Across two independent seeded windows, 14 policy buckets,
both seats, and 672 candidate games, it improved by `+15` wins (`+2.23` points)
with one-sided lower-90 `+0.05` points. Weak and strong aggregates and both
seats were positive. It was submitted as id `54570845` at 21:06 JST for live
distribution validation.

The compensation cut is a first-order interaction, not bookkeeping. With the
same Relicanth addition and the same 14-policy, two-seed, 672-game design:

- cut one Night Stretcher: `+15` wins, lower-90 positive;
- cut one Lillie's Determination: `-20` wins, weak group `-22`.

Changing only the removed card moved the paired result by 35 wins. Deck search
must therefore evaluate complete swaps as factorial arms; estimating an
"add-card effect" independently of its cut is invalid in this environment.

The operational replacement rule is intentionally more active than the
champion-promotion rule. Five daily slots may be used for locally valid live
probes when both the current and preceding mature submissions remain below
1000. A submission at or below roughly 700 can be replaced after checking for
execution errors and identifying the first loss buckets. A new submission that
is still climbing or has only a few games is not replaced merely because it is
below 1000; it normally receives about 20 public games before judgment.

At the first refresh after validation, `54570845` reached four public wins in
four games and score `939.48`, with wins over Mega Abomasnow/Kyogre,
Dragapult, Starmie/Froslass, and Mega Lucario. It remains active while the
sample matures.

At six public games the record became `4-2` and score `816.79`. The losses
were Ogerpon toolbox and Alakazam. This is above the early replacement line
and still too small to judge, so the submission remains active.

The next factorial arm initially replicated against the original baseline.
Increasing Night Stretcher from three to four while reducing Jumbo Ice Cream
from three to two improved `+21/672` over two windows. Direct comparison to
the currently submitted Relicanth swap was much weaker: `+6/672`, split
`-10/+16` by seed. A third independent window was `-1/336`; the three-window
direct total is only `+5/1008` (`+0.50` points), with seat-one `-4` and
remaining Alakazam, mirror, Great Tusk, and Marnie regressions. The packaged
archive is therefore rejected and must not be submitted.

The Ogerpon replay diagnosis was also corrected. The apparent missed attack
on turn ten was not an action-ranking error. Cubchoo used Snotted Up on turn
nine, whose effect prevents the defending Pokemon from attacking on its next
turn; the engine correctly offered no attack option. No deterministic policy
change is justified from that single lockout episode.

A 16-arm second-stage factorial around the live Relicanth incumbent did not
produce a replacement. The two selected g4 leaders (`+24/112`, `+21/112`)
fell to `+2/336` and `+4/336` on independent g12 windows, with seat-one and
all-Alakazam regressions. Screen and confirmation results are no longer pooled
for promotion because the screen maximum is selection-biased.

The live Relicanth probe reached the 20-game maturity checkpoint at `13-7`,
score `908.61`, after four consecutive wins. Seven classified losses were
Alakazam three, Archaludon two, Starmie one, and Ogerpon one. The repeated
action-level hypothesis is now an Alakazam-only, opponent-prizes-at-most-three
cap on acquiring a third Duraludon-family body when an attack route already
exists. Replay scoring changes only the digimagi loss, not the Ken or
SantaClaws losses, so broad seeded validation is required before submission.
