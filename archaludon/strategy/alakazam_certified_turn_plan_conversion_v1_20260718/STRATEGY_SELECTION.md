# Alakazam certified turn-plan conversion v1: strategy selection

Date: 2026-07-18 JST  
Role: read-only Sol-Ultra rule-hypothesis judge  
Scope: select one implementable deterministic rule; no implementation, simulation, packaging, or Kaggle write

## Submission-critical amendment

This file supersedes its earlier SHA-256
`68CC556D74578F098B5B5A3125A8135647B0FC0BABB675BEF9175AE440DAB4C0`.
The earlier version incorrectly treated `86594208/S105-S113` as a frozen
positive route. Exact `S105` hand inspection shows no Kadabra, Alakazam, or
other direct evolution card; Kadabra serial `10` appears only among the four
cards drawn by Enriching Energy at `S108`. Therefore that route depended on a
future drawn identity and contradicted the hidden-card contract. This
amendment does not relax that contract. It converts `86594208/S105` into a
mandatory no-start diagnostic and replaces it with the fully public
`86613371/S97` exact retreat-to-KO fixture.

## Executive selection

Implement **option B only: a certified attachment/evolution/retreat/attack-continuity transaction**. Derive it directly from the exact currently submitted v3 source. Do not change Boss selection, target ranking, ordinary attack ranking, deck construction, or any inherited setup rule in this candidate.

The rule addresses one broad but coherent defect: the parent sometimes spends the turn's attachment, evolution, or retreat on a locally attractive action that destroys the only observable attack-ready Abra-line, or ends despite an already complete exact retreat-to-KO conversion. The replacement may look several actions ahead, but only through a short, frozen sequence whose cards, payment, destination, attack, damage, and Prize effect are already observable. It must not depend on the identity of a future draw.

Option A (Boss/targeting) is deferred. A+B is also rejected for this iteration. The three strongest direct causal fixtures share the option-B continuity mechanism, whereas two prior Boss candidates produced unresolved tempo/stall and duplicate-copy regressions. Combining the mechanisms would prevent clean attribution and violate the one-hypothesis workflow.

## Frozen source and evidence

### Exact derivation source

Clone, then edit only in the isolated destination:

- source: `autonomous_gold_20260715/candidates/alakazam_parent_end_strict_prize_lead_retreat_ko_bridge_v3/main.py`;
- destination: `autonomous_gold_20260715/candidates/alakazam_certified_turn_plan_conversion_v1/main.py`;
- source SHA-256: `49E954F53E043CD79D928DFB2340CCB5D85A17F33CCB824C871CCE153C0C9C95`;
- runtime SHA-256: `9CA7A415451B84343165EF8A5CDC0D67BBF1B4969A13C984C09B142B4898CD9A`;
- deck SHA-256: `7B413177E5077777F2178143839C0155B03B92BBC8B3A6607621A7D43F351141`.

Do **not** derive from the older exact parent source `FAB47771161EF7F43C9402B58D38FF240C92B6A2B77FFA6B925DFEA7F990D033`. V3 is the stronger executable anchor: `86/144` versus `84/144`, with two paired gains, zero regressions, and nine fully completed END-to-retreat-to-Powerful-Hand transactions. Deriving from v3 also makes the current live replay population action-identical to the implementation source: v3 activation was zero in every checked callback, so a new first difference remains attributable to this overlay.

### Evidence used

- 12-loss multi-turn audit: `analysis/live_54794301_new26_loss12_20260718/QUALITATIVE_MULTI_TURN_GAP_AUDIT.md`, SHA-256 `3654D3667F53505696ABBDD65E3EB9BAC0823C0D36BF9A44943EF31390C7B544`.
- Earlier four-loss audit: `analysis/live_54794301_public4_20260718/LOSSES_DIAGNOSIS.md`, SHA-256 `9F6CF5B22D27529FD34C3CC6515115120F94D913B06D71F235E2399BE5D1B729`.
- New-10 diagnosis: `analysis/live_54794301_new10_20260718/QUALITATIVE_NEW10_DIAGNOSIS.md`, SHA-256 `C3DF7486FFBF000B71A81A5FB5ABF5FEBE6B0B32636D12D96E5696F41A634A8C`.
- Current-v3 win retention audit: `analysis/live_54797361_public3_20260718/QUALITATIVE_WIN_ROUTE_AUDIT.md`, SHA-256 `488A565C247C770675855E1EA1AB7F6A2EE1C9F5DB49C1725AF1E542A895E0BF`.
- Current-v3 three-loss audit: `analysis/live_54797361_new5_20260718/QUALITATIVE_LOSS3_TURN_PLAN_AUDIT.md`, SHA-256 `29DFB85305201A4D4B5E1945DD0EDE1C9890274DD0EB245AE53C48BD19263FFD`; its `86613371` replay SHA-256 is `F7C4A1B872758C867EACCAB40FF61317F331C9114499CE2961BEA0E941AE7A64`.
- V3 Phase-0 numerical audit: `evaluations/alakazam_parent_end_strict_prize_lead_retreat_ko_bridge_v3/phase0/PHASE0_NUMERICAL_AUDIT.md`, SHA-256 `052A0281F05657421A9928160BD73FA06664FAF2290AC1C7BF7C169E9EA08906`.
- Latest refreshed live snapshot considered: `live/54797361/refresh_20260718_1228/RAW_COLLECTION_MANIFEST.md`, SHA-256 `447CFCF476649D55DB3D83D74C163F5FEE22C67E32549BE474CECE3AF00627F9`; episode CSV SHA-256 `11FC22E41D36EE36F77593294A1D28BBEBDD7B8E7E54BFF8601EE14C60B904F5`.

The latest snapshot was `5-3`, score `763.3`, with `1/5` UTC-day slots used. Its 305 newly compared callbacks were still v3/parent/recorded-action identical and had zero v3 activation. These facts justify preserving v3 as rollback and using a bounded live probe if the practical gate passes; they do not establish a causal v3 weakness or improvement.

## Why B, not A or a combination

### Direct continuity evidence

1. **Episode 86596902, steps 51-61.** At `S51`, Basic Psychic serial `56`, Active Genesect serial `20`, and Bench Alakazam serial `13` are all already observable, and attaching that Psychic to the Bench Alakazam is already a legal option. The parent attaches to Genesect, then retreats, discards the only Psychic, promotes the unenergized Alakazam, and ends. Attaching to the benched Alakazam creates a ready reserve while retaining the lower-liability buffer and the matching Energy. It requires no future draw or opponent-policy assumption.
2. **Episode 86604494, steps 63-81.** At `S63`, Active Abra serial `5` already carries Telepath Psychic serial `58`, Kadabra serial `8` is already in hand, and evolution of the Active is already legal. The parent evolves a benched Abra, later retreats, discards the sole Psychic, and promotes an unenergized Kadabra. Evolving the energy-bearing Active preserves an immediately payable attack line; its evolution draw is not used to establish or complete that line.
3. **Episode 86613371, steps 93-97.** Telepath Psychic serial `60` is already attached to Bench Alakazam serial `13`; Boss has already brought a 130-HP, one-Prize Cinderace Active; Active Alakazam serial `11` has exactly one Enriching Energy and exact retreat cost one. At `S97`, hand size ten makes the destination's Powerful Hand exactly 200, RETREAT is legal, and exact v3 chooses END solely because its strict post-KO Prize-lead test rejects `5 < 3`. The complete public alternative is `RETREAT -> discard Enriching -> promote Alakazam 13 -> Powerful Hand KO`. It uses no future draw and preserves the earlier Boss choice.

These are separate replay states but one causal invariant: **before consuming a continuity resource or ending the turn, compare the bounded observable completion and preserve or execute the unique ready Abra-line when it produces no lower current yield and a strict readiness/damage/Prize improvement.**

### Corrected hidden-card diagnostic: 86594208

At `S105`, the exact hand is Poffin `27`, Hilda `50`, Battle Cage `52`,
Battle Cage `54`, Enhanced Hammer `41`, Dawn `46`, Hilda `51`, Boss `42`,
Lucky Helmet `37`, Battle Cage `55`, Enriching Energy `62`, Dawn `44`, and
Dawn `45`. Bench Abra serial `4` has Basic Psychic serial `56`, but there is
no direct evolution card. Kadabra serial `10` becomes visible only at `S108`
after Enriching draws four cards. Therefore the attractive
`attach Active -> evolve Bench -> retreat -> promote -> attack` story cannot
be certified at `S105`. The candidate must fail closed there and may not use
the realized Kadabra draw as retrospective evidence that the attachment was
dominant. The state remains useful deck-theory/optionality evidence only.

### Explicit scope decision: defer the Xerosic joint-kit branch

`86614484/S96` is valuable continuity evidence: retaining Alakazam plus one
Telepath Psychic as a joint forced-discard bundle can rebuild a successor by
public count effects. It is **not** part of this implementation. Supporting it
would add forced-discard contexts, a joint-card bundle optimizer, conditional
visible-reply reasoning, and new draw-count fixtures outside the bounded MAIN
transaction alphabet. Adding that mechanism now would weaken isolation and
delay the intended practical live probe. This candidate therefore remains
exact v3 in every forced-discard context; `86614484/S96` is a future isolated
hypothesis, not a positive fixture or promotion requirement here.

### Why Boss remains unchanged

- Boss-v1 scored `76/144` against `78/144` with seven gains and nine regressions. Broad suppression erased legitimate tempo/stall routes and duplicate Boss copies changed downstream play.
- Boss-v2 tied `78/144`, four gains and four regressions, while missing strict P0/fresh gates. Its Fezandipiti, Crustle, and tempo boundaries remained ambiguous.
- The four Boss-to-END observations (`86594208`, `86599601`, `86601220`, `86602325`) are not four certified positive labels; several are setup/board-out states in which no public action creates the missing attacker.
- V3 must retain successful Boss routes, including `86597987` steps 90-92 and the current-v3 Lucario win routes at steps 85-87 and 135-137.

The candidate therefore neither suppresses nor forces Boss. Boss-to-END and damage-reset observations remain exact-v3 behavior unless an independent future candidate certifies them.

## Exact rule contract

### Start boundary

The overlay may start only in `SelectContext.MAIN` and only after exact v3 has completed its normal scoring and earlier overlays. Its finalized selection must be exactly one option of type `ATTACH`, `EVOLVE`, `RETREAT`, or `END`. An `END` start is permitted **only** for `RETREAT_CONVERT_NOW` when the complete existing-field retreat/payment/promotion/attack route has an exact positive KO certificate. It must not start from `PLAY`, `ABILITY`, `ATTACK`, a multi-select context, a forced-selection context, or while any inherited latch is armed.

Existing v3 armed latches and start rules retain precedence. In particular, exact v3 first receives every END state and keeps all routes satisfying its strict-Prize bridge; only a returned `None` may be considered by the new END branch. On subsequent callbacks, an already armed new continuity latch is resolved after inherited armed-latch handling but before any new overlay may start. If it fails closed, the same observation delegates to exact v3 and may not restart another new transaction.

### Frozen route alphabet

A route contains only already visible elements and at most:

1. one manual attachment;
2. one direct ordinary Abra-line evolution (`Abra -> Kadabra` or `Kadabra -> Alakazam`), with no Rare Candy, search Item, Supporter, or newly drawn card;
3. one ordinary retreat whose cost and exact Energy payment are public and exact;
4. one exact `SWITCH`/`TO_ACTIVE` promotion;
5. one exact attack, limited to `Super Psy Bolt` or `Powerful Hand`.

The frozen sequence may be shorter. In particular, `BUFFER_READY_RESERVE` ends after its attachment is confirmed and delegates the remainder of the turn to v3; it must not force a retreat or attack.

### Three permitted branches

#### 1. `EVOLVE_ACTIVE_READY`

Replace a same-card-class benched evolution with the legal evolution of a Psychic-bearing Active Abra/Kadabra only when the Active evolution creates an exact positive attack this turn, preserves at least the same visible ready-reserve count, and has no lower certified effective damage/Prize yield than the parent's bounded visible branch. The evolution card serial, source serial, resulting stage, expected draw count, attack, target, and damage certificate are frozen.

#### 2. `RETREAT_CONVERT_NOW`

Use when an alternative placement/order, or an exact retreat suppressed by v3's strict post-KO Prize-lead predicate, turns a stranded Active into an exact current-turn conversion. The strongest initial fixture begins from END with every component already present: discard the frozen Enriching Energy for retreat, promote the already energized Alakazam, and take an exact one-Prize KO. A longer attachment/evolution route is legal only if every card needed after any count effect already existed before that effect. Newly drawn identities are ignored.

#### 3. `BUFFER_READY_RESERVE`

Redirect the sole matching Basic Psychic from a nonattacking buffer Active to a benched Abra-line that is already a legal ready attacker or is certifiably evolvable with an already held direct evolution. This branch is allowed only when attaching to the Active still leaves it with no exact positive attack, the buffer may legally remain Active, the bench attachment creates one additional ready successor, and no immediate effective Prize/damage yield is lost. After exact attachment confirmation, clear the latch and delegate to v3.

### Dominance certificate

Before replacing v3's first action, enumerate the bounded consequences of the parent first action and every permitted alternative using only the current observation and fixed card mechanics. Start only when exactly one alternative lexicographically and conservatively dominates the parent branch:

- certified immediate effective Prize yield is no lower;
- certified immediate effective damage is no lower;
- manual-attachment, Supporter, and once-per-turn consumption is no greater;
- exact Energy discarded or stranded is no greater;
- observable attack-ready Abra-line count is at least one higher, **or** the sole matching Psychic is preserved from an unready promotion;
- exposed Prize liability is no higher;
- deck and Prize clocks remain exact and nonterminal;
- at least one of effective Prize yield, effective damage, or a continuity component is strictly better.

Ambiguous ties do not start. This is a transaction certificate, not a general action ranker.

### Effective-yield certificate

Compute exact yield only for Super Psy Bolt and Powerful Hand. The helper must conservatively scan the target and every publicly visible global modifier: Active/Bench abilities, attached Energy, Tools, Stadium, resistance, immunity, prevention, and attack locks. The existing `_powerful_hand_target_is_publicly_clear` is insufficient by itself because it does not certify every global Bench effect.

If damage, prevention, or legal payability is unknown, the route has unknown yield and cannot start. Repelling Veil in episode `86600692` and Mist/Rock-style prevention must therefore produce zero or unknown—not a positive attack certificate. This candidate does not override a terminal ATTACK/END choice merely to repair that episode.

### Attachment/evolution effect constraints

- Ordinary Basic Psychic attachment requires an exact unique card serial and exact target serial.
- Enriching Psychic attachment is permitted only with a nonterminal safe deck count and exact post-effect count change: hand `+3` net and deck `-4` relative to the frozen pre-attachment counts. All downstream route cards must be pre-existing and remain present with the same fingerprints; new identities are ignored.
- Telepath Psychic may be used as already attached payment. Starting this planner with Telepath attachment is excluded because its search expands hidden branching; the inherited active-Psychic transaction remains responsible for its already certified immediate-KO case.
- A direct evolution's optional/automatic draw may resolve only with the engine-documented exact count delta. The route cannot depend on any drawn identity. After the count effect, every frozen serial, component fingerprint, target, and modifier must be revalidated.

## Latch and deterministic fail-close design

Use one new module-level latch, cleared by the same game/turn/player boundary machinery as v3. Its only legal stages are:

- `await_attach_effect`;
- `await_evolution`;
- `await_optional_draw`;
- `await_retreat`;
- `await_payment`;
- `await_promotion`;
- `await_attack`;
- `await_resolution`.

Not every branch visits every stage. Freeze at start:

- turn, player, context, route branch, and exact expected stage sequence;
- full relevant hand fingerprint and counts, deck count, both Prize counts, discard fingerprint, stadium fingerprint, and `energyAttached` state;
- Active/Bench positions, serials, component fingerprints, HP/status, attached-Energy fingerprints, Tools, and retreat cost;
- opponent Active and all relevant global-effect fingerprints;
- attachment/evolution/payment/destination/attack option fingerprints and unique serials;
- expected count deltas, exact damage, effective damage, Prize yield, ready-line count, and post-route public commitments.

At each callback require the expected context, exactly one matching option, the same turn/player, exact count deltas, unique protected serials, unchanged frozen public components, and the expected immediately preceding effect. A mismatch, missing/duplicate option, unmodeled modifier, status change, global protection, unexpected discard, unexpected newly required card, turn change, or state-incomplete Pokémon clears the latch and delegates to exact v3. Do not guess, repair a partially changed route, select a fallback option inside a forced context, or start again on that observation.

Repeated identical callbacks must return the exact cached action without advancing the latch. Recompute the decision signature immediately after first arming, as v3 does for its retreat bridge. At `await_resolution`, require that the attack target left Active or that the expected damage/Prize delta occurred, then clear. A route may legally clear after a verified ready-reserve attachment without attacking.

Critically, **do not force an attack solely because a retreat occurred**. The current-v3 Lucario win at steps 38-41 retreats Genesect to Kadabra and correctly ends because no useful attack is available.

## Helper reuse boundary

Prefer the stronger helpers already present in v3:

- `_bridge_card_fingerprint`, `_bridge_pokemon_fingerprint`, `_bridge_pokemon_is_publicly_complete`;
- `_bridge_protected_serials_are_unique`;
- `_bridge_retaliation_energy_unit`, `_bridge_retaliation_can_pay`;
- `_bridge_retreat_cost_is_publicly_exact`;
- existing decision-signature/cache and latch-boundary utilities.

The following prior Boss-v2 helpers may be copied or adapted under continuity-specific names when v3 lacks the same capability:

- `_boss_cards_fingerprint` and `_boss_pokemon_fingerprints` for ordered collection snapshots;
- `_boss_public_snapshot` for a complete frozen observation signature;
- `_boss_unique_attack_option` and `_boss_exact_attack_route` for unique attack/payability certification;
- `_boss_payability_skill_is_certified_irrelevant` and `_boss_payability_static_fingerprint` for conservative modifier rejection.

Do not import the old candidate at runtime. Do not port any Boss start/suppression/ranking/target latch, `_boss_resource_tax_certificate`, duplicate-Boss policy, or Boss-specific threshold. Helper reuse must not change Boss behavior.

## Mandatory fixtures and controls

### Positive engine fixtures

All three direct fixtures must reach the named first action and complete or safely terminate their frozen route with zero invalid actions:

| Episode/state | Required first difference | Required certified result |
|---|---|---|
| `86596902`, S51-S61 | sole Basic Psychic attaches to benched Alakazam, not buffer Genesect | ready reserve rises by one; Genesect stays Active; latch clears to v3 without forced retreat |
| `86604494`, S63-S81 | evolve Psychic-bearing Active Abra, not benched Abra | exact draw delta; Active attack line remains payable; no sole-Psychic discard into unready promotion |
| `86613371`, S97 | exact-v3 END becomes RETREAT after the inherited strict-Prize bridge declines | discard only Enriching; promote pre-energized Alakazam; Powerful Hand 200 KOs 130-HP Cinderace; one Prize is taken |

`86587331` may be a supporting backup-readiness inspection, but its hidden draw prevents using it as a causal positive label.

### Mandatory parent-identical or semantic retention controls

- `86597987` S90-S92 successful Boss-to-two-Prize KO remains exact v3.
- `86603941` Boss damage-reset state remains exact v3; it is evidence for a future targeting hypothesis, not this rule.
- `86600692` Repelling Veil yields zero/unknown and cannot start without an independent positive option-B route.
- `86594208` S105 is a mandatory hidden-card no-start control: the route may not depend on Kadabra serial `10`, first visible only after the Enriching draw at S108.
- `86614484` S96 is a mandatory scope no-start control: forced-discard bundle optimization is deferred and remains exact v3 in this candidate.
- Boss-to-END setup states and setup-only board-outs (`86593038`, `86600203`, `86601220`, `86602325`, relevant `86599601`) do not start merely because the outcome was a loss.
- Current-v3 Marnie win `86610595`: preserve inherited Psyduck retreat-to-ready-Alakazam attack, setup/draw before attack, successful invested-target Boss, Battle Cage defense, and terminal direct KO.
- Current-v3 Starmie win `86611150`: preserve successor preparation, Run Away Draw/rebench, the doomed 20-HP Active taking a three-Prize KO instead of retreating, and direct terminal three-Prize KO despite Boss in hand.
- Current-v3 Lucario win `86611702`: preserve legal retreat-to-END, pre-attack backup attachment/evolution, both successful Boss conversions, and direct terminal KO.
- Preserve all active-Psychic transaction fixtures, v3 strict-Prize retreat fixture `86585479` S142-S144, the lone-Dudunsparce guard, terminal attacks, and every existing v3 latch fixture.

For controls requiring ordinary v3 behavior, compare first action and complete transaction semantics; where exact serial identity is intentionally irrelevant, verify a canonical fingerprint rather than accepting any option of the same type.

## Fixed Phase-0 evaluation

Use the checked existing 144-pair schedule exactly; do not tune seeds after implementation.

- schedule SHA-256: `4271E31503F37EFE4B1BBB9ED2D3569D79D9C1E9B2A20387CCAC131F28346010`;
- blocks: `known_target`, `fresh_general`;
- opponents: `alakazam_oselcoun`, `alakazam_rmy`, `dragapult`, `great_tusk`, `historical_silver`, `kangaskhan_crustle`, `marnie_sota`, `mega_lucario`, `starmie`;
- seats: `p0`, `p1`;
- known-target seeds: `2026071586`, `2026071593`, `2026071599`, `2026071600`;
- fresh-general seeds: `2026101801`, `2026101802`, `2026101803`, `2026101804`;
- comparison key: `(block, opponent, seat, seed)`.

Reuse the frozen v3 baseline rather than rerunning it, provided every source/runtime/deck/schedule hash is rechecked:

- complete v3 raw tree SHA-256: `1B62E96F68BB555DB8D48731BC70915E2F522D42B55AD7F48FE0230F80244D3B`;
- v3 summaries+traces tree SHA-256: `E732A0F8F496664F671377A9F000B00AE4184A68B78F1E211C2AC1F069FF6276`;
- frozen v3 results: total `86/144`, P0 `45/72`, P1 `41/72`, known `44/72`, fresh `42/72`; Rmy `7/16`, Historical-Silver `8/16`.

Execute candidate-only 144 rows with exact schedule equality and checked repository runners. A 1,440-game broad panel is not required for this practical probe. Numerical interpretation and qualitative changed-trace judgment remain independent Sol-Ultra tasks; the root must recompute critical columns.

## Gates

### Structural gate: required before numerical judgment

- compile/import succeeds; deck is the exact legal 60-card list; source/runtime/deck hashes are frozen;
- deterministic repeated-callback tests pass for every latch stage;
- exact-engine multi-step tests cover all three positive fixtures, both `SWITCH` and `TO_ACTIVE`, every payment/effect context, and every fail-close group;
- every inherited latch and mandatory retention fixture passes;
- candidate run has exactly 144 unique schedule keys, exact seat/seed/opponent equality, zero nonzero exits, action errors, max-step hits, malformed selections, duplicate controls, or missing traces;
- every first difference is caused by the new rule, every changed position is inspected, and every started transaction either completes exactly or follows its specified fail-close;
- before any live write: frozen-file check, package import, and packaged both-seat smoke also pass.

Any structural failure blocks both exploratory probing and adoption regardless of win count.

### Practical live-probe gate

This gate deliberately permits a locally safe exploratory probe without pretending Phase-0 is perfect:

- total at least `84/144`;
- P0 at least `45/72`, P1 at least `40/72`;
- known at least `43/72`, fresh at least `41/72`;
- Rmy at least `7/16`, Historical-Silver at least `7/16`;
- no opponent more than one win below its v3 cell total;
- all three direct positive fixtures pass;
- all mandatory retention controls pass;
- paired regressions exceed gains by at most two, and every regression has a trace-level explanation with no known broken Prize conversion, attack continuity, terminal attack, or action validity.

If this gate passes but the strict gate does not, the root may package one clearly labeled **exploratory live probe** at the next permitted cadence after refreshing quota/status/replays. V3 remains the rollback and local promotion baseline.

### Strict local-adoption gate

- total at least `87/144`;
- P0 at least `45/72`, P1 at least `41/72`;
- known at least `44/72`, fresh at least `42/72`;
- no opponent below its exact v3 total;
- Rmy at least `7/16`, Historical-Silver at least `8/16`;
- paired gains strictly exceed regressions;
- all positive fixtures, retention controls, transaction audits, and structural checks pass.

Only this gate permits replacing v3 as the strongest local baseline. Live score alone cannot waive a broken structural or mandatory-retention control.

## Decision

**ACCEPT-TO-IMPLEMENT**
