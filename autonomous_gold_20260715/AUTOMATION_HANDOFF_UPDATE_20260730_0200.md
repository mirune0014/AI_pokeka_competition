# Automation handoff update — 2026-07-30 02:00 JST

This file supersedes stale current-live, quota, Hero-retention, next-rule, and
source-writer statements in earlier handoffs. Obey `AGENTS.md` and this file.

## Formal anchor and live closure

Exact historical-Silver remains the formal comparison and rollback anchor:

- source:
  `analysis_outputs/reference_agents/historical_silver_archaludon_54495224/main.py`
- source SHA-256:
  `F4B578453C9D953BE94885144DD50E05DBA4510DF3340BE27ADE07495896046E`
- deck SHA-256:
  `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`

Hero submission `55083165` matured after three hours at 41 public games,
`21-20`, exact score `843.5788139221186`. Across 2,332 correct-seat callbacks
it had zero starts, action differences, invalid actions, exceptions, or stale
transactions. Closure report:

`live/55083165/maturity_20260730_0127/ROOT_MATURITY_VERIFICATION.md`

SHA-256:

`F63A30BF0DA60D90CDD3A6D5DE452E7EF9B2FC13E919BA03AF689F17520C8495`

Never resubmit Hero's exact source/archive or use Hero as the formal parent.

## Controlling cumulative-rule policy

The user explicitly authorized multiple verified rules in one experimental
agent because correct-seat replay shadowing can diagnose rule-rule conflicts.
Absence of a Hero trigger is not a reason to remove Hero. It may remain as a
dormant component until it naturally fires.

Policy:

`strategy/archaludon_hierarchical_rules_20260729/CUMULATIVE_RULE_INTEGRATION_POLICY_20260730.md`

SHA-256:

`F8E81D3872C809477068E7C9B476302BE20C14001127EA308C4C80B4CB95BB66`

Each newly authored rule is still implemented and destructively verified in
isolation from exact historical-Silver first. A later cumulative candidate
may integrate verified components only with explicit precedence, eligible/
suppressed/winner telemetry, isolated-component and exact-parent shadows,
collision tests, state isolation, and fail-closed rollback.

## Selected next rule and completed pre-edit gate

Sol-Ultra selected:

`SEARCH_AWARE_ACTIVE_TERMINAL_BEFORE_NONTERMINAL_BOSS_V1`

Contract:

`strategy/archaludon_hierarchical_rules_20260729/next_rule_after_hero_maturity_20260730/STRATEGY_SELECTION.md`

SHA-256:

`DE30DBA76E39DC0F6FF922E24727A3A9013C266DCEAC5CC306E6581CE601FDB0`

Root completed the mandatory pre-edit gate:

- 8 same-turn terminal hit transactions, 80 callbacks;
- both logical seats;
- identity, serial remap, option reversal, equivalent duplicates, and repeated
  callback selections;
- public-only access `D=8`, `P=3`, `U=3`, `P(hit)=164/165 >= 0.99`;
- two all-in-Prize search-miss fixtures retaining two Boss copies, clearing,
  and delegating exact parent from the irreversible state;
- missing evolution, changed target, changed Prize, changed modifier, and
  post-search attack-illegal fail-closed branches;
- zero invalid actions, action errors, exceptions, nondeterminism, stale state,
  or max-step hits;
- deterministic rerun reproduced the exact raw output hash.

Evidence:

- runner SHA-256:
  `4CBE9B8FAE4739EEF43F37B54A50BA9AA0BECCF25C841CF116C0360F7CB374E7`
- raw JSON SHA-256:
  `0EFAB0FECAB5FFAEFE904322C79ACD762A5069E08AE6671D0FEC34E91BB03CF4`
- report SHA-256:
  `50A1D576A4F0D6AFEFA27DCD1A901535A9C64AD80905B4A1A49311AE7B70BF3A`

The gate authorizes one isolated direct-parent implementation. It does not
authorize packaging, submission, or formal-parent promotion by itself.

## Active source writer

The sole Fast candidate worker is:

`/root/implement_search_aware_terminal_v1`

It owns only:

- `candidates/archaludon_search_aware_active_terminal_before_nonterminal_boss_v1`
- `implementation/archaludon_search_aware_active_terminal_before_nonterminal_boss_v1`

No other agent may write candidate source concurrently. Collect the worker,
then Root independently verifies the exact parent diff, contract, public-only
count calculation, stage machine, search miss, all focused negatives, complete
current-plus-historical shadow, every first difference, compile/import,
legal60/ACE1, loader-last, cache-free tree, deterministic actions, and
both-seat exact-engine hit/miss transactions. Do not weaken the frozen
contract.

After isolated verification, define and verify a cumulative candidate that
retains frozen Hero and any other selected destructive-safe component. Compare
the cumulative candidate against exact parent and each included isolated
component, and require explicit collision/precedence evidence before packaging.

## Kaggle state

At Hero maturity, the current UTC day had five COMPLETE submissions; a
separate Alakazam write consumed the last successful slot. Treat quota as
`5/5 used, 0 available` until an authenticated refresh proves the next reset.
Kaggle CLI and episode retrieval work in this environment.

Immediately before any future Kaggle write, Root must refresh authenticated
submissions, UTC quota, current score/status, genuinely new episode IDs/
replays, and exact package hashes. Root alone packages and submits. Never use
a slot on a duplicate, invalid, illegal, unpackaged, filler, or known-broken
artifact.
