# H6 strategy selection: unique non-KO Metal Defender completion

## Decision

`SELECT_FOR_ONE_ISOLATED_IMPLEMENTATION`

Selected mechanism:

`H6_UNIQUE_ACTIVE_METAL_DEFENDER_CONTINUITY_RESERVATION`

There is enough evidence to implement one narrow experiment. The evidence
proves a missed same-turn Metal Defender, not a Prize, a match win, or a
stronger full-game policy.

The frozen destination is:

`autonomous_gold_20260715/candidates/archaludon_attack_completing_energy_reservation_v1`

It must be a fresh direct child of exact historical-Silver:

- parent `main.py`:
  `analysis_outputs/reference_agents/historical_silver_archaludon_54495224/main.py`;
- parent SHA-256:
  `F4B578453C9D953BE94885144DD50E05DBA4510DF3340BE27ADE07495896046E`;
- unchanged `deck.csv` SHA-256:
  `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`.

H1, H2, H3, H4, H5 v1, and H5 v2 are absent siblings. In particular, live
H5 v2 submission `55073442` is not a source parent and no H5 code may be
copied or stacked.

## Verified facts used

- `FUTURE_HYPOTHESES.md` has SHA-256
  `0B03FEF73D5223A35E1A3908AD68C1EE722862828707F4577FDBFF70866E946A`.
- The source replay is
  `autonomous_gold_20260715/evidence/live_54927163_refresh_20260729_0344/episode_88584180_replay.json`,
  SHA-256
  `047A9FC4AB682E4F9E22F0AFE8547CB7F3016D98C2021E76C36D75C46CDD27B0`.
- At seat 1, row `90`, turn `10`, Active Archaludon ex `190#67` had
  exactly Basic Metal `8#116,8#117`; manual attachment was unused; the hand
  contained the unique visible Basic Metal `8#120`; and the exact legal
  Active attachment option existed. Opposing Active Marnie's Grimmsnarl ex
  `648#26` had 310 current HP.
- An independent rerun of the exact parent scorer at row `90` produced:
  Ultra Ball `1121#81` `20,000`; `8#120 -> 190#67` `19,700`;
  `8#120 -> 169#63` `10,300`; End `0`; Retreat `-100`; and Night
  Stretcher `1097#90` `-500`.
- The exact parent therefore played Ultra Ball. At the forced discard
  callback, row `91`, it scored `8#120` at `20,000`, selected it with Night
  Stretcher, searched Archaludon ex, and reached Retreat/End without attacking.
- Attaching `8#120` to `190#67` pays printed Metal Defender `253`,
  whose exact printed cost is three Metal and base damage is 220. It deals
  positive deterministic damage to `648#26`, does not KO its 310 current HP,
  and would take no Prize.
- Rows `111-114` prove the required action-neutral ordering:
  Full Metal Lab `1244#111`, exact Active attachment `8#121`, Jumbo Ice
  Cream `1147#94`, then Metal Defender `253`.
- Rows `142-143` prove an ordinary exact Active attachment followed by Metal
  Defender. That attack KOs the 160-HP opposing Active and is outside the
  non-KO H6 v1 certificate.

Relevant exact-parent source behavior is at `score_play` lines `739-799`,
`score_attach` lines `966-1022`, `score_discard` lines `1164-1210`, and
`choose_options` lines `1299-1321`. Replays are used here to diagnose the
resource/attack sequence, not as general action labels.

## Behavioral hypothesis

When exactly one known Basic Metal in hand is the sole missing cost of the
current two-Metal Active Archaludon ex's non-KO Metal Defender, reserve that
exact card, manual attachment, attacker, attack, and turn. Preserve inherited
actions that are positively certified not to destroy the route. If an
inherited action would consume a reserved object or end the turn before the
route completes, attach the stored Metal to the stored Active. After the
attachment is publicly confirmed, preserve safe inherited setup/healing/search
actions and select Metal Defender before Retreat or End.

This is a current-turn attack-continuity rule. It is not `always attach first`,
`never discard Metal`, a future-attacker valuation, or a Prize rule.

## Exact observable-state certificate

H6 may arm only at an ordinary `MAIN` callback when every predicate below is
positively proved from the current observation, legal options, and frozen card
data. Own hand and revealed effect choices are known state. Unrevealed deck
order, Prize identities, opponent hand, future draws, opponent identity, and
replay future are forbidden.

1. The game is ongoing; the callback is not deck request, setup, promotion,
   damage placement, or another forced context.
2. Exact historical-Silver's semantic action is computed exactly once for the
   callback and cached before H6 considers an override.
3. Our Active is Archaludon ex `190` with a known serial and exactly two
   attached cards.
4. Both attached cards are positively identified Basic Metal `8`; aggregate
   Energy IDs, `energyCards`, and serial counts agree. Unknown or mixed Energy
   fails closed.
5. `current.energyAttached` is false.
6. Our hand contains exactly one Basic Metal `8`, with a known serial.
7. A legal current `ATTACH` option binds that exact Energy serial to that
   exact Active serial.
8. Metal Defender `253` is not currently a legal Attack option.
9. Frozen card data positively identifies `253` as Archaludon ex's printed
   `{M}{M}{M}` attack with deterministic base damage 220. Projecting only the
   exact attachment pays the cost without retreat, evolution, Ability,
   Supporter, search, draw, coin result, or hidden information.
10. Current status, public restrictions, attacker/defender effects, Tools,
    Stadium, weakness, resistance, reduction, and prevention positively prove
    that the projected attack is legal and deals known effective damage
    strictly greater than zero.
11. H6 v1 is deliberately non-KO: projected effective damage must be strictly
    less than the opposing Active's known current HP. A KO belongs to existing
    Prize/finishing policy and does not arm H6 v1.
12. No currently certified same-turn terminal win, deterministic Prize-taking
    route, or exact public forced-defense/terminal-loss-avoidance route has
    precedence. Enumerate currently legal direct, attachment, retreat/switch,
    evolution, and Boss-to-attack conversions. Do not count a route requiring
    unknown draw, search result, chance, or opponent cooperation.
13. The inherited semantic action is either the exact stored attach, an
    explicitly conflicting action defined below, or a route-neutral action
    whose known immediate and mandatory follow-up effects can preserve every
    stored object. An unknown action/effect classification fails closed and
    delegates unchanged without arming.
14. No H6 transaction is already active. The certificate is recomputed from
    observation state, never from an episode, opponent ID, matchup label,
    or remembered hidden information.

Zero or two visible hand Metal, one or three Active Energy, a used attachment,
an attack already legal, a Bench-only completion, zero/blocked/uncertain
damage, or an existing higher-priority route therefore cannot arm.

## Route-neutral and conflicting actions

A route-neutral inherited action must be nonterminal and must not, by its
known effect or mandatory selections:

- move, discard, shuffle, or attach the stored Energy except to the stored
  Active;
- consume the manual attachment on any other card or target;
- retreat, switch, evolve, remove, or otherwise replace the stored Active;
- attack, end the turn, or create an unmodelled target/modifier change; or
- make the stored attack illegal or non-positive.

Full Metal Lab and Jumbo Ice Cream are explicit route-neutral actions when
their exact projected public effects retain the certificate. Known
search/setup/healing/tool actions may remain parent-selected only when every
mandatory minimum can be met without a reserved object. This includes Ultra
Ball only when at least two legal non-reserved discards are positively
available. Search results are handled from the later observation; H6 never
predicts hidden contents.

Boss or another action that changes the opposing Active is not overridden:
clear H6, delegate the cached parent action, and permit a fresh certificate
only from the resulting observation. An unknown effect also clears and
delegates. Lillie's Determination or another known action that would shuffle
the unique stored Metal is conflicting, not route-neutral.

Before attachment, the following cached parent semantics are conflicting:

- selecting the stored Energy in a discard/move/shuffle callback;
- attaching it to a different target;
- consuming the manual attachment with another card;
- Retreat or End; and
- a known effect whose forced resolution cannot preserve the stored objects.

At `MAIN`, replace a conflicting action with the exact stored
`Energy -> Active` attachment. Inside an already-authorized mandatory
selection, retain every non-reserved parent choice and replace only the stored
Energy with the highest-ranked legal non-reserved option until exact
`minCount/maxCount` is satisfied.

After attachment, preserve route-neutral actions. Replace Retreat, End,
switching/removal of the attacker, or another turn-consuming action with exact
Metal Defender `253`. Exact terminal/Prize/forced-defense precedence is
rechecked first.

## Precedence

1. Deck request, setup/forced legality, terminal result, and mandatory legal
   counts.
2. Exact same-turn match win.
3. Certified deterministic Prize-taking or exact forced-defense/terminal-loss
   avoidance route.
4. A cached exact-parent Boss/target-changing action, followed by clear and
   recomputation.
5. Revalidation or completion of an active H6 transaction.
6. A route-neutral exact-parent action.
7. H6 conflict substitution.
8. Exact historical-Silver.

H6 adds no Ogerpon, Crustle, Grimmsnarl, comeback, or opponent-specific
precedence. Public zero-damage/prevention gates naturally keep it out of
blocked matchups.

## Transaction, snapshot, and confirmation

The state machine is:

`CLEAR -> RESERVED_PRE_ATTACH -> [SAFE_EFFECT] -> ATTACH_SENT -> ATTACK_READY -> ATTACK_SENT -> CLEAR`.

Snapshot at arming:

`(seat, firstPlayer, turn, turnActionCount, Prize counts, attachment flag,
Active id/serial/HP/maxHP/status, exact attached Energy id/serial tuple,
stored hand Energy id/serial, attack id/cost/base damage, opposing Active
id/serial/HP/maxHP/Prize value, Stadium id/serial, Tools, public
damage/cost/prevention/restriction inputs, cached parent semantic action)`.

Also snapshot complete legal semantic options needed to bind the stored
attachment and, after confirmation, the stored attack. A safe multi-callback
effect additionally stores its card ID/serial, expected callback-context
sequence, mandatory counts, and the proof that reserved objects can be
excluded.

Stages:

1. `RESERVED_PRE_ATTACH`: revalidate all certificate fields before every
   override. Return safe cached parent actions unchanged. At source row `90`,
   return Ultra Ball unchanged and enter its safe-effect substage.
2. `SAFE_EFFECT`: use the exact parent ranking after excluding only reserved
   objects. At source row `91`, the frozen semantic result is discard
   `1097#90` and `1147#94`; `8#120` must not be selected. The subsequent
   Archaludon ex search remains inherited.
3. `ATTACH_SENT`: return only the legal option matching stored Energy serial
   and stored Active serial. A returned action does not advance state.
4. Confirm attachment only when the next observation shows that Energy absent
   from hand, attached to the stored Active, `energyAttached == true`, and
   exactly three Basic Metal with the expected serial tuple. Then enter
   `ATTACK_READY`.
5. `ATTACK_READY`: revalidate target, damage, legality, precedence, and every
   modifier after each route-neutral action. Preserve row `113` Jumbo Ice
   Cream. Select only exact Metal Defender `253` before Retreat/End.
6. `ATTACK_SENT`: repeat the same semantic attack on an identical callback.
   Clear only after an observed attack/turn end, turn change, terminal result,
   new game/deck request, or reset.

## Duplicates, idempotence, reset, and rollback

- Bind cards and Pokemon by `(card ID, serial, player, area, target serial)`,
  never by replay or option index.
- The certificate itself requires one hand Metal. Duplicate semantic options
  for the stored attachment or attack use the lowest legal option position.
- When a mandatory selection must replace reserved Energy, keep all
  non-reserved parent selections and fill from exact-parent score descending,
  then lower option position. Never select the stored serial.
- A returned action never advances a stage. Repeated identical callbacks
  return the same semantic action and do not duplicate effects.
- Clear on deck request, setup/new game, result, seat change, turn change,
  Active or stored-card mismatch, unexpected context, exception, confirmed
  attack, or inability to make a legal stored choice.
- Before a reserved object is consumed, any mismatch clears H6 and returns
  the already-cached exact-parent action unchanged.
- A route-neutral action is irreversible but certified not to consume the
  reservation. If later observation changes uniqueness, target, modifier, or
  precedence, clear and delegate from that actual state.
- After exact attachment, rollback cannot undo Energy placement. On any
  mismatch, clear and delegate from the actual attached state; never attach a
  replacement Energy, substitute another attacker, or force an unproved
  attack.
- If an unexpected mandatory callback cannot legally avoid the stored Energy,
  satisfy legality with the cached parent action and clear. The focused
  preflight must prove this cannot occur for any action H6 authorizes.
- On an H6 exception, clear and return the cached parent semantic action if it
  remains legal. Do not introduce random fallback behavior beyond the exact
  parent.

No state may leak across game, seat, or turn.

## Required focused positive and controls

Primary positive, `88584180:90-93` reconstructed counterfactually:

1. row `90`: H6 and parent both choose Ultra Ball `1121#81`;
2. row `91`: parent chooses `8#120 + 1097#90`; H6 chooses
   `1097#90 + 1147#94`;
3. Ultra Ball's inherited search choice remains Archaludon ex;
4. H6 attaches `8#120 -> 190#67`;
5. H6 selects Metal Defender `253`;
6. exact engine damage is 220, `648#26` goes from 310 to 90 current HP, and
   zero Prize is taken.

This proves transaction completion only. The recorded replay's alternate
full-game result is unknown and must not be asserted.

Mandatory action-neutral controls:

- `88584180:111-114`: Full Metal Lab before attachment, exact Active
  attachment, Jumbo Ice Cream after attachment, then Metal Defender;
- `88584180:142-143`: ordinary parent attach/attack remains semantically
  identical and H6 does not arm because the projected attack is a KO.

## Required negatives

All must return exact-parent semantic actions and leave no stale transaction:

- zero visible Basic Metal in hand;
- two visible Basic Metal in hand;
- Active with one attached Energy;
- Active with three attached Energy / attack already legal;
- `energyAttached == true`;
- missing or wrong-target legal attachment option;
- Active Duraludon, non-ex Archaludon, Cinderace, or any non-`190` card;
- one or more attached cards not positively Basic Metal `8`;
- completion exists only on a Bench Pokemon;
- asleep, paralyzed, confused, or another state that makes positive damage
  or legality uncertain;
- Cornerstone-style prevention, Crustle-style zero damage, resistance or
  reduction to zero, unknown card text, unknown formula, or unknown
  persistent restriction;
- projected Metal Defender KO, including `88584180:142`;
- any deterministic current terminal win or Prize-taking route;
- a certified forced-defense/terminal-loss-avoidance route;
- target-changing Boss/disruption action;
- unknown action/effect classification;
- safe-effect preflight with fewer legal non-reserved mandatory choices than
  required;
- stored Energy, Active, opponent Active, status, Stadium, Tool, Prize,
  damage, or cost mutation before confirmation;
- duplicate/reordered options, repeated callback, turn/seat/new-game reset,
  and exceptions;
- every H1-H5 certificate state and all H7-A/H7-B successor-allocation states.

## Forbidden generalizations

Do not implement:

- `never discard Metal`;
- `always attach before Items`, Supporters, Stadiums, healing, search, setup,
  or Bench development;
- a preference for all two-Energy Pokemon;
- Duraludon Raging Hammer, non-ex Coated Attack, Cinderace, or Bench-only
  completion;
- KO, terminal, Prize-route, Boss, target-selection, or comeback arbitration;
- speculative next-turn attacks, future draws, opponent-policy prediction,
  replay-future lookup, opponent IDs, episode/seed checks, or hidden deck/Prize
  access;
- H7 successor preservation, generic Active investment, or `save Energy`
  scoring;
- altered parent weights, a global Metal-discard penalty, or any H1-H5 stack;
- any claim that the source alternate line wins the match.

## Frozen verification contract

Implementation artifacts belong under:

`autonomous_gold_20260715/implementation/archaludon_attack_completing_energy_reservation_v1`

Evaluation artifacts belong under:

`autonomous_gold_20260715/evaluations/archaludon_attack_completing_energy_reservation_v1`

### Structural and focused gates

- Candidate has the same 12 runtime members as the parent; all non-`main.py`
  runtime files and `deck.csv` are byte-identical to the parent.
- The direct diff contains only H6 certificate/transaction code and one wrapper
  around the captured historical-Silver chooser. There is one last callable
  `agent`; deck request remains deterministic; no cache files are present.
- Focused tests cover every positive, negative, safe action, duplicate,
  option/serial permutation, repeated callback, mandatory-count,
  rollback/irreversible stage, exception, and reset above in both logical
  seats.
- The source Ultra Ball/discard/attach/attack transaction and both mandatory
  control sequences pass exactly.
- Invalid actions, exceptions, stale transactions, and mandatory-count
  violations are all zero.

### Both-seat exact-engine gates

Use:

`analysis_outputs/cynthia_v9_vs_v11_poffin_role_selection_20260713/seeded_engine`

whose authoritative 11-file canonical SHA-256 is
`466638706BD5C6915E25D1B3CB9E3D966390FBC263F4ED3153108E29C0194FFF`.

In each logical seat, independently complete the source transaction through
real Ultra Ball mandatory discards, inherited search, exact attachment, and
Metal Defender. Verify exact Energy/attacker serial binding, attack ID `253`,
220 damage, no KO, zero Prize, turn completion, and reset. Also execute the
Full Metal Lab/attach/Jumbo/attack and ordinary attach/attack controls in both
seats. Require zero invalid actions, action errors, exceptions, stale
transactions, and max-step hits.

### Complete-shadow gates

Freeze the existing 207-file correct-seat source manifest:

`autonomous_gold_20260715/implementation/archaludon_public_lethal_active_no_ready_successor_nonex_120_ko_v2/shadow_source_manifest.csv`

SHA-256:
`A252E906160A83A36DA916593C31766F4586481F1995E6E9C05210A697685EC3`.

It covers 11,473 callbacks. H6 shadow must:

- keep `88584180:90` parent-identical on Ultra Ball;
- show the exact reserved-Energy discard difference at row `91`;
- clear safely when the frozen replay resumes the incompatible parent branch;
- keep rows `111-114` and `142-143` action-identical;
- preserve 100% certificate-external semantic equality;
- classify and Root-inspect every additional natural difference;
- require every difference to be the exact H6 resource reservation followed,
  in exact-engine continuation, by stored attachment and Metal Defender; and
- report zero invalid actions, exceptions, stale transactions, or max-step
  hits.

An additional natural trigger is not accepted from prose alone. Root must
verify its complete public certificate and intended continuation. Any
certificate-external difference rejects the implementation.

### Immutable fixed-760 gates

Create a fresh specification and fresh raw output. Do not reuse H5 results.
The reference population specification is:

`autonomous_gold_20260715/implementation/archaludon_public_lethal_active_no_ready_successor_nonex_120_ko_v2/fixed760_spec.json`

SHA-256:
`DFE0321E6BDF2BAC4BCBF746D9B2950626719351B30A52EE15A81DC06B25E574`.

Only policy/strategy/verification/candidate identities and fresh output paths
may change. Freeze all engine, runner, opponent, panel, seat, seed, game-count,
max-step, trace, schema, and gate fields unchanged:

- checked paired runner SHA-256:
  `5EC25C98F2777FF61DE2DBD0A03A08519A7FEA4B2B4C510B5B8895BC2000E000`;
- checked battle runner SHA-256:
  `E1ABA0151CDAEE425B858511AA760CE5C5647D555DDEFBD69D7319C29C5B773B`;
- historical-Silver mirror: seeds `271828182..271828281`, 100 games per
  seat, 200 rows;
- seven-opponent adjacent population from the reference spec: seeds
  `271958313..271958352`, 40 games per opponent per seat, 560 rows;
- exact total: 760 unique `(panel, opponent, seat, seed)` rows;
- `--engine-seed`, full traces, and `--max-steps 1000`;
- exact schema:
  `(panel, opponent, seat, seed, baseline_win, candidate_win,
  baseline_result, candidate_result, baseline_steps, candidate_steps)`.

Baseline A/B must reproduce the frozen historical result `100/200`, adjacent
result `378/560`, and total `478/760`, with 760/760 duplicate summary and
byte-trace identity. Otherwise the run is invalid, not repairable by a custom
aggregate.

For implementation safety and limited-live eligibility require:

- exact schedule equality, no missing/extra/duplicate keys, and all command
  exits zero;
- zero start faults, action errors, exceptions, nonbinary results, and
  max-step hits across baseline A, baseline B, and candidate;
- no parent-win/candidate-loss flip;
- no regression overall, historical anchor, adjacent population, either
  seat, any panel/opponent/seat cell, or the inherited Kangaskhan/Crustle
  floor;
- Root inspection of every candidate-parent action/trace difference and exact
  agreement with the intended H6 mechanism.

Exact `478/760` neutrality is safety evidence only. A tiny positive paired
delta is also insufficient for formal-parent adoption.

## Live eligibility and adoption boundary

H6 is not currently live-eligible. H5 v2 submission `55073442` remains the
single live sibling; through the Root-supplied five-game checkpoint, all five
public games were parent-identical. H6 may be implemented and evaluated
locally, but it must not be packaged or submitted until Root closes or matures
the H5 probe and verifies that H5 is not recovering or causally supported. H6
must never replace H5 because of parent-path score noise.

After H5 closes, one limited H6 live probe may be considered only if every
structural, focused, both-seat engine, shadow, fixed-760, package, quota, and
prewrite gate passes. Exact-neutral fixed-760 may authorize only that sparse
exploratory probe, not adoption. Root alone owns the external write.

During a probe, correct-seat shadow every replay against the exact parent:

- parent-identical games and score movement are zero H6 evidence;
- any action fault, stale/incomplete transaction, certificate breach, wrong
  discard/attachment/attacker/attack, H6-owned causal loss, or verified
  parent-win/candidate-loss conversion stops the probe immediately;
- no natural H6 trigger by roughly 40 public games or the normal three-hour
  checkpoint closes the probe and retains H6 inactive;
- one trigger, one-seat-only exposure, or attacks without a verified match
  conversion do not justify a second submission or adoption.

Formal-parent review requires all of the following, followed by a new
independent Sol-Ultra judgment:

- at least four certificate-valid natural transactions in distinct games,
  at least two per logical seat and at least two distinct public board
  configurations;
- every transaction completes the exact stored attachment and Metal Defender,
  with zero causal regressions or faults;
- at least one root-verified terminal match conversion relative to exact
  historical-Silver;
- a preregistered trigger-enriched both-seat paired schedule with repeated
  mechanism exposure, positive primary historical-anchor movement, no seat or
  adjacent-cell regression, no worse severe floor, and practical absolute
  strength; and
- more than a lone `+1` or other tiny paired movement. Repeated independent
  mechanism-owned gains, not aggregate noise, must account for the result.

Until those gates pass, exact historical-Silver remains the formal parent.

## Regression risks and exact evidence needed next

Primary risks are spending the unique Metal on an exposed non-KO Active
instead of a future successor; replacing Ultra Ball's preferred Metal discard
with a healing/setup resource; delaying a draw/shuffle line; enabling an
opponent's damage-dependent attack; stale state across nested effect
callbacks; and extremely sparse natural exposure. H7 successor preservation
is a separate sibling and must not be imported to patch these risks.

The exact evidence needed next is:

1. a Sol-xhigh direct-parent implementation at the frozen destination and its
   source/deck/direct-diff hashes;
2. root-recomputed focused and both-seat exact-engine outputs proving the
   source transaction and both controls;
3. the complete 207-file H6 shadow manifest, all classified differences, and
   Root verification of each;
4. a fresh immutable fixed-760 specification with candidate and output hashes,
   followed by raw rows, manifests, summaries, traces, exits, fault counts, and
   duplicate controls;
5. an independent Sol-Ultra numerical audit and Root recomputation; and
6. only if limited-live gates pass after H5 closes, correct-seat public
   certificates and full H6 transaction/outcome comparisons.
