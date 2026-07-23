# Strategy selection: stranded-Active ready-Alakazam retreat bridge v1

Date: 2026-07-18 JST  
Decision: **BUILD exactly this retreat mechanism next. Do not implement the
setup-before-KO deferral in the same candidate.**

## Evidence and priority decision

The live parent is
`candidates/alakazam_active_psychic_lone_dudunsparce_survival_v1`, exact
source/runtime/deck SHA-256
`FAB47771161EF7F43C9402B58D38FF240C92B6A2B77FFA6B925DFEA7F990D033` /
`9CA7A415451B84343165EF8A5CDC0D67BBF1B4969A13C984C09B142B4898CD9A` /
`7B413177E5077777F2178143839C0155B03B92BBC8B3A6607621A7D43F351141`.
Clone it unchanged except for the selected mechanism into
`autonomous_gold_20260715/candidates/alakazam_stranded_active_ready_alakazam_retreat_bridge_v1`.

The active-Psychic mechanism remains valuable: fixed Phase 0 is `84/144`
against accepted-v6 `78/144`, with 11 gains / five regressions, P0 `45/72`,
P1 `39/72`, known `43/72`, fresh `41/72`; only Alakazam Rmy fails its old
floor (`7/16` versus `9/16`). The lone-Dudunsparce overlay is outcome-neutral
on that panel and fixes the proven last-Pokemon self-loss. Its parent audit is
SHA-256 `DFA65CB1BFDC053686B108FBC6DB4B1E328721B1DD847ACF3B2E39A9857A30FD`.

New live self-play episode `86585479` (replay SHA-256
`8F0D9978D57F33B47862EC3D7F1A02E56BB6FEC16BC0715620937F0D33961B28`)
is stronger priority evidence than the local setup trade-off:

- submitted guard equals the active-Psychic parent on all P0 `87` and P1
  `91` decisions (comparison SHA-256
  `FFDFF10C970A92FF0C3B84684387B848C3B634BFEAF1C5A50E680C7273C9B878`
  and `4A8300EBB43E983282154E255EC3BB6BF44A8DEB3C723B50643E224E3E3AAF72`);
  the lone guard did not fire;
- active-Psychic attach-to-KO transactions complete on P0 turn 9 and P1
  turns 8 and 10, so the gain mechanism is functioning live;
- at P0 observation S141, forced Active Fezandipiti ex `140/s19` has no
  Energy, while Bench Alakazam `743/s13` already has Telepath Psychic `19`;
  deck/prizes are `5/2`. The inherited policy correctly attaches Basic
  Psychic `5` to Fez;
- at S142 the now-payable `RETREAT` is legal, but the policy plays Boss. At
  S144 `RETREAT` is still legal and it selects `END`. It repeats END with the
  same stranded Fez through deck `0` and loses by deck-out, despite the ready
  Bench attacker.

This is a general broken turn plan: the scorer recognizes the need to attach
retreat Energy, then forgets that intent because Fez is absent from the
hard-coded RETREAT whitelist. It is an immediate deterministic live loss and
its activation state is disjoint from the Active-Alakazam transaction. Select
it before setup-before-KO. The latter remains the next independent hypothesis;
stacking it now would destroy causal attribution.

## Exact selected rule

Implement one fail-closed, public-state transaction:

`stranded non-attacking Active + legal payable RETREAT + publicly complete
energized Bench Alakazam + opponent Active is KO-able by Powerful Hand ->
RETREAT -> pay exact Energy -> promote frozen Alakazam -> Powerful Hand`.

### Activation boundary

Start only at `SelectContext.MAIN`, own turn `>=2`, with no Hilda,
Enriching-Reserve, Fez-KO, active-Psychic, or new retreat latch active, and all
of the following true:

1. `state.retreated == False`; own Active is publicly complete and is **not**
   an Alakazam already carrying Psychic; there is no legal `ATTACK` option.
2. Exactly one or more legal `OptionType.RETREAT` options exist, the printed
   retreat cost is positive and publicly exact, and currently attached
   single-unit Energy can pay it. Visible Pokémon, Tools, and Stadiums must
   contain no retreat-cost modifier, using the existing exact-cost guard.
3. Deterministically select a publicly complete Bench Alakazam with Psychic
   attached using the existing destination rank (most attached cards, then
   Bench index, then serial). Freeze its component fingerprint.
4. Own hand is fully visible; opponent Active is publicly complete and its
   Powerful-Hand damage is publicly clear; `20 * handCount >= target.hp`.
   Freeze target, hand/deck/prize/stadium counts and require
   `post_KO_prizes == 0` or `deckCount > post_KO_prizes`.
5. All protected source, destination, target, payment-Energy and component
   serials are positive and unique. Tie payment by ascending Energy serial
   and RETREAT option by option index. No card ID, opponent, seat, turn, seed,
   or episode predicate is allowed.

The inherited attachment decision is deliberately untouched. In S141 it
already attaches to escape. This candidate begins at the first state where
RETREAT is actually legal (S142), making the mechanism materially broader
than Fez while isolated from Energy-placement policy.

### Controlled actions and stop condition

- At activation, select RETREAT and latch turn/player, source, destination,
  target, exact payment serials and all frozen fingerprints.
- At each `DISCARD_ENERGY` callback select only the next frozen payment serial.
- At `SWITCH` or `TO_ACTIVE`, select only the frozen energized Alakazam.
- On the next MAIN callback, require the frozen Alakazam to be Active,
  `state.retreated == True`, unchanged target/counts, a unique legal Powerful
  Hand `1072`, and still-sufficient public damage; then attack immediately and
  mark `await_resolution`.
- Clear after the resolution callback. Exactly one retreat and one attack are
  allowed; do not run setup, gust, draw, Ability, or a second retreat inside
  this transaction.

On any unexpected context, stale turn/player, changed source/destination/
target/hand/deck/prizes/stadium, ambiguous or missing option, altered payment,
retreat-cost uncertainty, illegal destination, insufficient damage, or failed
clock check: clear the latch and delegate to the exact parent. Never emit a
stale or guessed action. Preserve the lone-Active-Dudunsparce guard verbatim.

## Immutable implementation and Phase-0 gates

Before any exploratory write require compile/import, exact legal 60, source/
runtime parity, deterministic repeated-callback validity, and checked-engine
multi-step tests for RETREAT payment, `SWITCH` and `TO_ACTIVE`, stale-state
fail-close, plus packaged both-seat smoke.

Use the existing fixed 144-key schedule unchanged, SHA-256
`4271E31503F37EFE4B1BBB9ED2D3569D79D9C1E9B2A20387CCAC131F28346010`,
with the exact guarded parent above in both seats. The gate is conjunctive:

1. `144/144` starts and exits; zero action errors, max-step hits, malformed or
   duplicate rows, schedule/seat/seed mismatch, or invalid selections.
2. Candidate total `>=84`; P0 `>=45`, P1 `>=39`, known `>=43`, fresh `>=41`.
3. No 16-game opponent bucket falls more than one below guarded-parent values
   `Oselcoun 7, Rmy 7, Dragapult 15, Great Tusk 4, Historical-Silver 8,
   Kangaskhan/Crustle 9, Marnie 11, Mega Lucario 14, Starmie 9`; Rmy must stay
   `>=7` and Historical-Silver `>=7`.
4. Every new first difference is an activation-bound RETREAT; every started
   transaction reaches the frozen Alakazam and same-turn Powerful Hand KO, or
   fails closed for an exactly recorded public mismatch. Partial/stale routes
   and unrelated first differences are zero.
5. Direct fixtures retain all 60 certified active-Psychic attach-to-KO
   transactions, S134 positive / S135 negative / S143 positive boundaries,
   and live `86580164` S21 lone-Dudunsparce END behavior.
6. Reconstructed live `86585479` S142 must choose RETREAT instead of Boss,
   pay Basic Psychic `5`, promote Alakazam `743/s13`, and use Powerful Hand in
   that turn; both submitted seats must remain deterministic and valid.

If any gate fails, reject this candidate rather than adding setup-before-KO
or a Fez/episode exception. A later candidate may independently implement one
Psychic-Draw evolution before a certified KO, but that is explicitly outside
this implementation.
