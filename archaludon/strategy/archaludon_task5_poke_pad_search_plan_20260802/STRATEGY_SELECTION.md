# Task 5 strategy selection: Poké Pad declared executable role transaction

Date: 2026-08-02 JST

Decision: **SELECT**

Rule ID: `PUBLIC_POKE_PAD_DECLARED_EXECUTABLE_ROLE_TRANSACTION_V1`

## Selected hypothesis

When the exact parent selects Poké Pad, declare one executable public-state role before playing it. Own the Pad play, reveal-dependent target selection, transition to hand, immediate placement or evolution, and atomic handoff to the existing attack/Energy planner as one transaction. If the declared target is absent, select no card when legal and return to the same-turn exact parent attack. Never substitute an unrelated revealed Pokémon.

The declaration is a role plus target card id. It never claims that a hidden target is in the deck. A physical target serial is bound only after the engine exposes it on the reveal callback.

## Verified constraints

- Exact parent `main.py` SHA-256: `CAF2C696AE9F6102C1A4A8E67649C309104064CAABF9643865BE766D91BDE8DD`
- Exact parent `deck.csv` SHA-256: `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`
- Root evidence SHA-256: `B799B11918C4414EE753172B7D4397B466A9DCD2B7BCBE42E26A2AD0F8038782`
- Poké Pad `1152` has exact registered text and four deck copies.
- Duraludon `169` is Basic and can be placed during MAIN.
- Non-ex Archaludon `840` is a Stage 1 Duraludon evolution with Coated Attack.
- Cinderace `666` is not Basic or Stage 1; Explosiveness is setup-only. Task 5 v1 must not treat a mid-game searched Cinderace as immediately placeable.
- The existing `_pfc_search_watch` is narrow: parent Pad, Active Duraludon, Bench zero, exact current attack; after reveal it considers only Duraludon and requires a visible ex, hand Metal, and discarded Metal before starting the old transaction.
- Task 4 precedence remains: exact terminal, existing owner, continuity hold, non-terminal attack.

## Implementation location and ownership

Implement inside the PFC layer and replace the old Pad watch; do not append a competing outer watch.

- Replace `_pfc_arm_pad_watch()` use in `_pfc_clear_state_choose()` with a Task 5 start path.
- Reuse `_pfc_transaction`, adding Task 5 sub-rule identity and dedicated stages.
- Dispatch Task 5 transactions at the beginning of `_pfc_resume_transaction()`.
- Keep `_pfc_search_watch` unused for the new candidate; old and new watches must never run together.
- Do not change Task 4, SAPT, Full Metal Lab, Turbo allocation, or same-Active attack-selection wrappers.
- Call the captured parent exactly once per callback.
- Never leave simultaneous PFC and PCRD/TSC owners when handing off.

## Activation

All conditions are required:

1. clear MAIN, unresolved game, and single-choice prompt;
2. exact parent action is a valid single PLAY of bound Poké Pad `1152`;
3. exact Pad id, unique public serial, hand membership, and registered text;
4. public deck count at least one, without assuming its contents;
5. exact Bench count/max/serials and remaining capacity;
6. exact terminal scan with zero terminal rows;
7. no owner before start and no competing owner armed by the parent;
8. exactly one admitted role can be declared from current public facts;
9. Task 5 itself never replaces a non-Pad parent action with Pad.

Unknown terminal or malformed public proof means no start.

## Role priority

### 1. `DURALUDON_EXECUTABLE_SUCCESSOR`

Highest priority when at least one of these is exact:

- Active Cinderace has payable Turbo Flare but no executable recipient;
- Bench is empty;
- Task 4's exact worst-public-reply proof gives zero executable backups.

Additional gates:

- a Bench slot remains;
- if a Duraludon is already directly playable from hand, do not spend Pad for a duplicate;
- for the Cinderace route, the virtual Duraludon is a legal Turbo recipient and the existing exact Turbo planner can reduce its attack deficit;
- otherwise, placement must retain the current exact attack and public hand/discard facts must expose a next-turn Hammer In, evolution, ordinary attachment, or equivalent executable successor route.

Owned sequence:

```text
PAD_PLAY
-> REVEAL_DURALUDON
-> DURALUDON_TO_HAND
-> BENCH_DURALUDON
-> exact existing Turbo/attack-plan handoff
-> ENERGY_TO_BOUND_DURALUDON when applicable
-> NEXT_ATTACKER_READY or parent continuation
```

### 2. `NONEX_COATED_ATTACK_CONVERSION`

Only when the Duraludon-successor role is unnecessary:

- exactly one public Duraludon can legally evolve this turn;
- a same-turn non-ex Archaludon `840` evolution and Coated Attack plan is exact;
- current attack access is not lost;
- the route gives at least one exact improvement: Prize/KO conversion, Basic-attack prevention, attacker survival, Prize exchange, or attack continuity;
- no Bench slot is consumed because this role evolves an existing Duraludon.

After reveal and hand confirmation, rebuild the exact evolution plan and hand off atomically to the existing `EVOLVE -> COATED_ATTACK` machinery. Do not duplicate attack or effect logic.

### Explicit rejection: Cinderace

`CINDERACE_FREE_RETREAT_ENGINE` is not admitted in v1. If only Cinderace is revealed for a Duraludon or non-ex role, treat the declared target as absent. It may be added only after a real engine observation proves a legal same-serial mid-game placement route and a fixture completes the continuation.

## Transaction stages

Recommended stages:

```text
PAD_PLAY_EMITTED
PAD_TARGET_EMITTED
PAD_WHIFF_EMITTED
PAD_TARGET_IN_HAND
PAD_DURALUDON_BENCH_EMITTED
PAD_ROLE_HANDOFF
COMPLETE / ROLLBACK
```

Freeze at start:

- seat, turn, action count;
- Pad id/serial;
- declared role and target card id;
- Bench count/max and serials;
- Active/opponent fingerprints;
- terminal, backup, current-attack, and role proof;
- exact fallback attack semantic;
- order-independent callback fingerprint.

## Reveal and target selection

Require `TO_HAND`, matching effect id/serial, matching seat/turn/action transition, Pad play/discard transition, and still-valid capacity/role proof.

- Consider only the declared target card id.
- Different physical serials: select the lowest serial.
- Repeated UI entries for the same semantic card: use the lowest position.
- Conflicting meanings for the same physical serial: rollback.
- Never use option order as a strategic tie-break.

### Target absent

- If `minCount == 0` and `[]` is legal, return `[]` and persist `PAD_WHIFF_EMITTED`.
- An identical retry returns the same empty action without stage advancement.
- Do not select another role.
- At the next MAIN, rescan terminal and rebind the saved exact fallback attack. Hand off to the existing attack planner only if still exact.
- If an empty selection is not legal or the callback is malformed, clear and use the current parent's legal action.

### Duraludon present

1. select the bound Duraludon serial;
2. confirm that serial moved to hand;
3. recheck capacity and bind its Basic PLAY;
4. confirm placement by board/log transition;
5. for Cinderace, build an exact Turbo allocation containing that serial;
6. atomically hand off to the existing owner, otherwise clear and use the current parent.

### Non-ex Archaludon present

1. select the bound Archaludon serial;
2. confirm transition to hand;
3. rebuild the declared target-Duraludon evolution and Coated plan;
4. hand off atomically only if the exact purpose remains.

## Duplicate, rollback, and fail-closed behavior

- Duplicate identity uses public state plus an option-order-independent semantic multiset.
- Identical retries rebind the saved semantic action to current positions without advancing.
- Clear on seat/turn/result/effect/source/action-count/capacity/transition/log/proof discontinuity.
- After Pad is irreversibly used, never restore a past snapshot; compute the legal parent from the current observation.
- Never retain the transaction across turns.
- Malformed hand, Bench, serial, metadata, option, or owner state fails to the exact current parent.

## Required focused fixtures

1. Complete Duraludon path in both seats: Pad, reveal, select, hand, Bench, Turbo, Energy select, target, completion.
2. Identical duplicate at every stage.
3. Option permutation at every callback.
4. Multiple target serials select the lowest serial.
5. Equivalent duplicate UI for one physical serial remains deterministic.
6. Conflicting duplicate semantics rollback.
7. Target-absent empty selection followed by the exact same-turn attack fallback.
8. Cinderace-only reveal is not selected.
9. Complete non-ex path: Pad, `840`, hand, exact evolution, Coated Attack.
10. Non-ex route with no exact purpose does not start.
11. Bench full before start and capacity lost before placement.
12. Last Bench slot with and without executable role proof.
13. Exact terminal, unknown terminal, existing owner before/after parent, and callback owner conflicts.
14. Target/effect/source mismatch, skipped action count, seat/turn/result change, malformed metadata.
15. Failed handoff leaves no double owner.
16. Episode 89347400 has no Task 5-specific difference.
17. Inspect all Task 5 first differences in 89285518 and 89282820.

## Implementation safety gate

- only candidate `main.py` may differ from the exact parent package;
- all focused fixtures pass in both seats with deterministic valid actions;
- every admitted role completes an engine-shaped multi-callback path;
- compile/import, final callable, legal 60 cards and one ACE SPEC, and cache-free tree pass;
- every replay first difference is explained;
- both-seat exact-engine smoke has zero action errors and no max-step hit;
- stale/double owners are zero;
- natural Cinderace setup-only violations are zero.

This is an implementation-safety gate, not a broad win-rate claim.
