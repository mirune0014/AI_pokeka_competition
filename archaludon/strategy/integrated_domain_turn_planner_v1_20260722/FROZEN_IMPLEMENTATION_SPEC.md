# Integrated domain turn planner v1 — frozen implementation specification

Frozen by root on 2026-07-22 JST from the read-only Sol-Ultra strategy
decision. This is one combined implementation hypothesis and an exploratory
live-probe authorization. Local win-rate decline is diagnostic only; it is not
an adoption gate for this probe.

## Authority and parent

- Domain audit: `analysis/ptcg_domain_gap_audit_20260721/ROOT_DOMAIN_GAP_AUDIT.md`.
- Domain synthesis and matrix:
  `audits/domain_knowledge_20260716/DOMAIN_KNOWLEDGE_SYNTHESIS.md` and
  `KNOWLEDGE_TRANSLATION_MATRIX.csv`.
- Exact cumulative implementation parent:
  `candidates/alakazam_exact_prize_lane_boss_arbitration_active_psychic_handoff_v2/main.py`,
  SHA-256 `65527AEE74AED600B94C4A555BE9464A48E53E118C9FD674DB6403208706325D`.
- Fresh destination:
  `candidates/alakazam_integrated_domain_turn_planner_v1` and matching
  `implementation/alakazam_integrated_domain_turn_planner_v1`.
- Preserve the cumulative parent as the valid fallback. Add one final planner
  wrapper, one integrated transaction and one duplicate cache. Do not add a
  collection of principle-specific latches.

## Single hypothesis

Replace independent scalar decisions with one deterministic public-state
`IntegratedTurnPlan`. It assigns exclusive H0/H1/H2 roles, reserves physical
and turn-limited resources once, evaluates completed turn outcomes
lexicographically, and executes every multi-callback plan atomically through
the current legal `Options[]`.

## Public snapshot, typed semantics and turn budget

`PublicSnapshot` canonicalizes turn/player/action count, result and selection
context; exact own hand and all public zones; only opponent hand/deck counts;
Active/Bench identity, lineage, HP, Energy, Tools and status; Prizes, discard,
Stadium and used turn resources; normalized logs; and stable legal-option
keys. It must not contain deck order or hidden opponent content. Hash canonical
JSON with SHA-256. Hidden-order/content mutations that retain public counts
must not change the snapshot or action.

`TurnBudget` is copy-on-write and contains manual attachment, Supporter,
Stadium, retreat, attack opportunity, Bench slots, Tool slots and exposed
per-Pokemon Ability availability. No child plan may spend the same budget
twice.

Typed `Outcome` distinguishes at least `AttackDamage`, `PlaceCounters`,
`DirectKO`, `Draw/Search`, `Heal`, `SelfSwitch`, `OpponentSwitch`, `Promotion`,
`MoveEnergy`, `Recovery`, `Status` and `Unknown`. Weakness/resistance and
damage prevention apply only to attack damage. Mist/effect protection applies
to Powerful Hand. Lucky Helmet and Handheld Fan trigger only from positive
attack damage, not counter placement.

## Exclusive H0/H1/H2 ledger

Each Pokemon serial has one base role: `H0`, `H1`, `H2`, `PIVOT`, `ENGINE`,
`RECOVERY`, `SACRIFICE` or `LIABILITY`.

- H0 attacks now.
- H1 is a distinct successor for the public H0-KO branch. H0 may remain the
  attacker in the H0-survives branch without also being labeled H1.
- H2 is the third attack or named recovery route.
- Every Energy, evolution, recovery card, Boss, Bench slot, Tool slot,
  retreat payment and future attachment token has one named reservation.
- Reuse is permitted only across provably disjoint response branches.
- H1 readiness requires evolution legality, Psychic payment, promotion or
  retreat, public Bench-spread survival and an actual legal attack.
- Enriching Energy never satisfies a Psychic attack reservation.

Any same-branch ledger conflict makes the plan infeasible; it is not a score
penalty.

## Lexicographic turn objective

Compare complete plans in this exact order, never by a weighted sum:

```text
(
  win_now,
  avoid_public_forced_loss,
  preserve_H0_lethal,
  prizes_now,
  preserve_H1_attack,
  preserve_H2_route,
  shorter_certified_prize_lane,
  fewer_abandoned_reservations,
  safer_deck_clock,
  lower_bench_prize_liability,
  stable_semantic_tie_break
)
```

An Active terminal win beats Boss expenditure. A unique terminal Boss target
beats a nonterminal Active. A lethal higher-Prize Active beats any strictly
lower-Prize Boss KO. Stable serial/option identity breaks semantic ties.

## Powerful Hand and setup stopping

For a public-clear target, `required_hand = ceil(remaining_hp / 20)`. Project
the hand after every planned Boss, evolution, attachment, Tool, Basic play,
search and draw. An optional step that crosses an existing H0 lethal floor is
infeasible unless it wins immediately, avoids a public forced loss, or creates
a strictly shorter certified PrizeLane.

Once H0 and the selected H1/H2/clocks are sound, an optional draw, evolution,
Tool, Stadium or Bench play must strictly improve the objective vector;
otherwise attack. This must preserve `87111553/S85` 280-counter lethal rather
than play Dunsparce, while still allowing an exact Telepath/H1 transaction
that retains lethal.

## Turn-based draw, Prize, Board and Deck clocks

Model ordered current optional draw/search, opponent-turn Helmet/Fan triggers,
next mandatory draw, H1/recovery, next opponent turn, and H2 mandatory draw.

- Psychic Draw: optional two/three.
- Run Away Draw: draw first; shuffle Dudunsparce and attachments only if a
  card was drawn.
- Enriching: mandatory four after attachment.
- Flip the Script: conditional optional three.
- Lucky Helmet: conditional forced two during the opponent turn.
- Search removes deck cards but is not a draw.
- Sacred Ash adds the actually selected Pokemon before the mandatory draw.
- Deck zero loses only when the next mandatory draw cannot resolve.

Maintain `PrizeClock`, `BoardClock` and `DeckClock` for both players. A
deckout/control plan is eligible only when a complete public maintenance line
beats the Prize lane; never assume hidden escape cards are absent. The
`87109941/S111` Helmet-at-deck-two route is a mandatory negative.

## Atomic movement and callback plan

Retreat freezes source serial, exact Energy-payment serials, destination
serial, post-promotion attack, expected contexts and public deltas. Promotion
after KO and Teleportation post-attack switching use the same machinery.

An integrated transaction stores:

```text
plan_id, snapshot_hash, objective, fallback,
H0/H1/H2, TurnBudget, ResourceLedger,
PrizeLane, DrawClock, ordered PlanSteps,
expected_stage, allowed_option_keys, abort_predicates
```

Every callback revalidates public state and selects the next step only through
current `Options[]`.

## PrizeLane and Boss

Enumerate visible lanes through at most three KOs. Each step records target
serial/Prize value, attacker role, outcome/hit count, post-spend hand floor,
Boss/Supporter need, H1/H2 continuity, visible response and opponent clock.
Future target access is certified only by an exact reserved Boss or current
Active access; otherwise recompute after KO/promotion.

Boss is eligible only for immediate win, strictly fewer certified attacks,
exact recovery of a damaged target, removal of the sole public attack or
acceleration engine that changes the response clock, or a setup transaction
that certifies continuity. Never Boss merely for local target score. Preserve
the completed parent routes `87214287`, `87220395` and `87213204` in both
semantic seats.

## Bench liability, recovery, sequencing and endgame

Every Bench play has a named role and compares Prize value/gust shortcut,
visible spread/snipe vulnerability, slot cost, promotion/escape cost and
effect contribution. Fezandipiti ex is allowed only when its draw is needed
for H0/H1/named recovery enough to justify the two-Prize shortcut. Shaymin
guards Bench attack damage; Battle Cage guards Bench counter placement.
Enhanced Hammer is preferred when a visible Special Energy removal changes
protection or a payable response. Recovery must restore a named H1/H2 route,
not merely increase deck size.

Dependency order is terminal/forced-loss obligations; exact prerequisites;
necessary search/recovery; role assignment and attach/evolve; optional
information/draw only if it improves the selected route; attack. There is no
universal thinning or maximum-count rule. `87108851` is the mandatory
paid-Active-Abra/exclusive-resource fixture.

## One isolated deck package

Change only:

```text
Lucky Helmet 1156: 3 -> 1
Handheld Fan 1161: 0 -> 2
```

Retain the first Helmet deck row and replace the next two Helmet rows with
Fan. Expected `deck.csv` SHA-256:
`A7B6C7972915D09F6314C42633AA89D82B55DDF0A7199F7138E681FA52516529`.

Attach Fan only to a named Active/Genesect role while preserving PH floor,
H1/H2 and clocks, and only when a public attack-damage response branch exists.
On trigger, atomically move the Energy whose removal maximally increases the
attacker payment deficit to the opponent Bench recipient that minimally
improves attack/retreat readiness, using stable ties. A semantically incomplete
mandatory Fan child prompt may choose the lowest exact legal option and must
trace `MANDATORY_LEGAL_FALLBACK`; any such trace during verification is a
structural failure.

## Cumulative parent reconciliation

The final wrapper snapshots every parent latch/cache/semantic-failure field,
the Boss latch/cache and ability flags. For each first-seen callback: check
integrated duplicate identity; freeze parent state; call the cumulative parent
exactly once for a valid fallback; advance an owning integrated transaction;
restore speculative parent state before a successful override; retain genuine
parent post-state on abort; never broadly clear or resurrect consumed state.
Existing parent transactions own their callbacks. The already verified
Active-Psychic/Boss handoff remains; add no general handoff.

## Fail-closed boundaries

Exclude only the affected plan on raw/parsed disagreement, missing/duplicate
serials, unknown Prize/Energy/outcome/prevention semantics, unsupported payable
response, ambiguous option mapping, stale turn/player/action, budget or ledger
overspend, hand/clock threshold crossing, or incomplete transaction. When no
certified integrated plan remains, return the validated cumulative-parent
action. An emergency lowest-legal action protects runtime only; any occurrence
during verification is structural failure.

## Breakage-only exploratory gate

Local losses or paired win-rate decline must be recorded and must not block
this probe. Block only on:

1. compile/import, legal-deck, hash, entrypoint or source/runtime failure;
2. nondeterminism or hidden-order/content dependence;
3. invalid/out-of-range actions, exceptions, timeouts or max-step hits;
4. TurnBudget, ledger, typed-outcome, PH-floor or clock invariant failure;
5. stale transaction, duplicate mismatch, abort/rollback or boundary leakage;
6. failure of mandatory fixtures `87111553`, `87109941`, `87108851`,
   `87214287`, `87220395` or `87213204`;
7. incomplete Handheld Fan attach/trigger transaction;
8. an untraceable planner override or `MANDATORY_LEGAL_FALLBACK`.

Minimum evidence is focused fixtures for every invariant; checked-engine
completion in both seats for the three cumulative routes and one Fan route;
callback-complete current/historical shadows with zero invalid/duplicate/
unclassified overrides; and both-seat one-seed smokes versus Historical
Silver, Alakazam mirror, Starmie and Mega Lucario. Smoke wins/losses are
non-blocking. Passing authorizes one exploratory Kaggle submission; formal
adoption remains a later live-evidence decision.
