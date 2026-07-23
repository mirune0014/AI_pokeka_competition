# RL and Search API findings

This document records reproducible findings that may be useful for a future
Kaggle Discussion. It deliberately separates observed engine behavior from
hypotheses and benchmark results.

## Search is determinization, not belief-state search

`cg.api.search_begin` cannot search directly from the public observation. The
caller must supply concrete card IDs for every hidden own-deck, own-prize,
opponent-deck, opponent-prize, and opponent-hand slot. The native search then
treats that single assignment as the real state for the whole tree.

Consequences:

- Filling every hidden slot with one arbitrary legal card produces valid API
  calls but strategically biased branches.
- A strong search agent must maintain a deck hypothesis, subtract every visible
  or previously revealed card, and sample exact-size hidden zones without
  replacement.
- Root action values should be averaged across multiple independently sampled
  determinizations. One large tree on one guessed state is not equivalent.
- Samples that violate known copy counts, evolution lines, or revealed-card
  history should be rejected before calling the native API.

## Native state is process-global

The Python wrappers keep one module-global `agent_ptr` for search and one
class-global battle pointer for live games. `search_end()` acts on that shared
handle. There is no lock or per-root context.

Consequences:

- Concurrent games or search roots are unsafe inside one Python process.
- Parallel trajectory generation must use separate OS processes, not threads.
- Each search call needs `search_end()` in a `finally` block; otherwise later
  searches may reuse ambiguous native memory.
- A process worker should own one live battle at a time and recycle only between
  completed episodes.

## Evaluation variance can reverse small gains

The local engine does not expose a complete paired-randomness seed through the
current Python wrapper. In the residual-RL experiments, a candidate first scored
184/192 against selected Lucario and Starmie buckets while the rule baseline
scored 175/192. On a larger independent confirmation, the same candidate scored
343/384 while the baseline scored 357/384.

Consequences:

- Improvements of a few wins over a few hundred unpaired games are not enough.
- Challenger promotion should require thousands of games, multiple seed
  windows, per-archetype regression gates, and a confidence interval that
  excludes 50% in direct champion/challenger play where possible.
- Checkpoint or matchup selection must not use the final holdout that is later
  reported as evidence.

## Agent names are not independent deck holdouts

Deck identity was audited as the sorted multiset of all 60 card IDs, including
copy counts. The first 20-opponent training set contained only 16 unique deck
signatures, and a broader 74-opponent set contained 56. More importantly, 5 of
16 nominally held-out opponent decks had an identical 60-card signature under a
different author or episode label in the training pool.

Consequences:

- Splitting by author, replay label, or archetype can leak the complete decklist
  into both training and validation.
- All agents with the same canonical 60-card multiset must stay in the same
  split, even when their rule implementations differ.
- An honest policy/value benchmark needs two separate axes: unseen decklist and
  unseen opposing policy. Holding out only one does not establish the other.
- Deck-hypothesis models should report results on signatures that never occur in
  training, not only on newly downloaded leaderboard agents.

The machine-readable audit is saved as
`analysis_outputs/rl_policy_value/deck_signature_audit_v3.json`.

## A small exact-deck embedding overfits quickly

With only 20 labeled opponents, adding a learned bag embedding of the exact
opponent deck did not improve unseen-deck value prediction. The state-level
holdout MAE changed from approximately 0.265 without the exact-deck input to
0.315 after adding it, while training loss continued to fall. Reducing the
policy-loss weight did not fix the unseen Archaludon buckets.

This does not show that deck counting is unhelpful. It shows that the learned
deck representation needs substantially more unique decklists, whole-deck
validation splits, and stronger regularization before it can safely guide root
search. The next experiment uses 51 non-overlapping deck signatures for model
selection and preserves 16 external signatures for final evaluation.

## Battle and Search APIs mask a non-acting hand differently

When the observation perspective passes to the opponent, the normal local
battle API represents the non-acting player's hidden hand as one card-back
object with ID `7` per card. At the corresponding Search API leaf, that hand is
an empty list while `handCount` still preserves its size. Treating ID `7` as a
real card therefore lets a network distinguish the API source and creates a
train/search distribution shift.

The safe normalization is:

- retain `handCount` for both players;
- encode card identities only for the currently acting player's own hand;
- set every non-acting hand-identity slot to missing, regardless of whether the
  wrapper returns card backs or an empty list;
- include an explicit `acting_is_self` feature for fixed-perspective value
  evaluation.

After normalization, 91,246 opponent-turn states across the train and external
holdout collections contained zero non-acting hand IDs. This also prevents the
determinized Search API's hidden opponent hand from entering the public value
network.

## Terminal labels need episode-balanced weighting

The same terminal win/loss label is attached to every public state in an
episode. A plain per-record loss consequently gives a long game more optimizer
mass than a short game and makes record-level metrics look more certain than the
number of independent games supports.

Each trajectory now assigns weight `1 / public_state_count` to every state, so
the total value-loss mass of every completed game is exactly one. Policy loss is
still computed only on trainee decisions; opponent-turn observations are
value-only examples. Evaluation reports all-state, first-trainee-decision, and
episode-balanced views separately.

## One-step value improvements can be directionally wrong

The public-turn value model was used conservatively with 4 hidden-state
determinizations, a `0.15` mean-improvement margin, and a downside-risk gate.
Across three unseen Archaludon deck signatures, the rule-action control won
28/48 games. Applying the value model's accepted one-step changes won 20/48 on
the same opponent and seed windows. The candidate was rejected.

Inspection explains why the numerical gate was insufficient: many early states
were saturated near value `0.98`, and the median candidate-value spread was only
`0.0025` and `0.0041` in two of the three mirror buckets. A calibrated matchup
prior can predict which deck tends to win without ranking counterfactual root
actions correctly.

Consequences:

- Policy imitation accuracy and state-value calibration are necessary safety
  checks, but neither proves action-ranking quality.
- Every value-guided action changer needs an end-to-end win-rate A/B test before
  distillation or submission.
- Root labels should come from terminal rollouts of every candidate under the
  same determinization and coin sequence when shallow value differences are
  below the model's observed error.

## Kaggle replays contain a privileged hidden-state teacher

The public replay JSON contains more than the action/observation sequence used
by an agent. `steps[0][0]["visualize"]` contains a full visualizer state after
each action. Visualizer item `i - 1` is therefore the exact state immediately
before replay action `i`, including both decks, prizes, and hands.

The alignment was validated by checking every reconstructed hidden-zone length
against the corresponding public `deckCount`, prize count, and `handCount`.
This makes it possible to generate Search API rollout labels from the real
hidden state rather than a sampled belief state. The submitted model must still
receive only public features; the complete replay state is privileged training
information and must never enter inference features.

The first 53 public episodes produced 975 candidate decisions. Of these, 829
had a valid exact-hidden search result and 51 changed the rule baseline. This is
a useful teacher dataset, but the 51 changes are sparse and correlated within
only 47 usable battles.

## Candidate-pool construction can leak the teacher label

An early residual-gate experiment kept the baseline's top candidate pool and
then appended the expert action when it fell outside that pool. A grouped
five-fold Gradient Boosting evaluation appeared strong: at a conservative
threshold it recovered several expert changes with zero or one false override.

That result did not survive rebuilding every state with all legal options. On
829 states and 4,961 non-baseline option pairs, grouped by 47 Kaggle episodes,
the same model recovered 0 of 51 changed states. At thresholds from 0.5 through
0.7 it made 7, 3, and 1 overrides respectively, all on states where the expert
kept the baseline action.

The failure mechanism is structural: membership in a pool that was expanded
only when the teacher disagreed reveals information about the label even when
no feature is explicitly named `expert`. All policy-distillation validation
must construct candidate sets independently of the teacher.

Using every legal option is a useful leakage audit, but it creates a second
problem: the rollout teacher evaluated only `candidate_actions`, which is the
rule scorer's top-K pool plus the rule action. Unevaluated legal actions have no
outcome label and must not be treated as bad actions. The final safe training
representation therefore reconstructs the exact independently generated
`candidate_actions` set from the saved rollout evaluations. It includes the
baseline by construction and never appends an option merely because the expert
selected it.

## Exact hidden search does not equal deployable belief search

On manually inspected replay changes, a public-information determinization
policy selected the same action as the exact-hidden teacher in only 5 of 27
cases. Exact opponent-deck search did improve one Alakazam local bucket, from
92/120 to 106/120 wins when results were combined across three exact-deck
opponents. Replacing the exact deck with a nearest or robust catalog hypothesis
removed that improvement: the deployment-oriented variants were neutral or
worse than the rule baseline.

This separates two questions that are easy to conflate:

- whether a full-information rollout can identify a better action;
- whether the public agent can infer enough hidden state and opponent policy to
  choose that action reliably.

The first can train a public policy, but it does not justify running the same
search online with guessed hidden cards.

## Direct distillation and one-round DAgger were not stable

Sparse linear residuals had zero changed-label recall under episode-grouped
validation. Neural option scorers trained on seven Archaludon signatures reached
only about 20-25 percent exact agreement on changed holdout states. A one-round
DAgger dataset collected from failed-candidate trajectories initially appeared
five games better in a six-game bucket, then lost the larger confirmation:
84/224 wins versus 108/224 for the rule baseline. A more conservative residual
cap scored 193/448 versus 196/448 and was also rejected.

These failures do not imply that imitation learning is exhausted. They show
that 51-435 changed labels, depending on the collection, are not enough for a
high-cardinality action representation without stronger grouping, coarser
features, and substantially more independent battles.

## Continuous rollout advantage is richer but still hard to predict

The saved expert reports contain paired terminal values for every evaluated
candidate, not only the final accepted action. Rebuilding the teacher-independent
candidate pools yielded 2,343 non-baseline candidate pairs from 829 states.
Their paired mean advantages ranged from -2 to +2; 330 were positive, while
1,364 were exactly zero because the candidate and baseline reached the same
terminal result under every completed rollout.

A grouped Gradient Boosting regressor trained on these continuous advantages
had an out-of-episode correlation of only 0.069 and RMSE of about 0.400. At a
0.05 predicted-advantage threshold it made eight changes: six were non-worse
under the stored rollouts, only two were strictly positive, and the mean true
advantage was +0.023. Higher thresholds selected only rollout-neutral changes.

This shows why exact-action recall alone is too strict, but it also shows that
the extra continuous labels have not yet produced a useful policy. Promotion
requires strictly positive held-out advantage and end-to-end game gains, not
merely a high `non-worse` rate dominated by zero-difference actions.

## Public deck counting helps identification, not yet action prediction

A deployable belief feature was built from a fixed catalog of public 60-card
deck signatures. At each decision it removes every hypothesis incompatible
with the opponent's visible board, discard, tools, energies, and known prizes.
It exposes only the remaining hypothesis count and normalized signature mass;
the true replay deck is never supplied directly as an inference feature.

With 91 local meta agents, 186 of 829 states had a unique compatible deck and
217 had no compatible hypothesis. Extending the fixed catalog with public deck
lists recovered from both same-policy submission windows eliminated the empty
sets and made 295 states unique. Despite the better identification, the
episode-grouped classifier still recovered 0 of 51 accepted expert changes.
The advantage model selected only neutral actions at conservative thresholds.

Counting remains useful for opponent modeling and online search, but exact deck
identification alone does not solve the larger opponent-policy and hidden-zone
uncertainty in action selection.

## Rating paths are not policy A/B tests

The exact same `gtmidguard_lucariobev_crustledeckguard` archive was submitted in
two matchmaking windows. The earlier 77-game window went 41-36 and at one point
reached roughly 1,045 before settling much lower. The later window was around
31-22 while its displayed rating was still near 783. The code and deck were
identical.

Therefore a live rating snapshot, especially early in a run, cannot establish
that one implementation is stronger than another. Replays remain useful data,
but candidate promotion must use fixed local buckets and submission-window
holdouts before Kaggle rating is consulted.

## Hidden deck order makes some exact-teacher changes undeployable

The exact-hidden teacher repeatedly preferred free shuffle effects such as the
Spikemuth Gym ability in individual replay states. Those choices were often
strong under the replay's known deck order: shuffling replaced a bad exact top
deck with a favorable one. A public agent cannot observe that ordering.

A rule that always took the same shuffle opportunity against eight Marnie
opponents lost the larger local comparison, `315/384` versus `323/384` for the
unchanged baseline. Exact-hidden terminal advantage is therefore not a valid
supervised target when the advantage is caused by information unavailable at
inference. Future labels should marginalize over hidden order, or explicitly
discard actions whose gain disappears across public-belief determinizations.

## A second submission window increased data but not direct imitation quality

Exact-hidden labeling of all 77 earlier same-policy replays produced 1,228
usable states from 69 complete public episodes, 3,488 independently evaluated
non-baseline action pairs, and 105 accepted teacher changes. Forty-four
episodes contained at least one positive paired rollout action.

This dataset was kept strictly separate from the later 829-state submission
window. Models trained on the historical window did not generalize into the
later one:

- a conservative binary Gradient Boosting gate recovered only `1/51` later
  teacher changes at threshold `0.5` and made six overrides;
- a continuous advantage model reached correlation about `0.167`, but its
  thresholded changes were dominated by teacher-unchanged states;
- action-signature and board-signature tables had negative mean true advantage
  on the later window;
- matchup-specific Alakazam, Marnie, Archaludon, and Mega Lucario models did
  not produce a stable positive gate.

This exhausts the current direct-distillation variants rather than merely one
classifier. More replay labels alone did not remove the hidden-order and
opponent-policy distribution shift.

## Low-dimensional terminal-reward search needs paired robust selection

A Cross-Entropy Method search was restricted to 28 public features: four
visible matchup classes times seven coarse option types. This avoids the
high-cardinality action imitation problem and optimizes full-game reward
directly. The first run used 64 games per candidate against eight training
opponents. Its best sampled individual scored `54/64`, versus `46/64` for the
zero-weight rule policy.

That best individual failed a separate 256-game holdout. The zero policy won
`202/256` with mean shaped reward `0.646`; the selected CEM individual won
`192/256` with mean reward `0.557`. Losses were concentrated in the unseen
Alakazam and Marnie buckets, while only one Archaludon bucket and one Lucario
bucket improved. The iteration-one maximum was sampling noise and training-set
overfit, so it is not a submission candidate.

Distribution means from later CEM iterations were less brittle on another
unseen 256-game set: zero won `186/256`, iteration-four mean `189/256`, and
iteration-five mean `188/256`. These runs used different seed windows, so the
small margins are only a signal for paired confirmation, not proof.

The next CEM revision ranks each candidate by its paired gain over a zero
policy evaluated on exactly the same games, with an additional penalty for the
worst opponent-bucket gain. It also raises evaluation to 192 games per
candidate. This prevents a single noisy aggregate maximum from becoming the
saved policy merely because it sacrificed one matchup.

## The stock local battle API ignores Python seeds

The first robust CEM revision exposed a more fundamental evaluation bug. Its
first population intentionally contained two identical zero-weight vectors.
Despite receiving the same Python seed and game IDs, they returned different
win totals and opponent-bucket rewards.

The official engine source explains why. `ApiBattleStart` initializes
`GameConfig.seed` from `std::random_device`, sets `deviceRand = true`, and then
re-seeds the game's `mt19937` from four more device-random values. Initial deck
shuffle, coin flips, and several random effects therefore ignore
`train_reinforce.py --seed`. The Python seed had controlled only policy-side
sampling and module-level fallback randomness.

Consequences:

- previous small "paired" local deltas were not paired at all;
- independent large-sample win rates remain rough estimates, but candidate
  differences of a few games cannot be attributed to the policy;
- a search optimizer can select shuffle luck even when its feature and reward
  code are otherwise correct.

A local-only `BattleStartSeeded` entry point was added to the provided source.
It sets `deviceRand = false` and initializes the engine `mt19937` from the
explicit per-game seed. A separate DLL is built by
`tools/build_seeded_engine.ps1`; competition submission binaries are left
unchanged. Verification now shows identical full-game reward, result, and
decision count for repeated policy/seed pairs, and identical results for
duplicate control vectors evaluated in separate worker processes.

`train_cem.py` now fails fast if its duplicate controls diverge. All terminal-
reward optimization and promotion comparisons from this point use the seeded
engine. Unseeded CEM v1/v2 weights are retained only as audit artifacts and are
not eligible for submission.

## A zero residual must return the rule action before rescoring

The first seeded evaluator still had a second identity bug. With an empty
weight dictionary, `choose_residual` recomputed every baseline score, normalized
and sorted the options, and chose the resulting argmax. This usually matched
the rule action, but it could differ when the rule used a custom tie-break,
multi-selection order, or stateful priority not represented by the scalar
score. A "zero" policy was therefore not guaranteed to be the submitted rule
policy.

Evaluation now returns `rule_selected` immediately when weights are empty and
the policy is not training. A regression test deliberately supplies a rule
action that disagrees with score order and requires exact preservation. The
training loop also obtains the rule action through the real `agent(obs)` entry
point instead of calling `choose_options` directly, preserving opponent-attack
tracking and other stateful observation bookkeeping.

These two checks are complementary:

- duplicate CEM controls must produce identical seeded game results;
- zero residual actions must be byte-for-byte the rule actions.

Without both checks, a small RL gain can actually be a comparison between two
evaluation artifacts rather than between the candidate and deployed baseline.

## Submission wrappers must not rely on the agent directory being on sys.path

The first residual submission wrapper used `from residual_policy import
choose_residual` inside a broad `try/except`. The local agent loader imports
`main.py` by absolute file location and does not add its directory to
`sys.path`. The import could fail silently, leaving `_RESIDUAL_WEIGHTS = {}` and
turning the archive back into its rule baseline.

The wrapper now loads the sibling `residual_policy.py` with
`importlib.util.spec_from_file_location` and reads weights relative to
`Path(__file__)`. Package verification compares 220 seeded games from the
training-time candidate with 220 games from the built archive; actions, rewards,
results, and decision counts must all match exactly. A separate 320-game,
eight-archetype check confirmed that the targeted package is exactly the rule
baseline outside Archaludon detection.

## Phase-specific residuals generalized better than matchup-wide weights

The 28-variable matchup-by-option-type CEM candidate tied the zero policy on a
256-game unseen set. Splitting it into four independent seven-variable matchup
blocks isolated the useful signal in the Archaludon mirror, but a broad mirror
block improved only `1/400` holdout games and moved wins between opponents.

First-divergence traces showed a more specific pattern. In several mirror
states the rule preferred Ultra Ball or another item by a small score margin,
while terminal outcomes improved when Metal Energy was attached first. The
broad weight applied this ordering at every turn, creating both wins and
losses. Two public features were therefore retained:

- `public_matchup_turn_type=archaludon:4:8 = 0.03`;
- `public_matchup_turn_type=archaludon:10:8 = 0.03`.

They mean: in an identified Archaludon matchup, and only in early (`<=4`) or
middle (`<=10`) turn buckets, slightly prefer an otherwise close Attach action.
The residual cap and rule candidate pool still prevent discovery of prohibited
or low-scored actions.

Across four independently seeded mirror panels, the targeted pair improved by
`+11/3,840` games. The largest final panel used 11 opponent policies and 2,200
games: `1,026 -> 1,030` wins and shaped reward `-0.07060 -> -0.06669`. Non-
Archaludon games remained exactly unchanged. The effect is small but repeated,
and its deployment surface is only two sparse weights.

The first generic-runtime archives (`54526221` and `54526456`) failed at
validation step zero on both seats, even after removing dynamic imports. Kaggle
did not expose the Python exception, so the exact platform-specific cause is
not proven. The deployable fallback statically reproduced the same two-weight
ranking inside the baseline's existing `choose_options` function, adding only
883 bytes to `main.py` and preserving every other member and the exact member
order of the last successful archive. That minimal submission, `54526632`,
passed validation at 2026-07-10 20:59 JST.

Promotion still depends on the live rating reaching the gold range; local
repeatability and validation success are not the final competition result.

## Opponent scheduling can silently lock each deck to one seat

An audit invalidated the first Alakazam CEM panels. The evaluator selected the
opponent with `game_id % opponent_count` and the trainee seat with
`game_id % 2`. With an even number of opponents, every named opponent was
therefore evaluated from only one trainee seat. Candidate and zero policy still
saw the same games, but opponent-bucket estimates confounded policy behavior
with a fixed first/second-player assignment.

The shared schedule now emits `(opponent A, seat 0)`, `(opponent A, seat 1)`,
then opponent B, and so on. Both CEM and REINFORCE use this helper, and a unit
test checks the exact sequence. Earlier even-opponent Alakazam numbers remain
audit artifacts and are not promotion evidence.

Under the corrected schedule, a low-temperature REINFORCE policy produced a
promising validation result after strict Alakazam filtering and magnitude
pruning: `610 -> 630` wins over 800 games. Two more seed panels returned
`588 -> 584` and `586 -> 594`, for a three-panel total of `+24/2,400` games.
The effect did not transfer to eight Alakazam implementations excluded from
training: `625 -> 616` (`-9/800`). The candidate is rejected, and the next run
uses all 16 implementations for training while reserving a new external set.
This demonstrates that deterministic paired seeds and seat balance still do
not replace policy/deck holdout separation.

Live wins also need action-level attribution. Across the first seven public
Archaludon mirrors of submission `54526632` (four wins, three losses), replaying
all 479 target decisions through the exact pre-residual archive and submitted
inline archive produced zero action differences. Those games are baseline
evidence, not residual evidence. `tools/compare_replay_agent_actions.py` now
performs this stateful replay comparison so future live outcomes are linked to
an actual policy change before they are used as feedback.

## Blending independently overfit policies can recover external holdout gain

The first eight-opponent low-temperature REINFORCE run and a later sixteen-
opponent run overfit in different directions. The first policy improved its
known-agent seed panels by `+24/2,400` but lost `9/800` on eight excluded
agents. The sixteen-agent policy failed its own new seed panel. Pruning,
unpruned weights, and global scales of 0.25, 0.5, and 0.75 did not fix that
second policy by itself.

Both policies were restricted to explicitly detected Alakazam features and
pruned at absolute weight `0.005`. A 50/50 coefficient blend was selected on
the eight-agent external panel, where it scored `625 -> 632` (`+7/800`). It was
then frozen and evaluated once on seven Alakazam agents never used for
training, pruning, blending, or selection. The final holdout scored
`670 -> 677` (`+7/840`): Ebisu `+4`, Kohenyan `+4`, old Ketchum `+3`, with
small losses on Majkel `-1`, old 5.5 `-1`, and Tubotu `-2`.

This is not evidence that averaging always helps. It is evidence that two
different overfit directions can contain complementary residual signals, and
that the blend must still be frozen before a genuinely untouched policy/deck
holdout. `rl_ptcg/blend_weights.py` records the explicit coefficients and
produces a reproducible sparse artifact.

## Training and packaged policies must match across every selection context

The first static package passed local games but did not reproduce the
training-time policy. Over a 140-game paired panel, the training policy's mean
reward was `0.693`, while the package exactly matched the zero-weight rule at
`0.647`. The cause was not an import failure: the trainer applied the residual
to every selection context, while the package wrapper applied it only to MAIN.
The learned improvements included target and other non-MAIN selections.

Removing that restriction made all 140 package histories exactly match the
training policy in result, shaped reward, and decision count. The archive
builder also now copies the last successful tar member list, metadata, and
order, replacing only root `main.py`. This retains all 22 proven members rather
than repacking a cleaner but platform-untested 13-member archive.

The first prepared package was
`submission_archaludon_rl_alakblend5050_fullcontext_20260711.tar.gz`, SHA256
`F1F82184EE318AB272218FE8C5ECE0029C9B3CF0BC4B5DF45B9B4FC6C1391DBF`.
It has been superseded by the combined package described below. Live promotion
remains unproven until Kaggle validation and rating.

## Package configuration is part of the learned policy

The first Alakazam-plus-Iono integration accidentally used the builder defaults
of `top_n=3` and `residual_cap=0.35`, while the frozen Alakazam validation had
used `top_n=3` and `residual_cap=0.12`. The archive compiled and ran, but a
140-game package-equivalence panel changed from mean reward `0.576` for the
frozen training configuration to `0.637` for the package. This was not a valid
improvement because it was an unvalidated policy change introduced during
packaging.

Rebuilding with the frozen cap restored exact equality on all 140 games. This
is a stricter rule than checking that weights and source code match: candidate
pool size, residual cap, temperature, context coverage, and any other inference
hyperparameter must be versioned and replayed as part of the policy artifact.

## A narrow live rule can be composed with a matchup-scoped residual

Two live Iono/Bellibolt losses exposed Archaludon ex near the opponent's final
prizes despite a one-prize Archaludon line. A broad guard at three remaining
prizes fixed the replay choices but lost one local game where the ex line was
correct. Restricting the rule to two or fewer remaining prizes preserved all
400 local game results while still changing the verified late-game replay.

The final package combines that rule with the strict-Alakazam blend. Because
the residual features are matchup-scoped, the package matched the standalone
Iono rule on all 120 additional Iono games and matched the previous baseline on
all 240 non-Alakazam/non-Iono games. The final archive is
`submission_archaludon_rl_alakblend5050_ionoprize2_cap012_20260711.tar.gz`,
SHA256 `0164F3D0CFAA6E234A9F88F6E346C7044998CBC71ABA8E48C930A0B2EE0D26AD`.
It has 60 cards, 22 preserved archive members, 140 exact training/package
histories, 240 exact non-target histories, 120 exact Iono package histories,
and 67 passing unit tests.

## Small in-sample RL gains still require deck-policy holdouts

A five-agent Mega Lucario REINFORCE run improved its independent-seed training
panel from `370/400` to `374/400`. On three excluded Lucario implementations it
fell from `338/360` to `335/360`, including `113/120 -> 110/120` against the
live-style agent. The residual was rejected. More seeds against the same agent
implementations would not repair this evidence; the failure is policy/deck
generalization, not only seed variance.

## Replay attribution should cover wins and losses, not only selected examples

The Alakazam-plus-Iono package was replayed over all first 50 public games of
submission `54526632`. It changed actions in all seven Alakazam games and both
Iono/Bellibolt games: 26 Alakazam decisions and three Iono decisions. It made
zero action changes in the other 41 games across Mega Lucario, Archaludon,
Great Tusk/Crustle, Dragapult, Hop, Starmie, Marnie, Chandelure, Ogerpon, and
Mega Abomasnow/Kyogre.

This is stronger deployment evidence than showing that a targeted loss replay
changes. It verifies both coverage of the intended live bucket and absence of
observed cross-matchup leakage on live states, including states from wins.

## Checkpoint sweeps can rescue a method, but inference settings need a new gate

The initially selected Mega Lucario checkpoint lost on the three-policy
holdout. Sweeping all eight saved checkpoints found checkpoint 6 at `340/360`
versus the zero policy's `338/360`, with no opponent bucket worse under the
training inference settings. The method therefore was not abandoned after the
first failed checkpoint.

However, the combined submission must share the Alakazam policy's frozen
`top_n=3` and `residual_cap=0.12`. Under those settings checkpoint 6 scored
`339/360` versus `338/360` on the selection seed, then `331/360` versus
`332/360` on a new seed and `457/500` versus `470/500` on the five training
policies at a new seed. It was rejected. A checkpoint is not a portable weight
file independent of candidate-pool and residual-cap settings.

## A replay-plausible fix can remain wrong after two rounds of narrowing

One Archaludon mirror loss ended with a lone Cinderace while Hero's Cape stayed
in hand. A rule that attached the Cape to a bench-empty Cinderace changed that
exact replay, but scored `277/600` versus `278/600` across six mirror agents.
Adding turn-two-only and no-Duraludon/no-Archaludon-ex-in-hand conditions still
scored `277/600`. The rule was rejected instead of being accepted from replay
plausibility alone.

A separate Mega Lucario rule always evolves an attack-ready three-Energy Active
Duraludon. It changed one live loss and one live win, scored `742/800` versus
`741/800` on one seed, and tied `374/400` on a second seed with no opponent
bucket loss. This small rule is retained as an incremental candidate because
its two paired panels are non-negative and its live surface is narrow.

The final composed archive is
`submission_archaludon_rl_alakblend5050_ionoprize2_lucarioreadyevolve_cap012_20260711.tar.gz`,
SHA256 `5AD444B15E1ED27B331CAC174D3D8F18A95592F2591203CF35486B71CF30595F`.
It preserves 60 cards and all 22 known-good archive members. The packaged
policy exactly matched the external-weight Alakazam policy for 140 games, the
standalone Iono/Lucario rule policy for 300 games, and the old baseline over
240 non-target games. All 67 unit tests pass.

## Preserving a tactical card can still reduce end-to-end win rate

A later live Mega Lucario loss used Explorer's Guidance to keep two
Archaludon ex while discarding Boss's Orders. Keeping one ex plus Boss appeared
to preserve a direct answer to the opponent's benched next attacker. A broad
Lucario-specific version also changed turn-two and turn-six setup choices, so
it was narrowed to turn eight or later. The narrowed rule changed the intended
turn-ten live choice only in that loss.

Despite the plausible tactical story, the paired evaluations lost `1/800` and
`2/400` across eight Lucario agents, for `1121/1200` versus the baseline's
`1124/1200`. It was rejected. Card-preservation logic must be evaluated through
the full game because holding Boss can replace setup resources that are worth
more even when the later target is visible.

## Robust CEM needs state resolution, but added resolution can still cancel

A corrected-seat CEM experiment optimized Lucario residuals with a penalty on
the worst opponent-policy bucket. Seven matchup-wide option-type dimensions
produced no win improvement in any of four iterations. Adding turn buckets
found a training candidate at `96/100` versus `95/100` with no training bucket
worse.

On three external Lucario policies, two independent 600-game panels returned
`561/600` versus `560/600`, then `560/600` versus `561/600`. The total was
exactly neutral. Separating the turn-4, turn-6, turn-10, and turn-16 weights on
the first 300 games of both panels changed no wins in any bucket. Turn-10 and
turn-16 weights made only `+0.09` and `+0.06` total shaped-reward changes over
600 games.

Together with the REINFORCE checkpoint sweep, this exhausts the tested linear
Lucario residual family: global option type, turn-conditioned option type,
checkpoint selection, and bucket ablation all failed to reproduce a positive
external win gain. The narrow manual ready-evolve rule remains because it was
non-negative on two panels and has a much smaller live action surface.

## A positive aggregate can still fail an adjacent-policy safety gate

A live Archaludon mirror evolved a two-Energy benched Duraludon instead of its
three-Energy Active Duraludon on turn 14. A mirror-only ready-Active rule fixed
that exact decision. The first version scored `+1/1200` over two seeds but
moved wins sharply between opponent policies. Restricting it to turn 12 or
later again scored `+1/1200`, while losing two games to the Toru policy and
gaining elsewhere.

The live opponent used the exact public Archaludon deck, where the narrowed
rule was neutral, but the public and Toru deck lists differ by only one Boss's
Orders versus one card `1213`. At the live decision only one opposing Boss and
no `1213` were visible, so the hidden deck variants were not distinguishable.
The rule was rejected: a positive aggregate is insufficient when the known
adjacent-policy loss cannot be gated from visible information.

## Planned belief-state implementation

1. Identify the opponent archetype from visible cards and action history.
2. Load the corresponding 60-card hypothesis and subtract visible counts.
3. Track reveals, discards, returned cards, prizes taken, and deck/hand counts.
4. Sample hidden zones without replacement, preserving exact zone sizes.
5. Run shallow search for several determinizations with manual coin control.
6. Aggregate root actions by mean value and downside risk.
7. Distill search improvements into a compact policy for submission inference.

These findings are competition-engine specific and should be presented without
redistributing Competition Use Only engine files.

## 2026-07-11 04:35 JST live checkpoint

Submission `54526632` added one public win, episode `85252038`, against NSK's
Archaludon mirror. Its public score moved from about `847.1` to `851.8`. This
does not alter the promotion decision: the verified next archive remains the
Alakazam residual plus narrow Iono and Mega Lucario guards, scheduled only
after the expected 09:00 JST quota reset.

The downloaded leaderboard snapshot at
`analysis_outputs/leaderboard_current_2026_07_11_0434` placed rank 20 at
`1063.7`. The active agent therefore remains about 212 points below the
working gold boundary despite the latest mirror win.

## Kaggle requires the exported agent entrypoint to remain last

Submission `54561161` embedded the dependency-free residual runtime after the
baseline `agent()` definition. It was locally importable, completed local
self-play, preserved the proven 22-member archive layout, and had the same
deck and engine files as the successful baseline. Nevertheless, both
validation seats entered `ERROR` before a gameplay decision. Two earlier
generic-runtime packages had failed at the same boundary.

The policy was rebuilt without changing any rules, weights, deck cards, or
archive members. The only source transformation moved the sole top-level
`agent()` definition after the residual runtime and final `choose_options()`.
The new archive
`submission_archaludon_rl_alakblend5050_ionoprize2_lucarioreadyevolve_cap012_agentlast_20260711.tar.gz`
has SHA256 `D9304CF18E4EE234CB24819E97CBEB41718C477732D56B38623E8DA16722C294`.
It matched the failed package on all decisions across 36 saved replays and
completed local smoke games with zero action errors.

Kaggle submission `54561652` then passed execution validation and became
`COMPLETE`. Its validation self-play reward was `-1`, which demonstrates an
important distinction: validation may be lost while the submission remains
valid; execution status, not validation win/loss, is the deployment gate.
After one public game it was `0-1` at `483.1`, far too little evidence for a
policy rejection. The next public game was a win over Mega Abomasnow/Kyogre,
bringing the initial public window to `1-1` and the score to `602.4`.

This is an empirical packaging invariant for this competition runner. Future
residual builders now enforce exactly one top-level `agent()` and place it as
the final top-level function.

## Seat-relative result parsing is part of the evaluation contract

The first public loss of submission `54561652` was against a mixed
Kangaskhan/Crustle list. The opponent deck exactly matched the local
`great_tusk_bono_junlee_84743036_simple` agent. Replay analysis showed that the
existing Crustle guard repeatedly suppressed Archaludon ex while Kangaskhan
was the immediate threat, so a narrow ex-unlock family was explored rather
than abandoned after its first failure.

The sequence included a broad Kangaskhan-active unlock, a healthy-Kangaskhan
tempo guard, a full-health Hammer guard, a Hammer guard independent of
opponent HP, and a second-seat-only variant. The broad candidate lost
`33/400` on the first exact/adjacent panel. Trace-guided refinements eventually
won all seven diagnostic seeds selected from positive and negative flips, but
the independent promotion panels still rejected the policy.

During this work, one evaluator reported the opposite seat effect because it
counted `result == 0` as a policy win in both seats. `run_local_battle.py`
stores the winning player index: player 0 wins when `result == 0`, while a
policy running as player 1 wins when `result == 1`. The incorrect parser made
the second-seat rule appear positive. Correct seat-aware counting showed the
second-seat-only candidate at `473/800` versus the baseline's `491/800`, a
loss of 18 games. All Kangaskhan-active ex-unlock variants were rejected.

Two general lessons follow:

1. Paired seeds do not protect an experiment from an incorrectly normalized
   player-relative result.
2. A rule can fit every hand-selected diagnostic flip and still regress on
   an independent panel. Diagnostic seeds locate mechanisms; they are not a
   promotion set.

The local evaluator instructions now require an explicit policy-to-player
mapping and an identical-policy control before any seat delta is interpreted.

## Replay plausibility must be separated from seeded end-to-end gain

The first seven live Alakazam losses of submission `54561652` were inspected
against the inline baseline and the submitted residual. The residual changed
twenty of 227 decisions in the first four losses, but nineteen changes were
equivalent copies or selection ordering. The only material change was one
turn-two Explorer selection. In the next three losses, the proposed
turn-two empty-bench rule that benches Duraludon before Pokégear did not fire
at all. The repeated public pattern was opponent setup and prize-race tempo,
not one shared action defect.

The narrow opening rule still had plausible same-state evidence in episodes
`85357128` and `85351053`. Public-belief rollouts preferred or tied the
Duraludon-first action in those two observations. However, the duplicate-
controlled seeded suite across four Alakazam opponents and two seed windows
was exactly neutral: baseline `676/800`, candidate `676/800`, with no bucket
or seat difference. The rule was rejected. Improving a replay action estimate
is not sufficient when the changed action does not alter end-to-end wins.

The reusable evaluator `tools/run_seeded_paired_suite.py` now runs baseline
control A, baseline control B, and candidate for every opponent, seed window,
and seat. A report is invalid if duplicate controls differ, an action error is
observed, max steps are reached, or a subprocess fails. This also avoids two
earlier evaluation traps: `run_meta_suite --fair-seeds` does not invoke the
seeded engine, and `label_replay_rollout`'s `selected` action is the rollout
expert rather than the candidate agent's direct replay action.

## 2026-07-11 18:00 JST live checkpoint

Submission `54561652` reached 49 public games at `30-19`, with fetched score
about `887.9`. The latest game, episode `85369337`, was a win against
Marnie/Grimmsnarl. The prior 48-game archetype snapshot was Alakazam `4-7`,
Archaludon mirror `5-6`, Great Tusk/Crustle `6-2`, Mega Lucario `1-1`,
Starmie `2-0`, Marnie/Grimmsnarl `2-1`, Dragapult `4-0`, and the remaining
buckets sparse. The latest win moves Marnie/Grimmsnarl to `3-1`.

The current score is still below the saved rank-20 gold boundary of about
`1063.7`, but the agent is not in an execution or early-collapse state. No
replacement is justified from the rejected neutral Alakazam opening rule.

Four newer Archaludon mirror losses exposed a narrower repeated state. In
episodes `85363017` and `85364940`, at tied `2-2` prizes with a full-HP opposing
Archaludon ex active and another full-HP Archaludon ex benched, the policy used
Boss's Orders to take the one-prize card `57`. A broad one-prize Boss guard and
earlier mirror-front variants were already unstable by seat and mirror policy.
Only this fully visible `2-2` double-Archaludon predicate is being re-tested;
the empty-bench Ultra Ball symptom occurred in only one new loss and is not a
candidate.

The resulting candidate changes exactly two of the four refreshed mirror
replays: episode `85363017` step 126 and episode `85364940` step 150. It leaves
the earlier Boss action in `85363017` and all actions in `85363997` and
`85365452` unchanged. The duplicate-controlled seeded suite covered six mirror
policies, both seats, two seed windows, and 1,200 candidate games. All duplicate
controls matched, with no action errors or max-step games. Baseline scored
`559/1200`; candidate scored `563/1200`. Deltas were public `+1`, Ezreal `0`,
Ozanm `+1`, Shumpei `0`, Toru `+1`, and Victor `+1`; seat zero was `+4` and seat
one was neutral.

This is a valid positive candidate, but the gain is only four wins (`+0.33`
percentage points). The live submission was still climbing after roughly
three hours, so the candidate is retained without immediately resetting the
live observation window. Its archive is
`submission_archaludon_rl_alakblend5050_ionoprize2_lucarioreadyevolve_cap012_agentlast_mirror22_doublearch_norelicboss_20260711.tar.gz`,
SHA256 `1408E6E46FCD60A4573B97ACCFB6467200080DB25C0E9FF0E2982F963821BE52`.

At the 18:18 JST refresh the live record was `31-21` over 52 public games,
with fetched score about `880.7`. The new sequence was a Toru Archaludon mirror
loss, a Mega Lucario loss, then an Alakazam win. The narrow mirror candidate
made zero action changes in the new Toru loss `85369826`, so this additional
game does not strengthen the candidate's live coverage. The six-hour hold
decision remains unchanged.

## Small public-belief rollout signals need an independent larger sample

The new Mega Lucario loss `85370349` discarded two Ultra Balls during a
turn-two Explorer selection and later lost with one attacker. This resembled
an older, already rejected Ultra Ball preservation family, so it was tested
with public-information determinizations before reopening the rule.

Across 32 determinizations, the recorded `Metal Energy + Archaludon ex` action
won 31 rollouts while `Metal Energy + Ultra Ball` won all 32. The one-sample
advantage did not pass the paired confidence gate. A new `--replay-step` filter
was added to `label_replay_rollout.py` so the exact selection could be tested
without repeatedly evaluating unrelated decisions. Seven focused unit tests
pass.

On an independent 128-determinization run, the recorded action won all 128
rollouts and the Ultra Ball alternative won 127. Its paired mean delta was
`-0.01562` with lower confidence bound `-0.04125`. The apparent small-sample
gain therefore reversed rather than strengthening. The existing Lucario Ultra
Ball preservation family remains rejected.

This establishes a practical rollout gate: a one-outcome difference in a
32-determinization screen is a probe, not evidence for a policy edit. Re-run
the exact public state with an independent seed and at least 128 samples before
implementing the action. This is especially important when the rollout
opponent is a nearest local policy rather than the exact Kaggle policy.

## Opponent-policy ensembles can expose teacher mismatch before distillation

The rollout expert and replay labeler were extended to cycle over multiple
opponent-policy implementations while keeping the replay's opponent deck and
public-belief particles fixed. The robust action gate now evaluates the
Cartesian product of deck hypotheses and opponent policies. Thirteen focused
tests pass.

For `85370349` step 22, four Lucario policies and 256 particles gave the
`Archaludon ex + Ultra Ball` action aggregate paired delta `+0.02344` over the
recorded `Metal Energy + Archaludon ex`, with lower bound `-0.00517`. Separate
64-particle screens made the alternative look favorable or tied under every
policy. This justified an end-to-end candidate test, not promotion.

The exact candidate changed only the intended replay action and zero decisions
in Crustle, Alakazam, and Starmie controls. A valid seeded screen across eight
Lucario policies then scored baseline `295/320` and candidate `293/320`.
Akira and public each lost one game; seat zero was neutral and seat one was
`-2`. The candidate was rejected.

This is stronger evidence than another failed rule: hidden-state sampling plus
a small opponent ensemble still produced an optimistic root-action estimate
that did not transfer to complete games. Teacher reproducibility, continuation
policy, opponent-population weighting, and oracle headroom must be measured
before training a larger model.

The adopted next phase is documented in
`docs/gpt_pro_strategy_review_2026-07-11.md`: freeze the linear residual and run
a 512-state, two-batch public-belief teacher reproducibility pilot before any
neural ranker or new Kaggle submission.

## 2026-07-11 public-belief teacher calibration

The first complete-action teacher implementation confirmed that exact replay
decks overstate local teacher stability. A 32-state exact-deck screen reached
`82.69%` advantage-sign agreement, while the leakage-free public-catalog
screen with three opponent policies and two own continuation policies reached
`78.54%` at four particles per scenario. The latter still had positive mean
oracle advantage `0.1302` and episode-bootstrap lower-90 `0.0605`.

Only three states had a top-versus-runner-up margin of at least `0.25` in both
batches; all three agreed on the top action. Two of 32 states (`6.25%`) had an
action outside the rule-score top-three pool whose paired 90% lower bound was
positive in both independent batches. This is direct evidence that complete
action support can add value, but the stable label set is still too small for
distillation.

The teacher now constructs unknown deck variants without using the completed
replay deck, and balances deck-hypothesis x opponent-policy x continuation-
policy scenarios before reporting. The full result is
`analysis_outputs/teacher_pilot_publicbelief32_pop3_cont2_p4_v1/report_with_top3.json`.

Post-stratification shows that the instability is concentrated in synthetic
unknown-deck support. Real-catalog-supported states reached `85.71%` sign
agreement; synthetic-needed states reached only `71.96%`. The next ranker must
be selective: train and override on supported, positive-LCB states and retain
the rule champion everywhere else. This converts unknown-deck uncertainty
into an abstention condition rather than a noisy label.

The supported 64-state four-particle confirmation narrowly missed the global
sign gate (`79.74%`) and produced only six cross-batch positive-LCB labels.
Four of the six are outside the current top-three action support. The labels
are retained for future calibration, but neural distillation is paused. The
next phase is policy-frozen deck factorial screening rather than forcing a
larger model onto insufficient targets.

The first deck factorial exposed a strong add/cut interaction. Adding
Relicanth while cutting Night Stretcher improved `+15/672`, whereas adding the
same Relicanth while cutting Lillie regressed `-20/672` on identical policy
families and seed windows. The 35-win swing means that one-card additions have
no stable marginal value without specifying the compensating cut. Future deck
optimization must model swap pairs or small packages directly.

A follow-up attempted to suppress early Relicanth search and benching only
after `detect_matchup` returned Dragapult. Against the exact Lumen Dragapult
policy and both original seed windows, it changed none of 48 game results or
decision counts; the two target losses at seat one, seeds `46071103` and
`46071108`, remained losses. The opponent had not exposed enough identifying
cards when the early Relicanth decisions occurred. A matchup-conditioned rule
cannot repair an action taken before the matchup is publicly identifiable.
This candidate is rejected. Any future fix must use an uncertainty-aware
early-game value rule, not retrospective archetype detection.

The second deck-factorial arm also replicated. A fourth Night Stretcher in
place of the third Jumbo Ice Cream scored `+4/336` in the first seed window
and `+17/336` in the independent window, for `+21/672`. Weak/strong groups and
both seats were positive. Every non-mirror policy was neutral or positive,
but all three Archaludon mirror policies were `-2/48`. This is stronger total
local evidence than the live Relicanth swap, but its mirror tradeoff must be
measured on Kaggle rather than hidden by the aggregate.

That conclusion did not survive a direct third-seed comparison to the live
Relicanth swap. The first two direct windows were `-10/+16`; the third was
`-1/336`. Combined direct performance is `+5/1008`, with weak/strong `+2/+3`,
seat zero `+9`, and seat one `-4`. Regressions remain in Alakazam Cape,
Archaludon mirrors, Great Tusk, and Marnie. The Stretcher4/Ice2 archive is
rejected. This is another example where replication against an older shared
baseline is insufficient once a stronger incumbent exists; final selection
must be paired directly against the deployed candidate.

The six unique mirror flips were reproduced and traced. The three named mirror
agents are byte-identical deck/policy duplicates. No common public-state
predicate separates the six losses from four same-mirror candidate gains;
most flips are deterministic deck-order divergence, with only two showing a
plausible late Ice survivability cost. No safe mirror guard follows.

The second-stage factorial fixed the live Relicanth swap as the incumbent and
screened 16 additional complete swaps. The g4 leaders looked very large:
Ice4/FML2 `+24/112` and Stretcher3/FML2 `+21/112`. Independent g12 windows
shrunk them to `+2/336` and `+4/336`, respectively. Both became strongly
seat-sensitive and regressed in every Alakazam mapping. Neither is accepted.

This demonstrates a second selection-bias layer: even when every arm uses
paired seeds and duplicate controls, ranking 16 noisy arms and confirming only
the maximum creates a winner's curse. The screen is useful only for candidate
selection; its delta must not be pooled with confirmation evidence. A new
candidate must win on the independent window itself and against the deployed
incumbent, not merely retain a positive screen-plus-confirm total.

The Alakazam low-prize setup cap changed the intended digimagi replay choices
and left the Ken and SantaClaws loss replays unchanged. Across four Alakazam
policies, two seeds, and 192 games it changed decision counts in seven games
but changed zero winners (`158/192` for both). Three non-Alakazam controls were
also `53/72` identical. This is a useful distinction between action fidelity
and outcome value: fixing a plausible replay decision is not sufficient when
the continuation state has no measured win impact. The rule is rejected.
