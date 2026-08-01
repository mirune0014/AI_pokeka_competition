# Task 6 root verification

## Frozen inputs

- Parent: `archaludon_public_poke_pad_declared_executable_role_transaction_v1`
- Parent `main.py` SHA-256: `2B23D3AFC63A5BDC4BC7765CE1656725ED01890D161E3D23DCC672BE7FCCCFF4`
- Candidate `main.py` SHA-256: `99EE7BF5E6E6D61D863EF1D131232F90DCE36A3CFDF032AF6E534DECA79B2756`
- Deck SHA-256: `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`

## Independent root checks

- Focused contract suite: `210/210` passed.
- Replay shadow:
  - 89280661: 58 decisions, one intended difference. Two redundant Ultra Ball
    copies replace the Lillie and Explorer discard costs.
  - 89291523: 59 decisions, one intended difference. The purposeless Ultra
    Ball is replaced by a manual Metal attachment to the Bench Archaludon ex;
    Task 6 owns no callback.
  - 89347400: 11 decisions, zero action differences. The unchanged Ultra Ball
    action declares the Turbo-successor route; counterfactual continuation is
    covered by the engine-shaped fixtures.
- Structure: final callable `agent`, 12 package entries, only `main.py` differs
  from the parent, legal 60-card deck, one ACE SPEC, and no cache entries.
- Root both-seat historical-Silver smokes:
  - Candidate in seat 0: 90 steps, action errors 0, max-step false.
  - Candidate in seat 1: 134 steps, action errors 0, max-step false.
- Hard-protection fixtures:
  - Productive Metal plus an expendable duplicate is discarded while the
    concrete Boss, evolution and recovery routes remain bound.
  - Ultra Ball is declined when only Metal plus two bound cards remain.
  - Copies above a bound minimum remain discardable.
  - The chosen competing-target certificate, not only the enumerated variants,
    follows ready-attacker and backup-deficit ordering.
  - Wasted actions and overattachments are counted; the selected plan wastes
    zero actions.

## Energy-resource checks

The focused suite explicitly covers the two user-requested cases.

1. With at least two usable Metal Energy already in discard, a hand Metal gets
   zero productive-discard credit. Redundant safe cards are preferred.
2. With the intended attacker at one Energy, one Metal in discard, and one in
   hand, the planner compares both complete routes:
   - retain the hand Metal, Alloy one, then manually attach one;
   - discard the hand Metal, then Alloy two.

The first route wins when redundant safe costs exist. The second remains legal
when the alternative costs remove a specifically useful Boss, evolution, or
recovery route, or when the manual attachment has already been consumed. The
choice is made from the complete attack route rather than a blanket Energy
preservation rule.

## Final decision

ACCEPT for Task 6 commit and push. The revised planner derives exact-serial and
minimum-count bindings for Boss, recovery, evolution/successor, Supporter,
Stadium/Tool, manual/Turbo Metal, and the certified next attacker before cost
enumeration, then rejects every pair that breaks those routes. The independent
Sol-Ultra final audit accepted revision SHA
`99EE7BF5E6E6D61D863EF1D131232F90DCE36A3CFDF032AF6E534DECA79B2756`.
This is a transaction-safety decision, not a broad win-rate claim. No Kaggle
write was performed.
