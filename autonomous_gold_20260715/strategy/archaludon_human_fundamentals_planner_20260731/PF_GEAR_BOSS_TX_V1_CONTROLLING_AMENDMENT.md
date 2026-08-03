# PF_GEAR_BOSS_TX_V1 controlling amendment

Date: 2026-07-31  
Status: controls conflicting fallback language in
`EFFECT_REGISTRY_DEV_PARENT_AUDIT_AND_POKEGEAR_BOSS_CONTRACT.md`  
Scope: contract correction only; the single hypothesis remains
`PF_GEAR_BOSS_TX_V1`

## Consistency verdict

**The contradiction is real.** The inherited scorer places Pokégear in
`ITEMS` and returns `20000, "play item"` when no narrower exception applies.
The effect-registry wrapper calls its direct parent once and ultimately returns
that parent action. The frozen PF contract starts its positive transaction only
when a Gear-to-Boss purpose is certified, but otherwise requires exact-parent
fallback. Therefore, when the parent selects Gear and no purpose certificate
exists, the supposedly purpose-first child can still emit the blind Gear play.

The positive transaction alone means “the child never *initiates* Gear without
a purpose”; it does not mean “the final agent never plays Gear without a
purpose.” The original global wording was too strong.

## Controlling rule

Add the following **negative half of the same purpose-first rule**. It is not a
second hypothesis and owns no additional Trainer.

After invoking the exact direct parent once, at a live, transaction-free
`MAIN` decision:

1. If the positive `FINISH_NOW`, `AVOID_EXACT_LOSS`, or
   `PRESERVE_ATTACK_CHAIN` Gear certificate passes, follow the frozen
   Gear-to-Boss transaction.
2. Otherwise, inspect the direct-parent action. If it is not a legal play of
   Pokégear `1122`, return it unchanged.
3. If the parent chose Gear but no Gear purpose was certified, attempt the hard
   veto certificate below.
4. If exactly one semantic attack passes that certificate, return that
   prebound attack instead of Gear.
5. For every failed, unknown, ambiguous, or incomparable veto check, return the
   direct-parent action unchanged.

This ordering supersedes the prior statements that every negative Gear fixture
must be direct-parent-equivalent and that the child owns only positive
`GEAR_PLAY` sequences. The sole added ownership is
`PARENT_GEAR_VETO -> PREBOUND_ATTACK`.

It does **not** authorize a blanket Gear ban. When no exact safe attack can be
certified, blind parent Gear remains reachable by deliberate fail-closed
fallback and must be reported as such. Consequently, “purpose-first” means:

> the final agent never preserves a non-purpose parent Gear play when one
> unique exact nonworse attack or immediate finish is certified.

No broader no-blind-Gear claim is valid for v1.

## Hard veto certificate

All conditions are mandatory:

### Parent and boundary

- Live own turn, unresolved game, `SelectContext.MAIN`, no selection effect or
  context card, and no inherited or child transaction owner.
- The once-called parent's valid one-option action maps semantically to playing
  one physical Pokégear `1122`. Never recognize it by option position.
- The exact positive Gear-purpose evaluator has returned no certificate and a
  recorded rejection reason. A Gear purpose may not be suppressed merely to
  activate the veto.
- Public card/effect metadata, board serials, conditions, tools, Stadium,
  Energy, HP, Prize counts, hand visibility, and relevant registry semantics
  are exact. Registry `UNKNOWN`, rejected binding, public opponent
  Adrena-Brain, or a nonzero omitted-Adrena count rejects the veto.

### Exact payable attack

- Enumerate current legal attack options from the actual Active. Each admitted
  option must match a printed attack, have exact payment from currently
  attached Energy, and have an exact public combat certificate. No future
  Energy attachment, switch, search hit, hidden card, or opponent choice may be
  assumed.
- Collapse duplicate UI options only when attack ID, attacker serial, payment,
  and complete successor certificate are equal. Reordered options must not
  affect the result.
- Admit `DIRECT_FINISH` immediately when exactly one semantic attack takes at
  least all remaining Prizes under the exact certificate. An immediate win is
  nonworse regardless of unused setup actions.
- Otherwise admit `SECURED_NONWORSE_ATTACK` only when the turn has no unfinished
  uniquely certified setup, board-formation, healing, Energy-attachment,
  retreat, evolution, Ability, Supporter, Stadium, tool, or backup-readiness
  action that the immediate attack would skip. Unknown opportunity cost rejects.

### “Nonworse” without a scalar score

For a nonterminal attack, form public successor facts rather than a weighted
value. The chosen attack must be componentwise no worse than every other exact
payable attack in all of these dimensions:

- immediate Prize yield is at least as large;
- the set of our ready current/backup attackers after the exchange is a
  superset;
- retained Energy, hand, deck, recovery, and attachment-capacity facts are no
  worse individually;
- exact opponent next-turn terminal and attack-lock reply sets are subsets;
- our following-turn exact attack-continuity set is a superset;
- no public status, recoil, self-lock, forced switch, or resource-discard
  consequence is worse.

At least one dimension must be strictly better unless there is only one exact
payable semantic attack. This is a partial-order dominance test, not a sum,
weight, rank score, matchup rule, or option-index tie break.

Exactly one semantic maximal attack must remain. If two attacks are equal,
their complete certificates must also be equal; then select the deterministic
lowest semantic key, not a replay-specific index. If two successors are
incomparable, preserve parent Gear.

## Emission and lifecycle

- Bind seat, turn, attacker ID/serial/fingerprint, attack ID/payment, Gear
  serial selected by the parent, option multiset, public-state fingerprint,
  purpose-rejection reason, and full dominance certificate before overriding.
- Revalidate the bound attacker, payment, board, option semantics, and
  certificate immediately before returning the attack option.
- The veto does not play Gear, Boss, or another Trainer and does not create the
  positive Gear transaction. A read-only watcher may confirm the attack log,
  turn end, or terminal result; all subsequent callbacks remain owned by the
  once-called direct parent.
- Repeated identical observations emit the same semantic attack and may not
  double-count a veto. Any stale revalidation returns the already-called
  parent action and records `VETO_STALE_PARENT_GEAR`.
- Forced actions, active transactions, setup selection, mandatory callbacks,
  deck requests, malformed observations, and completed games retain their
  existing precedence.

## Required telemetry

Add exact counters/reasons for:

- `parent_gear_selected`;
- `positive_gear_purpose_found`;
- `parent_gear_without_purpose`;
- `gear_veto_direct_finish`;
- `gear_veto_secured_nonworse_attack`;
- `gear_veto_no_payable_attack`;
- `gear_veto_incomparable_attacks`;
- `gear_veto_unfinished_turn_purpose`;
- `gear_veto_unknown_or_unsupported`;
- `gear_veto_stale`;
- `blind_parent_gear_passthrough`;
- bound Gear/attacker serials, attack ID, exact certificate, and rejection
  reason.

Conservation at eligible parent-Gear decisions:

`parent_gear_selected = positive_gear_purpose_found + gear_veto_direct_finish + gear_veto_secured_nonworse_attack + blind_parent_gear_passthrough`.

The categories must be mutually exclusive. Invalid actions, exceptions, and
duplicate veto advances must remain zero.

## Controlling tests

Positive veto fixtures, both seats and reordered options:

1. Parent selects Gear solely through the generic item branch; no Gear purpose
   exists; one exact attack on the current Active wins the game. Expect the
   attack, never Gear, with `gear_veto_direct_finish += 1`.
2. Parent selects Gear; no Gear purpose exists; setup opportunities are
   exhausted; exactly one payable attack is componentwise nonworse. Expect that
   attack and `gear_veto_secured_nonworse_attack += 1`.
3. Two UI entries encode the same complete attack certificate. Reordering them
   preserves the same semantic attack and deterministic key.
4. Differential replay of the identical observation proves the exact parent
   returns Gear while the amended child returns only the certified attack.

Negative/fallback fixtures:

- A positive Gear-to-Boss purpose exists: start the original transaction; do
  not veto.
- Parent chooses anything other than Gear: exact parent action.
- No legal/payable attack; payment or combat unknown; two incomparable attacks;
  unfinished certified Energy/supporter/board/backup purpose; unsupported
  effect; Adrena quarantine; active transaction; callback; stale board; option
  ambiguity: exact parent action with the corresponding passthrough reason.
- Parent Gear plus a nonterminal attack that would skip a uniquely certified
  backup attachment or board action: preserve parent Gear.
- Repeated callback/observation, seat or turn change, result, malformed serial,
  and invalid parent action must not create a veto or invalid action.

Regression gates:

- Existing registry `31/31`, inherited `38`, frozen-16 classification, and all
  positive Gear transaction tests remain unchanged.
- Final wrapper still invokes the exact direct parent once per callback.
- Checked engine must exercise at least one `DIRECT_FINISH` veto and one
  `SECURED_NONWORSE_ATTACK` veto in both seats, with raw baseline/candidate
  actions from the identical observation.
- Zero action errors, exceptions, stale live watchers, and max-step hits.
- Any trace in which parent selected Gear, no positive purpose existed, a
  unique exact veto certificate passed, and the child still played Gear is an
  automatic contract failure regardless of match result.

## Remaining uncertainty and next evidence

This amendment closes the logical hole only on states with a certifiable safe
attack. It intentionally does not prove that every remaining parent Gear play
is strategically correct. The next discriminating evidence is a root-verified
checked-engine inventory of every `parent_gear_without_purpose` occurrence,
partitioned into vetoed finish, vetoed nonworse attack, and fail-closed
passthrough, followed by changed-position replay inspection. A future broader
Gear policy would be a separate hypothesis and is outside v1.

