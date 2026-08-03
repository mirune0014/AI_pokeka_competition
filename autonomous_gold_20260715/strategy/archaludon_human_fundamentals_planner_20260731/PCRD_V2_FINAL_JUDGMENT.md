# PCRD v2 final rule judgment

## Decision

**REJECT `PUBLIC_COMBAT_RETURN_DOMINANCE_V1`.** It is execution-safe, but it is
not a strength improvement and its selector repeatedly spends a non-ex
Archaludon evolution on an Active that the same public evolved reply certainly
KOs, solely for nonlethal chip.

Select exactly one next hypothesis:

> **`PUBLIC_COMBAT_RETURN_DOMINANCE_V2`: retain v1's exact public combat/return
> oracle and semantic transaction, but admit a plan only through a hard
> lexicographic hierarchy fed by a serial-level, post-action and post-public-
> reply resource ledger.**

This is one repaired selector rule. It does not add effect-registry coverage,
Trainer-purpose rules, matchup IDs, replay-key branches, or learned behavior.

## Verified facts used

- Judgment request current SHA-256:
  `352A143E7805186A4DAF29E134CF3B6462A16B5212392B9CB1D20FC0AAD66C4E`.
- Direct strength parent V2:
  `5A6B82E159CD7EC297AFD2B520580F97DDB01B7D500683F053B4C7096192CA0C`.
- v1 implementation substrate:
  `DCF7A4AB477CEA3743E7053DCABD0B1FBFDA20B13E84D256995A3557209400F1`.
- Root fixed760 report SHA:
  `3C0233B9CA83402DB1FFE85875F736768CDBC4B46768DE644AADAFE8715A74B5`;
  numerical audit SHA:
  `D6E454B1117C425A64E1BC8ECDECFC06449515D7178438098343250DC15542D0`.
- There are 760 unique paired rows: V2 `474/760`, v1 `474/760`, one
  gain, one regression, and 758 ties. Historical-Silver is unchanged at
  `99/200`; seat 0 is `+1` and seat 1 is `-1`. Every adjacent opponent/seat
  outcome bucket is unchanged. All 48 commands exited zero; 2,280 summaries
  have zero action errors, max-step hits, not-started games, or duplicate
  mismatch.
- Sixteen traces differ and contain 17 completed evolve-840-to-169 then Coated
  Attack signatures. The executor completes correctly; selection is the
  defect. The qualitative audit SHA is
  `5A20550D7634404128D7AE8995ADFCA58434515B2810617E5912F5476BFB2C28`;
  adjacent addendum SHA is
  `C1A4F32B636C3B26938C133E37EAFE297347FCBE020BB560A4963524DB765994`.
- Of the 16 first decisions, three are sound, one is conditional/defensible,
  and twelve are unsound. In adjacent game 22, the extra 40 chip also raises
  the opponent's Relicanth-enabled Raging Hammer return by 40; both attackers
  remain KO'd.

This fails practical promotion: no aggregate or primary-anchor movement, an
opposite-seat regression, repeated unsound behavior in both seats and both
panels, and no floor improvement. Exact adjacent outcome neutrality does not
make the four unsound adjacent decisions acceptable.

## Frozen implementation contract

### Parent and substrate

1. Create one isolated candidate from the exact v1 package. Preserve the full
   V2 `main.py` bytes as an exact prefix and preserve `deck.csv`, `cg/`, and
   `requirements.txt` byte-for-byte.
2. The sole behavioral parent is the captured exact V2 callable
   `_pcrd_v2_agent`, not v1's final selector. The final `agent` must call it
   exactly once on every callback. Every non-admission or failure returns that
   exact legal V2 action.
3. Reuse v1's `_pcrd_public_combat_oracle`, public-effect inventory, threat
   graph, projections, semantic binding, and transaction executor. Replace
   only the defective resource/plan-selection layer and the telemetry needed
   to prove it. Set the rule ID to `PUBLIC_COMBAT_RETURN_DOMINANCE_V2` and
   record the V2 parent SHA, v1 substrate SHA, and the root-verified SHA of this
   contract.

### Required functions and fields

The worker must replace current-observation pooling in `_pcrd_resources` /
`_pcrd_plan_fields` with these logically separate operations (the exact names
below are the contract names):

- `_pcrd_post_action_resource_ledger(obs, actions, projected_active)`;
- `_pcrd_worst_exact_public_reply(threat_graph)`;
- `_pcrd_post_reply_resource_ledger(post_action_ledger, reply)`;
- `_pcrd_exact_backup_conversion(obs, plan, reply)`;
- `_pcrd_lexicographic_layers(plan)` and
  `_pcrd_compare_lexicographic(candidate, parent)`;
- `_pcrd_doomed_chip_only_evolution(candidate, parent)`.

Each ledger row is keyed by `(card_id, serial)` and records host serial where
applicable. It must distinguish:

`HAND_READY`, `DECK_ACCESSIBLE`, `DISCARD_RECOVERABLE_NOW`,
`DISCARD_NOT_RECOVERABLE_NOW`, `IN_PLAY_PROTECTED`, `IN_PLAY_EXPOSED`,
`IN_PLAY_CERTAINLY_LOST_ON_REPLY`, `ATTACHED_AND_RECOVERABLE`, and
`ATTACHED_AND_LOST`.

The post-action ledger applies every proposed consume/move/attach/evolve. The
post-reply ledger applies the worst exact `READY_NOW` or
`KNOWN_PUBLIC_RESOURCE` reply. A certain Active KO removes its top Pokemon,
all pre-evolutions, attached Energy, and Tool from retained in-play value.
Discard is recoverable only when an exact surviving recovery resource can
legally recover that card; recovery capacity cannot be counted more than once.
Unknown deck identities or recovery ambiguity confer no advantage and cause
fallback if decision-relevant.

`_pcrd_plan_fields` must expose at least: `current_win`,
`certain_terminal_reply`, `current_prizes`, `opponent_prizes_after`,
`certain_return_prizes`, `current_attacker_survival`,
`public_return_prevented`, `next_turn_payable_attack`,
`exact_backup_ready`, `exact_backup_next_prizes`,
`exact_turns_to_next_prize`, `post_action_ledger`, `post_reply_ledger`, and
`doomed_chip_only_evolution`. Raw damage or `hits_to_same_prize` is not an
independent admission benefit; chip matters only when it crosses an exact
current-Prize or ready-backup conversion boundary.

### Hard precedence

Compare complete plans in this order; a lower layer never offsets a higher
layer:

1. engine legality, inherited terminal/forced ownership, and completion of an
   already-started transaction;
2. exact current win;
3. avoidance of an exact next-reply terminal loss;
4. current Prize result;
5. exact public-return prevention, attacker survival, and attack continuity;
6. exact ready-backup conversion and next Prize/finish timing;
7. post-action, then post-reply retained-resource Pareto comparison;
8. exact semantic tie returns V2. Serial order may choose only between
   physically equivalent copies of the same already-admitted semantic plan.

Hard negative: when candidate and V2 have the same current Prize, same
survival/terminal result, and same exact next-attacker Prize timing, a non-ex
evolution into the same certain return KO is ineligible if its only benefit is
nonlethal chip or if it worsens the public return. This includes damage that
increases an opposing Raging Hammer. Conversely, do not apply that ban when
Coated Attack takes a current Prize, prevents the visible Basic return/forces
a public bypass, makes the attacker survive, or crosses an exact ready-backup
Prize boundary.

## Frozen behavioral keys

These keys are fixtures only; production policy must not inspect opponent name,
seat, seed, game ID, or replay history.

Required positives (retain v1's evolve-to-Coated-Attack semantic action):

- `historical_silver`, seat 0, game 71, seed `271828253` — Basic prevention /
  Boss tax;
- `historical_silver`, seat 0, game 89, seed `271828271` — current KO plus
  Basic prevention;
- `arch_peak`, seat 0, game 19, seed `271958332` — current KO and protection
  against the visible Basic route; do not treat the later hidden evolution as
  public at selection time.

Conditional boundary:

- `historical_silver`, seat 1, game 2, seed `271828184` — admit only if the
  exact post-reply ledger shows the evolved Active is not certainly lost and
  the first strict layer is public-return/continuity; otherwise return V2 with
  a recorded exact reason. Either result must not pass through the doomed-chip
  exception.

Required negatives (return the exact V2 semantic action at the first
difference, with `DOOMED_CHIP_ONLY_RESOURCE_LOSS` or a more specific
fail-closed reason):

- Historical seat 0: games/seeds `10/271828192`, `12/271828194`,
  `57/271828239`, `67/271828249`;
- Historical seat 1: `16/271828198`, `25/271828207`, `29/271828211`,
  `30/271828212`;
- `arch_peak` seat 0: `9/271958322`;
- `arch_peak` seat 1: `18/271958331`, `25/271958338`;
- `arch_shumpei` seat 0: `22/271958335` (telemetry must show the 40-damage
  Raging Hammer amplification as well as the lost evolution stack).

## Fail-closed and transaction/telemetry requirements

Unsupported relevant public effects, incomplete threat inventory, ambiguous
serial/role binding, non-unique worst exact reply, decision-relevant ledger or
recovery uncertainty, incomparable parent plan, multiple non-equivalent best
plans, exception, stale owner, or invalid transition must select V2. Never map
unknown to zero and never assume a hidden card, draw, evolution, Boss, or
opponent policy.

Keep v1's serial/target/effect-bound whole transaction, irreversible transition
proofs, duplicate-callback semantic replay, completion, and rollback behavior.
Telemetry must serialize: rule/contract/parent/substrate IDs; parent and final
semantic actions; chosen source/reason; every lexicographic layer and first
difference; chosen public reply; post-action/post-reply ledgers and certainly
lost serials; backup-conversion proof; doomed-chip decision; unsupported
reasons; transaction start, each callback, completion/rollback, duplicate
retry, and exception. Counters must separate starts, completions, all fallback
reasons, doomed-chip rejections, duplicates, rollbacks, and exceptions.

## Minimal falsifiable verification gates

Before simulation, all must pass:

1. V2 prefix, deck, and non-`main.py` package hashes are preserved; compile and
   all inherited V2 tests pass.
2. Focused ledger/hierarchy tests prove: a certain KO loses 840, 169, attached
   Energy/Tool; recovery capacity is not duplicated; higher Prize/prevention/
   exact-backup layers beat resources; nonlethal chip alone cannot; unsupported
   public effects return exact V2.
3. Frozen 16-position test gives exactly positive 3, conditional 1 with an
   explicit reason, and negative 12 as specified, with no ID/seed branching.
4. At least one complete admitted transaction in each seat reaches the bound
   attack; option reorder/duplicate callback returns the same semantic action;
   starts equal completions; invalid actions, stale transactions, duplicate
   mismatches, exceptions, and max-step hits are zero.

Later adoption still requires root-verified paired evaluation. A tiny net delta
alone is insufficient: the primary Historical anchor and both seats must be
safe, the 12 rejection mechanism must repeat across buckets, the three sound
routes must remain, adjacent opponent/seat cells must not regress, every new
trace difference must match a declared lexicographic class, and all execution
fault counters must remain zero.

## Risks and next evidence

The main regression risks are an overbroad doomed-evolution ban suppressing
Basic prevention, treating all discard as dead despite Night Stretcher,
overvaluing hand location when chip crosses a real backup KO boundary, and
using one public reply as an opponent-policy prediction. Game 2 remains the
only material conditional boundary. Public-effect coverage remains narrow and
must fail closed rather than being expanded in this candidate.

The exact evidence needed next is the isolated candidate hash, focused test
output for the 3/1/12 matrix, both-seat transaction telemetry, and then raw
paired rows/traces from the root-frozen V2-versus-v2 schedule with independent
row, seat, duplicate, action-error, max-step, activation, and changed-position
verification.
