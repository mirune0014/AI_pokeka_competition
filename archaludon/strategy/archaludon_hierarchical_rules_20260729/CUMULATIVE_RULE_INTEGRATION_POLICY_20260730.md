# Archaludon cumulative-rule integration policy

Controlling user instruction: 2026-07-30 JST.

## Purpose

The live experimental Archaludon may carry multiple independently verified
rules at the same time. A verified rule is not removed merely because it did
not naturally fire during its first live probe. In particular, the frozen
Hero's Cape survival rule may remain dormant until a matching public state
occurs.

This policy changes live integration and diagnosis. It does not change the
formal comparison anchor:

- exact historical-Silver remains the formal baseline and rollback action;
- every newly authored mechanism is first defined and destructively checked
  directly against exact historical-Silver;
- no submitted source/archive may be resubmitted unchanged;
- rejected or known-broken rules remain excluded.

## Integrated decision protocol

At every callback, the cumulative policy must:

1. compute and preserve the exact historical-Silver action;
2. evaluate each integrated rule from the same public-state snapshot;
3. record every eligible rule and its proposed action;
4. resolve at most one winner through an explicit tested precedence table;
5. record every suppressed rule and the precedence reason;
6. execute the winner only if its complete certificate and transaction state
   remain valid;
7. otherwise roll back to the exact historical-Silver action.

An unknown, ambiguous, or untested collision always fails closed. Rules may not
silently mutate another rule's transaction state.

## Required telemetry

Each callback shadow must expose stable fields for:

- `exact_parent_action`;
- `eligible_rule_ids`;
- `proposed_actions_by_rule`;
- `winning_rule_id`;
- `suppressed_rule_ids`;
- `precedence_reason`;
- `final_action`;
- `transaction_stage`;
- `snapshot_id`;
- `rollback_reason`;
- `duplicate_or_reset_state`;
- `invalid_or_emergency_fallback`.

This is required even when the final action equals the parent action.

## Verification before a cumulative live probe

The Root must verify:

- each component's frozen source hash and prior destructive-safety evidence;
- exact-parent identity outside every component's certificate;
- all reachable pairwise precedence cases among active components;
- collision rollback without leaked state;
- duplicate callbacks and episode/reset boundaries;
- compile/import, legal 60-card deck, deterministic valid actions, loader-last
  behavior, cache-free package, and both-seat engine smoke;
- correct-seat shadow attribution of each first difference.

No local win-rate threshold is required for a practical probe if these
destructive gates pass. A weak live result is evidence to diagnose, not by
itself an implementation defect.

## Live causal audit

For every genuinely new replay:

- attribute the first parent difference to the winning rule;
- inspect any simultaneously eligible suppressed rules;
- separate a rule-owned loss, a rule-rule collision loss, and an unrelated
  parent-path loss;
- repair only the mechanism or precedence involved in the changed action;
- record unrelated improvements as deferred memos.

The first natural Hero's Cape activation receives a dedicated causal audit.
Until that occurs, Hero remains a dormant verified component and its absence of
activation is neither positive nor negative strength evidence.
