# Strategy selection after cumulative v2

Decision:

`SELECT_PERSISTENT_PUBLIC_BOSS_ACCESS_LEDGER_WITH_PLAN_EQUIVALENT_LAST_COPY_DISCARD_GUARD_V1__PRE_EDIT_ENGINE_GATE_REQUIRED`

This is exactly one isolated public-state hypothesis. It is not source-edit,
packaging, live-write, or formal-parent authorization. The implementation
target remains exact historical-Silver. The passive ledger may later be
integrated with the eight-rule cumulative resolver only after the isolated
candidate passes every gate below.

## Verified facts used

- Formal parent:
  `analysis_outputs/reference_agents/historical_silver_archaludon_54495224/main.py`,
  SHA-256
  `F4B578453C9D953BE94885144DD50E05DBA4510DF3340BE27ADE07495896046E`.
- Frozen 60-card deck SHA-256:
  `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`;
  it contains exactly four Boss's Orders `1182`.
- Current cumulative v2:
  `autonomous_gold_20260715/candidates/archaludon_cumulative_public_hierarchy_megabrave_lock_veto_v2/main.py`,
  SHA-256
  `DEE5092B6785DF7A63752C7AAE497051D08DCC62F7723CD9786225A0C5A99DE8`.
  Root's controlling audit reports parent=candidate `478/760`, historical
  `100/200`, adjacent `378/560`, seat 0 `243/380`, seat 1 `235/380`, zero
  gains/regressions/faults, and a 261-replay/14,464-callback union shadow.
- Positive raw replay:
  `autonomous_gold_20260715/live/55083165/maturity_20260730_0127/episode_88819392_replay.json`,
  SHA-256
  `4D625ADF892F1D0DC1453E31219025A96C4474D509E5B1E36819225A22F22698`.
  Root verification:
  `autonomous_gold_20260715/root_verification/archaludon_last_boss_discard_88819392_20260730/root_verification.json`,
  SHA-256
  `FF33866BAFF5A7F55093B6C5DF73A436DC3906B28C5A8BC1063CC22BA32C7740`.
  Bound memo SHA-256:
  `36BEA00F39C62663657029CA587F8D4F37B31420E12BD40A9241ED62AC2A666C`.
- In episode `88819392`, Archaludon is seat `0`. At row `119`, turn `10`,
  exact historical-Silver and cumulative v2 play Ultra Ball. At its mandatory
  two-card discard callback, row `120`, both return positions `[0,2]`,
  semantically Boss `1182#39` plus Basic Metal `8#57`. Three other Boss
  copies `#41/#40/#38` are already in public discard. Thus this action changes
  held deterministic Boss access from one to zero. The legal semantic
  alternative `[1,2]` is non-ex Archaludon `840#31` plus the same Metal
  `8#57`, retaining Archaludon ex `190#9` and Boss `#39`.
- A direct read-only cumulative-v2 rerun at row `120` confirmed owner
  `CLEAR`, all eight current proposals ineligible, exact-parent attribution,
  and the same semantic `[Boss #39, Metal #57]` action. On the recorded parent
  branch, rows `121-123` select Duraludon, Bench it, and use Metal Defender
  `253`. The alternate discard branch has not yet been executed and must not
  be called equivalent until the pre-edit gate below proves it.
- Visible opposing Bench Froslass/Munkidori targets are one-Prize targets, so
  a retained Boss has public route value. Later Unfair Stamp destroys the
  source game's causal attribution. This source proves a resource transition,
  not an alternate win.

## Selected hypothesis and deck-theory rationale

When an exact, public ledger proves that a mandatory discard would consume the
last held Boss while every other deck copy is already in public discard,
replace only that Boss with a uniquely plan-equivalent redundant card. Do so
only if the same search, backup formation, Energy disposition, attacker,
attack ID, target, damage, and current-turn Prize result remain executable.

This fits the Archaludon plan better than a generic discard score. Boss is a
finite finishing and Prize-route resource; preserving its last deterministic
copy can retain access to a fragile or damaged Bench target. In the source,
the Active attacker is already ready, the same Metal remains discard fuel,
Ultra Ball can still form the Basic backup, and the retained Archaludon ex is
the intended evolution bridge. The rule is not `never discard Boss`, does not
claim the source converts to a win, and gives terminal conversion, forced
defense, current Prize conversion, attack continuity, survival, and sole-board
formation precedence.

The mechanism jointly addresses setup, board formation, backup readiness,
Energy/hand/deck management, attack continuity, Prize exchange, and finishing
without using opponent identity or replay hindsight. Its principal risk is
discarding a non-ex evolution whose one-Prize body or attack later matters;
that risk is controlled by the exact plan-equivalence and public-distinct-value
vetoes below.

## Public inputs and ledger contract

Only these inputs are allowed:

- frozen deck manifest/counts and audited public card text;
- our complete visible hand (`handCount == len(hand)`), public discard/lost
  zones, board, attached cards, Stadium, deck count, and Prize **count only**;
- current public `looking`/revealed choices, selection context/effect/card,
  option semantics, unique positive card serials, action logs, seat, turn,
  action count, and result;
- opposing public Active/Bench cards, HP, attached cards, Tools, Stadium,
  Prize count, and exact currently payable attacks.

Hidden deck order, Prize identities, opponent hand identities, future draws,
archetype/opponent IDs, replay IDs, realized opponent actions, and Gold actions
are forbidden.

The ledger is generic bookkeeping but this v1 action consumer is Boss-only.
For each own card serial it may hold only `HAND`, `PUBLIC_DISCARD`,
`PUBLIC_LOST`, `CURRENT_REVEAL`, or `UNKNOWN_HIDDEN`. A card is
deterministically held-accessible only while confirmed in our complete hand;
a current reveal becomes accessible only after the next novel observation
confirms selection into hand. Unselected revealed cards, shuffled cards,
unrevealed deck cards, and all Prize cards are `UNKNOWN_HIDDEN` and contribute
zero deterministic access.

The positive guard requires all four Boss copies to be uniquely accounted:
exactly three in public discard, exactly one in complete hand, none in lost or
another public zone, and zero unidentified copies. It must not infer that an
unknown copy is accessible. Counts and serials must conserve against the
60-card deck, public zones, `deckCount`, and Prize count or fail closed.

### Lifetime, duplicate, and reset semantics

- Key state by `(game_epoch, yourIndex, firstPlayer, deck_sha)`. Persist across
  ordinary turn changes.
- Update a zone transition only from a novel confirmed public observation or
  matching log. Returning an action never advances the ledger.
- Repeated identical callbacks return the cached semantic action and leave
  ledger and transaction stage unchanged.
- After shuffle-to-deck or hand disruption, any formerly known serial absent
  from public zones becomes `UNKNOWN_HIDDEN` immediately. Unfair Stamp is a
  mandatory fixture: it must erase the preserved Boss's held-access status,
  not leave a stale known card.
- A card entering hand from search, reveal, return, draw, or Prize becomes
  known only when the complete hand confirms it; no hidden source is inferred.
- Reset on new game/setup, result, seat or first-player change, turn/action
  regression, observation discontinuity, unsupported zone effect, malformed
  or duplicate serial, conservation failure, incomplete own hand, exception,
  or emergency fallback. Reset delegates the exact parent on that callback.

## Exact trigger and action contract

At a mandatory Ultra Ball discard callback:

1. Context/effect/card text must exactly identify a two-card Ultra Ball
   discard, with a complete hand and unique semantic options.
2. The cached exact-parent action must be exactly one Basic Metal plus the
   uniquely held last Boss. The supporter window must already be used; this
   v1 does not construct a same-turn Boss route.
3. The Boss ledger must satisfy the four-copy certificate above.
4. Exactly one legal alternate pair must retain the same parent-selected
   Metal and replace only Boss with non-ex Archaludon. Archaludon ex must
   remain in hand as the evolution bridge.
5. The current attacker, all attached Energy, current attack payment, Stadium,
   board, Ultra Ball search pool, and Bench capacity must be unchanged. At
   least one public opposing Bench target must have positive Boss route value.
6. No terminal, forced-defense, higher/equal-Prize conversion, reserved
   attack, current-payable survival, sole-board formation, or other frozen
   transaction may own or propose the callback.
7. Emit the alternate pair by semantic `(card_id, serial)` binding, not source
   option positions; confirm the exact discard on the next novel observation,
   then clear and delegate. Do not force later search, Bench, or attack
   actions.

Source-only semantic difference:

`88819392:120  [Boss 1182#39, Metal 8#57] -> [non-ex Archaludon 840#31, Metal 8#57]`.

### Hard negative boundaries

Delegate exact historical-Silver if any of these holds:

- fewer/more than four audited Boss copies, any unidentified Boss copy, more
  than one held Boss, or any unsupported deterministic recovery/access chain;
- parent does not discard the unique Boss, the discard is not exact Ultra
  Ball `2-of-N`, or the alternate pair is absent/nonunique;
- the replacement changes the selected Metal, consumes Archaludon ex, changes
  Ultra Ball's legal search/Bench capacity, or changes the certified current
  attack prefix;
- non-ex Archaludon has distinct public value now: it is reserved, is the sole
  same-turn/next-step attacker or evolution, crosses a current Prize or
  survival breakpoint, answers a public effect that Archaludon ex does not,
  or is required by another frozen certificate;
- Boss has an exact same-turn terminal/forced-defense use, no visible future
  Boss target has positive route value, or the current board/damage/payment
  calculation is unsupported;
- incomplete hand, hidden Prize/deck inference, duplicate serial, option
  mutation, unsupported card text/modifier, ledger desynchronization, or any
  exception.

Mandatory parent-identical negatives include: `88819392` with a second held
Boss; one Boss moved to unknown deck/Prize; Boss replaced by Archaludon ex or
the only Energy; no visible Bench target; supporter unused with a certified
current Boss route; each existing rule's positive fixture; the all-eligible
collision family; and `88775564`, where changing a damage-engine target does
not cross a survival boundary.

## Precedence and interaction with all eight current rules

Exact-parent terminal priority remains rank 1 and an active transaction owner
remains rank 2. The passive ledger may reconcile public facts once before
proposal evaluation but is never an action owner and must not mutate during
speculative component evaluation. The discard consumer is clear-state only
and, if eventually integrated, ranks below all eight rules (new rank 11;
exact-parent fallback moves to rank 12).

| Current rule | Required interaction |
|---|---|
| H2 last-Prize Stretcher/Metal/Boss | Rank 3 suppresses the guard; never alter its Boss, Metal, or terminal transaction. |
| Search-aware Active-terminal | Rank 4 suppresses the guard; its audited discard/access ledger and exact terminal route remain self-contained. |
| H1 visible ready terminal threat | Rank 5 suppresses the guard; immediate forced-defense Boss use outranks future Boss preservation. |
| H5 v2 lethal Active/no ready successor | Rank 6 suppresses the guard; current public Prize conversion outranks ledger value. |
| H4 v3 plus Mega Brave lock veto | Rank 7 suppresses the guard; exact inherited-attack Prize arbitration and self-lock safety are unchanged. |
| H6 v2 attack-completing Metal reservation | Rank 8 suppresses the guard; never consume or substitute its reserved Metal or safe discard pair. |
| Hero's Cape same-attack survival | Rank 9 suppresses the guard; current payable survival while preserving the attack outranks future access. |
| H3 v2 lone-Cinderace line formation | Rank 10 suppresses the guard; never rewrite its Ultra Ball pair or interrupt its search/Bench/Turbo Flare transaction. |

If the new discard has been emitted, the next callback may only confirm it
and clear; it may not suppress a newly eligible frozen rule after an
irreversible action. If the resolver cannot prove that lifecycle without a
dual/stale owner, abort integration.

## Falsifiable fixtures and evaluation gates

### Mandatory pre-edit gate

Reconstruct episode `88819392` rows `119-123` from the raw observation and
checked engine API in both logical seats. Cover serial remapping, reversed and
duplicate-equivalent option order, and repeated callbacks. The parent branch
must emit semantic Boss+Metal; the candidate branch must emit semantic
non-ex+the same Metal. The candidate branch must then allow the unmodified
parent to select the same Duraludon, Bench it, and use the same Metal Defender
`253` into the same target for the same damage/Prize result, while Boss `#39`
remains in hand and non-ex `#31` plus Metal `#57` are in discard. Any
different search, board formation, attachment, attack, target, damage, Prize,
turn completion, invalid action, or max-step hit aborts implementation.

Ledger fixtures must separately prove both seats for: search/reveal selected
to hand; unselected reveal shuffled to unknown; public discard; public return
to hand; ordinary turn persistence; Prize-to-hand confirmation; Unfair
Stamp/hand-to-deck invalidation; duplicate callback idempotence; result/new
game reset; conservation and malformed-serial fail-closed behavior.

Collision fixtures must pair the positive guard with each of the eight frozen
positives in both ownership directions, plus all-eligible and post-emission
confirmation cases. Every frozen rule wins; no dual owner or stale ledger is
allowed.

### Post-implementation gates

- Exact source, negative, duplicate/reset, both-seat, collision, and
  full-corpus shadows: zero invalid actions, exceptions, stale/dual owners,
  telemetry faults, or max-step hits. Every changed callback must satisfy this
  certificate and expose before/after access counts and semantic cards.
- Re-run the immutable fixed-760 schedule with exact key/schedule equality.
  Require no regression in the `200` historical-Silver anchor, `560` adjacent
  panel, either `380`-game seat total, or any repeated matchup bucket; require
  zero action errors and max-step hits.
- A neutral schedule may justify retaining a contract-correct dormant
  component, not formal-parent promotion. Formal adoption requires practical
  absolute strength plus at least two independent natural or exact-engine
  certified triggers showing the intended last-access mechanism; a tiny
  paired delta, cloned option permutations, or one source game is
  insufficient.
- Inspect every gain and regression. Accept only if the observed mechanism is
  last-access preservation with current-plan identity, not changed setup,
  attacker readiness, Energy allocation, attack continuity, Prize route, or
  unrelated tie-breaking.

Abort before or during implementation if the pre-edit branch fails; a
persistent ledger cannot be reconciled without stale knowledge; source
activation needs a replay/opponent ID; any hard negative fires; any existing
component must be edited; or integration needs an unresolved precedence or
irreversible collision. Do not widen to `never discard Boss`.

## Why the other three options are not next

- **Opponent one-to-two-turn unfinished-threat envelope:** `88776108:41-44`
  exposes Duskull plus mature Dragapult while the parent takes Hammer In, but
  the defensive evolution continuation and the opponent's two-effect line are
  not fixed. `88814688:88` and `88820060:53` likewise add only a hidden
  attachment/switch access burden. No bounded access model yet separates a
  reachable threat from a speculative response.
- **Winning/normal/comeback mode classifier:** `88826155:132/135` depends on
  hidden Boss access; `88826681:135` is one narrow mirror race; and the two
  defensive-Boss sources still have hidden escape branches. They do not
  identify a three-mode transition/hysteresis contract. Adding actions now
  would bundle several mechanisms.
- **Harmful-KO/Active-versus-Bench future value:** the frozen 48-loss audit
  found zero new hard-gate candidate. `88826681:135` and `88824894:79` retain
  healing/retreat/future-attacker ambiguity. The strongest runner-up is
  `88247531:115`, where `[4]` evolves the healthy Active and `[5]` could save
  the invested Bench, but its Alloy-to-Active/Raging Hammer continuation is
  still an unexecuted engine branch and the two-Prize evolution has a larger
  continuity/gust regression surface. Preserve that fixture for the later
  future-value stage.

## Exact evidence needed next

The smallest next evidence-building task is the mandatory both-seat
`88819392:119-123` alternate-discard engine fixture above. A pass authorizes
one Sol-xhigh isolated direct-parent implementation of this contract; a fail
selects `NO_IMPLEMENTATION` for the ledger option and returns to the
root-verified `88247531:115` future-value branch fixture. No Kaggle or other
external write is part of this judgment.
