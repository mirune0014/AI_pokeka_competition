# Rule 3 Ultra Ball transaction repair amendment v2

Status: CONTROLLING FOR RULE 3 REPAIR ONLY
Date: 2026-08-03 JST

This amendment overrides only the prior rejection/failure handling for Rule 3.
Rules 1, 4, and 5, the Historical-Silver scorer, the deck, and every other
deferred or rejected rule remain unchanged.

## Frozen parent and destination

- Parent: `autonomous_gold_20260715/final/archaludon_historical_silver_single_resolver_salvage_v1`
- Parent `main.py` SHA-256: `D966E455E5110F9D5616195AEAAC8663E6A92F310DAFC4B7F79E4D37149A9C62`
- Deck SHA-256: `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`
- Failed Rule 3 helper SHA-256: `2015A4E589D2AE428A151AF50520C160CED7E1B1926D5599A2B35EB0CC6CEA61`
- New candidate: `autonomous_gold_20260715/candidates/archaludon_historical_silver_single_resolver_salvage_rule3_repair_v2`
- New evidence: `autonomous_gold_20260715/implementation/archaludon_historical_silver_single_resolver_salvage_rule3_repair_v2`

## Root-confirmed failure mechanism

The failed natural start was Arch Peak, seat 0, seed `271958318`.

- Ultra Ball began on global turn 2, which was seat 0's first own turn.
- The Active setup Duraludon reported `appearThisTurn=False`, but the game
  correctly offered no `EVOLVE` option because a player cannot evolve on their
  first turn.
- The old precondition checked only the Active's `appearThisTurn` flag and
  omitted the first-own-turn evolution prohibition.
- After searching, the old owner released to Silver, although Ultra Ball had
  already changed the physical deck order.
- The old search callback also ignored Silver's same-card physical search
  choice and selected the lowest serial independently.

Diagnostic trace:
`autonomous_gold_20260715/implementation/archaludon_historical_silver_rule3_repair_v2/diagnostic_original_seed271958318/traces/game_0000.jsonl`
SHA-256: `7D42D54F76BB7F193E2C80007808F52EB4EBE235C6260DC18499EBD780DD582B`

## Required repair

1. Keep exactly the Rule 3 declared-complete Ultra Ball routes. Do not add or
   alter any unrelated tactic.
2. The Active-Duraludon-to-Archaludon-ex route must not start on either
   player's first own turn. In the checked engine, require exact global
   `current.turn >= 3` in addition to `appearThisTurn=False`.
3. At the Ultra Ball search prompt, if the once-called Silver parent selects a
   unique physical copy of the required target card, preserve that exact copy.
   Only use deterministic serial tie-breaking when the parent selects a
   different card identity.
4. After search, rebind from the actual card now in hand and the actual legal
   `EVOLVE` option to the unchanged Duraludon destination. Do not assume that a
   deck-option position remains valid.
5. The single shared resolver and single shared transaction owner must own the
   complete sequence: Ultra Ball, two discards, search, evolution, Assemble
   Alloy activation, exact Energy selection and targets, optional manual
   attachment, and the preserved attack.
6. An irreversible Rule 3 start is a correctness commitment. Focused and
   natural-engine verification must demonstrate that every supported start
   reaches its declared terminal attack unless the game itself ends. A missing
   post-search evolution option is a test failure, not a normal successful
   fallback.
7. Rules 1, 4, and 5 retain their exact behavior and priority. Rule 3 may start
   only when no owner is active and the higher-priority exact-win,
   materialization, or Boss route did not start.
8. Preserve semantic duplicate retries and option-order rebinding. Call the
   Historical-Silver parent exactly once per callback.

## Required verification

- Reproduce seed `271958318` and prove Rule 3 no longer starts on the illegal
  first-turn evolution route; its trace must remain parent-identical through
  the former Rule 3 first difference.
- Run full multi-callback focused fixtures for both seats, all Energy states
  covered by the original contract, duplicate prompts, and option order
  permutations.
- Run at least one checked full-engine transaction in each seat that reaches
  the immediate declared attack. If the frozen 160 schedule does not supply
  both, use a deterministic seed search only to find natural coverage; do not
  broaden the rule.
- Then run the exact fixed160 schedule against this amendment's frozen parent.
  Require zero invalid actions, exceptions, max-step hits, duplicate mismatch,
  and irreversible aborts; paired gains must be at least regressions, with no
  seat or opponent three wins below the parent.
- Inspect every first difference. A Rule 3 start that does not complete is a
  rejection of the implementation and must be repaired and rerun, not used to
  reject the Ultra Ball strategy itself.

