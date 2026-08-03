# Episode 88247531 Bench-future deep audit

## Decision

`NO_IMPLEMENTATION`

Option `[5]` has a public, exact **local survival** certificate: Archaludon ex
evolving the damaged Bench Duraludon retains 120 damage, becomes 180/300, and
survives the currently assembled 30 Bench damage, or the public
Adrena-Brain-30 plus Shadow-Bullet-30 package, at 120 HP.

It does not have a public **value-superiority** certificate. Redirecting the
same Archaludon ex away from the healthy Active changes Assemble Alloy
targets and appears to replace the parent's current 220-damage Metal Defender
with an 80-damage Raging Hammer. That gives up the parent's public two-attack
two-Prize conversion route while exposing a damaged two-Prize Bench ex to an
uncertified gust line. The alternate callbacks have not been executed in the
engine. A rule broad enough to fire here would therefore violate the required
current-attack and Prize-route negatives.

This is one loss and one changed position. Confidence is high in the raw
state, legality, retained-damage arithmetic, and parent action; confidence in
generalization or match-outcome causality is low.

## Evidence boundary

- Replay: `autonomous_gold_20260715/evidence/live_54927163_refresh_20260729_0344/episode_88247531_replay.json`,
  SHA-256
  `26D1D7054A5C67ED89261B4CA391445A3EA46C5FC8D4AE314E63A577CFC7434E`.
- Episode: seed `301151539`; teams `[Haumea, rurumi]`; rewards `[1,-1]`.
  `rurumi` is player/seat `1`, the Archaludon player.
- Exact historical-Silver parent:
  `analysis_outputs/reference_agents/historical_silver_archaludon_54495224/main.py`,
  SHA-256
  `F4B578453C9D953BE94885144DD50E05DBA4510DF3340BE27ADE07495896046E`.
- Exact deck SHA-256:
  `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`.
- Public card/attack API SHA-256:
  `593F1298E52A635F90F8F505A52113E9AF114F444C293404E37906F18EE06CED`.
- Controlling prior audits:
  `BENCH_DAMAGE_FUTURE_VALUE_AUDIT.md`
  (`74C135E9F005F9BADC8C94933FF069F4F23B584183683D7AB0B2811F04F83A9C`)
  and `ROOT_BENCH_DAMAGE_AUDIT_VERIFICATION.md`
  (`4D8AC5B31817B4857A8520A5D862FFBCC5CCD6029ACD9188A0D4E0AD84F0A1AB`).

No hidden hand, hidden deck order, Prize identity, future draw, opponent
policy, replay action label, or opponent-policy proxy is used.

## Exact observed callback

The relevant observation is `/steps/115/1/observation`: ordinary `MAIN`,
turn `10`, `turnActionCount=1`, `yourIndex=1`, first player `0`. Seat 1 had
not attached Energy, retreated, played a Stadium, or played a Supporter this
turn. The action at `/steps/115/1/action=[0]` is the preceding promotion
response. The evolution decision resolves at `/steps/116/1/action=[4]`.

Public seat-1 state:

- Prizes: `3`; deck count: `23`; no status condition.
- Active Duraludon `169#63`: `130/130`, Metal `8#122`, no Tool.
- Bench Duraludon `169#66`: `10/130`, Metals
  `8#116,8#113,8#93`, no Tool, `appearThisTurn=false`.
- Complete hand: Archaludon `840#92`, Metal `8#115`, Archaludon ex
  `190#67`.
- Public discard, as `(cardId#serial)`:
  `1122#84,1122#87,1185#104,1097#89,1227#108,1152#79,1185#103,`
  `1182#100,1121#83,666#74,1227#106,1244#110,1227#107,8#112,`
  `666#72,1121#82,1152#76,190#69,169#65,8#121,8#114,8#118,`
  `1159#97,1182#99,169#64`.
  The four Alloy-payable Metals are `#112,#121,#114,#118`.

Public seat-0 state:

- Prizes: `2`; deck count: `23`; hidden hand count: `8`; no status condition.
- Active Marnie's Grimmsnarl ex `648#28`: `320/320`, Darkness
  `7#8,7#11`, no Tool. Shadow Bullet `937` is payable for 180 Active
  damage plus 30 to one Bench target.
- Bench Marnie's Morgrem `647#23`: `100/100`, no Energy or Tool.
- Bench Munkidori `112#15`: `110/110`, Darkness `7#12`, no Tool;
  Adrena-Brain is enabled but needs a damaged friendly source.
- Bench Munkidori `112#18` and `112#17`: each `110/110`, no Energy or Tool.
- One Boss's Orders, `1182#48`, is publicly discarded. The opponent's
  remaining hand/deck/Prize identities and any gust access are unknown.

The Stadium is Spikemuth Gym `1259#62`, owned by seat 0. It changes neither
the retained-damage arithmetic nor the printed attacks at this callback.

Exact legal semantics and reproduced parent scores:

| Index | Semantic option | Score |
|---:|---|---:|
| `0` | `840#92 ->` Active `169#63` | `-1000` |
| `1` | `840#92 ->` Bench `169#66` | `-1000` |
| `2` | attach `8#115 ->` Active `169#63` | `13800` |
| `3` | attach `8#115 ->` Bench `169#66` | `-5000` |
| `4` | `190#67 ->` Active `169#63` | `36000` |
| `5` | `190#67 ->` Bench `169#66` | `18000` |
| `6` | use Spikemuth Gym | `1` |
| `7` | Hammer In `223` | `30` |
| `8` | End | `0` |

The parent chose `[4]`.

## Observed parent continuity versus the bounded alternate

Observed parent branch, rows `116-121`:

1. `190#67` evolves Active `169#63`.
2. Assemble Alloy is accepted.
3. Metals `8#112,8#121` are selected and both attached to that Active.
4. Metal Defender `253` deals `220`, leaving Grimmsnarl ex at `100/320`.
5. The evolved Active remains a three-Energy, 300-HP two-Prize attacker.

The recorded next own turn includes a future-drawn Darkness attachment to a
second Munkidori. That card was not public at row 115 and is excluded from
the certificate.

Facts certified directly for `[5]` are narrower:

- `190#67 -> 169#66` is legal.
- Evolution retains 120 damage and Metals `#116,#113,#93`, yielding
  Archaludon ex at `180/300`.
- Shadow Bullet's Bench 30 leaves `150`.
- If our attack first supplies a damaged Grimmsnarl source, the already
  energized Munkidori's 30 plus Shadow Bullet's Bench 30 leaves `120`.

The exact post-`[5]` Alloy and attack callbacks are unobserved. Parent code
strongly predicts both Alloy Metals go to the one-Energy Active Duraludon
because the three-Energy Bench ex scores `-5000`; a healthy, three-Energy
Duraludon then offers Raging Hammer `224` for `80`. This is a hypothesis until
the engine fork below executes it.

If that predicted branch is confirmed, current damage falls from `220` to
`80`. After one public Adrena-Brain heal, a following Metal Defender deals
only enough to leave Grimmsnarl ex at `50`, whereas the parent branch's second
Metal Defender KOs it. Under the common public response
`Adrena-Brain + Shadow Bullet`, both branches can converge to one
three-Energy Archaludon ex at `120` HP after one three-Energy Duraludon is
KO'd for one Prize; the alternate is then 140 damage behind. This convergence
is a mechanics comparison, not a claim that the opponent must choose it.

Therefore, saving the invested Bench **from the named Bench-damage events** is
publicly certifiable. Saving it as a superior game resource, preserving the
parent's attack/Prize route, or improving the episode result is not
certifiable without the engine fork and opponent-policy assumptions.

## Regression surface

- **Current attack loss:** likely `220 -> 80`; this is the controlling veto.
- **Two-Prize exposure:** the Bench ex begins at exactly `180` HP. If gusted
  Active, payable Shadow Bullet `180` KOs it for the opponent's last two
  Prizes. Gust access is hidden, so this is a liability, not a certified line.
- **Alloy target mutation:** both target callbacks change identity and scores.
  Failure to attach twice to Active can also lose current attack payment.
- **Prize route:** `[5]` appears to abandon the parent's public two-hit
  Grimmsnarl-ex conversion; no compensating current Prize is certified.
- **Later promotion:** if Shadow Bullet KOs Active Duraludon, the saved ex is
  the forced promotion and remains attack-ready at 120 HP. This continuity is
  conditional on the public response, not guaranteed opponent behavior.
- **Energy route:** with two Alloy Metals routed to Active, either branch can
  lose a three-Metal Duraludon and retain a three-Metal ex. The alternate
  changes which exact Metals survive and does not prove a net resource gain.
- **Target choice:** Adrena-Brain and Shadow Bullet targets remain
  opponent-owned. The recorded target cannot be forced or imitated.
- **Rule breadth:** a generic damaged/invested-Bench bonus can spend an ex,
  create a gustable two-Prize breakpoint, react to a nonpayable attack, or
  preempt terminal, forced-defense, setup, survival, and attack-continuity
  transactions.

The local miss is policy target valuation, not deck construction: both
evolution targets and four Alloy Metals were public and legal. The episode
loss itself remains causally mixed with opponent strength, later hidden
access/draws, and policy; variance cannot be separated from one replay.

## Smallest exact engine evidence required

Run a read-only, both-logical-seat fork from the exact seed/decks and the
row-115 engine state, with semantic serial remapping:

1. Control branch emits `[4]`; alternate emits `[5]`. Assert identical prefix,
   promotion, public zones, options, and first difference.
2. On `[5]`, assert `#66` becomes `180/300`, retains 120 damage and
   `#116,#113,#93`, and Assemble Alloy exposes the same four discard Metals.
3. Delegate every later choice to the unmodified historical parent. Record
   the two Alloy target serials, resulting Energy serials, selected attack ID,
   target, damage, Prize change, turn completion, invalid action, and
   max-step status.
4. Stop at current attack resolution. If the alternate is Raging Hammer
   `224` for `80` while control is Metal Defender `253` for `220`, the source
   remains a mandatory negative and no implementation follows.
5. Only if current attack ID/damage/Prize-route identity is unexpectedly
   preserved should a second-stage fixture apply the already-public single
   energized-Munkidori plus Shadow-Bullet package through forced promotion and
   the next own attack. Do not add the later drawn Darkness, force opponent
   targeting in strength evaluation, or bundle Alloy/attack overrides.

This staged fork is smaller than replaying the full alternate game and tests
the first decisive regression before any source edit.

## Hierarchy and passive-ledger interaction

No component or precedence rank is authorized.

If a later source survives the attack-identity gate, develop it first as an
isolated direct-parent sibling. Integration must preserve exact-parent
terminal priority, active-owner priority, and all eight cumulative rules
(H2, search-aware terminal, H1, H5 v2, H4 v3/veto, H6 v2, Hero's Cape, H3
v2). Any active owner or competing frozen proposal suppresses the Bench rule;
unknowns delegate to the exact parent.

The pending Boss-access ledger remains passive bookkeeping and must not
mutate during speculative evaluation. Its Ultra Ball discard consumer is
already specified below all eight rules. It cannot collide with this source's
evolution option at the same callback, but an emitted/confirming discard
transaction must not acquire a second owner or be rewritten. A future
Bench rule would need explicit both-seat pairwise/all-eligible fixtures before
receiving any rank. Episode `88247531:115` itself must be a parent-identical
negative whenever inherited/current attack ID, damage, or Prize conversion is
not preserved.

## Raw rows for later verification

- `/steps/111/0/observation` through `/steps/113/0/observation`: payable
  Shadow Bullet and damage/KO prefix.
- `/steps/114/1/observation`, `/steps/115/1/action`: promotion control.
- `/steps/115/1/observation`, `/steps/116/1/action`: exact evolution options
  and parent `[4]`.
- `/steps/116/1/observation` through `/steps/121/0/observation`: parent
  evolution, Alloy, attack, and 220 damage.
- `/steps/121/0/observation` through `/steps/132/1/observation`: recorded
  opponent/next-turn facts; future draw/attachment must not be projected back
  into row 115.

No frequency, win-rate delta, uncertainty estimate, numerical promotion gate,
or Kaggle-slot recommendation is made.
