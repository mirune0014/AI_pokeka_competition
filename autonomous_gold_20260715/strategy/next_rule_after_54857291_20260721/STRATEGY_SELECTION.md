# Strategy selection: exact two-Prize Basic-PLAY lethal conversion v1

Date: 2026-07-21 JST  
Role: read-only Sol-Ultra strategy judge

## Decision

**SELECT exactly one hypothesis:** from the exact guarded formal parent, when
an optional Basic Pokemon PLAY is the one-card spend that destroys a currently
legal Powerful Hand KO on an exact public **two-Prize** Active, take the KO now
if a separate paid Alakazam successor is already ready and no better visible
Boss route exists.

Proposed isolated destination:
`autonomous_gold_20260715/candidates/alakazam_certified_two_prize_basic_play_lethal_conversion_v1`.

This selection authorizes one Sol-xhigh implementation and read-only local
evaluation only. It does not authorize packaging, parent promotion, replacement
of the recovering live submission, or any Kaggle write.

### Scope ruling: exactly two Prizes, not general one/two Prizes

The rule must require `prize_count(opponent_active) == 2`. One-Prize and
three-Prize targets are mandatory no-starts.

The three public starts of the current exploratory one-Prize overlay are not
Basic-Pokemon plays:

- `87107228/S126`: parent PLAY is Poke Pad `1152/s83` from hand index 15;
- `87111060/S114`: parent PLAY is Sacred Ash `1129/s95` from hand index 14;
- `87117603/S100`: parent PLAY is Poke Pad `1152/s25` from hand index 13.

They support the already submitted optional-resource one-Prize family, but do
not provide a one-Prize positive for this Basic-Pokemon-PLAY rule. The only
verified Basic-Pokemon exposure in the current set is the two-Prize defect
`87111553/S85`. Generalizing to one Prize would therefore add an unobserved
setup-cutoff domain and would blur this sibling with a broader overlay whose
formal adoption already failed. Exact-two scope is the clean causal test.

## Verified facts used

All paths are repository-relative.

- Root loss packet:
  `autonomous_gold_20260715/analysis/54857291_loss_selection_20260721/ROOT_VERIFIED_EVIDENCE.md`,
  SHA-256
  `78F947A16A2A1B4658EBDA5AF32AFAD7B51C6F3645D5CB6067B6EBE473E7A2E8`.
- Root 16-public checkpoint:
  `autonomous_gold_20260715/live/54857291/refresh_20260721_0204/ROOT_16_PUBLIC_CHECKPOINT.md`,
  SHA-256
  `C5CEA6EB4A89E6CB496FD2E44CE98CF096E5F8141A790A031E2665FF3C24661C`.
- Exact formal parent source/runtime/deck SHA-256:
  `4A95DCE0BB095A05F58085DFC450528C5939527E30B9D40E43A76B0CFCE2AE16` /
  `9CA7A415451B84343165EF8A5CDC0D67BBF1B4969A13C984C09B142B4898CD9A` /
  `7B413177E5077777F2178143839C0155B03B92BBC8B3A6607621A7D43F351141`.
- Current exploratory overlay source SHA-256:
  `E5922EFD77FE28F492FCE38CAA0BEDA3E2197F7C5C6FC046286664A1344651F6`.
  It is not a parent or donor.
- Current-15 shadow:
  `autonomous_gold_20260715/live/54857291/refresh_20260721_0151/ROOT_NEW15_SHADOW.json`,
  SHA-256
  `66550BBDA05C54183FD3A38B4D3DAE27D64C712DD4B37785A1BE83B37081A178`.
- Six-new shadow:
  `autonomous_gold_20260715/live/54857291/refresh_20260721_0222/ROOT_NEW6_SHADOW.json`,
  SHA-256
  `89943FD8239D5EA182C0489FC7F359A5982F4F227ADB46A441A3028AE40C237E`.
  It has 365 callbacks, one intended one-Prize resource change in a win, and
  zero invalid, duplicate, or unclassified differences.
- The 22-public CSV has SHA-256
  `67B2432C619BE2336C2E7FD65A4742506977367EE23DA7DDBF81B3FC94DD77C6`.
  Root and direct row checks agree on 22 unique public games, `14-8`, with
  latest API score `702.3896058371078`. The current live rule has three safe
  completed one-Prize resource starts and no action difference in eight losses.
  It has no semantic hard stop and root reports two quota slots remaining.
  This is monitoring context, not evidence to stack or replace it.
- Positive replay `87111553`:
  `autonomous_gold_20260715/live/54857291/refresh_20260721_0204/episode_87111553_replay.json`,
  SHA-256
  `67D3BEBFFEFC7EF22926A08751F19A6BF5C38187711716290DCC28ADC95668C6`.
- The current overlay's formal-adoption judgment, SHA-256
  `29DF15A6D59C2326B1788AF28D319B6AEAFF20C9A212E53A691CADDF49FC8829`,
  rejected formal adoption after compact parent/candidate equality `39/72`,
  `0G/0R`; it permitted only the now-running exploratory probe.

At `87111553/S85`, seat 1, turn 7/action 20, own hand/deck/Prizes and
opponent Prizes are `14/8/5/4`. Active Alakazam `743/s73` is old and paid by
Telepath Psychic `19/s118`; Benched Alakazam `743/s72` is paid by Basic
Psychic `5/s116`. The unchanged opposing Active is Archaludon ex `190/s8` at
270 HP with exactly two Prizes, and its Bench has two Duraludon. Powerful Hand
option 4 deals `14 * 20 = 280`. The parent instead selects option 3, PLAY
hand[12] Dunsparce `305/s74`; hand 13 then deals 260, leaving 10 HP. The
opponent subsequently uses Xerosic, forms another attacker, and the next
Alakazam attack must finish the old target. This proves the local conversion
error, but not that the S85 counterfactual alone wins the game.

The exact parent and submitted overlay were action-identical throughout all
six losses at the 15-public checkpoint. The latest two losses likewise have
no overlay start. The live score therefore does not establish or refute the
new two-Prize rule.

## Why this hypothesis wins the menu

This is the clearest immediate causal defect: all cards, damage, payment,
target HP, Prize value, parent hand spend, and successor readiness are public
at one callback. It converts two Prizes while behind `5/4`, preserves the
Basic in hand, removes a paid opposing attacker before Xerosic, and keeps a
paid Alakazam successor. Setup is already mature, so the rule changes prize
conversion rather than trying to predict a draw or hidden response.

Across the whole game plan:

- setup and board formation are protected by requiring an old paid Active and
  a separate paid Alakazam successor and by never replacing evolution;
- attacker and backup readiness are exact before activation;
- Energy, hand, deck, recovery, Boss, and disruption resources are not spent;
- attack continuity improves locally because the old target is removed now
  rather than consuming the next attack;
- the two-Prize exchange is materially stronger than the untested one-Prize
  Basic domain, while terminal and three-Prize prior art stays excluded;
- finishing remains parent behavior because own Prizes must exceed two and
  the opponent must have a Bench;
- regression risk is concentrated in forgoing one optional Basic body, and is
  bounded by the exact lethal-crossing and paid-successor predicates.

Other menu choices are deferred:

1. Mandatory-draw-three conservation has one strong draw-clock hypothesis,
   but the replay lacks an explicit terminal reason and its three-card future
   cadence is a multi-turn inference. Prior draw-clock candidates also showed
   either regressions or no practical movement. It is less causally exact than
   the S85 one-action conversion.
2. The Fezandipiti liability guard depends on hidden Boss/recovery access. The
   public attacker covering Fez HP is real, but a public winning alternative
   is not certified; prior Fez-exposure work had no incremental gain.
3. Paid-Active-Abra evolution is recurrent and has strong prior exposure, but
   the current mirror still formed and attacked with three consecutive
   Alakazam before losing. The earlier source-transition rule also had a known
   paired regression. It remains the best setup alternative if this narrow
   conversion rule fails to exercise.
4. Active Lucky Helmet retry remains excluded: the new loss is a clean local
   deck-survival error, but no materially new certificate overcomes its prior
   recorded regression.

## Frozen behavioral contract

Let `H` be the exact own hand length, `T` the unchanged opponent Active, and
`R = ceil(T.hp / 20)`. Evaluate one pure helper only after the guarded parent
has finalized its ordinary action.

### Base prerequisites

Every clause is mandatory:

1. Exact live ordinary MAIN callback: `result == -1`, `looking is None`, turn
   at least two, exact single-choice envelope `minCount=maxCount=1`, and one
   legal END option. Raw and parsed player, turn, zones, counts, serials,
   options, and logs agree.
2. No inherited transaction owner existed at entry and none remains after
   boundary preparation: Hilda source, Enriching reserve, Fez bridge,
   active-Psychic KO, stranded retreat, or guarded Teleportation. If stale
   cleanup occurred on this callback, delegate the whole callback.
3. Own field has exactly one Active Alakazam `743`, with a complete unique
   stack, exact max HP, `appearThisTurn == false`, clear status/effects, and
   exact public Energy units that pay Powerful Hand now.
4. Own hand is fully visible, serial-complete, unique, and
   `len(hand) == handCount == H`. Powerful Hand metadata is exact and there is
   exactly one fully encoded legal `ATTACK/1072` option.
5. Opponent has exactly one complete unchanged Active `T`; target stack,
   current/max HP, ownership, Tools, Energies, Stadium, status, and relevant
   effects are exact. Mist, applicable Rock protection, prevention, variable
   HP, unknown special Energy/effect text, or any helper disagreement fails
   closed.
6. `prize_count(T) == 2` after all public Prize modifiers. Legacy/Tool/Energy
   ambiguity fails closed. Own remaining Prizes are at least three and the
   opponent has at least one complete Benched Pokemon, excluding both
   prize-terminal and board-terminal prior art.
7. Current damage is lethal and the one-card Basic spend is exactly what
   destroys it: `20*H >= T.hp > 20*(H-1)`, equivalently `H == R`.
8. Own Bench has a serial-distinct complete Alakazam whose attached public
   Energy pays Powerful Hand unchanged. A Kadabra, unenergized second
   Alakazam, future Energy, future evolution, hand/deck/discard card, or the
   current Active does not count.
9. Every opponent Bench stack/effect is complete enough to rule out a better
   current-turn route. If a legal Boss exists, compute damage after its exact
   one-card hand cost. Any publicly clear Boss KO worth more than two Prizes,
   or any Boss route that wins when the Active KO does not, vetoes the rule.
   An equal two-Prize route is not higher; preserve Boss and KO the Active.

### Exact replaceable parent action

The finalized guarded-parent action must be exactly one ordinary
`OptionType.PLAY` selecting one unique own-hand card whose metadata proves it
is a Basic Pokemon. The play must be optional, must reduce hand by exactly one,
and must not own a mandatory selection or a certified same-turn draw/refill
transaction. Any entry/on-play/Ability ambiguity delegates to the parent.

Only that action may be replaced, and only by the unique semantically resolved
Powerful Hand option. Do not override Item, Supporter, Stadium, Tool or Energy
PLAY/ATTACH, Ability, EVOLVE, Rare Candy, recovery, Hammer, Boss, RETREAT, END,
another attack, selection callbacks, or any unclassified action. Resolve by
option metadata and card serial, never by a frozen option index.

### Precedence, state, duplicates, and failure

All inherited continuation overlays, emergency starts, ordinary scoring,
Run-Away hit-bound logic, fragile-bench guard, and Fez bridge retain precedence.
Insert the helper after the final ordinary choice/Fez start has been resolved
and before new guarded-Teleportation, stranded-retreat, or Hilda starts.

The rule is atomic and stateless: it creates no latch and mutates no inherited
owner, ability flag, quarantine, or gameplay state. Return through the existing
decision cache; an identical callback returns the same attack without rerunning
the parent. The KO, two-Prize selection, promotion, and later turns are exact
parent behavior. External telemetry may record the certificate and resolution
but cannot affect play.

On exception, malformed state, changed callback, duplicate serial, ambiguous
attack/Basic/target, failed certificate, or state-restoration disagreement,
return exact guarded-parent identity. An emitted attack cannot be rolled back;
safety is entirely pre-action.

## Frozen anchors

### Required positive

- `87111553/S85/seat1`: parent PLAY Dunsparce `305/s74` -> unique Powerful
  Hand; verify `H14 -> would-be H13`, `280 >= 270 > 260`, exact two-Prize
  Archaludon `190/s8`, paid Active `743/s73`, paid Benched successor
  `743/s72`, no higher Boss route, and unchanged inherited state. Checked
  engine continuation must deal 280, KO `s8`, reach the exact two-Prize prompt,
  move own Prizes `5 -> 3`, retain Dunsparce in hand, and delegate thereafter.

Reindex this fixture to both seats, permute option order, and substitute
serial-distinct equivalent physical cards. The semantic result must remain
the same.

### Mandatory anti-anchors

- `87107228/S126`, `87111060/S114`, and `87117603/S100`: exact parent
  identity. These are one-Prize targets and parent Poke Pad/Sacred Ash plays,
  not Basic-Pokemon plays; this proves the new sibling does not import the
  live overlay.
- `86976336/S85/seat1`, replay SHA-256
  `03AF61CCA67688BFD0C8B0917166CF0F7804855A3F688577064624E0AEAF749C`:
  Abra PLAY would cross `280 -> 260` into 280 HP, but the target is three
  Prizes; retain exact parent behavior.
- `87109941/S111`: Active Lucky Helmet ATTACH remains parent behavior.
- `87108851/S25`: Active/Bench EVOLVE choice remains parent behavior.
- `87110499/S85`: Enriching Energy ATTACH remains parent behavior.
- Synthetic boundaries: target Prize value 0/1/3; own Prizes 1/2; empty
  opponent Bench; no paid Benched Alakazam; only paid Kadabra; new/unpaid or
  statused Active; insufficient current damage; Basic spend still leaves
  lethal; selected card is not a Basic Pokemon; higher-Prize Boss KO;
  protection/HP/stack ambiguity; multiple/malformed attacks; incomplete hand;
  inherited/stale owner; non-MAIN/selection prompt; duplicate callback and
  changed turn/player. Every case must return byte-identical parent action.

## Falsifiable implementation, evaluation, and package gates

### Implementation and mechanism gate

1. Candidate is one isolated copy of formal parent `4A95DC...2AE16`; deck and
   runtime remain byte-identical. Static diff contains only this rule and its
   diagnostics, with no code copied from or import of `E5922E...51F6`.
2. Compile/import, exact legal 60 cards and one ACE SPEC, deterministic valid
   initial action, loader-last public `agent`, cache-free tree, and both-seat
   Historical-Silver smoke all pass. Action errors and max-step hits are zero.
3. Fresh-module focused tests pass every positive, anti-anchor, mutation,
   option permutation, duplicate, exception, stale-owner, and cache case.
4. A checked-engine branch completes S85 MAIN -> Powerful Hand -> KO -> exact
   two-Prize callback in both seat encodings with no state leak. The observed
   first mechanism must be the intended hand-threshold conversion, not a
   downstream action.
5. Shadow the complete current 22-public set and the frozen historical corpus
   against the exact formal parent. S85 must be an intended first difference;
   the three one-Prize resource starts must remain parent-equal. Every
   additional first difference must satisfy the full generic certificate and
   receive qualitative review. Any one-Prize/three-Prize start, setup cutoff,
   inherited-state mutation, invalid action, or unclassified difference
   rejects the candidate; do not add another state-separating patch.

### Compact-72 retention and strength screen

Use schedule
`autonomous_gold_20260715/evaluations/alakazam_active_psychic_immediate_ko_transaction_v1/PHASE0_SCHEDULE.csv`,
SHA-256
`4271E31503F37EFE4B1BBB9ED2D3569D79D9C1E9B2A20387CCAC131F28346010`.
Retain seeds `2026071586`, `2026071600`, `2026101801`, and `2026101804`, all
nine opponents, both seats, and exact order. Run parent primary, candidate
primary, and candidate duplicate: 216 commands.

Root must first reproduce the current parent compact baseline: `39/72`, P0
`21/36`, P1 `18/36`, known `25/36`, fresh `14/36`; opponent floors
Historical Silver `3/8`, Mega Lucario `7/8`, Starmie `3/8`, Dragapult `7/8`,
Marnie `5/8`, Great Tusk `1/8`, Kangaskhan/Crustle `6/8`, Oselcoun `3/8`,
and Rmy `4/8`. Any disagreement invalidates the run.

Exploratory retention requires candidate at least `39/72`, `0` paired
regressions, every seat/block/opponent floor retained, 72/72 duplicate trace
identity, zero faults, no mechanism-first loss, and complete classification of
every changed trace. Equality alone is safety, not promotion.

Formal compact eligibility requires at least `42/72`, at least `3G/0R`, no
seat or block decline, Historical Silver at least `4/8` with a
mechanism-linked gain, no adjacent-opponent decline, and repeated completed
starts across both seats and at least two seeds. A gain whose first difference
is not this exact Basic-PLAY lethal conversion does not count.

### Primary-anchor exposure extension

If compact72 has fewer than four natural starts or lacks either seat, freeze
before execution a 32-key Historical-Silver extension: 16 distinct seeds in
each seat, identical parent/candidate keys, max steps 1000, full traces, and a
candidate duplicate control. Require at least four completed starts spanning
both seats and at least three seeds, candidate absolute strength at least
`18/32`, at least `2G/0R`, zero faults, and no mechanism-first loss. The full
nine-opponent screen must still retain adjacent populations. No-start or only
one repeated state is failed coverage, not permission to widen to one Prize.

### Full-144 and package gate

Formal adoption remains impossible until a later independent rule judgment.
Necessary full-144 conditions are candidate at least `92/144`, at least
`3G/0R` versus the exact `89/144` parent, P0 at least `48/72`, P1 at least
`42/72`, known at least `47/72`, fresh at least `43/72`, Historical Silver at
least `9/16` with a mechanism-linked gain and no seat regression, every
adjacent opponent at or above its parent floor, repeated two-Prize conversion
in both seats, exact duplicate identity, and zero action errors/max-step hits.
These numbers are necessary, not sufficient; a tiny aggregate delta without
primary-anchor movement and the intended mechanism must still be rejected.

A clean archive is eligible to be built only after the mechanism, shadow,
compact-retention, and primary-anchor exposure gates pass. Its source,
runtime, deck, membership, loader, legality, cache-free status, and packaged
both-seat smoke must be root-verified. Packaging is not submission authority,
and the current recovering submission must not be replaced merely because an
archive exists.

## Regression risks and exact evidence needed next

The main risk is attacking before a useful third body is benched. A paid
successor protects the next attack, but it does not prove long-horizon board
depth under repeated KOs or Xerosic. The rule is also rare: only one natural
Basic-PLAY exposure is verified, and the counterfactual S85 KO is not a proved
win. Exact-two scope may consequently be safe but inert.

Next evidence, in order:

1. one isolated Sol-xhigh implementation receipt with parent/candidate/runtime/
   deck hashes and a source diff;
2. focused and checked-engine S85 continuation plus every anti-anchor;
3. callback-complete current-22 and historical shadow census with semantic
   first-change telemetry;
4. immutable compact72 raw rows, duplicate controls, zero-fault report,
   independent numerical audit, and root recomputation;
5. if coverage is insufficient, the precommitted both-seat Historical-Silver
   extension above;
6. only after practical absolute strength, primary-anchor movement,
   both-seat/repeated-bucket behavior, adjacent safety, and intended mechanism
   all pass, a fresh Sol-Ultra accept/reject judgment.

If the candidate is rejected for no exposure, the next discriminating rule
should be the already recurrent paid-Active-Abra evolution corridor, not a
silent widening of this rule to one-Prize targets or a retry of Active Helmet.
