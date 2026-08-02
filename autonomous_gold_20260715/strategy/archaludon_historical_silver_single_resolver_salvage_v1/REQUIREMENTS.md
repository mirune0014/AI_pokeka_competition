# Historical-Silver single-resolver salvage v1

Status: FROZEN
Date: 2026-08-03 JST

## Objective

Reintegrate only safe, useful Task 1-9 tactics directly onto exact
Historical-Silver without changing its deck, scorer, chooser, or public
`agent(obs_dict) -> list[int]` interface.

## Frozen baseline

- Source: `analysis_outputs/reference_agents/historical_silver_archaludon_54495224`
- `main.py` SHA-256: `F4B578453C9D953BE94885144DD50E05DBA4510DF3340BE27ADE07495896046E`
- `deck.csv` SHA-256: `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`
- Candidate: `autonomous_gold_20260715/candidates/archaludon_historical_silver_single_resolver_salvage_v1`
- Evidence: `autonomous_gold_20260715/implementation/archaludon_historical_silver_single_resolver_salvage_v1`

Existing source, candidates, packages, evaluations, and reports are read-only
inputs. All new work remains below `autonomous_gold_20260715`.

## Non-negotiable architecture

1. Historical-Silver is the only executable parent and is called exactly once
   per callback.
2. `score_option` and `choose_options` remain byte-identical.
3. There is one final `agent`, one resolver, and at most one active transaction
   owner.
4. A proposal contains only `rule_id`, `action`, `category`, `purpose`,
   `exact_proof`, and `transaction`.
5. Only exact public-information proofs may override the parent. Unknown,
   ambiguous, equal-priority, effect-incomplete, or owner-conflicting states
   return the exact Historical-Silver action.
6. Do not implement `SECURED_ATTACK_NOW`, new broad scoring, hidden-hand
   inference, opponent-policy proxies, generic lookahead, or a generic effect
   simulator.

## Resolver order

1. Valid continuation of the active transaction.
2. Exact terminal win.
3. Exact board-out prevention before a nonterminal attack.
4. Deterministic play/evolve/recover/attach that preserves the same attack.
5. Exact Prize improvement or exact threat removal.
6. Complete search/resource transaction.
7. Strict same-Active attack dominance.
8. Exact Historical-Silver action.

## Sequential rule order

Each rule is implemented alone from the last accepted parent. A failed rule is
removed; no compensating rule may be stacked onto it.

1. Exactly-one Duraludon setup.
2. Pre-attack successor and board continuity.
3. Declared-complete Ultra Ball route.
4. Deterministic materialization before Lillie; never synthesize END to hold.
5. Exact terminal/Boss Prize conversion as one transaction.
6. Declared-complete Poke Pad route.
7. Turbo Flare Energy concentration to one executable successor, then one
   backup; no overfill, empty-Bench expectation, or incomplete spreading.
8. Strict same-Active attack dominance with complete cost/effect proof.
9. Pokegear only for a complete Boss/Explorer/Lillie purpose.
10. Full Metal Lab and KO/comeback branches only with exact public Prize,
    survival, and attack-continuity improvement.

No natural activation in focused shadow plus fixed160 is not permission to
widen a rule. Preserve its evidence separately and do not merge it into the
accepted parent.

## Per-rule validation and adoption

- Compile/import, exact legal 60-card deck, exactly one ACE SPEC, last-callable
  loader behavior.
- Both seats, option-order permutations, identical prompt retry, and complete
  multi-callback ownership fixtures.
- Replay shadow: zero invalid actions/exceptions and every first difference
  attributable to the one candidate rule.
- Fixed160: first 20 frozen fixed760 seeds, both seats, Historical-Silver
  mirror, Arch Peak, Alakazam, and Marnie.
- Adopt only with zero known clearly harmful first differences, paired gains at
  least paired regressions, and no seat/opponent at least three wins below the
  exact parent.

One accepted rule equals one explicit commit and push. Rejected candidates are
not parents and are not repaired by broadening or stacking another rule.

## Final fixed760 gate

- Exact frozen 760 keys, both seats and identical seeds.
- Zero action error, exception, start fault, max-step, or duplicate mismatch.
- At least `478/760`, paired gains at least regressions.
- Neither seat more than two wins below Silver.
- Historical-Silver mirror at least `98/200`.
- No 80-game adjacent opponent more than four wins below Silver.
- Inspect and classify the first policy difference for every discordant result.
- Any clear harmful mechanism rejects the final candidate regardless of wins.
- Independent Sol-Ultra numerical evaluation and root recomputation must agree.

`478/760` establishes non-destruction. A strength claim additionally requires
at least `486/760` with neither seat worse.

## Scope exclusions

No deck change, Kaggle write, Alakazam port, RL, learned ranker, behavior
cloning, Gold-action imitation, or replay-derived opponent proxy belongs to
this implementation.

## Anti-overengineering rule

Use only focused fixtures, replay shadow, one fixed160 per implemented rule,
and one final fixed760. Add another diagnostic only when a named required gate
cannot be decided from those artifacts. Amendments are new versioned files;
this document is immutable after freeze.
