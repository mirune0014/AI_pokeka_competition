# Alakazam later-two isolated strategy selection

Date: 2026-07-17 (JST)  
Role: read-only `ptcg_sol_ultra_worker` strategy judge  
Scope: select and freeze exactly two rule hypotheses. No source edit, simulation,
package build, or Kaggle write was performed here.

## Decision

Implement and evaluate the following **two sibling candidates**, each directly
on the accepted `alakazam_fragile_bench_prize_clock_guard_v1` parent. Do not
stack them before each has passed its own paired screen and frozen 1,440-cell
broad schedule.

1. **Rank 1 — `alakazam_bossed_active_run_away_ko_bridge_v1`**: when the
   immediately preceding opponent turn used Boss's Orders to strand an
   unattached Dudunsparce Active, use Active Run Away Draw, promote an already
   energized Bench Alakazam, and take a same-turn Powerful Hand knockout under
   an explicit returned-stack/deck/prize certificate.
2. **Rank 2 — `alakazam_lone_dunsparce_enriching_reserve_v1`**: in a narrowly
   defined early singleton-Dunsparce emergency, take Enriching Energy from
   Hilda instead of a Psychic Energy, attach it to draw four, then spend the
   same turn establishing a Bench reserve through a deterministic priority
   chain.

These are materially distinct mechanisms: Rank 1 restores a developed board's
attack continuity after forced promotion; Rank 2 repairs opening-board
survival before the Alakazam engine exists. No deck-list change is selected.
The live opener shows an action-level Enriching line worth testing before
changing Basic counts, while the accepted 60-card list remains the only broad-
tested list for this parent.

## Frozen parent and evidence authorities

| Artifact | SHA-256 |
|---|---|
| accepted parent `candidates/alakazam_fragile_bench_prize_clock_guard_v1/main.py` | `60D61F4269566B5E922EA9044A32A0B3BA5BB769F8AE9959E86C0EDCB008A9C9` |
| accepted parent `deck.csv` | `7B413177E5077777F2178143839C0155B03B92BBC8B3A6607621A7D43F351141` |
| accepted parent runtime `main.py` | `89BB1CB867104ECF1418009CAAE6F9BC548682CC33474FF33537DC3DCFE75B60` |
| accepted parent broad freeze | `05EFBD4328547589E26B18BBE7658EA67AD91C36692CAB706457467E85033AC1` |
| accepted parent broad audit (830/1,440) | `B532657B64DE87E08A6C3536A97F24E63D3FA1CA9E484CB60A308FED4B426E71` |
| accepted parent Phase-0 audit | `6AF9B155C1516A6D958D1269C76C68AF4430DC74C7DE440FC5E3FBFCA1CA6D86` |
| live first-three qualitative diagnosis | `1CDA1E73932E6DF5C6A9C0167A5E72AB386DADDBE5D380753220D5F1B44CF2B5` |
| mirror replay episode `86369878` | `91CF2B01EC76288905BC319D0A4AADEDE2EB6BB1D855AE67AEB3C7696F59ACD8` |
| opener-loss replay episode `86371019` | `74F0B63CFAF76EFD43F2C1FB5D8C1C104B6A7C96CE1B49A89C0F49EB9BCD1D8E` |

Live replays support public-state diagnosis and rules, not action imitation or
opponent-policy inference. The local anchors below are exploratory opportunity
screens, not independent win-rate estimates.

## Rank 1: Bossed Active Run Away knockout bridge

### Why it ranks first

Episode `86369878` exposes the complete weakness twice. At replay state 153
and again at state 170, Boss's Orders has stranded Dudunsparce Active while an
energized Alakazam is ready on the Bench. The raw legal options include the
Active Dudunsparce ability as exactly `{"area":4,"index":0,"type":10}`.
The accepted parent instead ends without attacking. The same replay separately
executes Bench Run Away Draw twice and shows that the engine draws three and
returns both Dudunsparce and its underlying Dunsparce to the deck.

The two live states are arithmetically certified but are not live outcome
gains: the target already won by opponent deck exhaustion. At state 153,
hand/deck/prizes are `20/4/2`; drawing three gives 460 counters and returning
the two-card evolution stack leaves deck 3, enough to KO the 80-HP Kadabra. At
state 170 they are `18/3/2`; drawing three gives 420 counters and leaves deck
2, enough to KO the 140-HP Dudunsparce. This makes the replay a mechanics and
mill-clock boundary, not a causal win label.

### Exact fail-closed trigger

The overlay may replace the accepted parent's first MAIN choice only when **all**
of the following are true:

1. This is the first own MAIN decision of the turn (`turnActionCount == 1`),
   so no own action has erased the public forced-switch evidence.
2. The immediately preceding opponent-turn log contains a play of Boss's
   Orders `1182` followed by the forced-switch event whose destination serial
   is the currently Active Pokemon. If the Boss/play/switch/serial chain cannot
   be proven exactly from public logs, fail closed.
3. Own Active is Dudunsparce `66`, with exactly one pre-evolution Dunsparce
   `305`, zero attached Energy, and zero Tool cards. The exact Active ability
   option is legal.
4. At least one Bench Alakazam `743` has Psychic Energy `5` or `19` attached.
   Freeze the intended promotion serial before using the ability. If several
   qualify, select maximum attached-card count, then lowest Bench index.
5. Opposing Active serial and remaining HP are known and positive. Mist Energy
   `11` is absent; Rock Fighting Energy `20` is absent when that Active's
   printed Energy type is Fighting; and no other public status/card-metadata
   flag says damage counters cannot be placed. Unknown protection state fails
   closed.
6. Exactly three cards can be drawn. With this frozen zero-attachment,
   one-pre-evolution predicate, `returned_count = 2` and
   `post_deck = deck_count - 3 + 2`.
7. `20 * (hand_count + 3) >= opposing_active_remaining_hp`.
8. Let `post_KO_prizes = own_prizes - public_prize_value(opposing_active)`.
   Require either `post_KO_prizes == 0` or
   `post_deck > post_KO_prizes`. Equality fails closed.
9. The accepted parent does not already have a legal, certified same-turn
   knockout line that preserves the Active position without spending this
   draw. This overlay is an escape bridge, not a replacement for a stronger
   parent attack.

### Frozen three-step action latch

The implementation must be a small explicit state machine, not independent
one-step scores:

1. At qualifying MAIN, choose only the exact Active Dudunsparce Run Away Draw.
2. At the resulting `TO_ACTIVE`, choose only the frozen energized Alakazam
   serial. If the context or serial is not offered, clear the latch and use the
   unchanged parent policy; this unexpected branch is an engine-smoke failure
   and blocks promotion.
3. At the next MAIN in the same turn, require that the frozen Alakazam is
   Active with Psychic Energy, the opposing serial/HP/protection certificate is
   unchanged, and attack `1072` is legal. Choose Powerful Hand immediately.

Clear the latch on turn change, unexpected context, serial mismatch, absent
attack, changed target, or failed certificate. It must never select another
setup, Supporter, retreat, or draw action between promotion and H0 attack.

### Engine-legality gate before paired evaluation

The replay proves the Active ability is offered and separately proves the
three-draw/two-stack return effect, but it does **not** contain an executed
Active ability. A checked-engine integrated smoke must therefore demonstrate:

`MAIN Active ability -> draw 3/return 2 -> TO_ACTIVE frozen Alakazam -> MAIN -> legal Powerful Hand`

in one turn, with the expected hand/deck deltas and no invalid action. Failure
to produce that exact context sequence rejects Rank 1 before Phase 0.

### Exact Phase-0 paired screen

For every seed below run accepted parent and candidate on the identical engine,
opponent, seed, and both seats. The three positive anchor cells are:

| Block / opponent / seat / seed | Trace anchor | Required semantic change |
|---|---:|---|
| `new_fresh / great_tusk / p1 / 2026091708` | game 0007, step 100 | parent END becomes certified escape/promotion/KO; parent loss |
| `new_fresh / great_tusk / p0 / 2026091718` | game 0017, step 145 | parent attack drought becomes certified KO; parent later decks out |
| `new_fresh / great_tusk / p1 / 2026091725` | game 0024, step 115 | parent END becomes certified escape/promotion/KO; parent loss |

The positive schedule is the six exact cells formed by seeds
`2026091708, 2026091718, 2026091725` x seats `p0,p1` against
`new_fresh/great_tusk`. Only the three anchors above are expected to trigger;
their opposite-seat companions are paired controls.

Boundary schedule (also parent and candidate, both seats for every listed
seed) is exactly:

- `new_fresh / great_tusk / {p0,p1} / 2026091711`: Rock Fighting protection;
- `new_fresh / great_tusk / {p0,p1} / 2026091717`: attached Lucky Helmet cost;
- `new_fresh / great_tusk / {p0,p1} / 2026091723`: one Rock-protected state
  and one `post_deck == post_KO_prizes` state;
- `fresh / great_tusk / {p0,p1} / 2026081719`: Mist protection;
- `known / great_tusk / {p0,p1} / 2026071600`: insufficient damage/capacity.

All ten boundary cells must be complete-trace identical. Also rerun these eight
accepted fragile-Bench guard changed keys as inherited-retention controls:

`fresh/starmie/p0/2026081719`, `fresh/starmie/p1/2026081706`,
`fresh/starmie/p1/2026081712`, `known/starmie/p0/2026071597`,
`new_fresh/starmie/p0/2026091707`, `new_fresh/starmie/p0/2026091736`,
`new_fresh/starmie/p1/2026091719`, and
`new_fresh/starmie/p1/2026091730`.

Phase 0 passes only if all three anchors execute the exact three-stage latch,
all named boundaries remain trace-identical, the inherited gain
`new_fresh/starmie/p1/2026091719` remains a win, there are zero parent-win
regressions, and at least one of the three anchor parent losses becomes a win.

## Rank 2: lone-Dunsparce Enriching reserve

### Why it ranks second

Episode `86371019` loses when the target's only Dunsparce is Knocked Out before
any Bench Pokemon exists. Hilda's raw Energy selection at replay step 20 offers
four Telepath Energy, Basic Psychic, and Enriching Energy `13`; the parent takes
Telepath, which cannot search Basics when attached to Colorless Dunsparce.
Enriching instead draws four when attached from hand. In the remaining
44-card composition there were 17 immediate reserve-producing cards (nine
direct Basics, four Buddy-Buddy Poffin, four Poke Pad), an 87.1% composition
opportunity to see at least one in four draws. The actual counterfactual draw
order is unknown, so this percentage is not a replay win claim.

This ranks below the first rule because it spends the ACE SPEC, depends on
hidden draw order, and only probabilistically creates the reserve. It is still
worth an isolated test because it converts two otherwise dead choices—Hilda
and an Energy attachment—into the only same-turn path to a second Pokemon.

### Exact fail-closed trigger

Choose Enriching in Hilda's Energy `TO_HAND` selection only when **all** are
true:

1. The source/effect latch proves this is Hilda `1225`'s Energy choice (not its
   Evolution choice or another search). Every offered card is an Energy and
   Enriching `13` is an exact legal option. Ambiguous source context fails
   closed.
2. It is an early emergency: `state.turn <= 3`, own prizes are six, Active is
   Dunsparce `305`, Bench is empty, and that Dunsparce has no Energy attached.
3. Hand contains no Basic Pokemon from
   `{741,305,343,858,142,140}`, no Buddy-Buddy Poffin `1086`, and no Poke Pad
   `1152`. A guaranteed reserve route already in hand disables the rule.
4. The public opposing Active is in the frozen immediate singleton-loss threat
   set `{Solrock 676, Riolu 677, Duskull 131, Staryu 1030}`. This is a static
   public-board risk whitelist, not an inference about hidden cards or the
   opponent's policy. In particular, the Dudunsparce mirror boundary is off.
5. The conservative deck certificate `deck_count - 6 > own_prizes` holds. It
   reserves four draws, up to two search removals, and keeps the post-action
   deck strictly ahead of the prize clock.
6. Enriching has not already been attached/discarded and no emergency latch is
   active from another turn.

### Frozen multi-step action latch

1. In the certified Hilda Energy selection choose Enriching `13`.
2. At the next same-turn MAIN, if exact legal `ATTACH Enriching -> Active
   Dunsparce` exists and the singleton predicate still holds, choose it
   immediately. Otherwise clear the latch and revert to parent.
3. After the four-card draw, while Bench is still empty, choose the first legal
   reserve route in this fixed order:
   - directly play Basic: Abra `741`, Dunsparce `305`, Shaymin `343`, Psyduck
     `858`, Genesect `142`, Fezandipiti ex `140`;
   - else play Buddy-Buddy Poffin, then select Abra before Dunsparce at
     `TO_BENCH`;
   - else play Poke Pad, select the first available non-Rule-Box Basic in the
     same priority order at `TO_HAND`, then play it.
4. Stop as soon as Bench becomes nonempty. Do not force an evolution,
   Run Away Draw, second Basic, or unrelated hand-development action.

Clear on turn change, unexpected selection context, source ambiguity, missing
Enriching attachment, no legal reserve route, or any public-state predicate
change. A checked-engine integrated smoke must first prove the exact sequence
`Hilda Energy TO_HAND -> choose 13 -> MAIN attach 13 -> draw four -> MAIN legal
Basic/Poffin/Poke Pad route`. If attach/draw context does not match, reject
before Phase 0.

### Exact Phase-0 paired screen

Positive schedule is parent and candidate, both seats for each listed
opponent/seed (six cells); the expected trigger anchors are the three P1 cells:

- `new_fresh / mega_lucario / p1 / 2026091723`, trace game 0022 step 19;
- `new_fresh / dragapult / p1 / 2026091735`, trace game 0034 step 17;
- `fresh / starmie / p1 / 2026081710`, trace game 0009 step 19.

Boundary schedule is parent and candidate, both seats for each listed
opponent/seed (six cells):

- `new_fresh / alakazam_rmy / {p0,p1} / 2026091723`: Dudunsparce mirror,
  including a parent P1 win; threat whitelist must be off;
- `new_fresh / alakazam_rmy / {p0,p1} / 2026091728`: Poke Pad already in hand;
- `new_fresh / marnie_sota / {p0,p1} / 2026091725`: direct Basic already in
  hand.

Also rerun the inherited fragile-Bench gain
`new_fresh/starmie/{p0,p1}/2026091719`. Phase 0 passes only if all three P1
anchors choose and attach Enriching, at least two establish a Bench Pokemon
before the opponent's next attack, every boundary is complete-trace identical,
the inherited P1 gain remains a win, there are zero parent-win regressions, and
at least one anchor parent loss becomes a win. Repeated states sharing one seed
across opponents are robustness controls, not independent positive evidence.

## Broad gates for each sibling candidate

Only after its own Phase-0 PASS may a candidate run the exact accepted-parent
1,440-cell schedule from `BROAD_EXECUTION_FREEZE.md`: same checked engine, nine
opponents, `known/fresh/new_fresh` panels, both seats, and identical seeds.
Parent and candidate raw rows must have unique and exactly equal
`(panel, opponent, seat, seed)` keys.

Every candidate independently must satisfy all of these:

1. compile/import, legal unchanged 60-card deck, both-seat packaged-style
   smoke, deterministic repeat of every changed key, and frozen-file hashes;
2. exactly 1,440 started/result rows; zero command failure, retry, invalid
   action, action error, malformed/missing result, duplicate key, or max-step
   hit;
3. candidate wins `>= 830/1,440`, zero parent-win-to-candidate-loss flips, and
   no regression in either seat, any panel, or any opponent bucket;
4. Rank 1: Great Tusk combined wins improve by at least one and every changed
   trace is explained solely by the frozen Boss/escape latch;
5. Rank 2: combined Mega Lucario + Dragapult + Starmie wins improve by at least
   one and every changed trace is explained solely by the frozen opener latch;
6. the accepted fragile-Bench gain remains present, and no state outside the
   declared positive predicate changes before a later deck-order or opponent-
   choice boundary;
7. independent numerical recomputation and final Sol-Ultra rule judgment PASS.

These gates deliberately prefer clean safety over spending a slot merely
because time remains. Neither candidate may be called Bronze-stable, Gold-
competitive, statistically significant, or live-improved from these screens.
If both pass, they remain two mechanism-distinct submission probes; do not
merge them into a third candidate without a new strategy judgment and a full
new evaluation.

