# Root-verified evidence: Task 6 Ultra Ball discard and search plan

Date: 2026-08-02 JST

## Frozen parent

- Parent candidate:
  `archaludon_public_poke_pad_declared_executable_role_transaction_v1`
- Parent `main.py` SHA-256:
  `2B23D3AFC63A5BDC4BC7765CE1656725ED01890D161E3D23DCC672BE7FCCCFF4`
- Deck SHA-256:
  `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`
- Deck Pokémon: Duraludon 169 x4, Archaludon ex 190 x4,
  Cinderace 666 x4, non-ex Archaludon 840 x2.

Task 5 is accepted as the implementation parent. Task 6 may replace only the
PFC Ultra Ball planning and callback lifecycle. It must not rewrite the Task 5
Poké Pad transaction, Task 4 successor veto, Turbo allocation, attack choice,
or deck.

## Current Ultra Ball behavior and limitations

The current PFC Ultra Ball path is `_pfc_build_ultra_formation()` plus
`_pfc_safe_ultra_costs()` and the `ULTRA_*` stages in
`_pfc_resume_transaction()`.

Root source inspection established:

1. The path searches only Duraludon.
2. It requires an exposed physical Duraludon serial before Ultra Ball is
   played. This is stricter than declaring a card role and binding a serial on
   the legal reveal callback.
3. It begins only when the cumulative parent selected ATTACH or ATTACK and the
   current attack route is exact.
4. It hard-protects every Duraludon, both Archaludon identities, every Boss,
   Night Stretcher and Hero's Cape, regardless of whether that physical card is
   needed by the selected route.
5. It always reserves one hand Metal and refuses to start with no spare Metal.
6. It admits discard cards only from a short whitelist: Cinderace, duplicate
   Stadium/search item/draw Supporter, or surplus Metal. If fewer than two
   whitelist cards exist, it refuses the whole plan even when another legal
   pair is clearly less costly.
7. The old search callback has no declared-role empty-result continuation; an
   absent target clears the transaction and returns the generic parent action.
8. Generic Ultra Ball scoring outside the PFC route still chooses each discard
   and each search target independently.

These are implementation facts, not estimates of win-rate impact.

## Root-replayed failure examples

The checked inspector was run with the frozen Task 5 parent in the recorded
target seat.

### Episode 89280661

- Replay SHA-256:
  `38D317186A3C9E64C1469AE3B852C13141B1F7BA4E5ECD93C1D5AAD23565983B`
- Step 7 hand after selecting one Ultra Ball contained three more Ultra Balls,
  Full Metal Lab, Lillie, Explorer and Archaludon ex; Active was Cinderace and
  Bench was empty.
- Step 8 discarded Lillie plus Explorer because each received a larger local
  discard score than duplicate Ultra Ball.
- Step 9 correctly searched Duraludon.

The search target was coherent, but the independent discard scorer destroyed
both draw/selection Supporters while three redundant Ultra Ball copies were
available. A route-aware pair selector should retain the Supporters and consume
redundant search copies.

### Episode 89291523

- Replay SHA-256:
  `1F180D8C66ABA57B000D6D38E0EA3FDD5B1EE26F491EEEAFFE9B4B04478E84ED`
- At step 104 the hand contained Lillie, non-ex Archaludon, Metal, two Boss,
  two Archaludon ex and Ultra Ball; Active and Bench were already Archaludon ex.
- Ultra Ball was selected only by the generic `fuel Alloy` score.
- Step 105 discarded the Metal and one Boss.
- Step 106 searched a second non-ex Archaludon although one was already in
  hand and no declared same-turn Coated Attack role existed.

The play, cost and target were three unrelated local decisions. Task 6 should
decline to own or initiate Ultra Ball when no complete role improves the turn;
if an admitted Alloy/evolution role exists, its exact Metal demand and target
must be fixed before the two costs are selected.

### Episode 89347400 regression anchor

- Replay SHA-256:
  `F389CF9FD13BE52D155A3FA7B9FF5750358F3016848640236D4E2562DA1053A4`
- Task 4 restored the parent Ultra Ball at step 19 instead of allowing Turbo
  Flare to end the turn with Bench 0.
- The complete replay state had three Duraludon in deck and one in Prize, so the
  real game could complete `Ultra Ball -> Duraludon -> Bench -> Turbo Flare`.

This episode is the required positive callback anchor. Task 6 must own the two
discards, Duraludon reveal, placement and Turbo handoff without changing the
other ten canonical decisions.

## Required design direction

Task 6 must choose a complete executable role before Ultra Ball play, enumerate
all legal physical discard pairs, reject pairs that break the selected role or
a higher-priority terminal/continuity route, and rank the remaining pairs by
opportunity cost. A fixed global card penalty is insufficient.

At minimum the selected strategy must decide whether to admit:

- Basic Duraludon successor formation;
- Archaludon ex evolution plus Assemble Alloy / current attack conversion;
- non-ex Archaludon only for an exact same-turn Coated Attack conversion;
- no-purpose hold/return-to-parent behavior.

The strategy must distinguish productive Metal discard for a certified
Assemble Alloy route from destructive loss of the last Metal needed for hand
attachment or Turbo continuity. It must protect Boss, recovery, evolution,
Supporter, Stadium and Tool only when their physical copy has a concrete role,
not merely because of card identity.

### Controlling user amendment: exact Alloy fuel cap

Do not reward a hand Metal discard merely because an Assemble Alloy route
exists. For the exact same-turn route, compute:

```text
productive_metal_cap = max(
    0,
    min(2, exact_alloy_attachment_need) - usable_public_discard_metal,
)
```

- With 0 usable discard Metal and exact need 2, at most 2 hand Metal may receive
  productive-cost credit.
- With 1 usable discard Metal and exact need 2, at most 1 may receive credit.
- With 2 or more usable discard Metal, the productive cap is 0.
- If the planned attacker needs only 1 Alloy attachment, the cap is at most 1.
- Metal bound to manual attachment, Turbo completion or next-attack continuity
  remains protected.

Metal above this cap is an ordinary resource, not `Alloy fuel`. It may be
discarded only if it is still the least costly card in an otherwise safe pair.
If no safe pair exists, Task 6 must not start or own Ultra Ball.

The cap is not an automatic instruction to discard that many Metal. Enumerate
the complete energy route for every discard pair:

```text
attached_now
+ exact Alloy attachments available after the Ultra Ball costs
+ a retained-hand manual attachment, when the turn attachment is unused
```

Example: the attacker has 1 Energy, discard has 1 Metal, hand has 1 Metal and
the attack needs 3. Both `discard Metal -> Alloy 2` and
`retain Metal -> Alloy 1 -> manual attach 1` complete the attack. The planner
must compare the opportunity cost of both complete routes. It should retain the
Metal when two lower-cost redundant cards exist, but may discard and recover it
through Alloy when the alternative pair would consume a route-bound Boss,
evolution, recovery or other higher-value physical card. A used manual
attachment and competing attachment target must be part of this recomputation.

Unknown deck contents must not be invented. The role and target card id are
declared before play; a physical target serial is bound only on the legal search
reveal. Duplicate callbacks and option permutations must be deterministic.
