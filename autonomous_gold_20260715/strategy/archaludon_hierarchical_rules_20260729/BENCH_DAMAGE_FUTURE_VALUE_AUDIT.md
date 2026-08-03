# Bench-damage future-value audit

## Scope and immutable inputs

This is a read-only qualitative audit of exactly one replay:
`autonomous_gold_20260715/evidence/live_54927163_refresh_20260729_0344/episode_88247531_replay.json`.
It covers the cited callbacks `114-120` and only the minimum surrounding
resolution rows (`111-113` and `121-126`). No hidden hand, future draw,
opponent-policy model, simulation, aggregate, or alternate-game outcome is
used.

| Input | SHA-256 |
|---|---|
| Episode `88247531` replay JSON | `26D1D7054A5C67ED89261B4CA391445A3EA46C5FC8D4AE314E63A577CFC7434E` |
| Historical-Silver `main.py` | `F4B578453C9D953BE94885144DD50E05DBA4510DF3340BE27ADE07495896046E` |
| Historical-Silver `deck.csv` | `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A` |
| Historical-Silver public card/attack API, `cg/api.py` | `593F1298E52A635F90F8F505A52113E9AF114F444C293404E37906F18EE06CED` |
| `tools/analyze_kaggle_replay.py` | `991D85517AC1B5E8EAE697D1816871D582112006DE3BD2378F5B4BA095242205` |
| `tools/inspect_agent_replay_decisions.py` | `376D2834D5272DE87BDB918BC9C118DA034EE3F23A75A99488CDC1DE3A9E07B0` |

Episode metadata: seed `301151539`; teams `[Haumea, rurumi]`; rewards
`[1, -1]`. `rurumi` is seat/player index `1`, the Archaludon agent. The final
file SHA-256 is necessarily reported outside this file in the parent handoff;
embedding a file's own digest would change that digest.

## Qualitative verdict

**Confirmed mechanism-addressable target-selection failure; a coherent,
isolated deterministic evolution-target rule exists.** At the first relevant
evolution callback, the exact historical parent chose Archaludon ex onto a
healthy one-Energy Active Duraludon while a damaged three-Energy Bench
Duraludon was inside a publicly payable `30` Bench-damage breakpoint. The deck
and hand supplied both evolution resources and both targets were legal, so the
local failure is policy/future-board valuation rather than deck construction.

This is one loss. Confidence is high only in the observed mechanism and HP
arithmetic, and low in generalization or match-outcome causality. The evidence
does not prove that the alternate line wins this episode.

## Observed public sequence

### The opposing Bench-damage certificate

At `/steps/111/0/observation`, Haumea's Active was Marnie's Grimmsnarl ex
`#28`, HP `320/320`, with Basic Darkness Energy `#8` and `#11`. Its sole
attack is `Shadow Bullet` (`attackId=937`): `180` Active damage plus `30`
damage to one opposing Benched Pokemon, paid by `{D}{D}`. The two attached
Energy exactly paid the cost and were not discarded.

The same public state showed seat 1's Active Duraludon `#64` at `130/130`,
and Bench Duraludon `#66` at `40/130` with three Basic Metal Energy
`#116,#113,#93`. Rows `112-113` log:

- `Shadow Bullet` for `180` to Active `#64`, causing its KO;
- the subsequent Bench target choice and `30` damage to Duraludon `#66`,
  taking it from `40` to `10` HP;
- the KO move of `#64` to discard.

At row `114`, Haumea had taken one Prize (`3 -> 2` remaining). Seat 1 still
had three Prizes.

### Promotion is a control, not the diagnosed mechanism

At `/steps/114/1/observation`, seat 1 had two promotion options:

- index `0`: healthy Duraludon `#63`, HP `130/130`, Metal `#122`;
- index `1`: damaged Duraludon `#66`, HP `10/130`, Metals
  `#116,#113,#93`.

The historical parent scored both `8000`, reason `promote Duraludon`, and
chose `#63`. The raw resolving action `[0]` appears at
`/steps/115/1/action`. This audit does not propose changing that promotion.
The first callback addressable by an **evolution-survival** mechanism is row
`115`, not row `114`.

### Exact first mechanism-addressable callback

At `/steps/115/1/observation` (seat 1, turn `10`, first Main callback):

- Active Duraludon `#63`: HP `130/130`, one Metal `#122`;
- Bench Duraludon `#66`: HP `10/130`, three Metals `#116,#113,#93`,
  `appearThisTurn=false`;
- hand: Archaludon `#92`, Basic Metal `#115`, Archaludon ex `#67`;
- four Basic Metal Energy were publicly in discard:
  `#112,#121,#114,#118`;
- opposing Grimmsnarl ex `#28` still had Darkness `#8,#11`, so the public
  `Shadow Bullet` Bench-damage payment remained assembled.

The exact legal evolution options were:

| Option | Card and target | Historical score/reason |
|---|---|---|
| `0` | Archaludon `#92` -> Active Duraludon `#63` | `-1000`, hold non-ex outside Ogerpon |
| `1` | Archaludon `#92` -> Bench Duraludon `#66` | `-1000`, hold non-ex outside Ogerpon |
| `4` | Archaludon ex `#67` -> Active Duraludon `#63` | `36000`, evolve Active Duraludon |
| `5` | Archaludon ex `#67` -> Bench Duraludon `#66` | `18000`, evolve Bench Duraludon |

The exact parent chose option `4`; that resolving action is stored at
`/steps/116/1/action`, and independent replay scoring reproduced `[4]`.
This next-row action storage is important: `/steps/115/1/action=[0]` is the
preceding promotion response, not the row-115 evolution decision.

Rows `116-119` then show Archaludon ex `#67` on Active `#63`, acceptance of
Assemble Alloy, selection of discard Metals `#112,#121`, and both attachments
to that Active. At the two target callbacks the parent scored the Active
`14700` and then `19700`, while the already-three-Energy Bench Duraludon was
`-5000`, `skip: 3+ energy`. This attachment allocation is an observed
consequence, not part of the proposed evolution rule.

At row `120`, the damaged Bench Duraludon remained at `10/130` with its three
Energy. Non-ex evolution onto it was still legal but scored `-1000`;
Metal Defender (`attackId=253`) scored `220` and was chosen. Row `121` shows
the resulting `220` damage to Grimmsnarl ex (`320 -> 100`).

### Damage-counter KO and Prize timing

At row `121`, the opponent's Bench Munkidori `#15` visibly had Basic Darkness
Energy `#12`, enabling Adrena-Brain. This is an Ability, **not an attack**:
the Darkness Energy is a condition and is not consumed. Rows `121-125` show
the exact public transaction:

1. activate Munkidori `#15`;
2. select damaged Grimmsnarl ex `#28` as the source;
3. select three damage counters;
4. select Bench Duraludon `#66` as the target;
5. remove `30` damage from Grimmsnarl (`100 -> 130`) and place `30` as
   counters on Duraludon (`10 -> 0`);
6. move Duraludon `#66` and Metals `#93,#113,#116` to discard.

The KO opens a Prize selection at row `125`; after resolution, row `126`
shows Haumea at one Prize (`2 -> 1`). No claim is made that Haumea was forced
to select this target; only the observed action and its public legality are
asserted.

## Exact survival breakpoint

Duraludon `#66` carried `120` damage at row `115`
(`130 max HP - 10 current HP`), and evolution retains that damage.

- Archaludon ex has `300` max HP, so evolving `#66` with `#67` yields
  `300 - 120 = 180` current HP. It survives Shadow Bullet's `30` Bench
  damage at `150` HP.
- On the recorded attack-producing line, the visible next-turn package can
  include Adrena-Brain `30` plus Shadow Bullet Bench damage `30`. Archaludon
  ex remains at `180 - 30 - 30 = 120` HP if both effects target it.
- Non-ex Archaludon has `180` max HP, so evolving `#66` with `#92` yields
  `60` current HP. It survives either isolated `30` event, but reaches exactly
  `0` against the full public `30 + 30` package. Non-ex evolution therefore
  is not a certified full-turn save in this state.

The unconditional row-115 certificate needs only Shadow Bullet: current HP
`10 <= 30`, while ex post-evolution HP `180 > 30`. Adrena-Brain's availability
at row `115` is conditional on the opponent having damage to move; the
recorded Metal Defender supplies that source by row `121`. That condition must
not be silently projected from hidden information.

## Counterfactual prefix: proven legality only

The only exact alternate action vector proven by the replay is:

`/steps/115/1/observation -> [5]`

That means Archaludon ex `#67` evolves Bench Duraludon `#66`. No subsequent
exact option indices are claimed: evolution changes the Active/Bench objects
and therefore all Assemble Alloy target callbacks. Public card text supports
the narrow hypothesis that Alloy could select two of
`#112,#121,#114,#118` and attach them to Active Metal Pokemon Duraludon
`#63`, making its three-Energy Raging Hammer (`attackId=224`) available.
That continuation is not present in the replay and must be established by an
engine reconstruction before it is treated as fact.

## Narrow deterministic countermeasures

1. **Archaludon-ex evolution target survival reservation.** At a Main
   evolution callback, when the same Archaludon ex card has legal Active and
   Bench Duraludon targets, prefer an invested Bench target only when a
   currently payable, visible opposing attack has exact Bench damage `B`,
   `target.hp <= B`, and retained-damage post-evolution HP is `> B`.
   Investment should be public and narrow (here, three attached Energy).
   This rule changes the target of the already-selected evolution mechanism;
   it does not alter promotion or Alloy allocation.
2. **Full-public-turn shadow check.** Separately log all presently enabled
   public counter movement and Bench attack damage. Do not certify a rescue
   if post-evolution HP is only enough for one event when the same public turn
   can deliver both. In this callback it distinguishes ex (`180 > 60`) from
   non-ex (`60 <= 60`).

## Failure hypothesis and regression risks

Observed facts support a qualitative policy hypothesis: the historical score
function valued “evolve Active” and immediate Alloy acceleration above the
future value of a damaged, already attack-ready Bench body. This is a
resource-state/target-selection failure: three attached Energy were exposed
and then discarded on KO despite a legal ex evolution that crossed the public
damage breakpoint. It is not evidence that the deck lacked an answer.

Regression risks:

- Evolving the Bench can leave the Active unable to attack if parent Alloy
  targeting does not place two discard Metals onto Active Duraludon `#63`.
  That is an attachment interaction to test, not an attachment override to
  bundle into this rule.
- A Bench Archaludon ex is a two-Prize target and may improve an opposing Boss
  line. Survival against `30` Bench damage is not safety against all visible
  Active or gust threats.
- A broad “evolve damaged Bench” bonus can waste an evolution on low-value
  bodies, react to non-payable attacks, ignore damage prevention, or sacrifice
  an exact current-turn Prize/terminal action. The guard must use the actual
  legal option, attack payment, retained damage, and exact HP inequality.
- The Munkidori part of the full-turn package requires a public damaged source.
  It must be conditional when no such source exists; opponent future draws or
  hidden hand cannot be used to manufacture the certificate.
- Non-ex and ex evolutions are not interchangeable here. A one-event check
  would incorrectly call non-ex a complete save.

## Required both-seat engine reconstruction and shadow assertions

Before any implementation judgment, reconstruct seed `301151539` with the
exact two decks and both seat policies, and branch the row-115 state into
historical `[4]` and candidate `[5]`. Do not synthesize the opponent's hidden
hand from the public observation; obtain a reproducible engine state from the
seed/decks or fail closed.

Required assertions:

- seat identity is fixed: Archaludon is player `1`;
- promotion row `114` stays semantically identical (`#63` promoted);
- the first candidate difference is row `115`: `#67` targets Bench lineage
  `#66`, while every guard input comes from current public state/card data;
- the evolved `#66` retains Metals `#116,#113,#93`, retains `120` damage,
  becomes Archaludon ex with max HP `300`, and has current HP `180`;
- Assemble Alloy offers the correct four public discard Metals and the
  unmodified parent can route two to Active `#63`; if not, report the
  continuity regression rather than adding an attachment rule;
- after two such attachments, Active `#63` has exactly three Metal Energy and
  Raging Hammer `224` is legal; record the actual action if the parent chooses
  something else;
- under shadow application of Adrena-Brain `30` and Shadow Bullet Bench
  damage `30`, ex `#66` remains at `120`, while non-ex would reach `0`;
- opponent targeting remains policy-owned; do not force the replay's target
  choice in the strength comparison;
- repeat the reconstruction with the Archaludon policy in both seats under an
  identical seed/opponent schedule, checking semantic callback identity,
  action errors, and turn completion. Numerical comparison belongs to the
  root/Sol-Ultra numerical evaluator, not this audit.

## Raw evidence pointers for independent verification

All pointers refer to the replay JSON hash above:

- `/steps/111/0/observation` through `/steps/113/0/observation`: payable
  Shadow Bullet, `180` Active damage, `30` Bench damage, first KO;
- `/steps/114/1/observation` and `/steps/115/1/action`: promotion state and
  resolution;
- `/steps/115/1/observation` and `/steps/116/1/action`: first evolution
  callback and historical choice;
- `/steps/116/1/observation` through `/steps/120/1/observation`: evolution,
  Alloy selection/targets, retained Bench state, and attack decision;
- `/steps/121/0/observation` through `/steps/126/0/observation`:
  Adrena-Brain source/count/target, KO, Energy discard, and Prize resolution.

These rows are the complete raw set a later evaluator should quantify or
reconstruct for this mechanism. No frequency, delta, uncertainty estimate,
promotion gate, or Kaggle-slot recommendation is issued here.
