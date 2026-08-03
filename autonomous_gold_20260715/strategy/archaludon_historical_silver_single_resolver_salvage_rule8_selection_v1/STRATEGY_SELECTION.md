# Rule 8 Strategy Selection

## Frozen inputs

- Requirements SHA-256: `24282FA6A0EF91D936E2E5B2AAD725904EF3223FCFBDF9BEEA16C62C726038C9`.
- Accepted Rule 5 parent `main.py` SHA-256: `D966E455E5110F9D5616195AEAAC8663E6A92F310DAFC4B7F79E4D37149A9C62`.
- Historical-Silver deck SHA-256: `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`.
- Rule 7 is rejected and must not be inherited.

## Selected hypothesis

`PUBLIC_EXACT_SAME_ACTIVE_ATTACK_DOMINANCE_V1`

On a clear ordinary `MAIN` callback, when the accepted parent selects Hammer In
(`223`) from Duraludon (`169`), replace it with Raging Hammer (`224`) only when
both attacks are legal on the same uniquely bound Active and the complete public
outcome proves that `224` strictly Pareto-dominates `223`.

This is the only supported attack pair. No generic attack simulator, score,
effect registry expansion, transaction owner, or future-state projection is
allowed.

## Exact activation contract

All conditions are required:

1. No transaction owner is active and the callback is a clear ordinary `MAIN`.
2. The once-called Rule 5 parent action is one uniquely bound `ATTACK 223`.
3. Own Active is exactly one Duraludon (`169`) with a unique valid seat/serial
   binding; opponent Active is also uniquely bound.
4. Both `223` and `224` occur exactly once among the current legal options for
   that same Active. Option positions are not identity.
5. The parent card database exactly matches the frozen printed metadata for both
   attacks: name, text, printed damage, and Energy cost.
6. Public board data is complete: current damage counters, HP, Weakness,
   Resistance, Stadium, Tool, Energy, prize values, and all effect fields used
   by the comparison are known and internally consistent.
7. Both attacks have no recoil, self-damage, Energy discard or consumption, or
   additional side effect. A metadata/effect mismatch is UNKNOWN.
8. For the unchanged opponent Active, exact final damage, KO status, and prizes
   taken are computed for both attacks using only already-audited Rule 5 damage
   helpers. `224` must be no worse in every field and strictly better in at
   least one of final damage, KO, or prizes taken.
9. The two attacks must not differ in any other known purpose or resource
   consequence. Ties, unknowns, malformed options, unsupported modifiers, or
   effect disagreement return the exact Rule 5 action.

The proposal contains only `rule_id`, semantic `action`, `category`, `purpose`,
`exact_proof`, and `transaction=None`. It must be resolved at fixed priority 7,
after all active transactions, exact wins, board continuity, attack-preserving
setup, prize/threat conversions, and complete search/resource routes.

## Semantic binding and duplicates

- Bind by seat, Active card ID/serial, target card ID/serial, and attack ID.
- Reordered options must return the same semantic attack.
- An identical prompt retry must return the same semantic action without state
  advancement.
- Duplicate serials, duplicate semantic attack options, seat/turn drift, or an
  active owner return the exact Rule 5 action.
- The rule is stateless and creates no transaction owner.

## Focused fixtures

Positive fixtures, in both seats:

- Damaged Duraludon where both attacks are legal and `224` does greater exact
  non-KO damage.
- A state where `223` does not KO and `224` exactly KOs.
- A state where the KO increases exact prizes taken.
- Each positive with option order reversed and an identical prompt retry.

Negative fixtures:

- Parent does not select `223`; Active is not Duraludon; one attack is absent;
  either attack occurs more than once; or the attacks bind to different Active
  identities.
- Zero-damage Duraludon where outcomes tie.
- Unknown or mismatching metadata, Tool, Stadium, modifier, Weakness,
  Resistance, Energy, recoil, discard, or secondary effect.
- Any live transaction owner, terminal Rule 5 override, malformed prompt, or
  unsupported purpose difference.

All negatives must be byte-equivalent to the Rule 5 action.

## Shadow and fixed160 gates

Every first difference must be exactly:

`parent ATTACK 223 -> candidate ATTACK 224`

on the same Duraludon and opponent Active, with a persisted exact Pareto proof.
Any other action difference or clearly harmful first difference rejects the
rule.

Run the required replay shadow and frozen fixed160 schedule. Reject on any
invalid action, exception, max-step, duplicate mismatch, schedule mismatch,
`gains < regressions`, or a seat/opponent cell three wins below Rule 5. If
shadow plus fixed160 has zero natural starts, record `DEFER-DORMANT`, do not
widen the conditions, and do not integrate the rule into the final candidate.

## Selection decision

Selected for isolated implementation from the accepted Rule 5 parent. The
strategy judge is read-only; implementation, verification, adoption, commit,
and push remain root-owned.
