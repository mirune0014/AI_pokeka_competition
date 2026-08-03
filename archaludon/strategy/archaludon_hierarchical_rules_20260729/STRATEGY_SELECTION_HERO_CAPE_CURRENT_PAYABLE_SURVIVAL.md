# Strategy selection: Hero's Cape current-payable same-attack survival

Decision: `SELECT_IMPLEMENTATION_EXPERIMENT_ONLY`

This contract is frozen from the exact historical-Silver parent. It may be
implemented only after H6 v2 closes. It must be a fresh direct sibling and
must not stack H5, H6, H7-A, or any other candidate.

## Evidence identity

- parent `main.py`:
  `F4B578453C9D953BE94885144DD50E05DBA4510DF3340BE27ADE07495896046E`
- parent/candidate deck:
  `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`
- 48-loss audit:
  `18E965D0DB8BE3F7231F4F145A4083FEE7374620903EA7936CE34DF727D9B65D`
- Root source fact JSON:
  `8EA9B3B3D52EBE1C1CD9DDF1E46A145F3E89C08CF7C0A37126826792556EF7B8`
- Root verification script:
  `DEABE7B6BDE857F6CBC4BB4423B21FA3CAC7380DA817AECD7DB8DE4E6703607A`
- replay `88643491`:
  `5C385365DBCA461A5E99B633E00C011CFDCE18ADD7EB0E9DECAF6F4A2FD16DDF`

At `88643491:77`, historical-Silver uniquely chooses Active Duraludon's
Raging Hammer `224` with score `25,000`; Hero's Cape to that same Active has
score `8,000`. Cape followed by the exact same attack preserves attacker,
target, attack ID, 80 damage, zero Prize, and public resources except the
spent Cape. Duraludon moves from 130 to 230 HP. The opposing Mega Lucario ex's
currently payable Aura Jab `982` deals 130, changing a public immediate KO
into survival at 100 HP.

This proves only the current-energy survival boundary. One hypothetical Basic
Fighting attachment makes Mega Brave `983` for 270 payable and KOs the capped
Duraludon. The source proves neither opponent choice, next-turn safety, nor
match conversion.

## Selected rule

Name:
`HERO_CAPE_CURRENT_PAYABLE_SAME_ATTACK_SURVIVAL`

At an ongoing `MAIN` callback with `minCount == maxCount == 1`:

1. Compute and cache the exact historical-Silver semantic choice and all
   parent scores once. It must have one untied winner: Active Duraludon's
   Raging Hammer `224`.
2. Legal option types may be only `ATTACH`, `ATTACK`, and `END`. Any play,
   evolution, Ability, retreat, discard, switch, Boss, or other
   board-changing route delegates unchanged.
3. Bind the Tool-free Active Duraludon, opponent Active, visible Hero's Cape,
   and stored attack by card IDs and positive unique serials. Exactly one
   distinct Cape-to-Active semantic attachment must exist. Equivalent
   duplicate options are allowed.
4. Raging Hammer's public effective damage must be exact, positive, unchanged
   by Cape, and strictly below the opposing Active's current HP. Every other
   legal attack must also be a certified non-KO. No Prize, terminal,
   higher-Prize, or forced-defense conversion may be displaced.
5. Let `E0` be every opposing-Active attack payable using only its currently
   attached public Energy units. At least one `E0` attack must KO current HP,
   and every `E0` attack must deal strictly less than current HP plus 100.
6. Every `E0` payment and damage calculation must be supported and
   unambiguous. Fail closed on chance damage, effect/damage-counter KOs,
   unknown costs or restrictions, relevant status, matching Weakness or
   Resistance, any relevant Tool, nonempty Stadium, or unmodelled continuous
   and protection effects. Use an audited attack-formula registry. Attacks
   `224`, `982`, and `983` are mandatory covered formulas.
7. Separately compute `E1_BASIC`: attacks payable after adding one
   hypothetical Basic Energy unit of any type. This is public possibility
   telemetry, not hidden-hand inference. It excludes Abilities, evolution,
   switching, Supporters, special multi-unit Energy, and opponent-policy
   assumptions. Ambiguity fails closed.
8. `E1_BASIC` is telemetry, not a trigger veto. The source must be labeled
   `E1_CAPE_LETHAL` because Mega Brave 270 becomes payable. The rule must
   never claim that the Active is next-turn safe.
9. The Cape projection must add exactly 100 to current and maximum HP,
   preserve damage counters, Energy, attacker, target, attack payment,
   Raging Hammer damage, Prize counts, and every other public modifier.

## Score versus hard gate

This is not a global hard gate. Exact terminal, Prize, setup, and
forced-defense arbitration retain precedence.

For the single certified Cape option only:

`cape_score = max(parent_cape_score, stored_parent_attack_score + 1)`

The source therefore becomes `25,001` versus `25,000`. Do not modify global
Cape, Tool, threat, Duraludon, Lucario, or matchup scores. After confirmed
Cape attachment, selecting the stored exact attack is transaction completion,
not a second independent policy decision.

Precedence:

1. legality, deck, setup, and reset;
2. exact terminal, Prize, and forced-defense guards;
3. active transaction retry/revalidation;
4. this one certified local Cape modifier;
5. unchanged historical-Silver.

## Transaction

Stages:

`CLEAR -> CAPE_EMITTED -> ATTACK_EMITTED -> CLEAR`

Snapshot seat, game epoch, first player, turn/action count, Prize counts, both
Active fingerprints, Energy, Tool, status and modifier fields, Cape serial,
stored attack and score, `E0/E1` envelopes, and canonical semantic-option
multiset.

- Returning an action does not confirm it.
- An identical retry returns the same semantic action without another parent
  call or stage advance.
- Option-order changes rebind by semantics; equivalent duplicates choose the
  lowest current option position.
- Confirm Cape only from a novel observation showing the stored Cape removed
  from hand and attached to the same Active, current/max HP each exactly
  `+100`, and no other material mutation.
- Recompute the parent. The stored attack must remain uniquely legal,
  parent-selected, same-target, same-damage, and same-payment before emission.
- Repeated post-Cape callbacks return that exact attack.
- Before Cape confirmation, mutation clears and returns the cached parent
  action if still legal.
- After Cape confirmation, mutation clears and delegates from the actual
  irreversible state; never invent another Tool, attacker, target, or attack.
- Clear on result, deck request/new game, seat/turn change, rollback,
  log/action-count inconsistency, serial disappearance, semantic-option
  mutation, exception, observed attack, or turn end.

## Mandatory tests

Positive source:

- `88643491:77`: parent Attack `[5]`, candidate Cape `[2]`;
- exact continuation chooses Raging Hammer `224`;
- Mega Lucario ex moves `340 -> 260`;
- capped Duraludon is 230 HP;
- Aura Jab leaves it at 100 HP;
- `E1_BASIC` contains Mega Brave 270 and records
  `E1_CAPE_LETHAL=true` without vetoing the source.

Run the full transaction in both logical seats, with serial permutations,
option-order permutations, equivalent duplicates, and repeated callbacks.

Mandatory parent-identical negatives:

- `88643491:75` with Cinderace Active;
- any attack KO, terminal route, or visible Prize route;
- return damage already below current HP;
- return damage still lethal after Cape;
- danger that becomes lethal only after one attachment but no current-payable
  attack exists;
- no currently payable attack;
- Mega Brave already payable;
- missing or multiple distinct Cape bindings;
- existing Tool, wrong attacker, or stored attack disappearance/change;
- ambiguous payment/damage, chance/effect KO, status, matching
  Weakness/Resistance, Stadium, Tool, protection, or unmodelled effect;
- retry, rollback, reset, exception, and option mutation;
- all frozen H1/H2/H4/H5/H6/H7-A/Bench controls;
- `88417236:45`, where Cape is already attached.

Both-seat exact-engine branches must include:

1. no Cape, Raging Hammer, Aura Jab: Duraludon is KO'd;
2. Cape, same Raging Hammer, Aura Jab: Duraludon survives at 100;
3. Cape, same Raging Hammer, one Basic Fighting attachment, Mega Brave:
   Duraludon is KO'd.

Require zero invalid actions, exceptions, stale transactions, action errors,
and max-step hits.

## Shadow and fixed evaluation

Shadow at least the frozen 217-file correct-seat corpus:

`live/55073442/refresh_20260729_1541/`
`shadow_corpus_207_prior_plus_10_new`

It includes all 48 audited losses. Record every predicate, rejection reason,
parent/Cape scores, `E0/E1` IDs and margins, stage/reset, and semantic
difference. Every difference must be Cape followed by the stored same attack.
Certificate-external differences reject implementation.

Derive a fresh immutable fixed-760 schedule from the same exact historical
anchor, adjacent population, seats, seeds, engine, schema, traces, and
`max_steps=1000`. Baseline duplicates must reproduce 100/200,
378/560, and 478/760.

Implementation safety requires:

- exact schedule equality;
- zero faults, errors, exceptions, and max-step hits;
- no parent-win to candidate-loss flip;
- no overall, anchor, adjacent, seat, opponent, or cell regression.

Formal-parent acceptance is intentionally much stronger and requires a later
independent judgment:

- at least 104/200 on the primary anchor and 486/760 overall;
- adjacent at least 378/560;
- both seats nonnegative and no cell/floor regression;
- at least four certified completed transactions over two board
  configurations, at least two per seat;
- repeated `E1_CAPE_LETHAL` exposure with no causal loss;
- at least two Root-verified mechanism-owned parent-loss/candidate-win
  conversions including both seats;
- exact trace proof that Cape survival caused the extra continuity and gain.

Tiny deltas, one-seat gains, a source-only trigger, parent-identical wins, or
unrelated gains reject adoption.

## Risk and current authorization

Principal risks are spending the unique ACE SPEC on a one-Prize Duraludon,
ordinary one-step Energy acceleration invalidating survival, gust/evolution/
switch routes, opportunity cost versus a future 400-HP Archaludon ex, and
stale transaction state.

This selection authorizes isolated implementation only after H6 v2 closes.
It does not authorize packaging or a Kaggle write.
