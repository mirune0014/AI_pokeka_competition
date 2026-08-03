# Cumulative hierarchy v2 live-probe monitoring specification

Frozen: 2026-07-30 05:55 JST.

This specification controls the one authorized exploratory Kaggle probe for
`archaludon_cumulative_public_hierarchy_megabrave_lock_veto_v2`. It does not
authorize a write by itself. Root remains the only Kaggle writer and must
refresh authenticated submissions, quota, status, score, exact episode IDs,
and all package hashes immediately before submission.

## Immutable submitted artifact

- policy:
  `candidates/archaludon_cumulative_public_hierarchy_megabrave_lock_veto_v2/main.py`
- policy SHA-256:
  `DEE5092B6785DF7A63752C7AAE497051D08DCC62F7723CD9786225A0C5A99DE8`
- deck SHA-256:
  `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`
- clean archive:
  `packages/archaludon_cumulative_public_hierarchy_megabrave_lock_veto_v2_clean_20260730_0525_retry1/submission_archaludon_cumulative_public_hierarchy_megabrave_lock_veto_v2_20260730.tar.gz`
- clean archive SHA-256:
  `8C921DCCFE6F597F49D60B45799EB97FA4DE573EA7B8FF4C930A91C22FEA9F88`
- package manifest SHA-256:
  `AD3E6AD949A8C2ECCDAEF0B92982DA7894995EBBECE9E63D2AB460B9719781E3`
- package validation SHA-256:
  `20AE8B9676645A9F746708F83A77370B0DDD34E4829C600893B75D8B8774843D`
- formal rollback parent:
  exact historical-Silver policy SHA-256
  `F4B578453C9D953BE94885144DD50E05DBA4510DF3340BE27ADE07495896046E`

The earlier failed archive
`packages/archaludon_cumulative_public_hierarchy_megabrave_lock_veto_v2_clean_20260730_0525/submission_archaludon_cumulative_public_hierarchy_megabrave_lock_veto_v2_20260730.tar.gz`
SHA-256
`6850C9593297981DB6430831ED95866DB4F6B00330B353D361EE60264502CBC2`
is invalid and must never be submitted.

## Prewrite refresh

Immediately before the write, Root must record:

1. local/JST and UTC time;
2. authenticated Kaggle submission table and exact UTC-day slot count;
3. current status and score of the latest Archaludon and Alakazam probes;
4. exact current episode ID set for the latest Archaludon submission and its
   set difference from the previous snapshot;
5. source, deck, archive, manifest, and validation hashes above;
6. archive member count and absence of caches, tests, evidence, traversal, or
   generated files;
7. submission description identifying the eight-rule cumulative hierarchy,
   Mega Brave self-lock veto, fixed-760 `0G/0R`, and collision diagnostic.

If the submission command reports an encoding or response error after upload,
Root must not retry blindly. List submissions, take an exact set difference,
and prove whether one new row exists.

## Episode checkpoints

Create immutable checkpoints at:

- validation completion;
- first public game;
- approximately `5`, `10`, `20`, and `40` public games;
- the first naturally firing rule;
- the first natural collision or suppression;
- three wall-clock hours after successful submission;
- any execution fault or candidate-parent action difference associated with a
  loss.

At each checkpoint, download every genuinely new replay by exact episode-ID
set difference. Record CSV and replay hashes, correct target seat, result,
score before/after, opponent public deck identity only for descriptive
matchup classification, and whether the replay was completely shadowed.

## Required correct-seat shadow

For every actionable callback in every new replay, independently run:

1. exact historical-Silver;
2. the exact submitted cumulative v2;
3. the cumulative resolver telemetry.

Record:

- semantic exact-parent action;
- eligible rule IDs in precedence order;
- semantic proposal from every rule;
- winning rule and attribution owner;
- suppressed rule IDs and `suppressed_by`;
- active transaction owner and stage before/after;
- duplicate/retry/reset status;
- rollback or fail-closed reason;
- final semantic action and whether it differs from exact parent;
- option-binding result, invalid/emergency fallback, and state-clear result.

The eight rule IDs are:

1. `H2_CERTIFIED_LAST_PRIZE_STRETCHER_METAL_BOSS`;
2. `SEARCH_AWARE_ACTIVE_TERMINAL_BEFORE_NONTERMINAL_BOSS_V1`;
3. `H1_CERTIFIED_ENDGAME_ALAKAZAM_BOSS`;
4. `H5_V2_PUBLIC_LETHAL_ACTIVE_NO_READY_SUCCESSOR`;
5. `H4_PUBLIC_MEGA_BRAVE_SELF_LOCK_VETO_V1`;
6. `H6_UNIQUE_ACTIVE_METAL_DEFENDER_CONTINUITY_RESERVATION`;
7. `HERO_CAPE_CURRENT_PAYABLE_SAME_ATTACK_SURVIVAL`;
8. `H3_CERTIFIED_LONE_CINDERACE_ULTRA_BALL_TURBO_FLARE_LINE_FORMATION`.

Inspect every first parent difference and every later callback owned by the
same transaction. A win or loss without a policy difference is not causal
evidence for any cumulative rule.

## Collision analysis

For every callback with more than one eligible proposal, verify:

- the winner matches the frozen total precedence;
- every suppressed component remains clear and unmutated;
- there is at most one transaction owner;
- an irreversible owner is never transferred to a different component;
- a newly appearing different proposal causes the specified fail-closed
  parent fallback;
- the final action is legal and uniquely bound;
- telemetry attribution matches the actual first action difference.

A collision-owned loss must identify the first conflicting proposals, the
selected and suppressed actions, the public certificate, the irreversible
state already consumed, and the exact-parent counterfactual. Do not repair an
unrelated later action.

## Special live diagnostics

### Mega Brave self-lock

Any H4 proposal while the last observed opposing attack is Mega Brave `983`
is a destructive certificate breach. The repaired rule must preserve the
parent action and must never Boss away the self-locked Active merely to obtain
an immediate higher-Prize KO.

### H3 line formation

The first H3 action difference requires a complete qualitative trace:

- public Ultra Ball and Duraludon access calculation;
- Boss/Metal/Explorer opportunity cost;
- retained attacker, backup readiness, and Prize route;
- Turbo Flare target and Energy placement;
- whether the later Jumbo Ice Cream versus Metal Defender choice preserved
  attack continuity;
- whether the action changed the result relative to exact parent.

H3 remains a diagnostic component until the first causal evidence. A
parent-identical score movement or a dormant rule receives no strength credit.

### Dormant rules

No natural activation is neutral evidence. A dormant rule that remains
certificate-valid, deterministic, and nonmutating stays available until it
fires. Do not remove Hero, H1, H2, H5, H6, or another component solely because
the live sample did not reach its trigger.

## Immediate rollback conditions

Stop the live probe and return to exact historical-Silver for the next
candidate if any submitted-rule action causes:

- invalid action, exception, action error, max-step hit, or deployment fault;
- stale transaction, two owners, duplicate advancement, or reset failure;
- proposal/telemetry attribution disagreement;
- unknown or unregistered collision;
- Mega Brave self-lock release;
- use of hidden deck/Prize/hand identity, replay ID, opponent identity, seed,
  or replay-future information;
- a rule-owned or collision-owned parent-win/candidate-loss conversion;
- a certificate violation that changes setup, board formation, backup
  readiness, Energy allocation, attack continuity, Prize exchange, or
  survival outside the frozen rule.

Weak score alone is not an implementation defect. It is diagnostic evidence
only after the sample matures and every policy difference has been inspected.

## Unrelated losses

If a loss is entirely parent-identical, write a separate deferred memo only
when a concrete public-state improvement is visible. Record the exact episode,
row, current parent action, legal alternative, public board/resource facts,
hidden-information limitation, required engine counterfactual, and future
mechanism bucket. Do not stack that idea into the submitted cumulative source
or attribute it to the current rule set.

## Three-hour decision

After at least three hours and sufficient public games:

- continue unchanged if no destructive fault exists and evidence is still
  sparse;
- repair only a rule-owned or collision-owned certificate failure;
- retain safe dormant rules even with zero triggers;
- evaluate score only alongside correct-seat action differences and matchup
  composition;
- do not promote the cumulative policy to formal parent without a fresh
  Sol-Ultra judgment and the stronger formal-adoption gates in the integration
  contract.
