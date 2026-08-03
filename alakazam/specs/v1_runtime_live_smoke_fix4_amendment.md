# v1 runtime live-smoke fix4 amendment

## Status of fix3 evidence

The complete 140-game fix3 smoke passed, but the broader formal safety schedule
later exposed two irreversible verifier faults. Therefore fix3 is classified as
`SUPERSEDED_FORMAL_RUNTIME_FAULT`.

The interrupted fix3 formal output and the interrupted fix3 Comparison B panels
are diagnostic evidence only. They must not be completed in place, pooled with a
later candidate, or used for win-rate selection.

## Reproduced fault shape

Both faults occurred after a successful Alakazam evolution transaction,
Telepathic Swap, and Powerful Hand KO:

- Marnie seed base `202608510`, seat `1`, game `2`: six attached Energy;
- Marnie seed base `202608520`, seat `0`, game `6`: two attached Energy.

Damage, attack identity, target identity, action-count transitions, prize arity,
and nonterminal prompt shape all matched the strict transaction model. The only
shared mismatch was the ordered KO movement of attached Energy.

The engine emits the KO stack as:

1. Active Pokémon;
2. `preEvolution` in reverse order;
3. `energyCards` in reverse order;
4. tools in their existing order.

Fix3 already modeled item 2 correctly but modeled item 3 in forward order.

## Authorized fix4 change

Destination:

`alakazam_staged_20260729/versions/alakazam_newdeck_v1_package_runtime_certified_fix4`

Only `_attack_target_moves()` in `planner_deck_adaptation_v1.py` may change
behaviorally:

```python
for card in reversed(target.energyCards)
```

The verifier remains ordered and fail-closed. It must not accept both orders,
compare multisets, weaken public-discard equality, weaken MOVE_CARD-log equality,
or relax damage, prize, ownership, prompt, or action-count checks. Active,
pre-evolution, and tool ordering remain unchanged.

Regression fixtures must cover:

- a six-Energy two-prize KO in reverse Energy order;
- a two-Energy one-prize KO in reverse Energy order;
- rejection of the two-Energy forward order;
- preservation of forward tool order and rejection of tool-order mutation;
- the pre-existing reverse-preEvolution positive and forward-order negative.

## Frozen fix4 identity

- Policy closure file count: `33`
- Policy closure SHA-256:
  `48EEF98CD6054882FFB19E45D061AE90C739E5415A0F3F028A7981669589CA79`
- Planner SHA-256:
  `04DA4A797D48CFA3786778F9EAE2690780152417AB12F22CF5ADE65A151A3EA2`
- Runtime-test SHA-256:
  `CF85E855CA53CF40ED09E904CC8F12CD36FDD335BA9DFF80C81225FD75D9B632`
- Raw deck SHA-256:
  `F598F5E578D0440C96DC0492EAECF2E19739B7A23225BE57114A724EF7D0FB94`
- Normalized deck hash:
  `4414e8995e50c7a00d4b6aa7d9229f63c1dff5261643ec7cd86c4e329113ed69`
- Unit tests: `134/134`
- Candidate-function AST equality versus fix3: true
- Priority-chain AST equality versus fix3: true
- Agent AST equality versus fix3: true

## Fresh-output rule and hard gate

Use only new fix4 destinations:

- smoke:
  `alakazam_staged_20260729/metrics/smoke_v1_runtime_certified_fix4_seed202608500`
- formal safety suite:
  `alakazam_staged_20260729/metrics/formal_v1_runtime_certified_fix4_7opp_50seed`
- formal safety summary:
  `alakazam_staged_20260729/metrics/formal_v1_runtime_certified_fix4_7opp_50seed_summary`
- Comparison B panels:
  `alakazam_staged_20260729/evaluations/comparison_b_runtime_certified_fix4_panels`
- Comparison B combined:
  `alakazam_staged_20260729/evaluations/comparison_b_runtime_certified_fix4_combined`

The 140-game smoke must pass first. Because fix3 smoke did not expose the
multi-Energy shape, the complete 700-game fix4 formal safety suite must then
finish with zero transaction abort/fault, invalid action, exception, timeout,
max-step, unknown removed-card route, and candidate-owned fallback before any
Comparison B win-rate evaluation begins.
