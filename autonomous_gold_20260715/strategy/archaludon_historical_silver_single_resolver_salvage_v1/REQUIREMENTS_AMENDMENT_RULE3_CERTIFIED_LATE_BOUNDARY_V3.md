# Rule 3 controlling amendment: certified late-boundary Ultra Ball route v3

Status: CONTROLLING FOR RULE 3 V3 ONLY
Date: 2026-08-03 JST

This amendment replaces the activation semantics of the accepted Rule 3 v2.
It does not modify the deck, Historical-Silver scorer or chooser, Rules 1, 4,
or 5, the public interface, or any other deferred rule.

## Authority and frozen inputs

- User-supplied GPT Pro consultation:
  `C:/Users/amuam/.codex/attachments/66f4591d-747a-4494-b905-268047a29089/pasted-text.txt`
- Consultation SHA-256:
  `CF70347E14337DD38648306BDAEB3D352008ECCA5CB408789D01C32CA2CA8B27`
- Historical-Silver `main.py` SHA-256:
  `F4B578453C9D953BE94885144DD50E05DBA4510DF3340BE27ADE07495896046E`
- Direct integrated parent before Rule 3 v2 SHA-256:
  `D966E455E5110F9D5616195AEAAC8663E6A92F310DAFC4B7F79E4D37149A9C62`
- Accepted transaction-safe Rule 3 v2 source SHA-256:
  `4287A616E1611F5697964D9F4065978EED1CEA72CDB48C9F63F1430D69106C35`
- Deck SHA-256:
  `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`
- Exact deck counts relevant to Rule 3:
  Duraludon `169` x4, Archaludon ex `190` x4, Cinderace `666` x4,
  Basic Metal Energy `8` x11, Ultra Ball `1121` x4, Hero's Cape x1.
- New candidate:
  `autonomous_gold_20260715/candidates/archaludon_certified_late_boundary_ultra_ball_route_v3`
- New implementation evidence:
  `autonomous_gold_20260715/implementation/archaludon_certified_late_boundary_ultra_ball_route_v3`

The consultation is the design authority. This file records the executable
contract and factual corrections required by the current source tree.

## Corrected objective

Rule 3 is not an Ultra Ball continuation helper. It is a tactical selector
that may replace a non-Ultra-Ball Historical-Silver action when a complete
Ultra Ball route is provably superior on public information.

The v2 condition that the parent must already select the physical Ultra Ball
must be removed from Rule 3 activation. Parent-selected Ultra Ball remains a
supported safe case, but it is not required.

Non-destruction is only a retention floor. A completed v3 must demonstrate at
least one natural parent-non-Ultra start and the certified improvement it
claimed. Parent=candidate results alone do not establish completion.

## Architecture invariants

1. The exact accepted v2 source is the implementation parent.
2. Historical-Silver is called exactly once per callback.
3. There is one final agent, one resolver, and at most one active owner.
4. `score_option` and `choose_options` remain byte-identical.
5. Rules 1, 4, and 5 remain behaviorally identical.
6. Rule 1 remains setup-context-only in the current source; do not invent a
   new MAIN Rule 1.
7. In ordinary MAIN, Rule 3 starts only after the current exact terminal,
   Rule 4 materialization, and Rule 5 exact Boss/Prize routes decline.
8. Unknown, incomparable, equal, metadata-incomplete, or pre-commit binding
   failures return exact Silver.
9. A post-commit inconsistency is an `IRREVERSIBLE_FAULT`, not a successful
   fallback and not evidence against the Rule 3 strategy.
10. No generic scorer, generic simulator, hidden-hand inference, opponent
    proxy, episode exception, or new unrelated rule is permitted.

## Strategic result hierarchy

An Ultra Ball route may override Silver only with one of these certificates,
in this order:

1. `R3_WIN_NOW`: the declared attack wins now and Silver does not.
2. `R3_PRIZE_GAIN_NOW`: against parent ATTACK or END, the declared attack
   takes strictly more certain prizes now.
3. `R3_ATTACK_COMPLETION`: parent END performs no attack, while Rule 3 makes
   an exact legal attack now.
4. `R3_SAME_ATTACK_PLUS_CONTINUITY`: parent and Rule 3 use the same Active,
   attack ID, damage/effect, and certain prizes, while Rule 3 alone prevents
   an empty board or creates an immediately payable successor attack.

Evolution, discard conversion, Energy acceleration, hand reduction, and
setup are means, not independent reasons to override Silver.

Different attacks with equal certain prizes are incomparable. A stronger
future line that sacrifices a current legal attack is incomparable. A route
depending on a future draw or unknown opponent action is incomparable.

## Parent action boundary

Classify the once-called parent action before comparing it.

- `OPPORTUNITY_CLOSING`: ATTACK or END. All four certificates may be tested.
- `DEFER_AND_REEVALUATE`: a known nonterminal item, Basic play, evolution,
  attachment, recovery, Stadium, or effect continuation that does not consume
  a frozen Rule 3 route piece. Emit exact parent and reconsider at the next
  MAIN callback.
- `INCOMPARABLE`: Lillie, Explorer, draw/shuffle, retreat, a different-purpose
  action, an action that may consume a route piece, or any incomplete effect.
  Preserve Silver unless Rule 3 proves `R3_WIN_NOW`.
- `HIGHER_PRIORITY`: exact terminal or accepted Rule 5 route. Preserve the
  higher-priority proposal.

The route must therefore intervene at the last certified boundary before an
ATTACK or END closes the opportunity, not at every earlier setup action.

## Finite route catalogue

Only the following routes are allowed.

### A. `ACTIVE_EX_SEARCH_ROUTE`

Active Duraludon -> Ultra Ball -> search Archaludon ex -> evolve the unchanged
Active -> Assemble Alloy -> optional manual Metal -> productive parent prefix
-> Metal Defender.

Requirements include global turn at least 3, exact legal evolution readiness,
complete Stage-1 lineage, no attack-preventing condition, a guaranteed copy of
Archaludon ex in deck, an exact Energy plan, no known hard counter, and one of
the four certificates.

### B. `ACTIVE_EX_FUEL_ROUTE`

Active Duraludon -> Ultra Ball mainly as a discard-to-Alloy converter -> use
the exact Archaludon ex already in hand -> evolve -> reattach every discarded
Metal selected as cost -> optional manual Metal -> productive parent prefix ->
Metal Defender.

This route must exist even when Archaludon ex is already in hand. Its core
completion cannot depend on the search result. At the optional search prompt,
prefer a legal parent-selected physical card of a useful identity, otherwise
use a separately certified useful card, otherwise choose the legal empty
selection. Search whiff must not prevent the pre-certified core route.

### C. `TURBO_DURALUDON_ROUTE`

Active Cinderace -> Ultra Ball -> guaranteed Duraludon -> open Bench slot ->
productive parent prefix -> the same Turbo Flare -> attach the revealed Metal
to the new Duraludon -> complete.

The Bench need not be empty, but must have room and must not already contain a
resource-complete successor. Rule 3 must preserve the same Cinderace, Turbo
Flare attack ID, damage/effect, and certain prizes. Ultra Ball may not discard
Metal in this route. Public lower bounds must guarantee at least one Duraludon
and the claimed number of Metal Energy in deck. One guaranteed Metal certifies
Hammer In readiness; three certify Raging Hammer readiness.

## Guaranteed deck lower bound

For a fixed deck count, compute visible own copies recursively across hand,
discard, Active, Bench, attached cards, Tools, and pre-evolution lineage.
Separate known face-up Prize copies from unknown Prize slots.

`guaranteed_in_deck = max(0, total_copies - visible_non_deck - known_prized - unknown_prize_slots)`

Any malformed zone, duplicate serial, negative count, or inconsistent total is
unknown. Search-dependent routes require a lower bound of at least one. Do not
assume a hidden Prize identity.

## Cost reservations

Build physical-card reservations before enumerating two-card cost pairs.

`HARD_RESERVED` includes:

- the source Ultra Ball;
- the existing Archaludon ex used by the fuel route;
- the Metal reserved for a manual attachment;
- Hero's Cape;
- cards required by an already certified terminal or higher-priority Boss
  route;
- the sole continuity Basic, sole required evolution, sole required recovery,
  and the sole retained draw outlet;
- a uniquely required non-ex Archaludon where an exact public matchup/effect
  certificate proves that role.

`ROLE_RESERVED_ONE` retains at least one physical copy of a still-live role:
future search, Full Metal Lab where relevant, Lillie/Explorer as a draw outlet,
Night Stretcher with a visible recovery target, and Boss with an exact visible
future target. Do not reserve a card merely because its name is generally
useful; the role predicate must be explicit and testable.

Safe discard classes are discrete, not a new total score:

0. Metal discarded and physically reattached by this same Assemble Alloy.
1. A Cinderace copy with no remaining legal deck role after setup.
2. A true duplicate beyond all reservations.
3. Optional utility with the required role reserve still retained.

Choose only pairs that preserve the whole route. Compare class tuples,
manual-attachment use, card ID, and serial deterministically.

## Energy equation and physical binding

Let:

- `A` be exact Metal currently attached to Active Duraludon;
- `D` be exact Metal currently in discard;
- `M` be Metal selected as Ultra Ball cost;
- `H` be retained hand Metal after costs;
- `X` be Metal selected by Assemble Alloy;
- `Y` be an optional manual attachment, zero or one.

Require:

```text
0 <= X <= 2
Y in {0, 1}
A + X + Y == 3
D + M >= X
Y == 1 only if attachment is unused and one retained physical Metal exists
every Metal discarded by Rule 3 is included in the exact Alloy selection
```

Prefer plans that recover the selected cost Metal and preserve manual
attachment. Do not overfill above three Metal as part of Rule 3.

Required cases include all `A=0..3`, relevant `D=0..2+`, attachment used or
unused, and exact examples where `(A,D)=(1,1)`, `(1,2+)`, `(2,0)`, and
`(2,1+)` choose different Metal/non-Metal costs.

## Prize and attack guards

- Preserve existing exact terminal and Rule 5 routes.
- Remove the v2 blanket veto on the mere presence of a Boss PLAY option.
  Veto only an actually certified higher-priority proposal.
- For a nonterminal Duraludon-to-Archaludon-ex override, do not increase the
  Active Prize liability to two when the opponent has two or fewer prizes.
- Require exact current damage, weakness, resistance, prevention, reduction,
  prize value, and attack-cost proof for `WIN_NOW` and `PRIZE_GAIN_NOW`.
- Reuse audited Historical-Silver hard counters for Cornerstone Ogerpon,
  Crustle, and other exact effect identities. Unknown effects are not safe.
- Do not infer a future opponent attack to justify the route.

## Transaction and commit semantics

Reuse the v2 semantic rebinding, duplicate handling, receipt verification,
Alloy attachment stages, Turbo attachment stages, and bounded parent prefix
where correct. Replace its activation and plan generation.

Required stages are:

```text
PLAN_CERTIFIED
-> ULTRA_PLAY_EMITTED
-> DISCARD_EMITTED
-> SEARCH_EMITTED
-> PLAY_OR_EVOLVE_EMITTED
-> ABILITY_DECISION_EMITTED
-> ENERGY_SET_EMITTED
-> ENERGY_TARGET_i_EMITTED
-> OPTIONAL_MANUAL_ATTACH_EMITTED
-> READY_PARENT_PREFIX
-> ATTACK_EMITTED
-> TURBO_ENERGY_SET/TARGET_i (Turbo only)
-> COMPLETE
```

For a parent-non-Ultra override, commit the single owner immediately before
emitting Ultra Ball. Before emission, a failed bind returns Silver. After
emission, any impossible promised transition latches `IRREVERSIBLE_FAULT`.
The current callback may emit a legal parent action only as fault containment;
the run still fails and the fault owner remains until a stable release point.

Store seat, turn, action count, route and certificate snapshots, source/cost/
target/energy physical refs, destination lineage, declared attack, successor
requirement, stage, prompt fingerprint, and semantic action specs.

An identical prompt does not advance stage or budget. Reordered options rebind
by option type, card ID, card serial, target area/serial, and attack ID. Zero or
multiple matches are pre-commit fallback or post-commit fault respectively.

## Productive prefix

After declared attack readiness, retain the sole Rule 3 owner and emit exact
parent nonterminal setup actions and their effect choices while they preserve
the frozen route. Revalidate the declared attack at every MAIN callback.

- If parent selects the declared attack, preserve it and complete on receipt.
- If parent selects END, RETREAT, or another opportunity-closing attack while
  the original certificate remains true, emit the declared attack instead.
- If an exact superior Rule 5 route becomes available, perform an atomic
  owner handoff; never keep two owners.
- An unclassified action or lost readiness after commit is a fault, not a
  successful abort.

## Required focused verification

Implement the positive, negative, and fault fixtures listed in the consultation.
At minimum cover:

- all Active-ex search/fuel Energy matrix cases in both seats;
- Cinderace with empty Bench and with an open slot but no ready successor;
- parent ATTACK and parent END entry for both route families;
- all four certificate kinds where mechanically possible;
- parent nonterminal prefix actions and final attack enforcement;
- target lower-bound success and unknown/zero failures;
- reservation protection and safe-pair ranking;
- parent exact terminal, certified Boss, Prize-liability, hard-counter, and
  incomparable draw negatives;
- identical retries and option permutations at every irreversible stage;
- every declared post-commit fault class;
- existing Rule 1/4/5 fixtures unchanged.

## Natural and paired evidence gates

1. Freeze source and schedule before natural execution.
2. Record all plan opportunities, rejection reasons, starts, certificates,
   physical refs, prefix actions, completions, faults, and end-state deltas.
3. Require at least one natural first difference of exact form
   `parent ATTACK/END -> Rule 3 Ultra Ball`.
4. Require a complete parent-non-Ultra transaction in both seats.
5. To call each route family complete, require at least one natural
   parent-non-Ultra completion for Active-ex and Turbo respectively.
6. Committed completion must be 100%; irreversible faults must be zero.
7. Confirm that the promised certificate is present in the post-transaction
   public state.
8. Run fixed160 only after focused and natural lifecycle gates pass. Repair an
   implementation fault and rerun the same frozen schedule; do not reinterpret
   it as a strategic rejection.
9. Paired gains must be at least regressions, with no seat/opponent cell three
   wins below the exact parent and no clear harmful first difference.
10. Run fixed760 only for a candidate that passes the prior gates. The original
    final requirements remain the retention floor.

`0 gains / 0 regressions` is safety evidence only. Strength may be evidenced
by a confirmatory paired gain or an exact same-state certificate realization,
but a claim that the whole agent is stronger still requires the frozen global
strength threshold.

## Prohibited shortcuts

- Do not restore `parent_exact_ultra` as an activation gate.
- Do not implement only one or two episode-shaped exceptions.
- Do not require an arbitrary ready attack or full-HP Active as a proxy.
- Do not broaden a certificate because natural frequency is low.
- Do not force an attack immediately after readiness; preserve the productive
  parent prefix.
- Do not hide a committed abort behind a Silver fallback.
- Do not accept equality-only evidence as Rule 3 completion.
- Do not alter any other rule to make Rule 3 pass.

