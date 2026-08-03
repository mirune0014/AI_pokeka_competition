# Effect-registry DEV-parent audit and frozen next rule

Date: 2026-07-31  
Role: Sol-Ultra read-only strategy judge  
Scope: qualitative audit and one next-hypothesis selection only

## Verdict

**Conditional DEV-parent accept for one isolated paired experiment; reject as an
unrestricted semantic authority or Kaggle candidate.** The executable
`main.py` is sufficiently pinned and regression-tested to be the exact direct
parent of the next append-only candidate. Baseline and child must share this
same parent, and the child must not activate on a public Adrena-Brain state.
Two source-level Adrena completeness defects and one evidence-manifest hash
discrepancy remain promotion blockers.

The one frozen hypothesis is:

> **PF_GEAR_BOSS_TX_V1 — purpose-first Pokégear 3.0 to Boss's Orders complete
> transaction.** When a currently payable attack has one exact Boss-gust line
> that either wins the game now, removes all exact next-turn terminal replies,
> or uniquely preserves an otherwise-broken attack chain, using Pokégear only
> to access Boss and carrying a hit through Boss, gust, and the prebound attack
> will improve tactical conversion without sacrificing the already-secured
> attack on a miss.

This is one rule hypothesis, not a generic Trainer planner. It owns only card
`1122 -> 1182 -> target -> attack`; it never plays a Trainer merely because it
is legal or has a high score.

## Root-verified facts used

- Candidate executable:
  `autonomous_gold_20260715/candidates/archaludon_deterministic_public_effect_registry_phase1_v1/main.py`,
  SHA-256
  `B778D128D7ECC9999BF8B7C5C574A594B56BA6FC434524E4104676C3FF3066C1`.
- Exact PCRD-v2 prefix: 829,528 bytes, parent SHA-256
  `4B9851F54A49DE19614F4E9AACBB430539A2DB8CCCEA3EC57108FF21DDB34ED8`;
  appended suffix SHA-256
  `49365ED54263D5C7D2F9C77027847152B40D8EEB25D106B2159B45EAEC3CF0EF`.
- Root record:
  `implementation/archaludon_deterministic_public_effect_registry_phase1_v1/ROOT_VERIFICATION.md`,
  SHA-256
  `68AB58818ECC2C1B012508C19274155286015CF394CBFCC578BDE20E33897190`.
- Root verified final `agent`, direct-parent invocation exactly once per
  callback, 37 admitted bindings covering 60 cards, 11 unchanged non-main
  package files, and cache-free packaging.
- Test evidence in the root record: registry-focused `31/31`; inherited suites
  `16 + 5 + 17 = 38`; frozen-16 classification `3` positive, `1`
  conditional, `12` negative. Checked-engine evidence exercises only the two
  inherited Assemble-Alloy transactions, both seats, with `0` recorded faults.
- Production ownership is narrower than effect coverage: `20` direct semantic
  consumers, `2` inherited action transactions, `9` observers, and `3`
  semantics-only routes. Thus the candidate does **not** establish that all 34
  effect groups own correct human-like actions.
- Current deck contains Pokégear 3.0 x4 and Boss's Orders x4. The inherited
  generic item path gives otherwise-unhandled items a blanket `20000` action
  score. Pokégear therefore remains a four-copy blind-use path. Ultra Ball
  already has a bounded inherited transaction. Pokégear is tied for the
  highest deck count among remaining unowned item mechanisms and uniquely
  supports a bounded same-turn Boss-to-attack transaction.

## Audit findings the existing record does not close

### 1. Unsupported Adrena variants do not fail the threat graph closed

`_dper_adrena_route_variants` increments `unsupported_variants` whenever a
public move/route cannot be certified and returns that count. The caller then
adds the admitted variants and records
`registry_adrena_variants_not_admitted`, but does not set `complete=False` or
add unsupported text when the count is nonzero. A threat envelope may therefore
remain marked complete after dropping a public reply. This can understate the
opponent's best reply; telemetry alone is not a safety guard.

Required repair before any promotion claim: `unsupported > 0` must make the
affected graph `UNKNOWN`/incomplete and return the exact frozen parent path.

### 2. Nonterminal Adrena KO of our Active omits the rest of the opponent turn

When Adrena-Brain KOs our Active, the implementation emits an ability-only
route and immediately stops expanding that move set. It marks the route
terminal only when the ability prizes already end the game. If the KO is
nonterminal, the rules require our forced promotion and permit the opponent to
continue the turn and attack. Neither transition is projected, and the route
is not rejected as incomplete. The focused evidence covers a terminal combined
Active/Bench KO, not this nonterminal continuation.

Required repair before any promotion claim: either certify forced promotion
plus every relevant continued attack, or return `UNKNOWN` for every
nonterminal Active-KO Adrena route.

### 3. The evidence record's effect-manifest hash is internally inconsistent

The current on-disk
`effect_registry_manifest.csv` hashes to
`39A3B65BD45EF2D96A005EE25AB84714202D7ABA13A71E16E9990185D83131C8`.
`ROOT_VERIFICATION.md` records
`39A3B65B2E069642628186223487655822E1CED073E3C6FF1BC81264795031C8`.
The executable and root-record hashes match the supplied facts, so this does
not block an exact-main-prefix development branch. It does block calling the
whole evidence package immutable until root rehashes the intended manifest
and corrects or explains the record.

## Why this one Trainer rule is next

- **Setup and board formation:** Pokégear is not allowed as deck thinning or
  generic setup. It activates only after an attacker, attack payment, opponent
  target, and post-gust board are exactly certified. Poke Pad and broad search
  planning remain out of scope.
- **Attacker and backup readiness:** the current attack must already be legal
  and payable without any card found by Pokégear. The continuity purpose also
  requires an exact ready backup after the projected exchange.
- **Energy, hand, and deck:** no Energy assumption is hidden in the search.
  Supporter use must remain available; Boss must not already be in hand; at
  least one of the four Boss copies must not be publicly exhausted; deck count
  and the optional top-seven callback must be exact. A Gear miss must leave the
  prebound attack legal.
- **Attack continuity and Prize exchange:** the rule never trades away a
  secured attack. Its purpose order is finish now, avoid exact loss while
  attacking, then preserve a certified attack chain. Immediate Prize yield may
  not be worse than attacking the current Active for the latter two purposes.
- **Finishing and disruption:** final-Prize conversion is the first branch.
  Disruption is admitted only when removing the one prebound target eliminates
  all exact public terminal replies, not because the target has a favored name
  or opponent identity.
- **Regression control:** every uncertainty, collision, semantic tie, stale
  callback, unsupported effect, or changed board returns the direct parent's
  valid action. The known Adrena domain is excluded from child activation.

## Exact Sol-xhigh candidate-worker contract

### Destination and immutability

- Candidate name:
  `archaludon_purpose_first_pokegear_boss_transaction_v1`.
- Copy the exact directory
  `autonomous_gold_20260715/candidates/archaludon_deterministic_public_effect_registry_phase1_v1`
  to an isolated destination of that name.
- Preserve every non-`main.py` file byte-for-byte. Preserve the entire
  `B778...06C1` `main.py` as an exact byte prefix; implementation is one
  append-only suffix. Report source/destination hashes and exact prefix byte
  equality.
- Capture the direct parent `agent` once before defining the final wrapper.
  The final wrapper invokes that direct parent **exactly once on every
  callback**, including active-child callbacks, misses, errors, deck requests,
  and terminal observations.
- No opponent IDs, matchup names, replay/episode/seed keys, hidden-card oracle,
  learned ranker, behavior cloning, or scalar weighted score. Card/effect IDs,
  physical serials, legal options, logs, and current public state are allowed.

### Sole ownership boundary

The child may override the direct parent only for this sequence:

`GEAR_PLAY -> GEAR_REVEAL -> (MISS_COMPLETE | BOSS_ACQUIRED) -> BOSS_PLAY -> BOSS_TARGET -> TARGET_CONFIRMED -> ATTACK -> COMPLETE`.

It owns no other Item, Supporter, Energy, evolution, retreat, Ability, or
promotion. It must not start while any inherited transaction owner is active.
At every stage, map by semantic option fields and bound physical serials, never
by a fixed option index. Reordered options and equivalent duplicate physical
copies must produce the same semantic action.

### Purpose certificate before `GEAR_PLAY`

The wrapper may play exactly one uniquely identified Pokégear serial only when
all common gates and exactly one highest-priority purpose certificate pass.

Common gates:

1. Live own turn; `MAIN`; one-card play; no selection effect/context card; no
   active inherited or child transaction; legal unique Gear option.
2. Supporter not used; Boss absent from hand; Boss text and Gear text match the
   admitted deterministic metadata; at least one Boss copy is not publicly
   exhausted; positive exact deck count; top-seven optional selection is
   supported by the checked engine.
3. Current Active, attack ID, attack payment, Energy attachments, board
   serials, HP, Prize counts, statuses, tools, Stadium, and relevant registered
   effects are exact. Any registry `UNKNOWN`, rejected binding, Adrena-Brain on
   the public opponent board, or nonzero
   `registry_adrena_variants_not_admitted` rejects activation.
4. There is a legal currently payable attack that remains legal after spending
   Gear. Playing Gear cannot consume the supporter right, Energy attachment,
   retreat, Ability, attacker, backup, or another resource in that attack
   certificate.
5. One Boss target and the post-gust attack outcome are uniquely certified.
   Multiple incomparable targets reject. Publicly identical targets may use
   the lowest physical serial only when their complete successor certificates
   are equal.
6. If the current Active can already be attacked for an exact game win, reject
   Gear and preserve that immediate finish.

Purpose order, with no arithmetic score:

1. `FINISH_NOW`: the prebound attack KOs the chosen Benched target and its exact
   Prize yield is at least our remaining Prizes. No lower purpose is considered.
2. `AVOID_EXACT_LOSS`: without the gust line, the complete public reply graph
   contains at least one exact opponent next-turn game-winning route. After
   gust plus the prebound attack, the chosen target is removed, **all** such
   exact terminal replies are removed, our attack still occurs, and immediate
   Prize yield is not lower than the current-Active attack. Unknown/incomplete
   reply graphs reject.
3. `PRESERVE_ATTACK_CHAIN`: no terminal branch applies; the current-Active line
   has no certified attacker for our following turn under every admitted public
   reply, while gust plus attack removes the unique cause and leaves at least
   one exactly payable current or backup attack under every admitted reply.
   Immediate Prize yield is not lower, no ready attacker/backup is lost, and
   Energy recovery/attachment capacity is not reduced. Any incomparable reply
   or resource ledger rejects.

If more than one certificate survives within the chosen purpose and their full
successor states are not equal, return the direct parent's action. The rule may
not use a weighted score to break the tie.

### Callback and transition contract

- The transaction binds seat, turn, turn-action count, Gear serial, purpose,
  attacker ID/serial/fingerprint, attack ID/payment, Boss card ID, original
  Active serial, target serial/fingerprint, both board fingerprints, hand and
  discard multisets, Prize counts, supporter/Energy flags, public metadata
  hashes, option multiset, and the exact purpose certificate.
- At `GEAR_REVEAL`, require effect card `1122`, `minCount=0`, `maxCount=1`, and
  exact transient-card mapping. If one or more Boss copies are offered, select
  the lowest physical serial among semantically identical Boss copies. If no
  Boss is offered, deliberately choose the legal empty selection, mark
  `MISS_COMPLETE`, and clear only after the engine confirms the callback
  transition. Do not substitute Explorer's Guidance or Lillie's Determination.
- After a hit, prove the selected Boss entered our hand and the other revealed
  cards left the transient zone as specified. At the next `MAIN`, play that
  bound Boss serial; then select only the prebound opponent target serial.
- After the gust, prove target/original-Active movement, supporter consumption,
  hand/discard change, turn-action count, attacker/payment, and both board
  fingerprints. Select only the prebound attack ID. Mark complete when the
  attack log/effect transition is confirmed or the game result is terminal.
- Before an irreversible child action, any mismatch clears and returns the
  direct-parent action. After Gear or Boss has been spent, the child must still
  return a valid legal choice for the current mandatory callback; on a stale or
  unsupported state, use the already-called direct-parent action, mark
  `ABORT_TO_PARENT`, clear at the next safe boundary, and never guess a target.
- Reset on seat/turn change, game result, deck request, malformed observation,
  missing/duplicated serial, invalid direct-parent action, transaction-owner
  collision, or callback repetition. Repeated identical callbacks must emit
  the same semantic choice without advancing twice.

### Required telemetry

At minimum record counters and last-certificate fields for:

- starts by `FINISH_NOW`, `AVOID_EXACT_LOSS`, and
  `PRESERVE_ATTACK_CHAIN`;
- Gear hits, Gear misses, Boss plays, target confirmations, attacks, completes,
  aborts-to-parent, stale transitions, owner collisions, Adrena quarantines,
  unknown registry/effect rejections, semantic ties, invalid actions,
  exceptions, and direct-parent call count;
- bound Gear/Boss/target/attacker serials, attack ID, stage, rejection reason,
  and whether the already-secured attack remained legal on a miss.

Conservation invariant for checked traces:

`starts = completes + miss_completes + aborts_to_parent + live_transactions`,

with zero invalid actions and zero exceptions.

## Falsifiable pre-implementation fixtures

Positive fixtures, both seats and reordered options:

1. `FINISH_NOW`: no Boss in hand; Gear reveals Boss; one Benched target is an
   exact final-Prize KO. Expect Gear, that Boss, that target, then the bound
   attack, with transition proof at every callback.
2. `AVOID_EXACT_LOSS`: current line permits an exact next-turn loss; removing
   one unique ready threat removes every terminal reply without losing the
   current attack or Prize yield. Expect the complete four-action sequence.
3. `PRESERVE_ATTACK_CHAIN`: current line provably loses all following-turn
   attackers; the unique gust-KO leaves an exact ready backup under every
   admitted reply. Expect the complete sequence.
4. Multiple physically distinct Boss copies in the reveal and option
   reordering produce the same semantic selection and lowest-serial tie break.

Negative/fallback fixtures:

- current-Active attack already wins; Boss already in hand; supporter already
  used; Gear absent/ambiguous; zero/unknown deck; all Boss copies publicly
  exhausted; no payable attack; no Benched target; attack or Prize outcome
  unknown; lower immediate Prize; no ready backup for continuity;
- two incomparable targets or replies; unsupported status/tool/Stadium/effect;
  public Adrena-Brain; nonzero omitted-Adrena count; owner collision;
- reveal has Explorer/Lillie but no Boss: choose the legal empty selection,
  confirm miss, and never relabel another Supporter as the declared purpose;
- reveal/target/attack options reordered, duplicated, missing, or stale;
  repeated callback; seat/turn/result change; malformed serial/log transition.

Every negative fixture must be byte-for-byte direct-parent-equivalent until the
child has irreversibly played Gear; mandatory post-spend callbacks must remain
legal and explicitly accounted as miss or abort.

## Evaluation gates

Development gates before simulation:

1. Exact `B778...06C1` prefix and identical non-main files; final `agent` only;
   direct parent exactly once per callback; cache-free package.
2. All existing registry `31/31`, inherited `38`, and frozen-16 classifications
   unchanged, plus all positive/negative fixtures above.
3. Checked engine must exercise **this new transaction** from Gear start through
   hit, Boss, gust, and attack in both seats, plus a legal miss in both seats.
   Inherited Assemble-only traces do not satisfy this gate.
4. Zero action errors, exceptions, duplicate advances, stale live transactions,
   and max-step hits; telemetry conservation holds exactly.

Strategic adoption gates after the immutable paired schedule is frozen:

- Compare the exact effect-registry parent and child on identical seeds and
  both seats; keep historical Silver as the primary absolute-strength anchor
  and complete historical agents as adjacent anti-overfitting opponents.
- Root must verify unique `(panel, opponent, seat, seed)` keys, exact schedule
  equality, raw outcomes, action errors, max steps, and changed-position traces.
- Do not accept a tiny aggregate delta. Acceptance additionally requires
  practical absolute strength against Silver, non-regression in each seat,
  repeated benefit across more than one seed/activation bucket, no material
  adjacent-population floor break, and trace proof that gains came from the
  declared Gear-to-Boss purpose rather than unrelated parent behavior.
- Any activation without a predeclared purpose, any scalar-score tie break, any
  avoid-loss/continuity route built from an incomplete threat graph, or any
  Adrena-domain child override is an automatic rule rejection regardless of
  win rate.

The root has not supplied an immutable opponent/seed schedule or numerical
replacement threshold for this next candidate, so no honest numeric promotion
cutoff can be invented here. Those values must be frozen before execution.

## Regression risks and exact evidence needed next

Principal risks are wasting Gear when Boss is unavailable, skipping a useful
non-Boss reveal on a miss, stale hidden-zone callback mapping, colliding with an
inherited Boss transaction, overclaiming an incomplete reply graph, consuming
the supporter right before a better line, and attributing registry-parent
behavior to the new rule. The narrow purpose and paired exact-parent baseline
make these observable rather than eliminating them.

Next evidence required, in order:

1. Root explanation/correction of the effect-manifest hash discrepancy and an
   independently hashed destination package inventory.
2. Sol-xhigh implementation report with exact prefix/suffix hashes, changed
   lines, transaction state diagram, telemetry schema, and raw test outputs.
3. Both-seat checked-engine hit/miss traces whose raw rows show every bound
   serial and callback transition, with zero faults/max steps.
4. Parent-frozen immutable paired schedule and thresholds, followed by raw
   per-game rows for parent, child, Silver anchor, and adjacent population.
5. Sol-Ultra numerical audit plus root recomputation, then changed-position
   replay evidence separating finish, avoid-loss, continuity, miss, and abort
   buckets.
6. Before any Kaggle consideration, a separate repair candidate and tests for
   both Adrena defects; this Trainer experiment does not waive them.

