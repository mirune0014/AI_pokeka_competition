# Strategy selection: certified endgame Alakazam Boss transaction

## Decision

Select exactly one first hypothesis:

`H1_CERTIFIED_ENDGAME_ALAKAZAM_BOSS`

When both available KOs take the same one Prize, spend Boss's Orders to remove
the unique visible, already attack-ready Alakazam that has a public next-turn
terminal KO, instead of KOing a harmless Active and giving that Alakazam free
promotion.

Reject the generic turn-plan reservation rule as the first candidate. Its
callback ownership overlaps the rejected broad planner, which lost 440/2,400
paired games. Implement H1 alone, directly from parent source SHA-256
`F4B578453C9D953BE94885144DD50E05DBA4510DF3340BE27ADE07495896046E`.

## Verified evidence

The Sol-Ultra strategy judge verified all supplied hashes:

- Candidate-selection evidence:
  `82A3321B37B68C320E29A448DFBC7F7A24AED0A393785F3E3043F9C3FB64A955`.
- Alakazam audit:
  `C5122CC809EBD2D1D40894C714090AFC84883A38CFBC802907CEF6AECC8557A2`.
- Adjacent audit:
  `F65E9F8EB59EFA8C9ECB687710EFA957A8246275915F3C6F7D8958342CD1B272`.
- Root live evidence:
  `B783670F785675A86F9C1F063E6C5B2D7BB9D22705AFE528CDB2B478345BE868`.

At `88457867:144`, the exact parent suppressed known Boss because the Active
Dunsparce was KOable. Both Dunsparce and the unique ready Bench Alakazam
yielded one Prize; Metal Defender could KO either. KOing Dunsparce promoted
Alakazam, whose public Powerful Hand damage then took the opponent's last Prize
from our two-Prize Archaludon ex.

This certifies the decision defect and current-turn conversion, not the hidden
future outcome.

## Immutable trigger

Arm H1 only when every condition is true:

1. Selection is `MAIN`; Boss's Orders `1182` is legally playable and the
   Supporter has not been used.
2. Legacy matchup detection is exactly Alakazam. Crustle, Ogerpon, and
   hybrid-board higher-precedence rules are ineligible.
3. We have exactly two Prizes remaining.
4. Our Active is an already-evolved Archaludon ex `190`, worth two Prizes.
5. Metal Defender `253` is legal immediately from the current Active without
   retreat, attachment, evolution, Ability, recovery, or a hidden card.
6. Metal Defender deterministically KOs the current opposing Active after all
   public modifiers.
7. That Active is worth exactly one Prize; its KO is nonterminal and not a
   board-out win.
8. The opponent has one or two Prizes remaining, so KOing our Archaludon ex
   would end the game.
9. Exactly one opposing Bench Pokemon satisfies the target certificate below.
10. Boss plus the same already-legal Metal Defender deterministically KOs that
    target; it also yields exactly one Prize and is nonterminal.
11. After removing that target, no other visible surviving Pokemon is already
    capable, in its current form and with currently attached Energy, of a
    public terminal KO on our Archaludon ex.
12. No already-certified current-turn terminal Attack or terminal Boss target
    exists.

## Exact target certificate

The sole target must:

- be Alakazam `743`, identified by unique card serial;
- expose Powerful Hand `1072`;
- have enough currently attached public Energy to use it;
- have no public restriction preventing that attack;
- be KOable now by Metal Defender;
- be the unique visible ready terminal response threat.

Powerful Hand certification uses only its minimum public next-turn hand size:
current opponent `handCount` plus the mandatory turn-start draw, requiring
`deckCount > 0`. Exclude optional draw, evolution, attachment, search,
recovery, hidden cards, and damage-ceiling assumptions. Apply Stadium, Tool,
Weakness, protection, and other public modifiers exactly.

## Precedence

1. Exact current-turn match win or board-out win.
2. Existing hard legality, immunity, and terminal rules.
3. H1 Boss transaction.
4. Existing `save Boss: can KO Active` suppression.
5. All other legacy scoring.

H1 owns only Boss play, its exact target callback, and the already-certified
Metal Defender. It must not preempt unrelated callbacks.

## Transaction contract

Snapshot on arming:

`(seat, turn, prize counts, own Active id/serial/HP/Energy, Boss serial,
original opposing Active serial, target serial, attack id, relevant public
modifiers)`.

Stages:

1. `ARMED`: return the legal Boss option.
2. `BOSS_CONFIRMED`: advance only after the observation or log confirms Boss
   use; on the Boss switch callback, select the stored target serial.
3. `TARGET_CONFIRMED`: advance only when that serial is observed Active.
   Revalidate Metal Defender legality and KO damage.
4. `ATTACK_PENDING`: immediately choose Metal Defender at `MAIN` or `ATTACK`;
   do not insert Explorer, Items, attachment, evolution, retreat, or Ability.
5. `DONE`: clear after the Attack log, turn end, result, or new game.

Returning an option must not itself advance state. Repeated identical
observations return the same option.

Rollback is logical, not an undo of an already-played card:

- Before confirmed Boss use, any mismatch clears the transaction and delegates
  to the exact legacy policy.
- After Boss use, any target disappearance, serial ambiguity, state drift, lost
  attack legality, changed turn or seat, unexpected callback, or failed KO
  certificate clears the transaction and delegates from the actual current
  state.
- Reset on deck request or new game, result, turn change, confirmed attack, or
  exception.
- Never carry state across games or seats.

Duplicate handling:

- Multiple distinct eligible targets: fail closed; do not arm.
- Duplicate options for the same stored serial or attack ID: choose the lowest
  legal option index deterministically.
- Repeated callbacks: return the stored semantic choice without
  double-advancing.
- Missing stored serial or attack: rollback.

## Required positive tests

- Reconstructed `88457867:144`: Boss -> Alakazam serial `12` -> Metal Defender;
  Explorer is not chosen.
- Same public state with permuted option order and changed serial values.
- Opponent at two Prizes, with all other certificate fields true.
- Repeated delivery of every callback.
- Duplicate semantic options for the same serial or attack.
- Confirmation that only observed state or log changes advance stages.

## Required negative tests

No trigger for:

- direct final-Prize or board-out wins;
- a terminal Boss target;
- Boss absent, illegal, or Supporter already used;
- Active other than already-evolved Archaludon ex;
- an attack requiring attachment, retreat, evolution, Alloy, recovery, or
  coin success;
- target not `743`, not ready, protected, or outside Metal Defender range;
- damage supported only by optional hand growth or a ceiling estimate;
- multiple ready Alakazam or any other visible ready terminal successor;
- opponent deck count zero;
- unequal Prize yield between current Active and target;
- our remaining Prizes other than two;
- opponent having more than two Prizes;
- hybrid Ogerpon or Crustle classification;
- `88417236`, `88171291`, `87974582`, `87892692`, and `88096059` unless the
  complete H1 certificate independently holds;
- higher-Prize Mega or Fezandipiti Boss routes;
- last-Prize recovery, sole-Energy reservation, promotion preservation, Alloy
  allocation, Bench-damage protection, or non-ex evolution cases.

## Forbidden generalizations

Do not generalize H1 to:

- "Boss any higher-Prize target";
- "Boss any ready attacker";
- other matchups or opponent identifiers;
- episode IDs, exact option indices, seeds, or replay action labels;
- opponent hidden hand, deck or Prize identities, or likely behavior;
- broad next-attacker planning;
- Energy, evolution, promotion, healing, or recovery reservation;
- the rejected Continuity2 planner;
- the separate direct-final-Prize candidate;
- any claim that removing Alakazam guarantees the match.

The deterministic exception fallback is a safety requirement only: choose a
stable legal fail-closed option without changing normal-path policy.

## Shadow and engine gates

Before numerical evaluation:

- Verify parent and deck hashes exactly.
- One-step shadow all 185 frozen replay files and every observation in both
  24-loss audits.
- Reconstruct the complete primary Boss, target, and attack callback sequence.
- Every divergence must satisfy and log every certificate field.
- Trigger-external action equivalence must be 100%.
- Root-inspect every additional trigger; no automatic causal label.
- All listed negative controls must remain unchanged.
- Pass option permutation, repeated-callback, stale-snapshot, rollback,
  new-game, both-seat, exception, legality, min/max selection, and
  deterministic-fallback tests.
- Zero action errors, exceptions, stale transactions, and max-step hits.

## Paired evaluation gates

Reuse the immutable 200-game historical-mirror and 480-game
adjacent-population schedules used for the prior safe-gate audit, with identical
opponents, seats, seeds, engine, and raw schema. If their exact paths and hashes
cannot be recovered, the root must freeze a replacement specification before
execution.

Require:

- unique and equal `(panel, opponent, seat, seed)` schedules;
- exact row totals and zero duplicate controls;
- zero action errors and max-step hits;
- candidate wins no lower overall, in either seat, in the primary Alakazam
  bucket, or in any adjacent opponent bucket;
- every paired flip traced to H1;
- no trigger-external first divergence;
- observed continuation matching Boss -> certified target -> Metal Defender.

Any regression, even with a positive aggregate, rejects this first probe. A
tiny positive delta alone does not establish adoption.

## Live-probe judgment

A single safe exploratory live submission is conditionally justified even with
zero local outcome gain because the trigger is rare, the primary live defect is
root-verified, and the rule surface is deliberately narrow. This is justified
only if all structural, shadow, engine, both-seat, and zero-regression gates
pass.

Such a submission is an exploratory probe, not acceptance. Final adoption still
requires practical absolute strength, primary-anchor safety, repeated trigger
behavior, both-seat and adjacent-population safety, clean execution, and
confirmation that gains arise from removal of the certified response threat.

## Principal regression risks

- Spending Boss and forfeiting Explorer when hidden rebuilding still wins.
- Incorrect Powerful Hand floor or damage-modifier calculation.
- A second visible ready successor omitted from certification.
- Stale transaction state selecting the wrong target or attack.
- Hybrid matchup priority leakage.
- Callback ownership expanding beyond three semantic choices.
- Overfitting the exact replay through card, serial, or option-order
  assumptions.
