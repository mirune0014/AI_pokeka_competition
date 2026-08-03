# Final Fez-v1 judgment and next isolated rule: next-own-turn Powerful Hand continuity v2

Date: 2026-07-17 (JST)  
Role: read-only Sol-Ultra final strategy judge  
Scope: final v1 accept/reject decision and selection of exactly one next
deterministic hypothesis. No source, deck, battle, package, or Kaggle write
was performed.

## Decisions

1. **REJECT `alakazam_fez_ready_attacker_immediate_ko_bridge_v1`.** Preserve
   its source and raw evidence read-only. It must not be adopted, packaged, or
   submitted.
2. Select **option B: next-own-turn attach-plus-evolve Powerful Hand
   continuity** as the sole next hypothesis.
3. The implementation parent must be exactly the accepted
   `alakazam_lone_dunsparce_enriching_reserve_v1`. Fez v1 is code/mechanics
   reference only; it is not the parent. Do not stack Dudunsparce, Run Away,
   attack-disabled Active, Boss, deck-clock, deck-list, or another sibling
   change into this candidate.

Provisional candidate name:
`alakazam_fez_next_turn_powerful_hand_continuity_v2`.

## Rehashed authority and independent checks

I read every controlling report in full and independently recomputed these
SHA-256 values:

| Authority | SHA-256 |
|---|---|
| Fez-v1 broad freeze | `8DC01E8B181E0F6C9EB04A94A13E6342E64C1BA89C5ED0DD49BF2412B8A2DA2E` |
| Fez-v1 broad manifest | `E20D3C7480C2156EBAED82A96606DB2F3DF18654BBD73F2148C995A891A2BE86` |
| Fez-v1 broad numerical audit | `3A808E3632B49E88B4DB1F1B3A31F4C97C50C755A586D0C39D8D513C885E78F8` |
| changed-state reconstruction | `3A39550E6B3526B2FD4D78EF72982448A85F6FEE2A812915433C669D51229F91` |
| gain trace analysis | `05BADCEFC74636A5520D13511DFDA4E24F12B466ECBB4E8F5FD001B8E9347A2D` |
| regression trace analysis | `AD03C054F6BED060FE04EC8D11DB27F55245ADAF463F4624989E2012A91A519B` |
| root broad verification | `80979AF5BCC1401741B675025FE5E137E09C514A009CA846C7F79B9B60974BC5` |
| accepted-parent corrected broad freeze | `874E7A5583AE61622C340372524F9DCABE8B170F38CD4D0DFBB34409253BE53D` |
| accepted-parent corrected broad audit | `56F1D4413415AD215EE0B16C2EB82A3B3F82591FA05C00550D0D60D3F83AB47F` |
| accepted-parent root numerical verification | `2EAF0A372DDBD85DAC06493505FAB3B29B1A79FF5C1D2AC9EFE83B0E742F3421` |
| accepted-parent final judgment | `79935687A0EEDC27623E17737ED37857AC7F5029A534CFE4BB5CED92018ED8AE` |
| original live strategy | `1D530C759553B4661E634F5F63553A7ECBEB20864BCD30ACEC73EBB551130EB8` |
| v1 checked-engine live fixture | `3FE5959E5E132CC61A3919B9B47DDF1525DBB18229C2A1D6BBA2B3DC8B4EE3BC` |
| original Fez live-anchor verification | `C2D2A37875A16D593B4DBD44CC3A694BCAC2662BDA0B6FBAEB9347EA2AA55730` |
| latest-ten live synthesis | `B6047AC09C69F76ED2EC9FCABA3A3890B174555D158C761A3FA143A74109F04A` |

I independently reparsed all 2,880 broad summaries from raw paths. Parent and
v1 each have 1,440 unique equal keys, wins are `833 -> 838`, and paired
gain/regression/tie is `9/4/1427`; raw summary fault rows are zero. The four
regressions exactly match the root list. Historical Silver alone falls below
its floor, `60 -> 58`, with `0` gains and `2` regressions.

I also independently hashed all 1,440 complete trace pairs: `1,405` are
byte-identical and `35` differ. Only `34/35` first differences select RETREAT.
In `new_fresh|great_tusk|p1|2026091722`, both policies already choose the same
RETREAT and payment; the first difference is context-3 promotion. These direct
checks agree with the numerical audit and root verification.

## Decision 1: why v1 is formally rejected

The frozen broad gate is conjunctive. The aggregate `+5` cannot repair:

- four parent-win to candidate-loss regressions;
- Historical Silver `58 < 60`;
- one promotion-first difference that violates the declared RETREAT-first
  isolation boundary.

All 35 bridge transactions are mechanically real and exact, so this is not an
engine or invalid-action failure. It is a planning-horizon failure. In every
regression v1 spends the only exchange-relevant Alakazam to KO a one-Prize
target while five Prizes remain, then cannot present another Powerful Hand
attacker. The two Historical lines eventually concede Fez for the opponent's
last two Prizes anyway. Immediate KO legality is therefore necessary but not
sufficient.

The accepted parent remains frozen at source/runtime/deck hashes:

`77D111B6061A9A5EF1BCCA383181E1A5EBD67DF10CA45AB0936BE0AAD275785A` /
`6AF5399EEA0B9051722D39408E02822C6D641B499BC7D578F21ED2B0692EC0C9` /
`7B413177E5077777F2178143839C0155B03B92BBC8B3A6607621A7D43F351141`.

V1 source/runtime hashes
`7CFEC337D77EB027BD7D9B4D35064EF1C2917A48A788085F6184425AB96805DF` /
`524FD41ADC2FF91B9705EFADA0AD6B8AC05BF9612D504B77FF223291B80E7C78`
may be read to copy the already-proven immediate transaction, but those files
must not be edited or used as the implementation parent.

## Decision 2: choose B over A and C

Choose the **next-own-turn attach-plus-evolve extension (B)**.

The strict certificate A is safe in the observed classifier (`15` v1-changed
opportunities, `6G/0R/9T`). B adds exactly one domain-coherent construction:
a current Bench Kadabra plus an exact Alakazam and exact Basic/Telepath Psychic
Energy already known in hand can, on the next own turn, use the normal
evolution and normal attachment actions to become a Powerful Hand attacker.
It does not require a draw, search, Supporter, Rare Candy, opponent model, or
calendar/deck cutoff. The public classifier becomes `17` opportunities with
`7G/0R/10T`.

This choice is not justified merely because seven exceeds six. Evolution and
attachment are two independently legal ordinary actions in the same next own
turn, so excluding that line would discard a fully known attacker construction
for no game-rule reason. The B-only retained key is
`new_fresh|alakazam_oselcoun|p0|2026091733`; it is a required test boundary,
not an opponent/seed exception in source.

The full overlay additionally declines to intervene when the accepted parent
already chooses RETREAT. That orthogonal isolation condition keeps
`new_fresh|great_tusk|p1|2026091722` completely parent-identical. Consequently
the pure public B classifier is `17 = 7G/0R/10T`, while expected actual overlay
starts among those saved states are `16 = 7G/0R/9T`. This is not an
outcome-fitted threshold; it repairs the literal promotion-first isolation
failure.

Do not move to C yet. The current evidence supplies a public, interpretable
separator that rejects all four regressions and preserves a new exact live
anchor. Dudunsparce/other live gaps remain the next family only if this fresh
isolated v2 fails Phase 0 or broad evaluation.

## Exact a-priori start predicate

The worker must branch from the accepted parent and add one overlay only. The
overlay may replace the parent's action iff every base condition and one
continuity branch below is true.

### Base immediate-KO certificate

1. Own selection is `MAIN`, turn is at least 2, retreat has not been used, no
   Hilda/Enriching/Fez latch is active, and select multiplicity permits exactly
   one action. The accepted parent's deterministic top choice exists and is
   neither ATTACK nor RETREAT. If the parent already attacks or retreats,
   delegate exactly to it.
2. Own Active is Fezandipiti ex `140`, with a positive serial and complete
   public fingerprint. A legal RETREAT option exists. Printed retreat cost,
   all attached Energy identities/serials, and the exact positive-serial
   payment are unambiguous. Basic Psychic `5`, Telepath Psychic `19`, and
   Enriching `13` are single-unit payment cards; any unknown/multi-unit
   ambiguity fails closed.
3. Select the primary Bench Alakazam `743` exactly as v1 did: it has a positive
   serial and attached Basic/Telepath Psychic (`5` or `19`); choose most
   attached cards, then lowest Bench index, then lowest positive serial.
   Freeze it before evaluating a successor and exclude its serial from the
   successor set.
4. Opposing Active has positive serial/HP and a complete fingerprint including
   evolution stack, Energy IDs/serials, Tool, owner, and all statuses. Exact
   public Prize value is known. Mist Energy `11`, Rock Fighting Energy `20` on
   a printed Fighting Pokemon, any other known prevention, or incomplete
   protection information fails closed.
5. Current hand is fully materialized (`len(hand) == handCount`), all cards
   required below have positive distinct serials, attack `1072` will be legal
   after promotion, and `20 * current_hand_count >= target_remaining_HP`.
   No draw, evolution, Supporter, search, ability, or opponent action may be
   assumed for the immediate KO.
6. Let `target_prizes` be the exact public Prize value and
   `post_ko_prizes = own_prizes - target_prizes`. Require nonnegative
   `post_ko_prizes` and either `post_ko_prizes == 0` or
   `current_deck_count > post_ko_prizes`. Equality fails closed.

### Continuity disjunction

After freezing and excluding the primary Alakazam, allow the bridge iff at
least one branch holds:

1. **Final Prize:** `post_ko_prizes == 0`.
2. **Two-plus Prize target:** `target_prizes >= 2`.
3. **Known-draw-free next-own-turn Powerful Hand successor:** choose one
   complete, positive-serial secondary Bench Pokemon by the fixed rank below,
   then lowest Bench index, then lowest serial:
   - rank 0: another Alakazam `743` already has attached Basic/Telepath Psychic
     `5` or `19`;
   - rank 1: another Alakazam `743` lacks such Energy, and an exact Basic or
     Telepath Psychic card is already known in hand, so one normal attachment
     next own turn makes Powerful Hand legal;
   - rank 2: another Kadabra `742` already has Basic/Telepath Psychic, and an
     exact Alakazam `743` is known in hand, so one legal evolution next own
     turn preserves the Energy and makes Powerful Hand legal;
   - rank 3, the B extension: another Kadabra `742` lacks Basic/Telepath
     Psychic, while distinct exact Alakazam `743` and Basic/Telepath Psychic
     `5`/`19` cards are both known in hand. One normal evolution and one normal
     attachment on the next own turn make Powerful Hand legal.

For ranks 2/3, the current Pokemon must already be a public Kadabra with a
complete evolution fingerprint and remain evolution-eligible on the next own
turn under engine rules. A Kadabra that appeared/evolved this turn is allowed
only because a complete opponent turn necessarily precedes the next own turn;
the checked-engine fixture must test both current `appearThisTurn` values.
No Abra/Rare Candy path, search, retrieval, future draw, merely legal
30-damage Kadabra attack, Enriching-as-the-successor-Psychic assumption, or
opponent-policy prediction counts.

The successor certificate proves a known resource path to attack legality,
not that an unknown future target will be KO'd. Future target HP, protection,
damage, and clock must be re-evaluated from the then-current public state. V2
does not add a next-turn action-forcing overlay; doing so would be a second
hypothesis.

## Frozen latch and fail-closed behavior

At bridge start freeze turn/player, Fez serial/fingerprint, exact payment
serials, primary Alakazam serial/fingerprint, target fingerprint/Prize value,
hand/deck/Prize counts, continuity branch, successor serial/fingerprint, and
any exact hand Alakazam/Energy serials used by ranks 1-3.

Execute only:

`RETREAT -> context 30 exact payment -> context 3 exact primary Alakazam ->
same-turn MAIN attack 1072 -> certified KO`.

At every callback recheck same turn/player, complete target and count
fingerprints, source/destination/successor/resource serials, payment state,
protection, damage, attack legality, and clock. Any unexpected context,
mutation, ambiguity, absent unique option, lost card, changed target, or
failed certificate clears and delegates to the accepted parent. A latch clear
after irreversible RETREAT is an integrated-smoke failure even if fallback is
action-valid. No setup, draw, attach, evolve, Boss, Supporter, second retreat,
or opponent decision may occur inside the transaction.

Clear all Fez state after KO resolution. The successor fields are frozen to
prove and audit the start decision; they do not force a later action through
opponent disruption. This keeps v2 one isolated forward-looking gate plus the
already-proven immediate transaction.

## Six live-anchor disposition

All six targets below are one-Prize Pokemon while own Prizes are six, so the
terminal and two-plus-Prize branches do not apply. I read the exact visualizer
state for each start, not only the report label.

| Episode/state | V2 | Public reason |
|---|---|---|
| `86459487` raw 60 P1, replay `5D0FDEF2B8640210DAA61DBBA6EFE5F0494FADC108EB786A80BCD3261DAEC35F` | **PASS** | after freezing energized Alakazam `s71`, another unenergized Alakazam (`s72`/`s73`) remains and Telepath Psychic `19/s119` is known in hand: rank 1 |
| `86387405` raw 55 P1 | **PASS** | after freezing energized Alakazam `s72`, Kadabra `s70` already has Telepath `19`, and Alakazam `743/s71` is known in hand: rank 2 |
| `86386369` raw 49 P0 | suppress | remaining Kadabra is unenergized; Alakazam is in hand but no Basic/Telepath Psychic is known in hand |
| `86430395` raw 91 P1 | suppress | remaining Alakazam is unenergized and no Basic/Telepath Psychic is known in hand |
| `86387293` raw 73 P1 | suppress | remaining Kadabra is unenergized and Psychic Energy is known, but no Alakazam is known in hand |
| `86381796` raw 58 P0 | suppress | remaining Kadabra and Alakazam-in-hand exist, but no Basic/Telepath Psychic is known in hand |

The four suppressions must return the exact accepted-parent action. In
particular, suppressing the previously winning `86381796` boundary preserves
its parent win instead of treating a v1 fire as mandatory. `86385015` remains
fail-closed independently on damage, protection, and clock. The two PASS
anchors must execute the exact checked-engine payment/promotion/1072/KO chain;
no full-game counterfactual claim follows.

## Immutable Phase 0 after implementation

Before any execution, root must freeze accepted parent/candidate source,
runtime and unchanged legal deck hashes; v1 reference hashes; checked
runner/engine; opponents; live replays; reconstruction evidence; exact output
schema and an absent destination.

### Directed predicate/mechanics tests

1. Re-evaluate the pure B continuity predicate on all 35 reconstructed v1
   start states from public data: exactly `17` pass and `18` fail, with
   diagnostic categories `7G/0R/10T`. Then apply the parent-action isolation
   condition: Great Tusk P1 `2026091722` becomes parent-identical, leaving 16
   authorized overlay starts in that saved set.
2. All four v1 regression starts fail. The seven retained-gain starts below
   pass. The two rejected-gain starts and promotion-first Great Tusk control
   fail the full overlay gate.
3. Live `86459487` and `86387405` complete the exact chain. The other four
   listed live anchors and `86385015` are parent-identical.
4. Focused tests cover each continuity rank; distinct-card/serial accounting;
   rank-3 attach+evolve in both orders; next-turn evolution timing with current
   `appearThisTurn` true/false; final-Prize and two-plus-Prize branches; unknown
   hand/target/protection; Mist/Rock; strict clock equality; parent ATTACK;
   parent RETREAT; and mutation at every latch stage.

### Exact paired schedule

Run parent then candidate, both seats, one game per key, identical engine seed,
explicit decks, `--max-steps 1000`, and complete traces for these 18
block/opponent/seed triples (`36` paired keys, `72` commands):

Retained B gains:

- `fresh/alakazam_rmy/2026081714` (retained gain is P1);
- `fresh/marnie_sota/2026081719` (P0);
- `known/dragapult/2026071585` (P1);
- `new_fresh/dragapult/2026091728` (P1);
- `new_fresh/kangaskhan_crustle/2026091736` (P0);
- `new_fresh/marnie_sota/2026091706` (P1);
- `new_fresh/alakazam_oselcoun/2026091733` (P0, rank-3 B-only boundary).

Mandatory suppression controls:

- regressions:
  `fresh/marnie_sota/p0/2026081708`,
  `new_fresh/alakazam_oselcoun/p1/2026091703`,
  `new_fresh/historical_silver/p0/2026091736`,
  `new_fresh/historical_silver/p1/2026091706`;
- rejected v1 gains:
  `fresh/alakazam_oselcoun/p1/2026081701`,
  `new_fresh/mega_lucario/p0/2026091736`;
- promotion-first isolation:
  `new_fresh/great_tusk/p1/2026091722`.

Accepted-parent gains/control:

- `fresh/starmie/p1/2026081710`;
- `new_fresh/dragapult/p1/2026091735`;
- `new_fresh/starmie/p1/2026091723`;
- `new_fresh/starmie/p1/2026091719`.

The accepted parent has `22/36` wins on this exact both-seat schedule. Phase 0
passes only if candidate has at least `29/36`, retains all seven named
loss-to-win keys, has zero regression, and keeps all four original regression
keys, both rejected-gain keys, the promotion-first key, and the four accepted
controls completely parent-identical on their named seats. Opposite-seat
differences are allowed only when the complete v2 predicate and transaction
are certified; no unexplained action difference is allowed.

Every changed Phase-0 key must repeat candidate-only three times with
byte-identical complete traces and summary equality after normalizing only the
trace path. Compile/import, legal 60-card deck, both-seat packaged-form smoke,
command exits, schedule equality, action validity, action errors, max-step
hits, malformed rows, caches, and all hashes must pass with zero fault.

## Broad gate

Only after a fresh Sol-Ultra Phase-0 GO, run candidate-only on the accepted
parent's exact frozen 1,440-key schedule. Compare against accepted parent raw
tree digest
`0AFFC9C3F19CF166DA314FDBF514C95B0BEC210417FA345C75D36719AE0A02A9`.

Broad PASS is conjunctive:

1. exact equal 1,440-key schedules; candidate at least **`840/1440`** (the
   accepted `833` plus all seven retained gains); zero parent-win regression;
2. all seven retained-gain keys remain wins; all four v1 regression keys are
   complete parent-identical wins; the two intentionally rejected v1 gains
   and Great Tusk promotion-first control remain complete parent-identical;
3. candidate floors are at least the accepted parent: known `211`, fresh
   `202`, new_fresh `420`, P0 `415`, P1 `418`; Historical Silver `60`, Mega
   Lucario `134`, Starmie `105`, Dragapult `139`, Marnie Sota `106`, Great
   Tusk `26`, Kangaskhan/Crustle `77`, Alakazam Oselcoun `90`, and Alakazam
   Rmy `96`;
4. every non-trigger trace and normalized summary is parent-identical; every
   changed prefix is byte-identical until a RETREAT first difference, and
   every first difference certifies one of the exact continuity branches plus
   the full same-turn KO transaction. Promotion-first or unrelated differences
   are zero;
5. all three accepted Enriching gains and the inherited fragile control remain
   wins and trace-identical unless a fully certified v2 transaction occurs;
6. every missing serial/fingerprint field is reconstructed from the
   hash-bound checked engine; unverified changes, latch aborts after RETREAT,
   unexplained later fires, invalid actions, errors, max-step hits, malformed
   rows, schedule faults, retries, cache/reparse artifacts, or hash mismatch
   are all zero.

The `17`/`7G0R` and projected `840` figures are diagnostic expectations, not
counterfactual replay labels. Suppressing an early v1 bridge can expose a
later v2 opportunity, so complete fresh traces and outcomes remain mandatory.
No turn number, deck count beyond the predeclared Prize clock, opponent name,
seed, target card ID, or saved outcome may be added as a filter.

A literal broad PASS still requires root raw verification and a fresh
Sol-Ultra final accept/reject judgment. It does not itself authorize packaging
or Kaggle submission.
