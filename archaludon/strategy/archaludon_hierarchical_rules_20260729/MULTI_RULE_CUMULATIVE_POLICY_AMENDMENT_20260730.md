# Multi-rule cumulative policy amendment

Date: 2026-07-30 JST

## User authorization

The live replay-analysis environment may be used to diagnose interactions
between multiple deterministic rules. A candidate submitted for diagnosis may
therefore contain multiple individually verified rules instead of limiting
every live probe to a single rule.

## Controlling interpretation

- A new mechanism is still implemented and tested in isolation first.
- A mechanism that is legal, deterministic, fail-closed, and non-destructive
  may remain in the cumulative agent even when it has not fired in the
  available local or live evidence.
- A mechanism whose tested action is itself harmful is not kept merely as a
  dormant rule. It is recorded as a mandatory negative.
- After the isolated gate, compatible mechanisms may be accumulated in one
  Archaludon agent.
- The cumulative hierarchy must expose, for each decision:
  - every rule that proposed an action;
  - the proposed semantic action;
  - the rule that ultimately owned the action;
  - the priority or hard gate that selected it;
  - every suppressed rule and its suppression reason;
  - fail-closed or rollback events.
- A replay loss may justify a collision repair only when the changed action can
  be traced to the relevant rule or interaction. Unrelated loss observations
  remain separate future-work notes.
- A collision repair may change precedence or add a veto without removing
  otherwise valid dormant rules.

## Live-probe consequence

The prepared
`archaludon_cumulative_public_hierarchy_megabrave_lock_veto_v2` package remains
the next authorized live probe. It contains eight individually identified
rules and the Mega Brave self-lock collision veto. Its post-submit analysis
must use the frozen monitoring specification and inspect every action
difference and every multi-rule collision.

## Relationship to the active Goal

This amendment changes only the packaging and live-diagnosis policy. It does
not weaken the required legality, determinism, engine, both-seat, frozen-file,
package, or Kaggle prewrite gates. Root remains the only Kaggle writer.
