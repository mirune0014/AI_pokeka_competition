# Strategy selection: recycle -> Pad -> Alakazam attack line v1

Date: 2026-07-18 JST  
Parent: exact strict-Prize-lead retreat-KO bridge v3  
Decision: **IMPLEMENT as one isolated policy-only exploratory candidate**

## Evidence boundary

The submitted Active-Kadabra stage-up candidate first fell to
`624.0019429107213` after thirteen public games (`6-7`), then recovered to
`685.9451802890162` after twenty-two (`12-10`).  Checked replay-action comparison
found no difference from exact v3 on all 1,620 target callbacks, so neither the
drop nor recovery is attributed to stage-up.

Two independent Alakazam mirror losses exposed the same attacker-reconstruction
ordering failure:

- episode 86655180 consumed Poffin before Sacred Ash, then returned five
  evolution-line Pokémon after the search card was gone;
- episode 86657890 consumed Poké Pad before Sacred Ash while an energized
  Kadabra survived, then failed to build the replacement attacker before that
  Kadabra was Knocked Out.

Episode 86659510 later used Poffin before Ash but the Poffin fully converted
both open Bench slots into Abra, so the ordering was not causal; that game lost
to a distinct two-Prize Fez liability.  Therefore the candidate does not impose
a generic Ash-before-every-search rule and does not touch Poffin.

## Selected hypothesis

When exact v3 is about to play Poké Pad, replace that one choice with a frozen
multi-callback transaction only if all public information certifies an immediate
attacker reconstruction:

`Sacred Ash -> return exact Alakazam -> Poké Pad -> exact Alakazam to hand ->
evolve the established energized Active Kadabra -> Psychic Draw exactly three
-> delegate to exact v3`.

The hypothesis is that completing the whole visible reconstruction route before
spending Poké Pad restores attack continuity in one-Prize exchanges without
changing ordinary setup, deck composition or attack selection.

## Trigger contract

The transaction may start only at `MAIN`, after exact v3's finalized ordinary
winner is Poké Pad, and only when:

- Sacred Ash is also a legal play;
- Active is an already-established Kadabra with Psychic Energy;
- no Alakazam is on the field;
- discard contains an exact, uniquely visible Alakazam to return;
- both players have 1-4 Prizes remaining; Prize lead alone must not suppress
  attacker continuity;
- conservative deck arithmetic certifies Ash, Pad, evolution, Psychic Draw
  three and one later normal draw while retaining `deckCount > own Prizes`;
- every inherited transaction latch is empty.

The implementation freezes player, turn, Prize counts, hand/deck/discard facts,
the complete Active and Bench fingerprints, and exact Sacred Ash, Poké Pad and
Alakazam serials.

## Callback contract

1. Replace the frozen Poké Pad play with the frozen Sacred Ash play.
2. At `TO_DECK`, use deterministic parent-compatible selection up to the legal
   maximum and require the frozen Alakazam serial to be included.
3. Verify the exact Ash resolution deltas.
4. Play the frozen Poké Pad.
5. At `TO_HAND`, select the exact Alakazam returned by Ash.
6. Evolve the frozen Active Kadabra with that exact Alakazam.
7. Answer `YES` only to that Alakazam's Psychic Draw prompt.
8. Verify exact draw-three, top evolution, pre-evolution and Energy continuity.
9. Clear the transaction and delegate the remainder of the turn to exact v3.
   Powerful Hand is never forced.

Every stage fails closed to exact v3 on a turn/player/context/serial/board/
Prize/deck/hand/discard mismatch and may not restart in the same turn.

## Explicitly excluded changes

- no `deck.csv` change;
- no Poffin, Run Away Draw, Fez, Enriching, Boss, Hammer, retreat or Bench rule;
- no inherited score or latch change;
- no stage-up stacking;
- no opponent-policy proxy, hidden-card inference or replay-specific identity;
- no unconditional attack.

## Minimum exploratory live-probe gate

- compile/import, legal 60 cards and one ACE SPEC, deterministic valid actions,
  and exact deck equality;
- at least four complete positive routes covering both seats and serial order;
- at least twenty fail-closed cases covering stale/duplicate serials, dangerous
  deck, Prize or board change, fresh Kadabra, missing Energy/target and wrong
  context;
- exact fixed 144-row Phase-0 schedule, both seats on identical seeds, zero
  action errors and max-step hits, total non-inferiority and no v3-win-to-loss;
- every changed position inspected and every latch terminal;
- clean package and both-seat packaged smoke;
- authenticated Kaggle status/quota/new-episode refresh immediately before write.

Because the current live candidate is weak and the user has explicitly chosen
practical live experimentation, exact Phase-0 parity is sufficient for one
labelled exploratory submission after these safety gates.  Exact v3 remains the
rollback unless live evidence supports adoption.
