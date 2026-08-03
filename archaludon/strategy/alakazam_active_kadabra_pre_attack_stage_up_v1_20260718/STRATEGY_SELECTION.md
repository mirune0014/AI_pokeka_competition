# Alakazam Active-Kadabra pre-attack stage-up v1: strategy selection

Date: 2026-07-18 JST  
Role: read-only Sol-Ultra strategy judge  
Decision: **IMPLEMENT one isolated ATTACK-boundary transaction**

## Selection

Implement only this rule:

> After exact submitted v3 has finalized `Super Psy Bolt`, replace it with the
> complete public transaction `Active Kadabra -> direct Alakazam -> Psychic
> Draw exactly 3 -> Powerful Hand` when the latter is an exact KO with strictly
> higher current Prize yield.

Derive from exact submitted v3, not from the exploratory turn-plan candidate:

- parent source:
  `candidates/alakazam_parent_end_strict_prize_lead_retreat_ko_bridge_v3/main.py`;
- source SHA-256:
  `49E954F53E043CD79D928DFB2340CCB5D85A17F33CCB824C871CCE153C0C9C95`;
- runtime SHA-256:
  `9CA7A415451B84343165EF8A5CDC0D67BBF1B4969A13C984C09B142B4898CD9A`;
- deck SHA-256:
  `7B413177E5077777F2178143839C0155B03B92BBC8B3A6607621A7D43F351141`.

Do not change the deck, ordinary evolution/attack ranking, Boss, attachment,
retreat, setup, or any inherited latch. Do not import another candidate at
runtime.

## Why this hypothesis wins the comparison

It fixes three repeated, fully public Mega-Lucario states with one route
alphabet and no opponent-policy or drawn-card assumption. It is broader than
an episode patch: any energized Active Kadabra may stage up against any
publicly clear target when the count-only Powerful Hand route uniquely
converts a Prize that Super Psy Bolt cannot.

- Rare Candy/PLAY conversion (`86615595/S124`, harder extension `S144`) needs
  two held cards and, in the extension, a new Energy attachment and retreat.
  It changes a wider action alphabet and has fewer repeated closed fixtures.
- ATTACK-effect-to-damage retreat (`86616155/S127`) is exact but depends on a
  ready reserve plus the narrow Rock-Fighting/effect-prevention topology.
- Buffer/reserve planning is already represented by exploratory submission
  `54799469`. One new public win proves that two of its latches can execute,
  not that stacking them improves the new rule or resolves its local Marnie
  regression.

Therefore Active-Kadabra stage-up is the strongest independent next rule;
the alternatives remain separate later candidates.

## New live evidence and the non-stack decision

Authenticated snapshot `live/54799469/refresh_20260718_1420` records submitted
turn-plan candidate `54799469` COMPLETE at `709.5`, versus submitted v3
`54797361` at `770.3`. In public winning episode `86630035`, exact comparison
contains `64` decisions and exactly two v3/submitted differences; recorded
play agrees with the submitted candidate at both:

- `S38`: `EVOLVE_ACTIVE_READY`, energized Active Abra -> Kadabra -> draw 2;
- `S82`: `RETREAT_CONVERT_NOW`, Enriching-bearing Active Alakazam -> already
  energized Alakazam.

The two mechanisms were valid and live-active in that win. This supports
their implementation integrity, but one jointly activated win cannot identify
either mechanism's marginal value, while the candidate still has a known
Phase-0 Marnie regression and a lower early public score. It does **not**
independently compel stacking. Exact v3 remains the causal parent and rollback.

Evidence:

- detailed transaction record SHA-256:
  `AC98AC87C04DE46A55B9B9DAB5416E2C69B42E13F8B638FA10A02145E5671374`;
- exact comparison SHA-256:
  `367A05B3C9D8C10EB28C97B8C784ACE56A7C994148E8B25345CE786ABB62EA92`;
- authenticated quota/score rows SHA-256:
  `92AD63166250B06B9B3ECF01399A1901CAC46B59B8DDE052688DD21BB8E6F0CB`.

## Evidence correction and exact positive boundaries

The earlier shorthand "exactly one held Alakazam" is incompatible with the
replay: `86617263/S119`, `S128`, and `S137` each expose **two** legal held
Alakazam copies, serials `13` and `12`. A literal one-copy gate would make all
three named positive fixtures impossible.

The implementable invariant is exactly one *semantic route*: one Active
Kadabra target and one Alakazam card class. If multiple identical legal
Alakazam copies exist, choose the lowest legal option index, matching the
parent's stable tie order, and freeze that exact selected serial. Ambiguous
targets, non-identical evolution classes, or duplicate option encodings fail
closed.

The first difference in the first sequence is `S119`, not `S117`:

| Fixture | Exact v3 prefix/top | Projected hand | Candidate yield |
|---|---|---:|---|
| `86617263/S117-S119` | preserve Flip the Script at `S117`, Dunsparce play at `S118`; v3 then finalizes Super Psy Bolt at `S119` | `17 - 1 + 3 = 19` | Powerful Hand `380`, exact 3-Prize KO of 280-HP Mega Lucario ex |
| `86617263/S128` | v3 finalizes Super Psy Bolt | `18 - 1 + 3 = 20` | Powerful Hand `400`, exact 1-Prize KO of 110-HP Solrock |
| `86617263/S137` | v3 finalizes Super Psy Bolt | `19 - 1 + 3 = 21` | Powerful Hand `420`, exact 1-Prize KO of 80-HP Solrock |

At `S137` the target player still has six Prize cards and the opponent has
one; this is an exact one-Prize conversion while denying an opponent on a
one-Prize clock, not the target player's final Prize.

## Exact start certificate

Start only after all inherited v3 scoring and overlays have run and the
finalized single action is the unique legal `ATTACK_SUPER_PSY_BOLT` in
`SelectContext.MAIN`. All of the following are mandatory:

1. no inherited or new latch is armed; same turn/player and ordinary
   single-select MAIN context;
2. own Active is a publicly complete Kadabra, did not just appear this turn,
   has exact public Psychic payability, and is free of attack-blocking status;
3. the finalized Super Psy Bolt has an exact public damage/Prize certificate;
4. at least one direct held Alakazam legally evolves that exact Active; after
   collapsing identical-copy options there is one semantic route, with the
   lowest option index chosen and its serial frozen;
5. Psychic Draw metadata is exactly the checked optional draw-three effect;
   `deckCount - 3 > 0`, unless the certified KO takes every remaining own
   Prize immediately;
6. projected hand is exactly `start_hand - 1 + 3`; Powerful Hand is payable
   from the Kadabra's unchanged Energy and is an exact positive KO;
7. candidate Prize yield is strictly greater than Super Psy Bolt's. Equal
   KO, damage-only improvement, or unknown yield does not start;
8. the opponent Active, every in-play Pokemon, attached Energy, Tool, Stadium,
   status, attack lock, immunity, prevention and transient public effect has
   a complete fingerprint and certified interpretation.

Powerful Hand places damage counters as an attack effect. Mist Energy,
Rock Fighting Energy on a Fighting target, Repelling Veil, a public Splashing
Dodge heads result, immunity, or any unclassified global/temporary effect
makes its yield zero or unknown and prevents start. Weakness/resistance apply
to Super Psy Bolt's damage but not to Powerful Hand counters.

The modifier-aware helpers from the exploratory candidate may be copied and
adapted into this isolated source after review; none of its start branches or
latches may be copied or stacked.

## Frozen multi-callback transaction

Use one new latch with only these stages:

1. `await_draw_offer`: choose the frozen Active-evolution option. Repeated
   identical callbacks return the cached action without advancing.
2. At exact `SelectContext.ACTIVATE`, require the frozen Alakazam/context card,
   exactly one YES option, unchanged public state, hand `-1`, unchanged deck,
   and the evolved-card transition. Choose YES; set `await_draw_resolution`.
3. At the next MAIN callback, require deck `-3`, hand net `+2`, all pre-existing
   hand fingerprints except the consumed Alakazam still present, exactly three
   new serials (their identities are ignored), and the selected Alakazam now
   Active with the Kadabra, Energy, Tool and prior evolution fingerprints
   intact. Revalidate target and every modifier; require one payable Powerful
   Hand option and the same exact KO/Prize certificate. Choose it; set
   `await_resolution`.
4. On the following callback, require the frozen target to have left Active or
   the expected Prize delta/damage resolution, then clear and delegate.

Freeze at start: turn/player/context; full visible hand and discard; hand/deck
and both Prize counts; Active/Bench order and component fingerprints; selected
evolution option/card/source; original Energy units; statuses; opponent field,
discard and Active target; Stadium; current Super Psy Bolt certificate;
projected Powerful Hand count/yield; all public modifier fingerprints; and
expected count deltas.

Any unexpected context, NO/required alternative effect, missing/duplicate
option, serial collision, count mismatch, new required identity, changed
target/modifier/status, turn/seat change, incomplete public Pokemon, or failed
resolution clears the latch and delegates to exact v3. It must not repair,
restart on the same observation, evolve a Bench target, use Rare Candy, draw
again, attach, retreat, Boss, or choose any card because it was newly drawn.

## Mandatory fixtures

Positive checked-engine transactions:

- `86617263/S119`: first difference EVOLVE; YES; exact draw 3; Powerful Hand
  380; three-Prize KO;
- `86617263/S128`: EVOLVE; YES; draw 3; Powerful Hand 400; one-Prize KO;
- `86617263/S137`: EVOLVE; YES; draw 3; Powerful Hand 420; one-Prize KO.

Mandatory no-start/retention controls:

- `86617263/S99-S108`: retain Bench-then-Active dual-Kadabra evolution, Run
  Away Draw, backup Basic-Psychic attachment and attack; `S108` has no exact
  Alakazam KO;
- `86617263/S117-S118`: retain Flip the Script and the Dunsparce play; the
  stage-up begins only when v3 finally chooses ATTACK at `S119`;
- `86615595/S72-S76`, `S124`, `S144`: retain Super Psy Bolt; Rare Candy and
  Telepath/retreat routes are outside scope;
- `86616155/S83-S89`, `S119`, `S127`: retain the clear Powerful Hand KOs and
  the blocked-attack behavior; never add effect-to-damage retreat here;
- `86616724/S117-S120`, `S130-S132`, `S157`: retain Hammer-removes-Mist KO,
  respect Splashing Dodge heads, and keep deck-zero no-start;
- `86619417/S37-S47`, `S69`: preserve the exact buffer-retreat KO and do not
  treat an unenergized Kadabra as eligible;
- `86600692` Repelling Veil and synthetic Mist/Rock/immunity/transient
  variants: no-start;
- full v3 win histories `86610595`, `86611150`, `86611702`, every inherited
  latch fixture, terminal attack, lone-Dudunsparce guard, and strict-Prize
  retreat fixture remain semantically intact.

Add synthetic fail-close tests for one versus two identical Alakazam copies,
duplicate encodings, deck counts `3/4`, NO-only draw offer, missing/extra draw,
target switch, status change, replayed identical callbacks, and both normal
resolution and unexpected prevention.

## Immutable Phase-0 and gates

Use the existing checked 144-key schedule without tuning:

- schedule SHA-256:
  `4271E31503F37EFE4B1BBB9ED2D3569D79D9C1E9B2A20387CCAC131F28346010`;
- blocks: `known_target`, `fresh_general`;
- opponents: `alakazam_oselcoun`, `alakazam_rmy`, `dragapult`, `great_tusk`,
  `historical_silver`, `kangaskhan_crustle`, `marnie_sota`, `mega_lucario`,
  `starmie`;
- seats `p0`,`p1`;
- known seeds `2026071586, 2026071593, 2026071599, 2026071600`;
- fresh seeds `2026101801, 2026101802, 2026101803, 2026101804`;
- comparison key `(block, opponent, seat, seed)`.

Reuse only after hash verification the frozen v3 baseline trees:

- complete tree SHA-256:
  `1B62E96F68BB555DB8D48731BC70915E2F522D42B55AD7F48FE0230F80244D3B`;
- summaries+traces SHA-256:
  `E732A0F8F496664F671377A9F000B00AE4184A68B78F1E211C2AC1F069FF6276`;
- baseline `86/144`, P0 `45`, P1 `41`, known `44`, fresh `42`, Rmy `7/16`,
  Historical-Silver `8/16`.

Structural gate: compile/import, exact legal 60, deterministic repeatability,
all three engine positives and every no-start/fail-close fixture; exactly 144
unique equal keys; zero nonzero exits, action errors, max-step hits or missing
traces; inspect every first difference and complete/failed latch.

Exploratory live-probe floor: total `>=84/144`; P0 `>=45`, P1 `>=40`; known
`>=43`, fresh `>=41`; Rmy `>=7/16`, Historical-Silver `>=7/16`; Mega Lucario
no worse than v3; no opponent more than one win below v3; gains-minus-
regressions `>=-2`; no broken Prize conversion, terminal attack, modifier
guard or transaction. Passing this floor permits one labelled probe while v3
remains rollback.

Strict adoption: total `>=87/144`; P0 `>=45`, P1 `>=41`; known `>=44`, fresh
`>=42`; no opponent below v3; Rmy `>=7`, Historical-Silver `>=8`; paired gains
strictly exceed regressions; all structural and retention gates pass. Marnie,
Great Tusk and Historical-Silver are explicit retention targets; Mega Lucario
is the primary gain target.

## Recommendation

**IMPLEMENT.** This is one ambitious, interpretable multi-step rule with a
strict ATTACK boundary and three exact Prize-conversion fixtures. Keep the
submitted turn-plan candidate as population evidence only and exact v3 as the
implementation parent, evaluator baseline, and rollback.
