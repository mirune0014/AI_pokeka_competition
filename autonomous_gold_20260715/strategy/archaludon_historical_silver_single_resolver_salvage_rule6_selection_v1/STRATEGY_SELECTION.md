# Rule 6 strategy selection

Date: 2026-08-03 JST

Decision: **SELECT**

Rule ID: `PARENT_POKE_PAD_EMPTY_BENCH_DURALUDON_ONE_METAL_READY_SUCCESSOR_TRANSACTION_V1`

## Selected hypothesis

Target exactly one role: `DURALUDON_ONE_METAL_READY_SUCCESSOR`.

Only when the once-called accepted Silver parent already selects Poké Pad `1152`, own the route that searches Duraludon `169`, places that same physical card onto an empty Bench, and attaches one visible Basic Metal `8` so Hammer In `223` is payable. Cinderace `666`, non-ex Archaludon `840`, Turbo Flare, and evolution search are outside Rule 6.

This is the smallest complete path whose purpose can be proved from public state without assuming hidden deck contents or future draws.

## Frozen parent

- Parent: `autonomous_gold_20260715/candidates/archaludon_historical_silver_single_resolver_salvage_rule5_trial_v1`
- Parent `main.py` SHA-256: `D966E455E5110F9D5616195AEAAC8663E6A92F310DAFC4B7F79E4D37149A9C62`
- Deck SHA-256: `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`

Only candidate `main.py` may differ. The stored Silver parent, scorer, deck, runtime, and other package files remain byte-identical.

## Priority and structure

1. existing Rule 4/5/6 owner continuation;
2. Rule 1 setup;
3. Rule 5 exact terminal;
4. Rule 4 materialization;
5. Rule 5 Boss;
6. Rule 6 start;
7. exact Silver parent.

Add Rule 6 locally to the existing `agent`, `_resolve`, and shared `_materialization_owner`. Do not add an agent, resolver, wrapper, scorer, effect simulator, or second owner. Call the exact parent once per callback. UNKNOWN or conflict returns the current parent action.

## Activation

All conditions are required:

- unresolved normal MAIN, owner empty, and `minCount=maxCount=1`;
- parent action is one legal PLAY of the exact physical Poké Pad `1152`;
- Poké Pad name, text, and effect metadata match the frozen expectation;
- own Bench is exactly empty and has at least one slot;
- no Duraludon `169` is already in hand;
- `energyAttached == false`;
- hand contains at least one visible Basic Metal `8`; bind the lowest serial;
- the current Active has a legal Rule-5-registered attack option with exactly one distinct attack ID;
- Rule 5 terminal proof is false;
- all needed Active, hand, Bench, Energy, option, turn, and action-count data are exact;
- deck count is exact, but never infer that Duraludon remains in the deck.

If any proof fails, do not watch the Pad callback. Return the exact parent action.

Freeze seat, turn, action count, Pad reference and metadata digest, Active fingerprint, saved attack ID, empty-Bench facts, bound Metal serial, hand multiset, Duraludon/Hammer In metadata digest, and semantic option multiset.

## Transaction

```text
PAD_PLAY_EMITTED
-> PAD_TARGET_EMITTED
-> DURALUDON_BENCH_EMITTED
-> METAL_ATTACH_EMITTED
-> CLEAR_TO_CURRENT_PARENT
```

- `PAD_PLAY_EMITTED`: emit the parent's same Pad action; never change to another Pad.
- On the exact Pad `TO_HAND` callback, consider only Duraludon `169`.
- If multiple physical Duraludon cards are exposed, choose the lowest serial. Equivalent duplicate UI entries use the lowest position. Conflicting meanings for one serial fail closed.
- Confirm that exact serial reached hand. At the next MAIN, play that same Basic to the empty Bench.
- Confirm its Bench placement. At the next MAIN, attach the frozen lowest-serial Basic Metal to that Duraludon.
- Confirm the Metal moved from hand to that Pokémon and Hammer In `223` is now payable.
- Clear the owner and return the once-computed Silver action from the actual current state. Do not re-enter another rule in that callback.

Advance a stage only after the next callback publicly confirms the preceding action.

## Whiff

```text
PAD_PLAY_EMITTED
-> PAD_WHIFF_EMITTED
-> CLEAR_TO_CURRENT_PARENT
```

If Duraludon is absent from the exposed options and an empty selection is legal with `minCount=0`, return `[]`. Never substitute Cinderace or Archaludon `840`. An identical retry returns `[]` without advancing. After effect resolution, clear the owner and use the current-state parent action. If empty selection is illegal or the callback is malformed, clear and use the current parent.

## Duplicate, order, and rollback

- Rebind by serial, attack ID, and target serial; option order is never strategic.
- The same semantic prompt returns the same action and does not advance state.
- Conflicting duplicate semantics fail closed.
- Seat, turn, result, source, effect, action count, Active, saved current attack, Bench capacity, or hand-transition mismatch clears the owner.
- Never restore a pre-Pad snapshot after Pad was used.
- Never retain Rule 6 across turns.
- UNKNOWN, ambiguity, or owner conflict returns the exact current parent action.

## Focused fixtures

1. Complete both-seat path: Pad, Duraludon select, hand confirmation, empty-Bench placement, one Metal attachment, ready confirmation, parent continuation.
2. Duraludon absent with only Cinderace/`840`: legal empty whiff and next-MAIN parent recovery.
3. Identical retry and option permutation at every stage.
4. Multiple Duraludon cards choose lowest serial; equivalent duplicate UI chooses lowest position.
5. Conflicting duplicate, wrong effect/source, failed target movement, and failed attachment all fail closed.
6. Parent non-Pad, nonempty/full Bench, no Metal, attachment already used, or Duraludon already in hand do not start.
7. No current attack, multiple attack IDs, terminal attack, existing owner, and seat/turn/result changes do not start.
8. All Rule 1/4/5 tests remain passing.
9. Both-seat engine smoke has zero action errors and no max-step hit.

## Shadow classifications and rejection

Allowed first/action differences are only:

- `POKE_PAD_DURALUDON_TARGET`;
- `POKE_PAD_DURALUDON_BENCH`;
- `POKE_PAD_DURALUDON_READY_ATTACH`;
- `POKE_PAD_DURALUDON_WHIFF_EMPTY`.

Record Pad, target, and Metal serials, saved attack ID, stage, and parent/candidate semantic actions.

Reject for a non-Pad start, selecting a non-`169` target, losing the current attack, failing to complete Bench plus one-Metal readiness in the same turn after a successful search, stale/double owner, illegal action, exception, max-step, unclassified difference, clearly harmful first difference, fixed160 gains below regressions, or any cell three wins below the parent.

If shadow plus fixed160 contains zero Rule-6 natural starts or attributable action differences, do not widen. Record `DEFER-DORMANT` and exclude Rule 6 from the accepted parent. If natural starts occur but neither a whiff nor a ready completion is observed, record `REJECT` as an incomplete implementation.
