# Gold Replay Distillation Progress

## Status

- Phase: `3 - information-set belief counterfactual teacher`
- Decision: reconstruction, candidate coverage, paired belief rollout, and opponent-policy population checks are operational. Gold actions remain proposals; only split-bound actions that survive nested particles and independent batches may become teacher targets.
- Current blocker to Phase 4: Marnie p8 retains only one train state and two
  development states, while the independent Gonsaku family retained zero p2
  states. The latest public Alakazam backup-line rule also regressed on its
  fixed target panel. All three Marnie states survived p16 and retained a
  positive target-action advantage in every p8 batch under both baseline and
  Shumpei continuation policies. One low-HP retreat batch ranks the target
  second under Shumpei, and no exact trigger has transferred to the three live
  Marnie losses. A global ranker is not yet justified.
- Goal source: `docs/gold_replay_distillation_goal.md`

Fresh live evidence for submission `54570845` now contains `76` public games,
record `37-39`, latest fetched score `831.810`. Its largest buckets are Alakazam
`6-14`,
Archaludon mirror `8-8`, Great Tusk/Crustle `3-4`, Mega Lucario `8-2`, and
Marnie `0-3`; Okidogi/Barbaracle is now `0-2`. A Marnie-only rule is therefore not sufficient evidence for a
replacement submission; any candidate must preserve Alakazam and mirror
behavior while addressing the narrow Marnie timing states.
The 2026-07-12 19:23 JST leaderboard snapshot places rank 20 at `1082.2` and
rank 100, the working silver lower boundary, at `989.0`. ShumpeiNomura's
Archaludon team is rank 27 at `1066.6`; it was rank 20 at `1083.6` in the
17:10 snapshot. Its second active Archaludon submission was `993.8` at the
17:45 fetch.

## Current Hypothesis

Gold replays should be treated as candidate and opponent-policy proposals, not
unconditional labels. Their actions may enter a distilled ranker only after
acting-player information-set reconstruction and paired belief rollout show a
stable positive advantage over the frozen rule action.

## Phase 0 Audit - 2026-07-11

### Repository State

- Workspace: `C:\Users\amuam\project\AI_pokeka_competition`
- Git commit SHA: unavailable. The repository has no initial commit and
  `git rev-parse HEAD` fails. Until a commit exists, experiment manifests must
  record content hashes for every source, policy, deck, and engine artifact.
- Python: `3.11.6` from `.venv-rl`.
- Test runner: standard-library `unittest`; `pytest` is not installed in the
  workspace venv.
- Baseline test result: `104` tests passed.

### Commands

```powershell
git rev-parse --show-toplevel
git rev-parse HEAD
.venv-rl\Scripts\python.exe --version
.venv-rl\Scripts\python.exe -m unittest discover -s rl_ptcg\tests
```

### Reusable Foundations

| Capability | Existing implementation | Status |
|---|---|---|
| Acting-player public projection | `rl_ptcg/public_state.py` | Partial, reusable |
| Stable public state ID | `public_state_hash` using BLAKE2b | Reusable |
| Visible-state vector encoding | `rl_ptcg/encoding.py` | Partial; raw order/serial fields are unsafe |
| Deck-consistent belief sampling | `rl_ptcg/belief.py` | Partial; posterior feature contract missing |
| Complete option-index enumeration | `rl_ptcg/search_expert.py`, `teacher_pilot.py` | Reusable search machinery, not semantic actions |
| Paired belief rollout | `rl_ptcg/rollout_expert.py` | Partial; semantic random tape missing |
| Multi-policy teacher pilot | `rl_ptcg/teacher_pilot.py` | Reusable after data-boundary fixes |
| Paired teacher statistics | `rl_ptcg/teacher_statistics.py` | Reusable |
| Seeded A/B/candidate evaluation | `tools/run_seeded_paired_suite.py` | Reusable; promotion statistics incomplete |
| Submission packaging | `rl_ptcg/build_submission.py` | Partial; clean-environment and source/package equivalence gates missing |

### Confirmed Gaps

1. `teacher_pilot.complete_actions` represents a complete action as raw option
   indices. There is no semantic canonical action or environment round trip.
2. `encoding.py` includes `option_ordinal`, raw selection indices, and
   `serial`. These cannot be ranker inputs or persistent action labels.
3. No versioned Gold replay decision record contains all required perspective,
   history, legal semantic action, rule-rank, source, and style metadata.
4. Exact-hidden replay labels are not separated by a loader whitelist strongly
   enough to prevent accidental training use.
5. Required leakage tests are missing: A/B perspective swap, future-log
   deletion, hidden-order/prize invariance, serial/option-order invariance,
   canonical action round trip, and cross-process stable IDs.
6. There is no immutable grouped train/development/blind split manifest or
   overlap validator.
7. Candidate promotion lacks exact McNemar, seed-block bootstrap, per-decision
   latency percentiles, and a fully hashed evaluation manifest.
8. The current policy-value model is an option-level legacy model, not a
   variable legal complete-action ranker with uncertainty/OOD/safety gates.
9. Gold style heads and selective DAgger are not implemented.

### Existing Teacher Evidence

The supported public-belief 64-state pilot is valid but below the Goal gates:

- top-action agreement: `54.69%` (required `>=70%` for high-margin states);
- advantage-sign agreement: `79.74%` (required `>=80%`);
- stable positive-LCB labels: `6`, of which `4` are outside rule top-3.

Artifact:
`analysis_outputs/teacher_pilot_supported64_pop3_cont2_p4_v1/report.json`.

Decision: preserve the labels, but do not train the new ranker until Phase 1
data boundaries are correct and the teacher audit is rerun on Gold replay
candidates.

## First Implementation Slice

Implement and test the Phase 1 data boundary in this order:

1. `rl_ptcg/canonical_actions.py`
   - semantic option identity without ordinal, serial, or raw object identity;
   - stable canonical action ID;
   - option-order/serial invariance;
   - resolution back to a currently legal environment option;
   - a transaction representation that can later compose chained selections.
2. `rl_ptcg/replay_records.py`
   - versioned acting-player decision schema;
   - strict training-column whitelist;
   - separate exact-hidden diagnostic fields and loader.
3. Tests
   - `test_canonical_actions.py`;
   - `test_replay_records.py`;
   - `test_leakage.py`.
4. Dataset/split manifests
   - group by episode, submission/style family, date, seed, and deck variant;
   - freeze and hash blind membership before audit tuning.

## Phase 1 Completion - 2026-07-11

### Implemented Contracts

- `rl_ptcg/canonical_actions.py`
  - stable BLAKE2b semantic option, prompt-action, and transaction IDs;
  - no raw option ordinal, zone index, object identity, or serial in labels;
  - order-invariant multiselect and deterministic resolution to a currently legal environment action.
- `rl_ptcg/replay_reconstruction.py`
  - uses observation at replay step `i` and the submitted action at `i+1`;
  - projects only logs from visualizer frames strictly before the decision;
  - drops exact Draw identities and private-only card moves;
  - groups causally adjacent prompts by main-menu return, seat, turn, and replay-step continuity;
  - retains prior actor-only canonical actions separately from public history.
- `rl_ptcg/replay_records.py`
  - frozen `gold_replay_decision.v1` record schema and deterministic IDs;
  - actor hand, unordered deck-search multiset, ordered visible `looking` zone, and prior private action history;
  - exact-hidden diagnostic labels physically rejected by policy/value loaders;
  - strict JSONL validation and training-column whitelist.
- `rl_ptcg/gold_replay_dataset.py`
  - frozen leaderboard or multi-snapshot Gold catalog selection;
  - UUIDv1 match time, configuration seed, deck/archetype/result, source checksum, and proxy-confidence metadata;
  - immutable decision, transaction, dataset, and split artifacts;
  - cross-file checksum verifier and blind-sealed split loader.
- `rl_ptcg/split_manifest.py`
  - atomic episode/submission/seed/deck components;
  - explicit style-family and date-period holdouts;
  - write-once blind manifest and overlap audit;
  - backward validation for the rejected strict-all-fields manifest.

### Local Replay Inventory

- Source replay files: `461`.
- Unique episode names: `433`.
- Usable unique episodes: `431` (`2` validation/error episodes had no initial 60-card decks).
- Conflicting duplicate checksums: `0`.
- Seat/deck rows: `862`.
- Inventory catalog SHA256: `de8093c3375b0a4e5ea40d51ca720c1e3b207aa7182db6f10bea5031c93175bd`.
- Gold rank-20 proxy catalog: `31` seats from `26` episodes and `18` styles.
- Proxy confidence: `20` post-game snapshots with the same pre-match submission, `11` pre-game snapshots with unconfirmed continuity.
- Gold selection catalog SHA256: `c472e578f56602153548ccf78db93c483f4ff5c0feacf8ce67688fee0f947673`.
- Gold selection manifest SHA256: `224c31aa3a975d3a67cc4ee8fad95b0715b63faeca0d77b5337feb299ed2ad2b`.

### Frozen Ranker Dataset

Artifact directory:
`analysis_outputs/gold_replay_phase1/catalog_rank20_multisnapshot_ranker_v2_privatehistory`.

- Decisions: `2,594`.
- Retrospective transactions: `1,708`.
- Dataset manifest SHA256: `f521918b55f41f4b6b5af7c23b6405fa2eb615cd0e92fa74f2ecc6c617b5c6b6`.
- Decision JSONL SHA256: `bc3b8168e7f1fbe3bfe1f1692f91d64d085b2e0d6403feabdab0279d7d966741`.
- Split manifest SHA256: `ab24ae7e2c0ac213fa6ead752a6314b2a8b3bb16b1b7810b9004cd98a4c7def7`.
- Split counts: train `1,012`, development `1,126`, policy-family holdout `64`, sealed blind `392`.
- Blind period: `2026-07-11`; development period: `2026-07-10`; hash fractions are both zero.
- Policy-family holdout: `Michael Long` Alakazam (`64` decisions).
- Direct Gold-proxy Archaludon in train: ShumpeiNomura (`183` decisions).
- Known-private coverage outside the sealed blind:
  - prior private action history: train `1,000`, development `1,114`, holdout `63`;
  - deck-search multiset: train `93`, development `123`, holdout `8`;
  - ordered looking zone: train `15`.

The blind loader raises `PermissionError` unless the one-time evaluator passes
`allow_blind=True`. No policy tuning or action/result inspection has used the
sealed blind records.

### Leakage and Reconstruction Evidence

- Real replay `85402220`: `120` total acting-player decisions, `75` transactions, and all semantic actions re-resolved to equivalent legal actions.
- Expected prompt chains were recovered exactly at steps `6-7`, `20-22`, `24-28`, `29-31`, and `33-35`.
- Target seat 1 produced `58` decision records with JSONL round trip, policy whitelist, raw-coordinate absence, and opponent-hidden absence.
- Required tests cover seat relabeling, opponent hand/prize/deck leakage, future-log deletion, serial and option-order invariance, hidden-order invariance, actor-known order sensitivity, action round trip, and cross-process state-ID stability.
- Full test suite: `148` tests passed; `git diff --check` passed.

### Split Ablation

The first split algorithm connected records sharing any one of episode,
submission, style, date, seed, or deck values. It was leakage-safe but unusable:

- single-date 1,219-record pilot: `1` component, no blind or development set;
- four-date 31-seat catalog: still `1` component because style/date/deck links were transitive.

Decision: reject strict all-field connectivity as a degenerate split. Keep its
manifest readable as an ablation. The selected split treats episode,
submission version, seed, and deck variant as atomic components, reserves
style families explicitly for policy holdout, and reserves periods explicitly
for time development/blind evaluation.

## Phase 2 Gold Replay Disagreement Audit - 2026-07-11

### Frozen Rule Baselines

Artifact directory:
`analysis_outputs/gold_replay_phase2/frozen_baselines_v1`.

- Six archetype-specific rule agents are frozen: Archaludon, Alakazam,
  Cynthia/Garchomp, Great Tusk/Crustle, Marnie/Grimmsnarl, and
  Okidogi/Barbaracle.
- Baseline manifest canonical SHA256:
  `ffe46852d1dfb19c401820ce8875a41267697d343db74b7e2669f9ad0de962aa`.
- Baseline manifest file SHA256:
  `618c945b26451945c9216161b03ce23a83d343e6613eee47ce8b4c647b9e735b`.
- Archaludon source archive SHA256:
  `31c1fcad5aa5053b15a1a17d654db89729fcb43a5edd9a4bdf43b2b60210fc91`.
- The manifest binds the engine DLL/API, every `main.py` and `deck.csv`, and
  the archetype-to-agent map. The self-hash and all bound files verified.

### Frozen 512-State Audit

Artifact directory:
`analysis_outputs/gold_replay_phase2/disagreement_audit_512_v2`.

- Non-blind eligible decisions: `2,202`; frozen sample: `512`.
- Sample: `20` episodes, `14` Gold styles, both acting seats overall.
- Realized strata: own Archaludon `180`, Gold opponent versus Archaludon
  `179`, Mega Lucario `53`, neutral `100`.
- Replay/state/action reconstruction errors: `0`.
- Exact complete-action enumeration was used for all `512`; truncations: `0`.
- Gold action was generated by the complete candidate generator in
  `512/512` states.
- Semantic Gold/rule disagreement: `204/512` (`39.84%`).
- Rule rank was available for `497` states. Great Tusk's frozen agent does not
  expose `score_option`, so its `15` states retain semantic/coverage results
  but are explicitly excluded from rank denominators.
- Gold outside rule top-3: `85/497` (`17.10%`).
- Gold outside rule top-10: `9/497` (`1.81%`).
- Same-state cross-style agreement coverage was only one state; its observed
  agreement was `1/1` and is not treated as evidence of general agreement.

Direct same-archetype Gold-proxy Archaludon evidence is promising but highly
clustered:

- `180` sampled decisions, semantic disagreement `104/180` (`57.78%`).
- Gold outside rule top-3: `55/180` (`30.56%`); outside top-10: `5/180`.
- Versus Alakazam: `40/90` outside top-3; versus Okidogi: `15/90`.
- All direct Archaludon decisions come from one style, seat 0, and two
  episodes: one Alakazam win and one Okidogi loss. They use
  `pregame_snapshot_unconfirmed_continuity` Gold-proxy evidence.
- The observed Gold Archaludon deck overlaps the frozen baseline in `47/60`
  cards. Exact own deck identity is actor-known, but this distribution shift
  must be retained in the oracle and ranker analysis.

Decision: candidate coverage is not the limiting factor, and Gold supplies
meaningfully different actions including rule top-3 outsiders. The evidence
does not establish that those actions are better. Proceed to the predeclared
paired belief rollout oracle; do not perform direct behavior cloning.

Artifact SHA256 values:

- sample manifest: `2abd4c3cdcf1752a96a78c005bf50a8b38498c44c13c1bd363ad0ba7a7555f1d`;
- rows: `fc473d7219c59a885926d3c6fce7ebddaafd208722a24694b4f306145be654db`;
- report: `eac5ada33e4d5a3e763f60a0d2de5f32f5007dbd49749d17934259fc0901d138`;
- checksum manifest: `e489bf201939430256212acba69a7686f2cec8e9f00c1f3e98a8101ec5b81048`.

The read-only verifier checks sample self-hashes, row membership, report
bindings, dataset manifests, all baseline files, and implementation source
hashes. It reads no blind decision content.

### Commands

```powershell
.venv-rl\Scripts\python.exe -m unittest discover -s rl_ptcg\tests
.venv-rl\Scripts\python.exe tools\build_gold_replay_dataset.py `
  --seat-metadata-csv analysis_outputs\gold_replay_inventory_20260711\all_local_replay_seats.csv `
  --gold-selection-csv analysis_outputs\gold_replay_inventory_20260711\gold_seat_candidates_rank20.csv `
  --output-dir analysis_outputs\gold_replay_phase1\catalog_rank20_multisnapshot_ranker_v2_privatehistory `
  --gold-rank-max 20 --split-seed gold-catalog-rank20-ranker-v1 `
  --holdout-style-family "Michael Long" `
  --blind-date-period 2026-07-11 --development-date-period 2026-07-10 `
  --blind-fraction 0 --development-fraction 0

.venv-rl\Scripts\python.exe tools\run_gold_disagreement_audit.py `
  --dataset-dir analysis_outputs\gold_replay_phase1\catalog_rank20_multisnapshot_ranker_v2_privatehistory `
  --engine-dir analysis_outputs\gold_replay_phase2\frozen_baselines_v1\archaludon_agentlast_relic1 `
  --baseline-map analysis_outputs\gold_replay_phase2\frozen_baselines_v1\baseline_map.json `
  --output-dir analysis_outputs\gold_replay_phase2\disagreement_audit_512_v2 `
  --seed gold-disagreement-512-v1 --target-count 512 --max-complete-actions 4096

.venv-rl\Scripts\python.exe tools\verify_gold_disagreement_audit.py `
  --audit-output-dir analysis_outputs\gold_replay_phase2\disagreement_audit_512_v2 `
  --dataset-dir analysis_outputs\gold_replay_phase1\catalog_rank20_multisnapshot_ranker_v2_privatehistory `
  --baseline-map analysis_outputs\gold_replay_phase2\frozen_baselines_v1\baseline_map.json `
  --workspace-root .
```

## Phase 3A Candidate and Belief Corpus - 2026-07-12

### Frozen 23-State Oracle Corpus

The selected rollout corpus is
`analysis_outputs/gold_replay_phase3/oracle_states_23_v1`.

- `23` non-blind direct Archaludon disagreement states from `2` source
  episodes: `13` versus Alakazam and `10` versus Okidogi/Barbaracle.
- Every state contains the baseline, rule top-3, rule top-6, action-type
  diverse candidates, and the recorded Gold candidate as semantic IDs.
- Belief construction considered `111` catalog decks, accepted `67` after
  public-board preflight, rejected `2`, selected `40` known hypotheses, and
  produced a compatible synthetic unknown hypothesis in `22/23` states.
- Posterior mass sums to one in every state. Unknown mass is `0.15` whenever
  a synthetic hypothesis is available.
- The strict verifier reconnects every source replay, dataset/audit/baseline
  input, engine DLL/API, inventory row, extra deck, candidate semantic hash,
  own deck, and belief posterior. It also reruns the hidden-key leakage guard.

Artifact hashes:

- selection manifest file:
  `2975e353de7d01ae63020ea979624c86528a0290d8759385fbda4a05cdbde91a`;
- states JSONL:
  `c5fcd1db056daef384b1c0d95c8df83025d8a584dcdc5db8515b82d4a95eb54f`;
- manifest file:
  `280b5fad54714d4bdc0855e3b1e39b097c380b25c57b1aaea3b48c53e8686c50`;
- manifest canonical self-hash:
  `b54838cf28837e26cb3763ae588b232233c67ef401b8e7467729c850ace1175e`.

### Full Direct-Arch Candidate Coverage Ablation

The prior ad-hoc coverage calculation is now a verified write-once artifact:
`analysis_outputs/gold_replay_phase3/candidate_coverage_arch104_v1`.
It reconstructs all `104` semantic disagreement states from the same two
direct-Archaludon episodes.

| Matchup | States | Gold outside top-3 | outside top-6 | outside top-6 + type diversity |
| --- | ---: | ---: | ---: | ---: |
| Alakazam | 52 | 40 | 20 | 4 |
| Okidogi/Barbaracle | 52 | 15 | 4 | 2 |
| Total | 104 | 55 | 24 | 6 |

Action-type diversity therefore recovers `49/55` (`89.1%`) of the Gold
actions missed by rule top-3. Only six actions are genuinely incremental to
the bounded diverse set: four Alakazam states and two Okidogi states. Their
action types are PLAY (`7`) four times, TO_HAND (`8`) once, and EVOLVE (`9`)
once. This materially narrows the expensive Gold-specific rollout question;
the broader rule-diverse oracle still remains relevant for ranker training.

Coverage artifact hashes:

- selection manifest file:
  `317a6dd9cab0351769dea5e8f8f1b215be43f14b3ef20e852021ff681dd5a8fa`;
- states JSONL:
  `465c568b332882c36c1d1e516a1eb1a308676c26128d04bbd25b2dbef4c1218c`;
- manifest file:
  `6a5f53c2c4b05843ae1b3cb2062e08262cb10726964c405230f691d9963832fb`;
- manifest canonical self-hash:
  `91b68d73342e46ea8b14e7f917184df56e92f1a4cbd7cf44656abfa29b0e2cd5`.

## Phase 3B Paired Belief Rollout - 2026-07-12

### Search RNG Defect and Local Fix

An initial forward/reverse branch-order test failed on Alakazam step `25`
even after Python RNG reset, fresh Search roots, copied observations/zones,
and fresh policy modules per candidate. Inspection of the published engine
source established the cause:

- `ApiAgentStart` seeds `Game.rng` from `std::random_device()`;
- every copied Search state retains a pointer to the same `Game` object;
- therefore candidate branches consume one shared native RNG stream in branch
  order, even when their sampled hidden zones are identical.

A local-only `AgentSeed` API now resets `Game.rng`, disables `deviceRand`, and
is called with the same particle seed before every candidate branch. The
competition submission engine is not replaced. The seeded Search engine is
`analysis_outputs/gold_replay_phase3/seeded_search_engine_v1`; its DLL SHA256
is `2095c4f50eba3c2b1d41e02c7e28e9da439400e31d513565841f292169af2e06`.
The previously failing Alakazam state then passed exact forward/reverse
terminal-utility parity.

This is a general methodological finding: supplying the same integer to the
Python sampler or the same hidden deck order does not make the stock Search
API a paired evaluator. Native Search RNG must also be reset or replaced by a
semantic random tape.

### Runner and Artifact Contract

The new runner is `rl_ptcg/gold_oracle_runner.py`, invoked through
`tools/run_gold_oracle_teacher.py`.

- It verifies the Phase 3A corpus before loading any state.
- It replays the baseline from the beginning so module-local history matches
  the target decision, then revalidates `state_id` and `decision_id`.
- Canonical candidates are resolved to raw options only in memory and are
  round-tripped before Search.
- Every belief hypothesis is evaluated separately. The same sampled hidden
  world is reused across all candidates, opponent policies, and continuation
  policies.
- Every candidate gets a fresh Search root, fresh opponent/continuation
  module, Python RNG reset, and native Search RNG reset.
- Forward and reverse root orders must produce identical semantic scenario
  rows. A mismatch aborts before a shard is written.
- One immutable shard is written per `(state_id, batch_id)`. Shards contain
  semantic action IDs, stable policy IDs, posterior masses, world digests, and
  terminal utilities; they never contain replay observations, hidden zone
  lists, or raw option indices.
- Resume skips only a self-hashed shard with exact Cartesian coverage. The
  verifier recomputes the report from all shards and checks every bound source,
  policy, engine, C++ seed extension, and Python implementation hash.

`rl_ptcg/gold_oracle_statistics.py` reports posterior-weighted action values,
paired advantages, hidden-world cluster standard errors, one-sided LCB90,
probability of positive advantage, opponent-policy group advantages, VPI,
batch ranks, stable labels, and episode-cluster bootstrap bounds. Utilities
are also converted to win-probability units so the `1.5` point Goal threshold
is not confused with the `[-1, 1]` terminal utility scale.

### Population Pilot

The current diagnostic pilot is
`analysis_outputs/gold_replay_phase3/oracle_teacher_population4_b2_p1_v2`.
It uses four states (Gold-incremental and matched non-incremental states in
both matchups), two independent batches, two opponent policies per matchup,
two continuation policies, and one particle per scenario.

- `8` state/batch shards and `672` semantic paired outcomes;
- Search errors: `0`; forward/reverse parity failures: `0`;
- batch top-1 agreement: `75%`;
- advantage sign agreement: `79.17%`;
- high-margin pairs: `1`, with top-1 agreement `100%` for that single pair;
- stable positive-LCB labels: `0`;
- mean rule-plus-Gold oracle gap versus rule-diverse oracle: `0.0` win-rate
  points in all `8` units;
- Gold action at the Alakazam incremental state changed from `-7.08` points
  in batch A to `+10.83` points in batch B, with negative LCB90 in both;
- the Okidogi incremental Gold action was exactly neutral in both batches;
- only two episode clusters exist, so every bootstrap interval is explicitly
  marked insufficient.

Run manifest canonical self-hash:
`1f79ac8ec9bb9fec0c90cb30ad488dc0c20d73f87b0704d560c42c0976867da8`.
Report canonical self-hash:
`3f7b44528a727aa0b80ad3e15fabe2dbbdbe0e6ae7870912877e88d3fe9635c1`.

Decision: the p1 pilot is not promotion or rejection evidence. It confirms
that the paired pipeline works and that Gold-specific labels are currently
unstable or neutral. Increase particles on the six genuinely incremental
states and matched controls before expanding to all 104 disagreements. Keep
the sealed blind split unopened.

### Gold-Incremental Screening and p4 Convergence

`analysis_outputs/gold_replay_phase3/oracle_teacher_goldincremental6_b2_p1_v1`
evaluates all six actions that are absent from `rule_diverse`, with the same
two batches, two opponent policies, and two continuation policies.

- `12` state/batch shards and `1,136` paired semantic outcomes;
- Gold increased the rule-diverse oracle in `0/12` units;
- step `94` Gold changed sign across earlier pilots and had negative LCB90;
- steps `122` and `267` were negative in at least one batch;
- steps `183` and `256` were exactly neutral;
- step `242` Gold was positive in both batches, but tied an existing rule
  candidate, so its incremental oracle gap remained zero.

The p4 follow-up
`analysis_outputs/gold_replay_phase3/oracle_teacher_alak_gold2_b2_p4_v1`
contains `2,304` paired outcomes for Alakazam steps `94` and `242`.

- batch top-1 agreement: `100%`;
- all-candidate sign agreement: `68.75%`;
- step `94` Gold: `+5.31` and `-11.67` win-rate points across batches, with
  LCB90 `-6.10` and `-21.14` points;
- step `242` Gold: `+5.31` and `+3.54` points, with positive LCB90 `+1.83`
  and `+0.58` points;
- however rule top-3 action `e0a77a10...` had exactly the same value as the
  step `242` Gold action in both batches, so rule-plus-Gold versus
  rule-diverse oracle gap stayed `0.0`.

The stable labels at p4 are therefore one rule-diverse action at step `94`
and the Gold action at step `242`; only the former is uniquely useful to the
candidate oracle. A high-particle direct-Gold test can use the best frozen
rule comparator as an upper-bound screen: if Gold cannot beat that one rule
action, it cannot beat the full rule-diverse maximum.

### Gold Upper-Bound Screen and Full Step-242 Confirmation

`analysis_outputs/gold_replay_phase3/gold_upper_bound_selection6_v1.json`
freezes one baseline or best rule-diverse comparator plus the Gold action for
each of the six incremental states. The selection manifest self-hash is
`1e73ba42583a43f250ddd13692bc6f175b75d7da98eec3cded8268c03977da05`.

The snapshot-backed p1, p4, and p16 upper-bound runs are:

- `oracle_teacher_gold_upper6_b2_p1_v1`;
- `oracle_teacher_gold_upper6_b2_p4_v1`;
- `oracle_teacher_gold_upper6_b2_p16_v1`.

At p16, all forward/reverse parity checks passed and both manifests verified
without implementation drift. Five of six states had Gold UCB90 below `+1.0`
win-rate point in both independent batches. Step `242` was the sole surviving
state: Gold beat its fixed comparator by `+3.33` and `+3.54` points, with
positive LCB90 `+1.72` and `+2.10` points. The six-state mean upper-bound gap
was still `-11.39` points, so this is a narrow state-level result rather than
evidence for broad Gold imitation.

The required full-candidate follow-up is
`analysis_outputs/gold_replay_phase3/oracle_teacher_step242_full_b2_p16_v1`.
It evaluates all ten semantic candidates over two batches, two Alakazam
opponent policies, two continuation policies, and 16 particles per scenario.

- `5,120` paired semantic rows and `2` immutable shards;
- Search/parity failures: `0`;
- Gold action `25cc6900...` ranked first in both batches;
- rule-plus-Gold oracle gap versus the complete rule-diverse oracle: `+1.80`
  and `+3.33` win-rate points;
- Gold action LCB90 versus baseline: `+0.73` and `+2.49` points;
- mean full candidate-set gap: `+2.57` points;
- episode bootstrap remains insufficient because this is one state from one
  episode.

Run manifest canonical self-hash:
`5e14e35f7a87d14b99f4865b1257b2e192f4305cd775e21b52c7a407ce1c6e6d`.
Report canonical self-hash:
`16bf91586db3a7ed977598ae2c6afa6644e3c2341bbcdc4b12274ce938905c0e`.
Verification recomputed the report with an empty implementation-drift list.
This clears the p16 state-level full-oracle screen, but it does not yet clear
the Goal's multi-state, multi-episode, or blind promotion gates. Run p32 and
p64 convergence for this frozen state before using it as a teacher label.

### Direct-Policy Deck Applicability Gate

The p16 result exposed a structural eligibility issue before ranker training.
The step `242` Gold action is `PLAY Xerosic's Machinations (1197)`, while the
frozen target baseline contains no copy of card `1197`. More broadly, the only
two direct-Archaludon Gold episodes use one ShumpeiNomura deck with only
`47/60` multiset overlap with the target baseline, or `13` minimum card
replacements. This is not a near-deck replay under the existing local
operational convention of at most four swaps.

`rl_ptcg/gold_direct_policy_gate.py` and
`tools/build_gold_direct_policy_gate.py` now produce a fail-closed downstream
manifest without modifying the immutable Phase 3A corpus. The gate records
actor/target deck distance, multiset overlap, actor-owned card dependencies of
the complete Gold action, missing target-deck cards, exclusion reasons, and
threshold sensitivity. Ineligible rows remain usable only for source-deck
policy modelling and upper-tier state-distribution work; they cannot enter a
current-deck direct prior or belief-teacher action set.

Official sampled output:
`analysis_outputs/gold_replay_phase3/gold_direct_policy_gate_archbaseline_v2`.

- states: `23` across `2` episodes and one source deck;
- source deck distance: `13` replacements for every state;
- direct-policy eligible at the frozen four-swap threshold: `0/23`;
- Gold actions whose actor-owned cards exist in the target deck: `18/23`;
- states excluded for deck distance: `23/23`;
- states additionally excluded for a missing Gold-action card: `5/23`;
- even at threshold `13`, only `18/23` become action-card compatible;
- step `242` is excluded by both the 13-card distance and missing card `1197`.

Manifest canonical self-hash:
`e9e149d42eaccf00579932438c34d028f29bf4684a3cd8ca1eed078cfa9d0c4b`.
Rows SHA256:
`6f6147d40e75d2c00acfb91dac4bfed174a0f66bdd811574cba14cd263bb31af`.
The verifier recomputes all 23 rows with an empty implementation-drift list.

The gate was also run over all `104` direct-Archaludon semantic
disagreements, not only the 23-state oracle sample:
`analysis_outputs/gold_replay_phase3/gold_direct_policy_gate_arch104_v2`.
All `104/104` are 13 replacements away from the target deck and `0/104`
pass the direct-policy gate. `95/104` Gold actions use cards present in the
target deck, while `9/104` additionally require absent cards (`414`, `1192`,
`1197`, or `1213`). The source has `104` unique decisions but `103` unique
public state IDs, so the gate correctly keys rows by `decision_id` and permits
multiple complete transactions from one public state.

Full-corpus manifest canonical self-hash:
`c8bc01956a915e85a2e5422e6596b4dd4ca97a6510a9538bd13e956ac2b1252e`.
Full-corpus rows SHA256:
`171ce4e8ad78039d28a2e5f802fe7cd5cb1b2a362865cf9a923adab47352cd29`.

The rank-20 inventory contains no additional Gold Archaludon acting-player
episode: all other near/exact-baseline Archaludon seats belong to the local
`rurumi` agent while Gold status belongs to the opponent. Treating those
Archaludon actions as Gold labels would be a player-role attribution error.
Consequently p32 may finish as a convergence diagnostic, but step `242` must
not be promoted and p64 is not justified for this structurally ineligible
label. The next direct-policy search must first obtain a non-blind Gold acting
seat that passes the deck gate, or use Gold data only for opponent-policy and
state-distribution roles.

### Step-242 p32 Diagnostic Completion

The frozen p32 follow-up completed as
`analysis_outputs/gold_replay_phase3/oracle_teacher_step242_full_b2_p32_v1`.
It contains two immutable shards and `10,240` paired semantic rows. Verification
recomputed the report without errors or implementation drift before subsequent
runner development.

- Gold action `25cc6900...` ranked first in both independent batches;
- its baseline-relative win-probability advantages were `+4.67` and `+2.57`
  points, with one-sided LCB90 `+3.47` and `+1.68` points;
- rule-plus-Gold exceeded the complete rule-diverse oracle by `+4.45` and
  `+3.33` points;
- the mean candidate-set increment was `+3.89` points;
- this remains one state from one episode and the action requires Xerosic
  (`1197`), which is absent from the target deck.

Run manifest canonical self-hash:
`f978f8811d140dd8758d8ac2633d0a7faeb8c9993525686a1e3550dcd1448db5`.
Report canonical self-hash:
`f6e576865589dd06ddc24d8f88ead89f627e08dbe2e0a5401c4c3514b0ad5573`.

The original process completed batch 0 but retained native Search allocations
while entering batch 1. Its working set eventually approached `47 GB` and its
paged allocation approximately `69 GB`. The process was stopped only after the
completed shard was preserved. A fresh invocation bound to the identical run
manifest skipped batch 0, completed batch 1, and produced the verified report.
Long rollout jobs must therefore execute one bounded shard per fresh process
rather than accumulating batches in one native-engine process.

The p32 convergence result strengthens the source-state diagnosis but does not
override the direct-policy deck gate. No p64 resource is spent on this
structurally ineligible action.

### Prompt Ranker Safety-Gate Ablations

The fixed-alpha rule/ranker blend improved development accuracy but reduced the
Michael policy-family holdout by `1/60`; it is rejected as a direct replacement.
The selective action-type gate was chosen entirely on development before the
holdout payload was evaluated.

- full-history gate
  `alakazam_prompt_safety_gate_stylefree_v5`: development `+14/770`, holdout
  `+1/60`;
- runtime-compatible no-history gate
  `alakazam_prompt_safety_gate_stylefree_nohistory_v6`: development `+16/770`,
  holdout exactly neutral (`3` improvements and `3` regressions).

The no-history gate is non-degrading but does not establish a useful independent
holdout gain. It remains eligible only as one opponent-policy population head,
not as the submitted target policy or a sole teacher.

### Target-Deck Upper-Tier State Distribution

`analysis_outputs/gold_replay_phase3/upper_tier_target_states5_v1` freezes five
non-blind states where the acting seat is the near-exact target Archaludon deck
and the opposing seat is a rank-20 Gold proxy. July 11 blind-period states were
excluded before replay loading.

- states/episodes: `5/5` (`3` Alakazam, `2` Marnie);
- every recorded acting-seat action is `provenance_only`;
- direct Gold candidates: `0`;
- `rule_plus_gold` is exactly equal to `rule_diverse` in every state;
- candidate `gold` source tags are forbidden by both builder and verifier.

Corpus manifest canonical self-hash:
`a975cb859d5e776b2d66852c77c00d0b92f6ffb046217f27c480ed6f7a536145`.
States SHA256:
`0b3757da756802eb6aa9e0eacefee0cc7a09106349769af0e2315fe03d433dd9`.
Selection manifest SHA256:
`2e5f2b4574ba7bde4d1f8dbd1a6419b7893e94982ddef73f5ca9b921d92e34c9`.

The paired runner now dispatches fail-closed between
`gold_oracle_states.v1` and `gold_upper_tier_states.v1`. In the upper-tier
schema it verifies that the recorded replay action is never promoted into the
candidate set. The first real-data pilot,
`upper_tier_teacher_85035844_b1_p1_v1`, produced `48` rows over eight scenarios
and six rule-diverse candidates. It contains zero Gold memberships and a zero
rule-plus-Gold increment. Several candidates tied the baseline at this very low
particle count, so the pilot is plumbing evidence only.

Pilot run manifest canonical self-hash:
`63842abd5cdd178b10e1f78f7544adbfd0a22416357625dbef4e341f70213796`.
Pilot report canonical self-hash:
`a7ce1f0c0e89504392c6b3082ae5cee434b765a43a7b28ec931d61bb6f28fce7`.

### Portable Corpus and Process Isolation

The upper-tier corpus was migrated without semantic changes to portable schema
`gold_upper_tier_states.v2`. Every replay, inventory input, policy deck, and
implementation snapshot uses a workspace-relative path and a content hash; the
competition engine is represented by a hash-only binding. The authoritative
corpus is
`analysis_outputs/gold_replay_phase3/upper_tier_target_states5_v2_portable_final`.

- corpus manifest: `c1d5322f4186feb46370d24a1099968d699ad8c31324085e4fbab50c92e79606`;
- selection manifest: `e6396917ec1f2cf492dc348f928aae2e7553c80030c72532d4a47ab765ca385f`;
- states: `fe19999713adfd1fd95f5acdc8649879887f4edb7f4d1d24d420f7f5d66651a5`;
- v1/v2 migration audit: `5b860453fa28df55a2ee5c4d9e9e37f496fe54b3458e652a0fd0b1d33013facc`.

The rollout runner now writes one immutable shard atomically and exits when
`--max-new-shards 1` is used. A later process verifies the partial run, skips
existing shards, and writes the report only after all expected shards exist.
The two-process integration artifact
`upper_tier_teacher_85035844_b2_p1_partial_v1` finished with `96` rows; run and
report self-hashes are
`e8509b8fa3c2a8353b1b30c4e3ec8c769d03206cd4283280c24af5e1439fe696` and
`7b5142c8f289308d5689dcf5ca4f41be92258758a3b92b14327ee802568436d8`.
This removes the native-memory
accumulation observed in the p32 diagnostic.

### Seeded Linux Engine and Platform Audit

`rl_ptcg/seeded_engine_linux.py` verifies the exact official competition
source and Python-wrapper hashes, applies the bounded deterministic-seed patch
in a temporary directory, compiles with C++20, checks exported symbols, and
retains no C++ source. The WSL build manifest is
`2e1d61c7726abd9f76ce2555aac22d9b53f13c5c3d36b8d9739d6d46c918f506`;
the local binary is
`ea0955ac1322ba27446e0cdd01ba3f29a91362f7d8fa1f57276be7a300ef729a`.
Kaggle rebuilt the same wrappers with binary
`3bbb12b5e49b1c9c27b1a32efe25e7f30d3b625d73b34c8cc5820542e91e9538`
and engine manifest
`d9470fea9fa5a67132827df409ab95b1225371f8e49369e12d8653a141c0629c`.

Windows and Linux must not share rollout shards: one smoke audit found four
balanced terminal-utility discordances despite equal aggregate action means.
The authoritative teacher platform is Linux. Kaggle Linux and WSL Linux were
then run with the same seed and configuration; all `48/48` rows, utilities,
action means, and ranks matched exactly. Audit self-hash:
`974f88cb33d372eb19db6af315c52a3a087f5b33969ec5977719f7d6bb97300f`.
A full-seed p2 representative shard later also matched all `192/192` row hashes.

### Kaggle Compute Allocation

Kaggle CLI authentication and private-kernel access were verified. Compute is
split by workload rather than assigning every experiment to an accelerator.

- native belief rollout is CPU/RAM bound and runs in a private CPU Notebook;
- one fresh process writes at most one bounded immutable shard, then exits;
- small-particle independent batches replace monolithic p32/p64 processes;
- neural variable-action rankers and later DAgger ensembles use a separate
  private GPU Notebook;
- the local RTX 4070 remains the fast debugging and short-ablation device;
- TPU is deferred because the current irregular variable-action workload does
  not justify its input-pipeline and compilation overhead.

The competition-only engine is attached from the official Kaggle competition
source and, where seeded Linux symbols are required, compiled inside the private
Notebook. It is not uploaded to a custom dataset or republished. Internet is
disabled, policy assets remain private, and every returned shard is checked
against the local input hashes and seed manifest before aggregation.

The private engine-free Dataset version used by the bounded run contains `91`
payload files and `19,311,715` bytes. It contains zero engine binaries, C/C++
sources, credentials, or bytecode caches. Asset manifest self-hash:
`a8ee2ba8de5c5de7eb69c86815cdb6feb7a5ab1aaecbe2e8962756988be5a864`.
The server-downloaded manifest file matched the local file at SHA256
`93cf73cb1ec8df1ad070ebe762e0b2843f958e1aeb2be9094206570d96b31c19`.

Private Notebook version 3 completed the five-state p2 run with `3,360` paired
rows and `20` process-isolated shards. The same-runtime Notebook verifier and
the downloaded cross-runtime verifier both passed with zero implementation
drift and zero execution errors.

- execution manifest: `452ce8331caac5c3f4f896f836d5a15400b5a6584039511860d9ae028b46a9c8`;
- run manifest: `df859afe4d09241954bb8c9b7911ac680bf26c3b7c73d522feb68e0f696ab9ae`;
- report: `2bde8cd5d679b0f348d769de4d9e541f784256b28e5ca06ec01b58bdbe0c2fe7`;
- mean rule-oracle advantage: `+7.08` win-probability points;
- first-two-batch top-1 agreement: `40%`;
- advantage-sign agreement: `83.33%`;
- high-margin state pairs: `0`;
- stable labels: `0`.

The mean improvement is therefore not a trainable teacher result. A frozen
refinement rule selected only non-baseline actions that were top-1 in at least
two of four batches and averaged at least `+5` points. It selected episode
`85056873` Hero's Cape (`3/4` top-1, `+6.30` mean) and episode `85082271`
Lillie's Determination (`2/4`, `+11.20` mean). The reproducible p4 selection
manifest is
`aa752210ba0d210607b121eaa7b50a07b737b09d49b760ed2816156fc291c452`.

Private Notebook version 4 evaluated those two states at p4 with the same seed,
candidate set, and four Alakazam policy heads. It completed `3,072` rows and
`8` shards with zero execution errors.

- execution manifest: `ca4c376d7d89b626f46d79df5206dc6a74e959f6e9c376e886928d3e7c53f245`;
- run manifest: `9f55b87323dd825ab3b54585254a4d9daafb9dfc2727429ae577badda9154f0b`;
- report: `710d8c5d2ca9cd98257e529275b4efa52ca5355e500e293d14c4031350804623`;
- first-two-batch top-1 agreement: `0%`;
- advantage-sign agreement: `40%`;
- stable labels: `0`.

Hero's Cape remained top-1 in `3/4` batches and averaged `+5.34` points, but
only one batch had a positive one-sided LCB90 and the worst policy-head result
was `-21.25` points. Lillie's Determination fell from `2/4` to `1/4` top-1;
its mean remained `+9.92` points but it was not the stable best action.

The p2-to-p4 audit proved that every one of the `768` shared Hero's Cape rows
was reused exactly and had identical terminal utility. Thus the rank changes
come from additional hidden worlds rather than rerun nondeterminism. Audit
self-hash:
`f4cffff9b2612754d460c721f45bef5a0fc6b2e0a803e1f808978b2e39c61344`.

A stricter frozen rule for the final p8 diagnostic requires `3/4` top-1 and at
least `+5` mean points at p4. It selects only the Hero's Cape state. Selection
manifest:
`b737d17038d1d7583685c29449d2cd0cf672235eace9cb18b4b919f5aaaf0ff5`.

Private Notebook version 5 completed the selected state at p8 with `3,072`
rows and `4` shards. All artifacts verified with zero execution errors.

- execution manifest: `16875aa55f73a16fe51d7e3fa201f90eefa9c69b43d9aeae27b60bb209464cd6`;
- run manifest: `23966427d51a56ea9bdc0c063213f477eca41c48f96c1d298446334e6450f0f8`;
- report: `56738540fa6378337d67abb32a5965381e833216ea94d3d570683c198c1c1cab`.

Hero's Cape became top-1 in `4/4` batches, with positive point estimates in
all four and `+5.77` mean win-probability advantage. This is genuine rank
convergence. It is not a stable hard label under the frozen gate:

- minimum batch advantage: `+1.67` points;
- positive one-sided LCB90 batches: `1/4`;
- stable labels emitted by the report: `0`;
- public Alakazam policy-head mean: `-2.71` points;
- worst public-head batch: `-12.29` points.

The p2-to-p4-to-p8 audit verifies exact nested sampling. All `768` p2 rows are
contained in p4, all `1,536` p4 rows are contained in p8, and shared terminal
utility mismatches are `0`. Final convergence audit self-hash:
`f0343e939c946baac3d0616c33db74cbd6e0ed3ed4e6b2fb49040060a72fec14`.

Decision: do not train or implement an override from this state. Increasing
particles repaired rank consistency but did not clear the LCB or policy-family
safety requirements. The positive mean alone is insufficient under the Goal.

### Upper-Tier State Expansion

The five source episode/seat pairs were expanded without consulting recorded
actions, terminal results, or post-target frames. The frozen screen keeps only
main-menu transaction roots with at least four legal options, then selects the
earliest root in each actor turn not represented by the original corpus and
deduplicates by `state_id`.

- valid actor prompts reconstructed: `215`;
- non-base main-menu roots with at least four options: `81`;
- roots in previously unrepresented turns: `71`;
- deterministic additional states: `18`;
- final states: `23`, all with unique `(episode, seat, turn)` and `state_id`.

The executable screen exactly reproduces every state spec in the final corpus.
Screen manifest self-hash:
`cd98cd64e5731b20a3117964a9b48eda97309b1879244b295bc936aab09634bb`.
The final 23-state corpus uses the original five-state seed; all five original
state objects, including belief hypotheses and candidate sets, are byte-for-byte
equal to their source objects. The earlier 23-state build with a changed seed is
rejected because it changed the selected belief hypotheses for all five shared
states.

### Opponent-Population And RNG Audit

The four configured Alakazam paths are not four independent policy-deck units.
`matsurih_live_85056873` and `rmy_live_85082271` have identical `main.py` and
`deck.csv`. The other two paths share one implementation but use different
decks. The old population therefore assigned `50%` weight to one duplicated
policy-deck unit. It also included path-derived `policy_id` in the rollout seed,
so the duplicate paths received different simulation streams.

The runner now has two explicit, manifest-bound controls while preserving the
legacy defaults for old artifact verification:

- `structural_unique_v1` deduplicates by `(main_sha256, deck_sha256)`;
- `common_stream_v1` excludes opponent identity from the scenario seed and
  uses the same stream for every structural policy unit.

A real-engine acceptance run loaded the exact duplicate from both paths under a
common stream. All `48/48` paired rows were identical after removing only the
path-specific policy ID. Run manifest:
`f7f473a1c175aa7d66062fd39ce5c756579be3661620a42601a31a6bf8cd1af4`;
report:
`d2300b157d16b23a32ed3bda2a3c1687556ce9dd2f957c05a813532fbd8ce80f`.
A four-path structural run records `configured_count=4` and
`effective_count=3`, with forward/reverse parity intact.

Private Notebook version 6 repeated the Hero's Cape state at p8 with the
three structural policy-deck units and common rollout streams. It completed
`2,304` rows and four shards; the downloaded execution, input asset, Linux
engine, run, shards, and report all verify.

- execution manifest:
  `51879e2a6cdd0c55cbdaf8011e24a93e302572cfa1bc38ed0f8db0bf09482e95`;
- run manifest:
  `95dd5b6bc20da37619a5abbe863aa2e08645b6c320395a96b18f2ec203da1772`;
- report:
  `17d1f466b6a3a1dda727a4d8a026410d8c802b525829aa01bbaa307ff598b751`.

Hero's Cape is top-1 in `3/4` batches and averages `+9.27` win-probability
points. Two batches have positive one-sided LCB90, but the minimum batch is
`-1.875` points and the report emits zero stable labels. All three structural
policy units have exactly the same per-batch advantage under the common stream.
Thus the previous policy-head spread was simulation-RNG variance, not measured
behavioral diversity in this state. The remaining uncertainty is primarily the
hidden-world batch sample. This is not yet safe to distill, but it justifies the
already launched nested p16 continuation rather than rejecting the action.

Private Notebook version 7 completed the nested p16 continuation with `4,608`
rows and four shards. All downloaded artifacts verify.

- execution manifest:
  `b675abfde3df52fd08c37f2a7a3fa28f459f915116e6c32db347ead1c6d4ff15`;
- run manifest:
  `d0d8587a876cc7328a366f89f62577f89142dffd151c70b8db7c0bea21001fe1`;
- report:
  `f0edcbfcfd820b1a144ce7a02ce6fc5a4b77c6437a50ce7da3124bc331142826`.

Hero's Cape remains top-1 in `3/4` batches and averages `+9.32` points. All
four batch point estimates are now positive (`+21.35`, `+6.15`, `+8.96`, and
`+0.83` points), every structural policy-head point estimate is positive, and
two batches have positive one-sided LCB90. It still emits no stable label, so
it is not distilled yet. The p8-to-p16 convergence audit proves exact reuse of
all `2,304` p8 rows with zero utility mismatch. Audit self-hash:
`90daa0e305fbbddda6bc037793bd901e6d1b7cb5ce1d44312b4507f276d859ac`.

All three structural rule heads again produced identical p16 terminal rows.
Notebook version 8 therefore continues to p32 with the public rule head alone,
same seed and common stream. This is both a compute reduction and the required
single-policy versus population ablation; the p16 population result remains
the safety reference.

The single-public p32 continuation completed `3,072` rows and four immutable
shards:

- execution manifest:
  `3074b1b42eb62113a0ee3a6cbb37a65def5990cc0dd0c286905476676aaf97fa`;
- run manifest:
  `ed47490e572ef417bd0d7aa1818c6756be56d4acc01c90f4189379331c26b2b3`;
- report:
  `2532316dfcbee307b64c6edb52213f2ebbdcfe99f1c8975a94c432bb03bbbce1`.

Hero's Cape is top-1 in `4/4` batches and all point estimates are positive,
but the mean advantage has shrunk to `+4.88` points and only one batch has a
positive one-sided LCB90. It is still not a stable hard label. Projecting the
public head out of the p16 population and conditionally normalizing its weights
gives exactly `384` nested rows per batch (`1,536` total) inside p32, with zero
terminal-utility mismatches. The projected convergence v2 audit self-hash is
`652b2c40c19c7ef4386152d2376031f410bb3ff9185845017c7cb247a6787b7d`.
A same-seed p64 single-public run completed `6,144` rows and four verified
shards. Hero's Cape remains top-1 in `4/4` batches, but its mean advantage is
only `+4.11` points, the minimum batch is `+0.83` points, and only `2/4`
batches have positive one-sided LCB90. Execution, run, and report hashes are
respectively
`9861cd2f458ddee9adda9371f8196106661d9805ef587fc4d06d71b7c83f97a2`,
`55028415abb0e41822dfd2b4b182a8e6658630b567cd0a27b8c5d5e199640f04`,
and `22f556822d110b67ccff24555fdaaadf0f5e350225f49a8a275756733b271fcd`.
The public-head mean advantage contracts from `+9.32` at p16 to `+4.88` at
p32 and `+4.11` at p64. Every p16 row is reused exactly at p32 and every p32
row at p64, with zero utility mismatch. The p16/p32/p64 projected convergence
audit self-hash is
`16998b4b44514d2d1030f6bddce741106144e0fdae1c93dd6992967739a87ba8`.
Combined with the negative learned-head bucket, this action is rejected as a
hard teacher label rather than promoted from its positive point estimate.

### Expanded-State P1 Screen

The 18 new states were screened in a second private CPU Notebook at p1 over
four batches and three structural policy units per archetype. The run completed
`4,848` paired rows and `72` process-isolated shards, all verified.

- execution manifest:
  `eb8a05752330ddef7ee631bb45411473de1fa0000d1b658a54468f8f166b89f7`;
- run manifest:
  `cd051ba295dae70c6db797cdd6333ce9882ec0155fbc28da7c63399d856fbc4d`;
- report:
  `b0c71fd250fe8d894f8a9217e0022301750c4564d92c072ea59262497dd93f30`.

The frozen strict screen selected exactly one state. Selection manifest:
`3e6797dc67da113ef674e07265d0ecbca6a3626274db2a85c2f02ab51784aac4`.
It is episode `85083586`, turn 6, replay step 68, versus Marnie/Grimmsnarl.
The baseline spends two Jumbo Ice Cream cards healing a damaged three-Energy
Archaludon ex before attacking; the selected action attacks immediately with
Metal Defender. At p1 the immediate attack is top-1 in `3/4` batches, averages
`+71.67` points, has minimum batch/head advantage `+15` points, and has positive
LCB90 in `3/4` batches.

An exact Linux branch trace disproved the suspected continuation bug: the
baseline branch really does heal twice, attach Energy to the bench, and attack
in the same turn. The immediate-attack branch instead allows the damaged Active
to be knocked out, preserves the healing cards and Energy, and rebuilds a fresh
Archaludon ex on the following turn. This counterintuitive sacrifice/rebuild
line is a plausible strategic effect, not a missing-action artifact. A nested
p4 refinement completed with `1,344` rows. The immediate attack is top-1 in
`4/4` batches, averages `+63.54` points, has minimum batch and opponent-head
advantage `+46.67` points, and has positive one-sided LCB90 in every batch.
Execution, run, and report hashes are respectively
`ffff2cbad1d0fb18fd8b1804ec12e0838dc6456539185245754a4f2d967fac26`,
`47ce4f7d1cef812aa77849a9b982c5cf1792c7d1ef37cafb9c5807b3425c9a46`,
and `0629afa09fd25e53b526626f6cc2a675d8252b5cce66a321ce886c2d5cfa57bf`.
All `336` p1 rows are exact subsets of p4 with zero utility mismatch. The
convergence audit self-hash is
`2a2af8fdd5158e5c6b190acaee982ec2d163ad6868dc1a09fba48a24064206ee`.
The unchanged-seed p8 refinement completed `2,688` rows. The immediate attack
is top-1 in `4/4` batches, averages `+67.97` points, has minimum batch/head
advantage `+55.63` points, and has positive one-sided LCB90 in every batch.
Execution, run, and report hashes are respectively
`08a8a4f0e9de8c6911ab9a65cc2d0f05cfcef569d1cdfccdf6e63fff6b0dcff4`,
`f35145c2a56adda40c6ee6df727ad6b4cb3a426ac8969f96b455283f0359f91e`,
and `2ccc3994f86b0f882e19d113915678d1a444ba31cf4fdc51e2f8796996018168`.
All `1,344` p4 rows are exact p8 subsets with zero utility mismatch. The
p1/p4/p8 convergence audit self-hash is
`f7520d47b873f1fb2417a41643f259574fada7e0bc0ed7129e0c3bc908930333`.
The unchanged-seed p16 refinement completed `5,376` rows and four verified
shards. The immediate Metal Defender attack is top-1 in `4/4` batches,
averages `+64.77` points, has minimum batch/head advantage `+60.73` points,
and has positive one-sided LCB90 in every batch. Execution, run, and report
hashes are respectively
`e0418613cea5213449926667f61b5ae4dba7e539eea6a1c8bf032aa30ee1afe0`,
`86a5ed2a8a5133399bb58c66b516219387d341969235060d204e8b4faba826b6`,
and `c65b4d08cad35c6740e53854ce942d12975e6cbc089a073ad21a2a3687b2a703`.
All adjacent p1/p4/p8/p16 row sets are exact nested subsets with zero utility
mismatch; the convergence audit self-hash is
`cb43ddfe68ae750d862ed5016c897bbc53378edca7759770428e69fcb2b0c307`.

Kaggle-side same-runtime report verification is preserved across the Linux to
Windows boundary by a source receipt that binds the downloaded execution
manifest, JSON log, run/report hashes, row/shard counts, and the unique clean
`report_recomputed=true` event. The p16 receipt self-hash is
`003d5ef90d2d194a2000d5be276edbad8f1750eb0516e8bd0084092659174f69`.
Before reading the 30-state extension result, a teacher-specific episode split
was frozen using episode IDs only: `34` train states, `35` development states,
and `17` policy-family holdout states. It assigns one train and one development
episode per Marnie/Alakazam where available and reserves the third Alakazam
episode as holdout. Split self-hash:
`8d40c73050deb637b0b0f05fa45e02d06962ebc212b270f3c4354a2d7bed609d`.
The stable action was then joined one-to-one to its split-bound decision ID and
actor-view legal option in a write-once teacher-label artifact. Its final
self-hash is
`1aa4bccf11d52c4c49977695fdba5b404be009d2578406247b89519ccb8a8c69`.
The adapter rejects empty/duplicate/illegal labels, blind splits, actor or deck
drift when constrained, source hash drift, and unverified cross-runtime runs.

The initial screen exposed only one structurally eligible stable label, so the
state corpus was expanded deterministically from every candidate-pool main-menu
root with at least four legal options. The resulting portable corpus contains
`86` unique states and preserves all `23` prior state payloads byte-for-byte.
Its containment/provenance audit self-hash is
`c2fa8e43e3a101d953c4a7a0baab6580dba12413bdd73cea95182751a46c5679`.
The first leakage-safe extension selects the `30` Marnie/Grimmsnarl states that
are present only in the expanded corpus. Selection depends only on state ID,
episode/seat/step, and pre-decision belief archetype. The corrected v2
selection counts each `rule_diverse` candidate, four belief hypotheses, and
three opponent heads, for `1,896` p1 rollout rows rather than the rejected
v1 estimate of `90`. Selection manifest self-hash:
`b00bba1b43f19f686749f2f664b1b94f5a645103ae43d46a279c616f34abf541`.

The 30-state p1 screen then completed exactly `1,896` rows and `30` shards on
the private Linux CPU runtime. Execution, run, and report hashes are
respectively
`58a9dce00b53019742bc625a9b5d3a13c53272b98c6f3b7242e2fb1281841b57`,
`44ca21a3b97ea6baffa8bd9b0b303cf7faf10cd65209bc73bff795b23c589235`,
and `b8538aecb753cab7555d7c2777a5c53a2442b8021051dd64e0bb84af72617f32`.
The source receipt self-hash is
`c76f7dcaa89843ababb7904e4f8929ddb4e618d1508ee2a044b8a5cd8b727cd3`.
Using the frozen p1 gate (`top-1`, mean advantage at least `+10` points, and
strictly positive batch advantage) selected `12/30` states: four from the
precommitted train episode and eight from development. Selection self-hash:
`20cbef44b674d0947ae0fad5b4a740aa9d7a7ed53765cf538eba6a8d5678d05b`.
Because a one-particle single batch is only a screen, these are not labels.

The nested p2/two-batch refinement then completed exactly `3,264` rows and
`24` shards on the private Linux CPU runtime. Execution, run, and report
hashes are respectively
`aba6534fe0d0130beccadd97436d2fb97fae29660dc88cdf9aadff6906827b25`,
`f98824bfbbd5e586d18d1f54024869f87c1070066ec112fa5668eb01ab20c253`,
and `b14b598211664f57de80593b4916a0f3129cd1af0da8175369bf669c81fdf10f`.
The cross-runtime source receipt self-hash is
`19d22d605cb3c38ccee8a9bbeb6656439ed8b16384f6cc9af45a523e577d1d7a`.
Requiring the same non-baseline action to rank first in both batches, mean
advantage of at least `+10` points, and strictly positive advantage in every
batch retained `8/12` states: three train and five development. Selection
self-hash:
`8dc524976f8c845b40bbebad50562c64c605c9ad2d6a4520a1208a260af2c99c`.
The four rejected p1 survivors demonstrate why one particle and one batch are
not label-quality evidence. The nested p4/four-batch run over the eight p2
survivors completed `8,256` rows and `32` shards while preserving the p1/p2
seed. Execution, run, and report hashes are respectively
`d5f2b9c518733dd0c2d90c155925cdf130750fdf6177d7542fc72437371d46a8`,
`80e7b6b9469d188055b41b244d46764dcc48590406e771a001efcc80b40c1421`,
and `685afa2271e2d86741820508e5885a3559287c06499329cc41397814f30c6dc8`;
the cross-runtime source receipt self-hash is
`cab30830bce8e71c1daf1d1e599033195934aa0c73ed041e66c435e0679dd393`.
Requiring the same non-baseline action to be top-1 in all four batches, mean
advantage at least `+10` points, and strictly positive advantage in every
batch retained `4/8` states: one train and three development. Selection
self-hash:
`7d43460bdb850c298c88e4f4657581b8905df89fc8fcaaa24df01a599e2e9254`.
The split-bound p4 advantage artifact contains `19` complete actions over the
four retained states and has self-hash
`fb8f21a8d6155f4eeed7a1fe780c7eb225906c0805ab6f9cd6b0ec952ed07de6`.
A nested p8/four-batch run over only those four states completed as private
Notebook `rurururumi/ptcg-gold-marnie-extension-4-p8` with exactly `7,296`
rows and `16` shards. Execution, run, and report hashes are respectively
`91750ff8b5afe00ca8c6482bd6943014bb6106ba8f7641c34c81a08d96d7f53e`,
`3b3f133b9d292d2fa923734d07899cf816f5969a43a749a8102062c99957adad`,
and `bf1e729c2cb90dbe6be916e2e3ab928bbeabd45a7b8e7d7260a911ca99ce925d`;
the source-receipt self-hash is
`6ec9233a114b6d5080148754e2f5ee531ca4e42b6d62f55b0e0eb78eefb10b5f`.
The Notebook snapshot predates the all-batch report reducer fix, so its
`stable_labels` field is not consumed. Reapplying the frozen gate directly to
all four per-state batches retained `3/4` states; selection self-hash:
`9055dc52fa5b3d54153ab82688771c6ac859294e4f0ebc0ede1e7656546cc29e`.
The full-health early retreat state `fbc8...` fell to `3/4` top batches and is
rejected. The retained actions are the low-HP retreat (`06db...`, mean
advantage `+0.2656`, minimum batch `+0.1042`), attack before ineffective heal
(`5c591...`, `+0.3807`, minimum `+0.2167`), and delayed bench evolve
(`b6dc...`, `+0.3174`, minimum `+0.2500`). Their split-bound artifact contains
`14` actions over three states and has self-hash
`409d44327822a68011f57ea8ff822589c2d915ecb006b74538f449ed2bc1f4fe`.

Asset v9 changes only `rl_ptcg/gold_oracle_statistics.py` relative to v8 and
includes the all-batch reducer fix. The server-downloaded private copy verifies
to `116` files, `26,987,187` bytes, and manifest self-hash
`5250f85187732d182c6547e2a3ca2191785b6f0bb15c614e8f4b73a614b639ed`.
Private Notebook `rurururumi/ptcg-gold-marnie-extension-3-p16` completed the
three survivors at 16 particles and four batches with the unchanged seed. It
produced exactly `10,752` rows and `12` shards. Execution, run, report, and
source-receipt hashes are respectively
`f90d549379bd3fe186b82038f3d6546601916b6ce00688ed6f76c8d42d7480cb`,
`dc9605622fc4ed5d92e655ff1e6876442bfe1157f309a1d6e87fedaaff19e7be`,
`efdea0956dc62f75c1f5965c2b2d552ebf50c3396f9bd4eea35b367442e1d13c`,
and `2e88ad72f2eece552b37eccf99c01ef3a0e79f992b4bc1e4a53d49f12c5f9c1d`.
Notebook version 1 was killed with subprocess return code `-9` after writing
seven valid shards. The first invocation wrote four shards in about 12 minutes;
the second process accumulated native-engine memory while attempting four more
and was killed after three. No report or execution manifest was produced, so
the partial run is diagnostic only. Version 2 now writes exactly one shard per
fresh process over at most 12 invocations, preserving the same asset, seed,
state set, policies, and expected row count. This restores the already proven
bounded-process memory discipline instead of changing the experiment.
All seven shards shared with the failed first run are byte-identical. The
multi-state nested audit also proves that all `5,376` selected-state p8 rows
are an exact subset of p16 with zero terminal-utility mismatches; audit
self-hash:
`30e0273a5efb862e86bbccb3fedb28e996a074ab128d4149382113eb36186235`.
All three states retain the same non-baseline action in all four p16 batches.
Their mean/minimum-batch win-probability advantages are `+0.2128/+0.1854`,
`+0.4073/+0.3760`, and `+0.3064/+0.2781`. The p16 selection and split-bound
advantage artifacts have self-hashes
`a0851d2c9f249174c4c0708101d9c8ee497b031b3ecd154546ab054da75cd303`
and `9cf6643e692d95575a29fcffca318ba8aafc42e8cfbe4e1bd3f28ebe1a944fb3`;
the latter still contains only one train and two development states.
`gold_multi_state_particle_convergence.py` and its CLI now provide the missing
multi-state nested-sampling audit. They require every selected p8 row to be a
p16 subset with identical terminal utility, bind all selected actions and
batch statistics, reject unlisted source drift, and permit only the explicitly
recorded statistics-reducer hash change. Three focused tests cover exact reuse,
drift rejection, and utility-mismatch detection.

The rollout runner now also exposes `common_population_v2`. Unlike
`common_stream_v1`, which excludes only opponent-policy identity from the
scenario seed, the new diagnostic mode excludes both opponent and continuation
policy identities. This permits a two-continuation sensitivity ablation under
one common chance stream while retaining the existing modes for direct
comparison. It is an ablation control, not a claim that native sequential RNG
has become a fully event-keyed semantic random tape.
Asset v10 adds the ShumpeiNomura-style Archaludon continuation policy and the
current rollout runner needed by this ablation. Both the local and
server-downloaded private copies verify to `119` files, `27,043,877` bytes,
and manifest self-hash
`3e383829802c90229a44ae2cf206033384be51e76fa056f97a1517b17b28bcf5`.
Private Notebook `rurururumi/ptcg-gold-marnie-continuation-2-p8` completed the
three p16 survivors over four batches, eight particles, three Marnie opponent
heads, and two continuation policies. The policies shared the same scenario
stream through `common_population_v2`; the verified output contains `10,752`
rows in `12` process-isolated shards. Execution, run, report, and source
receipt hashes are respectively
`707b33e8677cc6b822d4d70906f2535da8303bee92c342700c87600a0cb3843d`,
`b1e53bb8a3a5befb0e03a3fd4dea22e40ca4150e68c88efd12fecd5b860b3693`,
`209f68098213ec6c2a8c736aa4630e996f0a1145be4735c5eac1454a0d563ecd`,
and `bc77461c3da37e7bb6c98b45f83d1a2b6e184ea66cbf1f73bb2d3e03465940b9`.

The reproducible continuation-sensitivity audit binds those outputs to the
frozen p16 selection and recomputes weighted target-versus-baseline results
from every raw row. For the low-HP retreat state, mean/minimum-batch advantage
is `+0.2193/+0.0729` under the baseline continuation and `+0.1880/+0.0375`
under Shumpei. For attack-before-ineffective-heal it is
`+0.4375/+0.3396` and `+0.4057/+0.3396`; for delay-evolve it is
`+0.2063/+0.1083` and `+0.1927/+0.1083`. All six state/continuation cells are
positive in all four batches, so there is no continuation-policy sign
reversal. The low-HP target is second-ranked in one Shumpei batch, which is
retained as uncertainty rather than hidden by the aggregate. Audit self-hash:
`ab83896b184d0280f76faf35d7c871533467c6c0759fb1044a2d39a16affdbd7`.

Private Notebook `rurururumi/ptcg-gold-marnie-extension-3-p32` is now running
the next nested-particle check. It changes only particles from 16 to 32 while
holding the three selected states, four batches, semantic seed, three Marnie
opponent heads, baseline continuation, candidate construction, and
process-isolated one-shard invocation discipline fixed. Expected output is
`21,504` rows in `12` shards. This is compute evidence only and does not create
a competition submission candidate by itself.
Version 1 failed before engine build because it retained the p16-era private
asset manifest hash while Kaggle now serves verified asset v10. No rollout row
was produced. Version 2 changes only that expected hash to the independently
verified v10 value
`3e383829802c90229a44ae2cf206033384be51e76fa056f97a1517b17b28bcf5`
and is running; the p32 state, seed, policy, and acceptance configuration is
unchanged.

Version 2 subsequently completed exactly `21,504` rows in `12` shards with
report manifest hash
`05b4cbb6be19e632869ea77aa7c62899ecaf1d1c74757f974cb8bb385c917225`
and run manifest hash
`9bcdf5468361222a26b3363bb17dd012c5f65d1d4733fefe633d8d8870f93411`.
The p16-to-p32 multi-state nested audit reused all `10,752` p16 rows exactly,
with zero terminal-utility mismatch in every state and batch. Audit self-hash:
`52e56054d83d935a70963a310218a20c2136185827fa01bc339b9b0e3ff6f762`.
The only explicitly allowed source drift is the v10 continuation-population
plumbing in `gold_oracle_runner.py` and its CLI; the frozen baseline-only
semantic configuration, engine, seed, state set, candidate construction, and
opponent policies are identical, and exact nested row reuse independently
checks the chance stream.

All three selected actions remain top-1 in all four p32 batches and have a
positive one-sided 90% lower bound in every batch. Their p16-to-p32
mean/minimum-batch win-probability advantages are:

- low-HP retreat: `+0.2128/+0.1854 -> +0.2167/+0.1510`;
- attack before ineffective heal: `+0.4073/+0.3760 -> +0.4393/+0.4062`;
- delay bench evolve: `+0.3064/+0.2781 -> +0.2915/+0.2641`.

This closes the nested-particle stability check positively. It does not remove
the three-state coverage limitation, the negative independent Gonsaku-family
transfer, or the absence of exact safe triggers in current live losses; a
global Marnie ranker remains unjustified.

The public daily-episode index was refreshed through `2026-07-11`. The sample
downloader now supports authenticated full pagination, bounded retry/backoff,
size-checked caching, atomic partial downloads, even sampling over a day, and
ranking by either `avg_score` or `min_score` from the daily manifest. Anonymous
multi-page listing repeatedly returned HTTP 404; the authenticated Kaggle API
listed all `5,019` files for July 11 and `5,227` files for July 10. This is an
acquisition-backend failure, not evidence against the replay hypothesis.

The first stratified inventory results materially narrow the same-deck Gold
teacher question:

- An even 60-episode July 11 sample contained `120` classified seats and no
  Archaludon deck. It was dominated by Alakazam (`52`), Great Tusk/Crustle
  (`34`), and Marnie/Grimmsnarl (`23`).
- An even 60-episode July 10 sample contained one Archaludon mirror: winning
  `daiki_H` versus losing `Xander`. Neither was Gold in the nearest preserved
  snapshots; Xander was rank 30 at `1043.9` and daiki_H rank 51 at `1026.7`
  in the July 10/11 snapshot sequence, then both fell below 950. The episode
  is valid upper-tier opponent-policy evidence, not a Gold acting-player
  policy head.
- A score-ranked July 10 sample selected the 40 episodes with the highest
  `min_score`. The selected range was `1252.946` to `1287.435` minimum agent
  score and `1253.266` to `1297.151` average score. All `80` seats were either
  Alakazam (`76`, Yushin Ito/Majkel1337) or Great Tusk/Crustle (`4`,
  MPGaming); no Archaludon appeared.
- The same frozen selection procedure on July 11 covered minimum-agent scores
  `1263.885` to `1276.969` and average scores `1264.345` to `1278.699`.
  Its `80` seats were Alakazam (`41`) and Great Tusk/Crustle (`39`) only,
  primarily Yushin Ito and Budew; again, no Archaludon appeared.

The three raw-sample SHA256 manifest-file hashes (July 11 even, July 10 even,
July 10 top-min-score) are respectively
`22d34cc0d98c7c6c95a967d863f706479f7a304db254de5e6c2a9f55bcb9e9e5`,
`df724f241c65063f990020108faf11d89a05c6e2906ed28c4f2690fc1ad9809e`,
and `4b52186790b9cc9cbae0b92737565b964be0dec3988f46cc18cf6627e30929fb`.
The top-min-score set was independently checked against the daily manifest:
all expected top 40 episode IDs were present with zero missing or extra JSON
files.
The July 11 top-min-score sample has SHA256 manifest-file hash
`49c478b1946e66e1fa86256cac5bb7ab6bed127f777e6c3c59bd4c6770745947`
and also has zero missing or extra files relative to its daily top 40.

The score-ranked absence applies only to the `1250+` extreme slice, not to the
whole medal range. A fresh `2026-07-12T08:10:29Z` leaderboard snapshot and the
public-safe team-submission API identified ShumpeiNomura at rank `20`, score
`1083.6`, with active submission `54588240`; the team's other active submission
`54588173` at `998.1`, inside silver. Public episode `85543431` independently
confirms that the silver submission is also Archaludon: relative to the gold-
boundary list it replaces one Energy and one Full Metal Lab with two Switch.
All `81` fetched episodes for `54588240` were
downloaded. The acting team produced `82` deck rows including self-validation,
and every row is the same `archaludon_metal` list. Its public-data record in
those rows is `48-34` including validation seats. The current deck has
Duraludon/Archaludon ex `4/4`, Relicanth `2`, Team Rocket's Articuno `1`,
Metal Energy `13`, Night Stretcher `4`, Carmine `4`, Judge `2`, Xerosic `1`,
and Full Metal Lab `4`; compared with the older Shumpei deck already modeled
locally, it swaps one Energy for a second Relicanth.

This corrects the earlier broad inference: Archaludon is present at the live
gold boundary, but not in the very highest-score daily slice. Direct current
same-archetype Gold data is no longer count-starved. The remaining problem is
reconstructing the current policy version from acting-player information and
obtaining an independent non-Shumpei Gold policy family for holdout.

Action-level diagnosis shows that the four surviving proposals are narrow
public-information tempo decisions, not a broad Marnie action override. Two
Kazuki states prefer retreat over a nonlethal Metal Defender: the high-confidence
case rotates a `120/300` four-Energy active Archaludon ex into a `210/300`
three-Energy bench attacker against the publicly demonstrated 180-damage
Grimmsnarl line. A third state attacks before Jumbo Ice Cream because healing
from `40` to `120` still does not cross the visible 210-damage survival
threshold. The train state ends instead of evolving an unenergized bench
Duraludon while a doomed active Duraludon absorbs the next knockout, delaying
two-prize exposure. These may become rules only if p8/p16 remain positive and
paired counterfactual guards remove each preference when the alternate tank is
not ready, healing crosses the survival threshold, or the benched evolution is
immediately required. No opponent-private signal is needed or permitted.

Before observing any additional teacher result, a third leaderboard-Gold
Marnie policy family was isolated from episode `85034863` (Gonsaku). Its `15`
main-menu roots with at least four legal options extend the portable corpus
from `86` to `101` states. A dedicated extension audit verifies that all `86`
shared JSONL rows are byte-identical, the expanded-minus-reference set is
exactly those `15` predeclared episode/seat/step triples, and no direct Gold
candidate source entered the action sets. Audit self-hash:
`f1f0c3ddcaf444b8f6ad240b4de7d5517bfd9b69675993fd99e9fafb5fccc30d`.
The teacher episode split preserves all five prior episode assignments and all
`86` prior decisions, while assigning only the new episode to
`policy_family_holdout`. Its self-hash is
`55be83721241ff504992ad21333e800505f8c7f30821d4c70f883d2fc78849db`.
This holdout may evaluate Marnie policy-family transfer but must not be used to
fit the current ranker or tune its thresholds.
The 101-state private compute asset was uploaded and independently downloaded
from Kaggle. Both copies verify to `116` files, `26,987,267` payload bytes, and
manifest self-hash
`26afa88effa9365fdde6d6d612df7a3c6aca37334faaecce4ab92f185ff29724`.
A p1 screen over all `15` Gonsaku holdout states completed `786` rows and `15`
shards. Execution, run, report, and source-receipt hashes are respectively
`dbf95d9857fba8b36e237185c8a44fd7a1eb4aa82b98b0c1cfd3dc1944b3997c`,
`1c204451dfe556e8e9194f5f7a7fbd0e672a1f65134538e22776b474577d8153`,
`ada296af7556c4b9c343f955905bdb5b0ba9d8208166b658efd14e8b6105994d`,
and `c46baf01262aca364372c681ba4c87eac40dda6d7bf40f1e7b3df2cfaa2ef583`.
Applying the already frozen p1 gate without changing any threshold selected
`5/15` states; screen-selection self-hash:
`f7e6e3d558adb8f002f06cfac233e79f9b4637981e5d3a5ce1c0b13b9ed80e44`.
The five are being remeasured, not fitted, in private Notebook
`rurururumi/ptcg-gold-marnie-gonsaku-5-p2` with two batches and two particles
(`1,104` rows, `10` shards). Execution, run, report, and source-receipt hashes
are respectively
`c05b93c76133aa458ea9b858409ff06a2ced0befbfbc0cc412dd4e9ac58fccd8`,
`6f4ea15389b9c6bc4b7d9ea51d13b06cbeef0cd917322555dcaa14af0dd4f5a1`,
`bb034729bc7c8e330a6c7a387a6606e6ede27005ef9c46f5a8b2665db77928e4`,
and `bc7f407eb0d614a208aaccd888af1b0ff341dcd5508fdf33bb46ee823a5a0a6f`.
None of the five p1 survivors retained the same non-baseline top action in
both p2 batches while satisfying the frozen positive-margin gate (`0/5`);
selection self-hash:
`55d33cc8e1f7985117c4c793706fb85b5f7d555f808af49900716f3144fcb2f6`.
The independent Marnie policy-family transfer test is therefore negative. Do
not train a global Marnie ranker from the existing episode clusters and do not
spend p4 holdout compute. All Gonsaku outcomes remain evaluation-only.

A split-bound complete-action advantage artifact was added before ranker
training. It preserves all `43` evaluated actions across the eight p2 survivor
states, including batch advantages, one-sided LCB90, opponent-head minima,
cluster standard errors, rule scores, and canonical complete transactions.
There are three train and five development states; artifact self-hash:
`2129daa0542ff800d935d06bca85adcb597b8c9a13b1a18decfc72e33deb5d3d`.
The loader projects belief hypotheses without catalog paths, source hashes, or
signatures, and includes the known actor deck composition as a variant feature.

An exact target-deck applicability check failed as intended. These replay
states use actor deck hash
`3d8a18c51b6e6fed180ddd9306f0ddee8250525227c26b1e0146879b89ecf3f9`,
whereas the frozen continuation baseline deck hash is
`b9054134e4f90ebf30149ddfe6d0d41907494faf9934cefd35630132476aaeac`.
The artifact is therefore archetype-bound, not falsely advertised as exact
deck supervision. A five-seed pairwise-plus-regression smoke fit on the three
train states reached `100%` train top-1 for every seed but only `0-20%`
development top-1 and `55.6-65.1%` development pairwise accuracy. This global
ranker is rejected: p4 labels must first be established, then independent
states must be added through selective DAgger or the result must be narrowed to
a local rule/table override.

### Gold Bootstrap Opponent Head

The non-blind Alakazam Phase 1 set contains `953` usable one-selection prompts:
`123` train, `770` development, and `60` policy-family holdout. A no-style,
no-public-history prompt ranker was trained so its runtime input contract can
be reproduced from each rollout observation. It reaches `35.58%` development
top-1 and `43.33%` fully held-out-style top-1. On the Matsurih source replay,
the safe hybrid policy returns valid actions for all `58` prompts and matches
the recorded action on `31`; it differs from the public rule head on `21`.

The hybrid uses the learned ranker only for exactly-one prompts and falls back
to the existing Alakazam rule policy for multi-selection prompts or any
inference error. The policy descriptor now binds the checkpoint, evaluation
report, and implementation snapshots in addition to `main.py` and `deck.csv`.
A common-world/common-stream p1 pilot produced `9/24` terminal-row discordances
between the learned and public heads, proving real policy diversity. Pilot run
manifest:
`d29cd83737b1ae1b62d56f4ef69b5e89910593d6950952ed1b273fa55c31d13a`.

A second no-history head was fit on train plus development after selecting the
architecture without the held-out policy family. It remains legal on all `58`
Matsurih prompts, matches `30`, differs from the public rule head on `12`, and
differs from the first learned head on `18`. Structural deduplication now binds
auxiliary checkpoint hashes, so the two identical wrappers remain distinct
population units. A four-batch p1 population pilot over public plus both learned
heads completed `288` verified rows (run
`cfe0f0db2d3efe60864d59edc653fbcc8e35ba84750f899f93ea4b30525bd975`,
report `caab30570ba6a829ab8825424f57bce893fadc701712f21aa01dfe294f24e63a`).
The Hero's Cape mean remains positive at `+10.69` points, but one learned head
is `-28.33` points. This is the first real opponent-policy sign reversal and
shows why the three behavior-identical rule heads were insufficient.

A Windows p4 follow-up over the same three heads completed `1,152` verified
rows (run `c41197bc9531efaa36b8a16a130527a492d0017de89ff65778281fdae2fd491b`,
report `02d7d8ff757dc8e90b6efc72de91c6c08ffed7401d0f8392f0a7d72ae0030cd9`).
Hero's Cape is top-1 in only `2/4` batches, averages `+2.40` points, has a
minimum batch of `-1.11` points, a minimum opponent head of `-14.17` points,
and zero positive LCB90 batches. It is rejected as a hard label under the
learned population even if the single-public p64 point estimate remains
positive.

The corresponding private Linux p4 run also completed `1,152` rows. Hero's
Cape is top-1 in `4/4` batches and averages `+10.07` points, but the minimum
learned-head advantage remains `-14.17` points, so the hard-label rejection is
unchanged. Execution, run, and report hashes are respectively
`8d05d174bc8de2012ff9205f35341c1ca2eeac0a2dabfe6f490ea475bfd124d1`,
`59cafb53f6f9793723ed2d83a5689099f71ef6e3d06220c9b18ae4bfeb6ef30d`,
and `3d8f62f66199f5ba8eb40dec08784c8dfae3bff0a53185f3e0b059e9166b8bda`.
A Windows/Linux platform audit found structurally identical keys for all
`1,152` rows but `277` terminal-utility discordances (`24.05%`), unequal action
ranks, and maximum action-mean utility delta `0.3278`. Cross-platform shards
are therefore never merged and Linux is authoritative for Kaggle teachers.
Audit self-hash:
`72202f5ec8ce5c7b93e0af712d07a2ccdc37b7c08f56d2399a1ea8cb194ae52a`.

The next private asset payload includes both learned heads, the corrected
structural binding, and the expanded 86-state corpus. It is prepared and
verified locally at `109` files, `24,173,730` bytes, manifest self-hash
`1564d2a11586087bbaecc7c7faa793688f6cba7298239ab74e0a681bff3d71af`.
After the older-Dataset runs completed, it was uploaded privately and then
downloaded from Kaggle again; the server copy verifies to the same 109 files,
byte count, and manifest hash. An initial CLI attempt omitted the payload
directory because `--dir-mode` defaulted to `skip`; no Notebook used that
incomplete version, and the latest corrected version was uploaded with
`--dir-mode zip` and independently verified. The earlier 23-state v6 payload
was superseded locally without being published.

The private Dataset was updated with the final 23-state corpus and the new
runner. It contains `91` payload files and `20,291,337` payload bytes, with no
engine binary, C/C++ source, credentials, or bytecode cache. Asset manifest
self-hash:
`3d49904eb14124567404f968ade023839aa892a36c08b0f287657b0ba1bd9622`.
The server-downloaded manifest file matches the local file at SHA256
`700290918039b7ace7c0c9752043f2b5c521c7c4746894d993f6f418e18bdc44`.

### Verification Commands

```powershell
.venv-rl\Scripts\python.exe tools\build_gold_oracle_states.py `
  --verify-only analysis_outputs\gold_replay_phase3\oracle_states_23_v1 `
  --workspace-root .

.venv-rl\Scripts\python.exe tools\build_gold_oracle_states.py `
  --verify-only analysis_outputs\gold_replay_phase3\candidate_coverage_arch104_v1 `
  --workspace-root .

.venv-rl\Scripts\python.exe tools\run_gold_oracle_teacher.py `
  --verify-only analysis_outputs\gold_replay_phase3\oracle_teacher_population4_b2_p1_v2 `
  --workspace-root .

.venv-rl\Scripts\python.exe tools\run_gold_oracle_teacher.py `
  --verify-only analysis_outputs\gold_replay_phase3\oracle_teacher_step242_full_b2_p32_v1 `
  --workspace-root .

.venv-rl\Scripts\python.exe tools\build_gold_upper_tier_states.py `
  --verify-only analysis_outputs\gold_replay_phase3\upper_tier_target_states5_v1 `
  --workspace-root .

.venv-rl\Scripts\python.exe tools\run_gold_oracle_teacher.py `
  --verify-only analysis_outputs\gold_replay_phase3\upper_tier_teacher_85035844_b1_p1_v1 `
  --workspace-root .

.venv-rl\Scripts\python.exe tools\verify_kaggle_gold_rollout_execution.py `
  --execution-manifest analysis_outputs\kaggle_compute\ptcg_gold_rollout_full_v3\ptcg_gold_workspace\kaggle_execution_manifest.json `
  --workspace-root analysis_outputs\kaggle_compute\ptcg_gold_rollout_full_v3\ptcg_gold_workspace

.venv-rl\Scripts\python.exe tools\build_gold_teacher_refinement_selection.py `
  --verify-only analysis_outputs\gold_replay_phase3\upper_tier_promising2_p4_selection_v1.json `
  --workspace-root .

.venv-rl\Scripts\python.exe tools\build_gold_particle_convergence.py `
  --verify-only analysis_outputs\gold_replay_phase3\upper_tier_85056873_p2_p4_p8_convergence_v1.json `
  --workspace-root .

.venv-rl\Scripts\python.exe -m unittest discover -s rl_ptcg\tests -q
```

The current full suite passes `346` tests.

## Reproducibility Manifest Requirements

Every new experiment must record:

- schema version and experiment ID;
- source content hashes, because Git HEAD is unavailable;
- engine binary and deck/policy hashes;
- Python/platform/dependency versions;
- replay/dataset/split manifest hashes;
- seed blocks, opponents, seats, games, and max steps;
- duplicate-control result;
- paired discordant outcomes and exact McNemar result;
- seed-block bootstrap configuration and confidence bounds;
- action errors, max-step hits, and choose-call latency p50/p95/p99;
- raw command, raw rows, and aggregate report.

## What Failed

- `python -m pytest` is not available in `.venv-rl`; use `unittest` unless the
  dependency policy is deliberately changed.
- Current Alakazam teacher stability is insufficient for ranker training.
- The original Gold-oracle report stability reducer inspected only the first
  two batches. It now requires top-1, sign, and positive-LCB consistency across
  every available batch; a four-batch regression test rejects candidates that
  look stable only in batches 0-1.
- Hero's Cape remains positive through p32 under the public rule head but is not
  a stable label; a learned Gold opponent head introduces a negative policy
  bucket that the behavior-identical structural rule heads could not reveal.
- The frozen Gonsaku Gold Marnie policy-family holdout produced `5/15` p1
  screens but `0/5` p2 stable survivors. Existing Marnie episode clusters do
  not justify a global Marnie ranker.
- The p8 Marnie proposals do not explain the three live Marnie losses from
  submission `54570845` (`85413613`, `85411671`, and `85512671`). In the first
  two, retreat or the required heal/sacrifice trigger was absent. Episode
  `85512671` exposed superficially similar legal actions, but the low-HP Active
  had no healthy energized replacement, attacking before healing could not KO
  the visible Grimmsnarl, and the evolves were not the retained 40-HP Active
  sacrifice state. Broad versions would retreat into liabilities or skip a
  necessary heal, so the observed `0-3` bucket still supplies no safe trigger.
- The late visible-Alakazam backup-line rule is rejected. On the clean fixed
  800-pair Alakazam panel it changed `605-195` to `601-199` (`-0.50` points):
  Rmy `-2`, Majkel `-2`, and both digimagi buckets unchanged. Seat zero lost
  four wins while seat one was unchanged. Four adjacent matchup controls were
  exactly `315-85` for both policies, with zero duplicate mismatches, action
  errors, or max-step hits. The first evaluator output had concurrent writers
  and is explicitly invalid; only the clean rerun is evidence.
- Live loss `85528347` again exposed an active Alakazam plus two visible
  backup Alakazam, but supplied no demonstrated better continuation. It is an
  earlier-prize instance of the same class already rejected at `-4/800`, not a
  reason to broaden that override.
- Live Okidogi/Barbaracle loss `85527810` benched an unused Relicanth that was
  gusted for one prize before two Archaludon-line knockouts exhausted the
  board. The other loss in the same live bucket does not repeat this Relicanth
  sequence, and only one available Night Stretcher was used; neither a deck
  reversal nor a broad matchup rule is justified.
- Existing option vectors and raw index actions do not satisfy the new Goal's
  leakage and invariance requirements.
- Direct `python tools/build_gold_replay_dataset.py` initially failed because
  the repository root was absent from `sys.path`; the CLI now has a subprocess test.
- UUIDv1 timestamp conversion differed by one microsecond between two float
  conversion paths; it now uses integer 100 ns ticks and accepts a one-microsecond legacy-catalog tolerance.
- Strict connectivity across every protected metadata value collapsed all
  available Gold data into one component and was rejected.

## What Remains Uncertain

- Whether the current Shumpei `54588240` policy can be reconstructed with
  sufficient held-out canonical-action fidelity from its `81` public episodes.
  Replay count is now adequate, but current rules may differ from the older
  simple Shumpei model and hidden information must remain excluded.
- Whether Gold candidates add at least `1.5` blind oracle win-rate points after
  semantic canonicalization and information-set belief correction.
- Whether sequential rollout RNG materially changes teacher ranks relative to
  a semantic random tape.
- ShumpeiNomura remains the only directly attributable Gold Archaludon team.
  The current submission supplies many new episodes and a distinct deck
  version, but it is not an independent team-level policy-family holdout.
- The public `MoveCard` history projection is conservative; private-only moves
  are intentionally absent even when the actor could infer part of the event.
- The three p16-confirmed Marnie actions retain positive sign in every p8 batch
  under the independent Shumpei continuation policy, but the low-HP retreat is
  second-ranked in one Shumpei batch. Higher-particle rank stability remains
  unproven, and none of the three current live Marnie losses supplies the exact
  safe trigger.
- Whether selective DAgger can add enough independent train episodes to avoid
  the measured three-state ranker overfit; current development top-1 is at most
  `20%` despite perfect train fit.

## Next Experiment

Complete the running three-state p32 Notebook under the frozen baseline continuation, preserving
the nested seed/batch construction so every p16 row must be an exact subset.
Require the selected action to remain top-1 and positive in all four batches;
if the low-HP retreat remains marginal, remeasure that state under Shumpei at
higher particles before promotion. Treat the negative Gonsaku transfer result
and absent live triggers as fail-closed gates: do not fit a global Marnie
ranker, and do not convert a confirmed state into a local rule until its exact
public trigger appears in additional live evidence and paired guards pass.
The visible-Alakazam backup rule and Hero's Cape remain excluded. Keep the
sealed blind split unopened until every policy, threshold, and ensemble is
frozen.
