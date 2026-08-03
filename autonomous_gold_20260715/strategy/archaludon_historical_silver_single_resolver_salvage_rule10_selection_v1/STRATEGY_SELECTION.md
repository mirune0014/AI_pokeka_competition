# Rule 10 strategy selection

## Frozen inputs

- Requirements SHA-256: `24282FA6A0EF91D936E2E5B2AAD725904EF3223FCFBDF9BEEA16C62C726038C9`.
- Accepted Rule 5 parent `main.py`: `D966E455E5110F9D5616195AEAAC8663E6A92F310DAFC4B7F79E4D37149A9C62`.
- Historical-Silver deck: `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`.
- Only Rules 1, 4, and 5 are inherited. Rules 2, 3, 6, 7, 8, and 9 are not parents.

## Selected hypothesis

`EXACT_PROACTIVE_FULL_METAL_LAB_EXCHANGE_V1`

Implement directly from accepted Rule 5. Do not copy or inherit the prior
cumulative Full Metal Lab candidate.

At an owner-free exact MAIN boundary, insert Full Metal Lab before the parent's
sole exact payable nonterminal attack only when a complete two-world public
comparison proves all of the following:

1. `KEEP` and `PLAY_FML` use the identical attacker, target, attack ID, and
   payment.
2. Current damage, KO, Prizes, finish status, and exact attacker/successor/
   backup readiness are identical.
3. FML strictly improves the worst supported immediate public reply by changing
   at least one payable reply from KO to survival, or by removing an exact
   terminal/board-out reply.
4. Every supported immediate reply is enumerated, and no opposing Pokemon gains
   an equal-or-greater survival, Prize, next-KO, or attack-continuity benefit.
5. The stored attack remains uniquely legal and payable after FML resolves.

This is a one-reply public exchange certificate, not a general simulator. Only
fixed numeric damage with empty effect text and already exact Rule 5 attack
texts may be admitted. Unknown attack text, modifiers, Tools, Special Energy,
Abilities, conditions, payment, promotion, or next-attack consequences make
the comparison `UNKNOWN`.

## Exact entry gates

All are mandatory:

- Live game; exact ordinary MAIN; `min=max=1`; no effect, context card, deck
  selection, looking state, setup, or prior attack log.
- Sole owner empty.
- Effective Rule 5 action is one uniquely bound registered ATTACK.
- That attack is payable now and nonterminal by Prize and board-out.
- Rule 1, Rule 4, Rule 5 exact win, and Rule 5 Boss behavior have declined.
  Rule 4's parent-Lillie FML materialization is outside Rule 10.
- Stadium is empty, `stadiumPlayed == False`, and exact FML metadata matches.
- Exactly one physical FML PLAY is selected deterministically. Lowest serial is
  allowed only when each physical copy has one unique semantic binding;
  duplicate bindings fail closed.
- Complete public fingerprints exist for both boards, Energy, HP, damage,
  Weakness, Resistance, Prize values, statuses, Tools, Abilities, and current
  or forced Active identities.
- Every immediately payable opposing reply after the stored attack is
  supported by the bounded oracle.
- `KEEP` and `PLAY_FML` current certificates are identical in damage, KO,
  Prize take, terminal status, payable next attack, and ready-backup set.
- Worst public return strictly improves under FML, while the opponent's current
  and certified next exchange does not improve.
- Any tie, incomparability, multiple nondominated replies, or missing field
  returns exact Rule 5.

No Boss targeting, attack holding, END synthesis, comeback ordering,
hidden-hand inference, future draw, multistep search, or opponent-specific rule
is permitted.

## Precedence

1. Reset/result/deck handling.
2. Continuation of the sole Rule 4/5/10 owner.
3. Rule 1 setup.
4. Rule 5 exact current win.
5. Rule 4 materialization.
6. Rule 5 unique higher-Prize Boss transaction.
7. Rule 10 proactive FML exchange, only when effective Rule 5 remains the sole
   exact attack.
8. Exact Rule 5 fallback.

Rule 10 cannot delay an exact win, preempt Lillie materialization, or replace
an accepted Boss conversion.

## Proposal and transaction

Every proposal contains only `rule_id`, `action`, `category`, `purpose`,
`exact_proof`, and `transaction`.

- `category = DETERMINISTIC_SAME_ATTACK_PRESERVATION`
- `purpose = EXACT_FML_PUBLIC_RETURN_KO_OR_BOARDOUT_PREVENTION`

Lifecycle:

```text
EMPTY
-> FML_EMITTED
-> ATTACK_EMITTED
-> CLEAR
```

`FML_EMITTED` stores seat, turn/action count, FML ref, hand/stadium ledger,
complete public fingerprint, attacker/target fingerprints, attack ID/payment,
both world certificates, reply set, and semantic option signature.

- Identical retry rebinds the same FML role without advancing.
- The next callback must prove FML left hand, became the sole Stadium,
  `stadiumPlayed` changed correctly, all other board/resources match, and the
  same attack comparison still passes.
- Rebind and emit only the stored attack; never reuse a stored option index.
- Identical attack-prompt retry rebinds without advancing.
- Confirm the matching attack log, then clear before passing Prize, promotion,
  result, or after-attack callbacks to Rule 5.
- Any stale turn/seat, owner collision, receipt mismatch, changed
  attack/target/payment, ambiguity, or failed re-proof clears ownership and
  returns that callback's once-computed Rule 5 action.
- A natural post-spend abort is a candidate fault.

## Focused fixtures

Both seats must cover:

- return KO to survival with identical current attack result;
- exact terminal/sole-board-out reply removal;
- supported forced-promotion and non-KO reply forms;
- Weakness, Resistance, then FML damage order;
- every admitted Rule 5 attack/effect path;
- full FML to same-attack lifecycle;
- option reversal, FML serial remapping, identical retry, and physical-copy
  determinism.

Required negatives include terminal current attack; any current damage, KO,
Prize, or next-Prize change; saving an opposing Pokemon or equally improving
opponent survival; successor/backup readiness regression; no return threshold
change; parent Lillie, Boss, nonattack, multiple attacks, or owner present;
occupied or unknown Stadium; Tool, Special Energy, condition, Ability, attack
text, damage-counter effect, or payment uncertainty; reply/promotion ambiguity;
and every stale or post-spend mismatch.

All inherited Rule 1/4/5 fixtures, compile/import, legal 60/ACE1, final loader,
one parent call, one resolver, one owner, scorer/chooser byte identity, and
both-seat smoke must pass.

## Shadow and activity gates

The only allowed first-difference class is:

`parent same registered nonterminal ATTACK -> candidate bound FML PLAY`

Each difference must prove identical current attack outcome, strict public
return improvement, no opponent protection, and subsequent emission of the
same attack.

Any FML-before-Lillie, Boss, END, different attack, unsupported reply,
unexplained difference, invalid action, exception, or owner fault rejects.

Require at least one complete non-fixture `FML -> same attack` transaction in
replay-compatible evidence or fixed160. Zero starts, or starts without natural
completion, is `DEFER-DORMANT`; do not widen or integrate.

## Fixed160 adoption gates

Against exact Rule 5 on the frozen 160 keys:

- candidate at least `100/160`;
- paired gains at least paired regressions;
- Historical-Silver anchor non-worse;
- no opponent-seat cell delta of `-3` or worse;
- no aggregate seat delta of `-2` or worse;
- exact schedule and duplicate equality;
- zero action errors, exceptions, start faults, max-step hits, owner faults, or
  natural aborts;
- zero clearly harmful or unclassified first differences;
- every completed mechanism matches the intended public return-KO/board-out
  proof.

Passing numerics alone is insufficient. A harmful mechanism rejects. A neutral
pass supports only safe-neutral Rule 10 adoption, not a strength claim.

## Main risks

- Symmetric FML may protect the opponent or delay the next Prize. The
  identical-current-outcome and no-opponent-protection gates are mandatory.
- Opponent reply coverage may be too sparse. That warrants dormancy, not a
  broader effect engine.
- Spending FML creates an irreversible callback boundary, so receipt/re-proof
  ownership is the main execution risk.
- Inherited Rule 4/Silver FML choices remain outside this rule; Rule 10 makes no
  claim that all parent FML plays are optimal.

