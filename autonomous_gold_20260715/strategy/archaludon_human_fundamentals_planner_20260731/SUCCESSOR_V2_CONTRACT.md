# Parent-first public complete-turn dominance overlay v2

## Decision

Implement a fresh child of:

`autonomous_gold_20260715/candidates/archaludon_integrated_public_turn_plan_transaction_v1`

Candidate destination:

`autonomous_gold_20260715/candidates/archaludon_parent_first_complete_turn_fundamentals_v2`

The rejected
`archaludon_human_fundamentals_turn_planner_v1` is test evidence only.
Do not import or copy its executable planner, comparator, generic callback,
search target, resource priority, state machine, or loader replacement.

## Single hypothesis

Preserve the exact parent for every unsupported state. Override it only when one
purpose-bound transaction certifies the complete public turn, retains every
certified parent attack/Prize result, and strictly improves accessible board
formation, attack continuity, exact Prize route, or certified survival.

The parent action is an admissible plan, not an activation condition.

## Arbitration

1. Engine/deck request, reset/result, and legality.
2. Exact parent terminal or forced action.
3. Existing parent transaction owner.
4. Existing overlay transaction owner.
5. Clear-state candidate-versus-parent dominance comparison.
6. Exact parent on tie, uncertainty, collision, binding failure, or exception.

Evaluate the parent once per callback. Never switch owners midway through a
transaction.

## Preserved contexts

Outside an owned overlay transaction, return the exact parent result for:

- `IS_FIRST`;
- `MULLIGAN`;
- setup Active;
- `DRAW_COUNT` and other number selections;
- damage, promotion, switch, activation, discard, search, attachment, and all
  other mandatory callbacks.

One setup exception is allowed: during `SETUP_BENCH_POKEMON`, add exactly one
legal Duraludon when none is already committed and capacity exists. Do not
bench every copy.

## Complete-turn certificate

Every proposal records:

- source snapshot and purpose;
- all card and target serials;
- search source, exact costs, acceptable result roles, and whiff continuation;
- evolution target;
- Assemble Alloy and manual attachment allocations;
- attacker, attack, opposing target, damage, KO, and Prize result;
- end-of-turn Active;
- accessible backup, including its legal promotion/switch/retreat and payable
  attack route;
- reserved Metal, line pieces, Boss, recovery, and ACE SPEC;
- contingency for every reveal-dependent callback.

An override is legal only when:

- all known steps are legal;
- when the parent attacks this turn, the candidate also attacks this turn;
- no parent terminal, certain KO, immediate Prize, or current attack is lost;
- damage and Prize result are no worse;
- opponent immediate return-Prize and terminal routes are no better;
- current attachment and attack remain accessible;
- backup readiness is executable, not merely a powered Bench Pokémon;
- the ex/Alloy route and last deterministic Boss route are preserved unless a
  better exact Prize clock is proved;
- at least one strict improvement is proved;
- no unsupported text, hidden card, unknown draw, or hidden Prize is required.

This is Pareto dominance. Do not add the fields into an arbitrary weighted
score.

## Initial enabled transactions

### Lone-board formation before attack

In a lone Active Duraludon state, a legal Explorer may precede attachment only
when:

- the same current attack remains guaranteed after every reveal branch;
- no terminal/Boss line is displaced;
- deck-out is excluded;
- an empty-Bench backup route is the purpose.

After Explorer resolves, recertify before each Pad, Bench, attachment,
evolution, Alloy callback, or attack. Never assume a drawn card.

### Empty-Bench search

For purpose `CREATE_BASIC_BACKUP`, only Basic Duraludon satisfies the search.
Archaludon ex and non-ex Archaludon must not satisfy it.

Ultra Ball must bind two unique discard serials and its target before play.
Preserve the current attack Metal, required line pieces, final functional
Boss/Stretcher/ACE SPEC, and an executable Alloy route. A search whiff must
already have a safe continuation.

### Accessible Energy

Attach to the current attacker when required for the certified current-turn
attack. Credit a Bench attachment only when a legal same-turn or next-forced-
promotion route and payable attack are both proved. Never attach the sole Metal
to a stranded Bench Cinderace.

### Non-ex Archaludon

Permit the evolution only when Coated Attack is payable and used this turn, and
either:

- 120 is a certain valuable KO; or
- the opposing Active is Basic, every supported ready attack is actually
  prevented, and the one-Prize route strictly improves the exact Prize clock.

Do not consume the only ex/Alloy-capable Duraludon unless the loss is dominated.
“Opposing Active is Basic” alone is not a certificate.

## State safety

- Bind semantics and serials, never option indices.
- Duplicate snapshots return the identical semantic action without stage
  advancement.
- Advance only after the expected public transition is observed.
- Before an irreversible action, binding failure clears and returns the fresh
  parent action.
- After an irreversible action, clear ownership and recompute the parent from
  the actual state; never reuse a stale pre-action result.
- Clear on turn/seat/game/result changes, ambiguity, skipped stage,
  double ownership, or exception.

Telemetry must record parent/candidate semantics, purpose, every gate, the full
certificate, stage, bindings, owner before/after, strict improvement, rejection
reason, transition confirmation, duplicate/retry, rollback, exception, and
emergency status.

## Focused acceptance

Run each relevant fixture in both seats, with option reversal, serial remap, and
duplicate retry:

- the verified valid-hand mulligans remain parent `NO`;
- free `DRAW_COUNT {0,1,2}` remains parent maximum `2`;
- both seed `2026073117` Explorer formations complete backup, attachment,
  attack, and next-turn ex/Alloy readiness;
- empty-Bench Ultra Ball and Poké Pad bind Basic Duraludon;
- unsafe Ultra Ball costs and whiffs return safely to the parent;
- sole Metal never chooses inaccessible Bench Cinderace;
- setup benches exactly one Duraludon;
- non-ex exact 120 KO;
- non-ex exact Basic-prevention/Prize-clock positive;
- non-ex negatives at 0–2 Energy, with only one ex-capable Duraludon,
  ineffective prevention, or lost Alloy/terminal route;
- parent terminal and parent-owned transaction fixtures remain identical;
- reveal failure, missing callback, turn change, and ambiguous binding clear
  and produce a fresh legal parent action.

Require compile/import, legal 60 cards and one ACE SPEC, final loader callable,
zero caches, deterministic duplicates, both-seat exact engine completion, and
zero invalid actions/exceptions/max-step hits.

## Fixed v1b advancement gate

Rerun the exact `PAIRED_SEEDED_V1B_SPEC.md` schedule with only the candidate
path/hash replaced. Require all:

- 16/16 unique valid rows and equal duplicate controls;
- zero action errors, max-step hits, exceptions, stale owners, binding faults,
  or telemetry faults;
- candidate at least 8/16;
- historical Silver at least 3/8;
- Alakazam at least 5/8;
- seat 0 at least 6/8;
- seat 1 at least 2/8;
- no opponent-by-seat bucket below the parent;
- paired gains at least paired regressions;
- both verified Explorer positions corrected;
- every first difference explained by the complete-turn certificate.

Passing this gate allows an adjacent-population confirmation. It does not by
itself authorize packaging or Kaggle submission.

