# Strategy selection after Hero maturity

## Decision

Select exactly one new mechanism:

`SEARCH_AWARE_ACTIVE_TERMINAL_BEFORE_NONTERMINAL_BOSS_V1`

Decision status:

`SELECT_CONDITIONAL_PREEDIT_GATE_ONLY__NO_SOURCE_EDIT_YET`

The rule must first be specified and verified as an isolated direct child of
exact historical-Silver:

- parent `main.py` SHA-256:
  `F4B578453C9D953BE94885144DD50E05DBA4510DF3340BE27ADE07495896046E`;
- deck SHA-256:
  `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`.

No candidate worker may edit source until the mandatory both-seat pre-edit
counterfactual below passes and Root freezes its raw output and hashes. Passing
that gate authorizes one isolated implementation from the exact parent; it
does not authorize packaging, live submission, or formal-parent promotion.

Hero closed as
`UNINFORMATIVE__SAFE__REJECT_FORMAL_PARENT__RETAIN_INACTIVE` at 41 public
games, `21-20`, with 2,332 correct-seat callbacks and zero starts,
differences, or faults. Its maturity report SHA-256 is
`F63A30BF0DA60D90CDD3A6D5DE452E7EF9B2FC13E919BA03AF689F17520C8495`.
Hero is not the parent of this rule.

## Verified evidence and candidate comparison

The controlling bundle is
`NEXT_HYPOTHESIS_EVIDENCE_BUNDLE_20260730.md`, SHA-256
`843DC281839E1327F7B660C697B2DCA0F2C5FD8992F9323A1F8898FCD0B6B96F`.

The selected source is `88827776`, memo SHA-256
`CB3F412FBF92AF912CE747DEC9F8237C7A38DCBBC483AA6D2D675332B2216EE0`,
replay SHA-256
`7B3D23A6F04179A10E6B972033D8D84151FDBD81FB6D6AB47AC3D6129DBADD8A`,
and Root output SHA-256
`3FE0588CF32565D945902F9BAE9171B031F75093D214DEC716495243B150C33E`.
Root verified that at callback `:134`:

- three Prizes remained;
- established Active Duraludon `169#66` had three Metal and could evolve;
- unchanged Active Mega Lucario ex `678#16` was worth all three Prizes and
  had exactly `220` HP;
- the parent chose a nonterminal Boss class over two legal Ultra Balls;
- the realized remainder of the same turn publicly exposed three Archaludon
  ex, evolved the same Duraludon, resolved Assemble Alloy, and used Metal
  Defender for the observed `220`.

This is the strongest source because it joins Prize arbitration, a winning
out, search-aware board formation, attacker completion, and turn-plan
commitment without an opponent-response interval. It aims at all remaining
Prizes rather than a nonterminal local improvement.

The alternatives remain separate:

- `88814136` is a clean public Pokégear-to-Boss final-Prize route, but it is a
  narrower search-choice continuation and its full Boss branch is also
  unexecuted.
- `88825590` proves a post-attachment non-ex `120` KO, but it is nonterminal,
  belongs to the already explored H5 family, and has unproved later resource
  cost.
- `88824363` requires survival plus a long next-turn
  search/evolve/retreat/Boss package.
- `88826681`, `88826155`, `88824894`, `88819392`, and
  `88814688`/`88820060` depend respectively on multi-turn Prize-race
  uncertainty, hidden Boss access, unknown future attackers, later access
  disruption, or hidden escape access. They are valuable mode/resource
  memos, not response-free terminal rules.
- `88826701` supplies no defensible deterministic countermeasure.

## Behavioral hypothesis

At an ordinary `MAIN` callback, try a publicly quantified Ultra Ball
evolution out before allowing an exact-parent **nonterminal** Boss diversion
when the unchanged opposing Active itself yields every remaining Prize and
the searched Active evolution has an exact same-turn Metal Defender KO.

The policy is deterministic and uses only the deck list, own public zones and
counts, current observation, and audited card/effect formulas. The initial
search is explicitly a high-confidence winning out, not a guaranteed hit.
It becomes an exact terminal transaction only after Archaludon ex is exposed
in the public Ultra Ball search choices.

### Initial certificate

Arm only when every condition holds:

1. The callback is ongoing ordinary `MAIN`, `minCount == maxCount == 1`, with
   complete hand visibility, exact `handCount`, positive unique serials, and
   no active transaction.
2. Compute the exact historical-Silver option scores once. Its unique
   top **semantic class** is legal Boss; equivalent Boss copies may tie, but
   no different semantic action may tie. Supporter is unused.
3. No currently legal attack, already-complete Boss route, or other fully
   certified response-free action wins the game. Every legal Boss target is
   nonterminal under the exact stored attack envelope.
4. Our unique Active is an established, legally evolvable Duraludon with
   exactly three supported Basic Metal, no relevant status/Tool/protection,
   and no manual attachment or retreat requirement. Archaludon ex is not
   already in hand.
5. The unchanged opposing Active has a positive unique serial, exact HP and
   Prize value equal to our remaining Prizes. Audited Metal Defender `253`
   damage is exact and lethal after evolving the same Active.
6. At least one semantic Ultra Ball is legal. The complete-hand simulation of
   its mandatory two-card payment must retain at least one legal Boss as the
   search-miss fallback and must not consume any required attacker, payment,
   target, or terminal component. V1 uses only the exact-parent discard
   semantic pair when every option-order-equivalent parent pair is route-safe;
   it does not add a general discard optimizer.
7. Public count-only search access passes. With total deck copies `N = 4`,
   let `U` be Archaludon ex copies not in any identified public zone, `D` the
   current deck count, and `P` the facedown Prize count. Require deck/prize to
   be the only unidentified zones and compute
   `P(hit) = 1 - C(P,U) / C(D+P,U)` when `U <= P`, otherwise `1`.
   Require `P(hit) >= 0.99`. Never read hidden deck or Prize identities.
8. Attack payment, evolution, Prize value, HP, Weakness, Resistance, Tool,
   Stadium, status, prevention, continuous effects, and card text are fully
   supported by audited registries. Chance, effect/damage-counter KOs,
   unsupported energy, or any ambiguity fails closed.

For only the canonical certified Ultra Ball:

`search_score = max(parent_ultra_ball_score, top_parent_score + 1)`.

No global Boss, Ultra Ball, evolution, Alloy, attack, matchup, or opponent
score changes.

## Precedence

In the isolated candidate:

1. engine legality, setup, deck request, result, reset, and forced callbacks;
2. an already legal exact terminal attack or shorter guaranteed exact
   terminal Boss transaction;
3. a currently active and still-valid transaction;
4. this search-aware terminal attempt;
5. exact historical-Silver.

Thus the new rule beats only a nonterminal diversion. It never replaces a
current guaranteed win, forced defense, higher-certainty terminal route, or
irreversible transaction.

## Mandatory pre-edit both-seat counterfactual

Before any source edit, a checked exact-engine fixture must start from the
Root-hashed `88827776:134` state and execute the no-Boss branch in both logical
seats. The semantic contract is:

1. choose Ultra Ball `1121#81`, not Boss;
2. discard route-safe Cinderace `666#72` and Boss `1182#99`, retaining the
   other Boss copies;
3. select exposed Archaludon ex `190#67`;
4. evolve unchanged Active Duraludon `169#66`;
5. accept the standard Assemble Alloy activation;
6. select Basic Metal `8#93` and `8#114` from discard and attach both to that
   evolved Active;
7. before another Item, attachment, or setup action, use Metal Defender `253`
   into unchanged Mega Lucario ex `678#16`;
8. observe exact `220` damage, three Prizes taken, and terminal victory in the
   same turn with no Boss play or opponent action.

Serials above define the source fixture only; runtime policy binds semantic
roles and never tests an episode, row, seat, opponent id, or fixed serial.

The pre-edit gate must also:

- reproduce the source public-access inputs and Root-verify the computed
  search probability (expected source case: `D=8`, `P=3`, `U=3`,
  `P(hit)=164/165`);
- repeat the terminal branch after seat mirroring, serial remapping, option
  permutation, equivalent duplicate options, and repeated callbacks;
- prove zero invalid actions, exceptions, nondeterminism, action errors,
  stale state, and max-step hits;
- run a search-miss branch with the same public count model: retain Boss,
  clear the terminal transaction at the public search callback, and delegate
  exact historical-Silver from the actual irreversible state;
- run missing-evolution, changed-target, changed-Prize, changed-modifier, and
  post-search attack-illegal branches and prove fail-closed delegation.

Root must freeze engine, fixture, action trace, output, and hashes. If the
unchanged Active does not receive the `220` terminal hit in either seat, the
search probability is not reproducible from public counts, or the miss branch
cannot preserve a legal Boss fallback, the decision becomes
`PREEDIT_GATE_FAILED__NO_IMPLEMENTATION`.

## Transaction contract

Snapshot:

`(game epoch, seat, first player, turn/action count, contexts, Prize counts,
supporter/attachment/retreat flags, complete hand and count, public
Archaludon-ex ledger, deck/prize counts and access probability, semantic
option multiset, Ultra Ball serial, permitted discard multiset, retained Boss
serials, both Active fingerprints, Stadium and modifiers, stored evolution,
Alloy Energy serials, attack id/payment/damage)`.

Stages:

`CLEAR -> ULTRA_BALL_EMITTED -> DISCARD_EMITTED -> SEARCH_EMITTED ->
EVOLUTION_EMITTED -> ALLOY_ACTIVATE_EMITTED -> ALLOY_SOURCE_EMITTED ->
ALLOY_TARGETING -> ATTACK_EMITTED -> CLEAR`.

- Returning an action never confirms it or advances a stage. Only a novel
  public observation/log proving exactly the expected mutation advances.
- Identical retries return the same semantic action without another parent
  call. Option reordering rebinds by semantic identity.
- Equivalent copies use the lowest positive serial; duplicate options for the
  stored semantic action use the lowest current option position.
- Confirm Ultra Ball only from its exact removal and standard discard effect;
  confirm discards only from the selected serials entering discard; confirm
  search only from the selected Archaludon ex entering hand; confirm evolution
  only on the same Active position/stack; confirm Alloy only from its standard
  effect and selected Energy leaving discard/appearing on that Active.
- At every stage revalidate the unchanged opposing Active, Prize equality,
  exact `220` terminal damage, stored attacker, payment, and public modifiers.
  Once the terminal attack is legal, no unrelated Item or setup action may
  preempt it.
- Before Ultra Ball confirmation, mutation clears and returns the cached
  exact-parent action if still legal. After any irreversible action, never
  replay the stale initial Boss: clear and delegate exact parent from the
  actual state.
- Search miss is an expected rollback, not permission to invent a target.
- Clear on result, deck request/new game, seat/turn change, action-count
  rollback or unexplained jump, semantic-option mutation, target/evolution/
  attack mismatch, exception, observed attack, or turn end. State never
  crosses games, seats, or turns.

The final exported `agent` must be the last top-level runtime definition or
assignment in `main.py`; no later wrapper, alias, or executable statement may
replace it. Loader-last, loader-only, deck-request, import, and cache-free
structure checks are mandatory.

## Mandatory implementation tests

Positive component fixtures are `88827776:134`, `:136-:143`, and `:147`;
the policy-positive continuation is the new no-Boss engine trace, not the
recorded Boss branch. Test the complete transaction in both seats, every
stage retry, serial/option permutation, equivalent Boss/Ultra Ball/
Archaludon-ex/Metal duplicates, and reset/exception paths.

Important parent-identical negatives include:

- `88814136:151-152` Pokégear/Boss terminal search;
- `88825590:59` post-attachment non-ex `120` KO;
- `88824363:112` opponent-forced discard;
- `88826681:135-136` mirror two-hit race;
- `88826155:132/135`, `88824894:79`, `88819392:120`,
  `88814688:88`, and `88820060:53`;
- Hero source `88643491:77`;
- frozen H1/H2/H3/H4/H5/H6/H7-A, Bench-evolution, setup, promotion,
  attachment, healing, and exact-terminal controls.

Also remain parent-identical when any initial certificate term fails:
non-Boss parent winner; direct terminal attack/Boss; insufficient Prize value;
nonlethal or ambiguous `253`; wrong/new Active; evolution unavailable;
unsupported Energy or modifier; Archaludon ex already in hand; Ultra Ball
missing/illegal; incomplete hand; unsafe discard; Boss fallback lost; access
probability below `0.99`; unidentified zone; hidden identity use; supporter
already played; status/protection/chance damage; or wrong context/count.

## Isolation, evaluation, and adoption gates

After the pre-edit gate passes, one Sol-xhigh worker may implement only this
rule in a fresh direct-parent directory. Require:

- exact source/deck identities, only intended runtime changes, compile/import,
  legal 60 cards/one ACE SPEC, loader-last, zero caches;
- focused positives/negatives and both-seat exact-engine branches above;
- complete current replay shadow. The primary first difference must be
  `88827776:134`, exact parent Boss to certified Ultra Ball. Every later
  difference must belong to the stored transaction; certificate-external
  callbacks must be exact-parent-equal;
- immutable identical-seed/both-seat historical-Silver and adjacent
  evaluation, unique schedule keys, duplicate controls, exact traces, and
  zero start faults, invalid actions, action errors, exceptions, stale
  transactions, and max-step hits;
- no parent-win/candidate-loss flip and no overall, anchor, adjacent, seat,
  opponent, or cell regression for destructive-safety passage.

Neutral local results are safety evidence only. Formal promotion requires
practical absolute strength and primary-anchor movement, both-seat and
adjacent safety, repeated completed transactions across at least two board
configurations, at least two activations per seat, no attributable regression,
and at least two Root-verified mechanism-owned parent-loss/candidate-win
conversions covering both seats. Score movement from parent-identical games
does not count.

## Cumulative integration and practical live eligibility

Per the controlling user policy, isolated verification comes first, but a
later experimental/live candidate may carry frozen Hero and other
destructive-safe verified rules. Exact historical-Silver remains the formal
comparison and rollback anchor; Hero remains a dormant overlay, not a parent.

At a clear callback, evaluate all components against the same observation and
one cached exact-parent decision. Collision order is:

1. forced legality/result/setup/reset;
2. already legal direct terminal action;
3. guaranteed response-free terminal rule, preferring fewer irreversible
   steps;
4. this `P(hit) >= 0.99` search-out terminal attempt;
5. certified forced-loss defense and deterministic Prize conversion;
6. attack/energy continuity and resource rules;
7. Hero's Cape non-KO survival;
8. setup heuristics;
9. exact historical-Silver.

Once an irreversible transaction is confirmed, only its validated
continuation may act. If another rule becomes eligible mid-transaction, two
rules propose different actions at the same precedence, or ownership/
continuation was not explicitly interaction-tested, clear component state and
delegate exact historical-Silver from the actual state. Never run two
transactions simultaneously.

Every callback must emit stable per-rule telemetry:

`rule_id, eligible, rejection_reason, proposed_semantic_action,
suppressed_by, precedence_rank, winner_rule, exact_parent_action,
final_action, transaction_stage, snapshot_id, duplicate_or_retry,
rollback_reason, attribution_owner`.

Before packaging, compare the integrated candidate simultaneously against
exact parent and every isolated included component. Require:

- pairwise and synthetic all-eligible collision tests, including new-rule
  versus Hero, active-transaction collisions, retry, rollback, reset, both
  seats, and option permutations;
- integrated differences equal only the tested precedence union of isolated
  component differences; no interaction-created external difference;
- exact-parent, isolated-new, isolated-Hero, and integrated shadows with
  per-rule action attribution and zero faults;
- the full fixed evaluation and clean extracted-package both-seat smoke.

If all destructive gates pass, a Root final judgment may authorize one
practical cumulative live probe even with neutral local win rate. Natural
Hero firing is retained and attributed to Hero; absence of Hero activation is
not removal evidence. Any rule-owned or collision-owned loss is analyzed from
the changed callback and transaction trace. Unrelated losses remain memos.

## Principal uncertainty and next evidence

The realized turn proves the components but not the no-Boss engine branch.
The initial search can miss: under the expected source public counts the miss
risk is `1/165`. Ultra Ball and two discards are paid before the hit becomes
public, so preserving Boss fallback and proving miss rollback are essential.
Damage/modifier drift, incorrect public-zone accounting, redundant post-Alloy
setup, and transaction collisions are the main regression risks.

The exact next evidence is therefore the frozen pre-edit both-seat hit trace,
the matched search-miss/fallback trace, public-access calculation, and zero-
fault logs. Until those exist, implementation permission is withheld.
