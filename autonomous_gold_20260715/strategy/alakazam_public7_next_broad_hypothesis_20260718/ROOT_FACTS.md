# Root-verified facts for the next broad Alakazam hypothesis

## Immutable live state

- Current submission: `54802782`, Active-Kadabra stage-up v1.
- Authenticated 2026-07-18 18:48 JST state: `COMPLETE`, CLI `685.9`, exact
  latest episode score `685.9451802890162`, UTC quota `3/5` used.
- Twenty-two public games: `12-10`; the nine games after the 18:08 snapshot
  were `W,W,W,W,W,L,W,L,L` (`6-3`).
- Exact strict-Prize v3 and submitted stage-up are identical on all 1,620 target
  callbacks; stage-up has zero live activations.  No live result is attributed
  to the new rule.
- Exact v3 source SHA-256:
  `49E954F53E043CD79D928DFB2340CCB5D85A17F33CCB824C871CCE153C0C9C95`.
- Current deck SHA-256:
  `7B413177E5077777F2178143839C0155B03B92BBC8B3A6607621A7D43F351141`.
- Exact v3 is the only permitted parent for the next isolated candidate.  Do
  not stack stage-up or the previously submitted turn-plan overlay.

## Direct failure facts

### Alakazam mirror, episode 86655180

- The game was tied at four Prizes each after our second Alakazam attack.
- Our list has 3 Alakazam / 3 Rare Candy / 3 Dunsparce / 2 Dudunsparce; the
  opponent had 4/4/4/4.
- After the second Alakazam was Knocked Out, our newly promoted Abra could only
  become Kadabra that turn.  We then missed three consecutive attacking turns
  and gave up four consecutive one-Prize Pokémon.
- On the recovery turn, Fez drew Poffin; the agent used Poffin before Sacred
  Ash, so the search had no useful Basic target.  Sacred Ash then returned five
  evolution-line cards, but Poffin was already spent.  Two legal Dudunsparce
  abilities were not converted into Bench space/search before turn end.
- The opponent's earlier Enhanced Hammer removed Telepath Energy from the
  prepared backup Abra.  We later held two Hammers while the opponent's active
  attacker used Telepath Energy, but did not disrupt that public attack route.
- These facts diagnose attacker continuity, recovery ordering and core density;
  they do not establish a causal winner from one replay.

### Mega Froslass/Starmie, episode 86655738

- We attacked on every own turn after the first attack (five attacking turns),
  took two Prizes, and still lost the exchange.
- Mega Froslass ex's Resentful Refrain does 50 damage for each card in our
  hand, directly punishing the same large-hand state that powers Alakazam.
- Stage-up and v3 were identical for all 81 callbacks.  This is a matchup-level
  constraint, not a candidate regression.

### Second Alakazam mirror, episode 86657890

- Both players reached two Prizes remaining, but our board collapsed from
  Alakazam to Kadabra and finally a lone Dudunsparce while the opponent retained
  active and backup Alakazam.
- The opponent again had a fourth Alakazam while our list had three.
- On our turn 13 the public log shows Poké Pad before Sacred Ash; after Ash we
  still produced no replacement Abra and the Kadabra was Knocked Out next turn.
  This is a second independent live mirror exhibiting search-before-recycle and
  failed attacker reconstruction, not a one-off from episode 86655180.
- Stage-up and v3 were identical for all 79 callbacks.

### Great Tusk/Crustle, episode 86656277

- The game reached our turn 45; we took zero Prizes and attacked on only three
  own turns after first attacking on turn 7.
- The opponent used Great Tusk's Land Collapse mill/stall plan.
- Late public state included a trapped active Shaymin/Kadabra and two energized
  bench Alakazam.  Enriching Energy remained in hand from approximately deck
  eight through terminal deck exhaustion rather than becoming draw four plus a
  retreat/promotion/attack conversion.
- Stage-up and v3 were identical for all 76 callbacks.

### Latest two losses, episodes 86659510 and 86660075

- Episode 86659510 was a loss to a complete Mega Lucario list.  A newly played
  Fezandipiti ex was unnecessary for the already available one-Prize attack
  route, then became the opponent's exact final two-Prize gust-and-KO target.
  Ash/Poffin ordering was not causal in this game.  Exact v3 and stage-up were
  identical for all 69 target callbacks.
- Episode 86660075 was a loss to a complete Mega Kangaskhan ex / Crustle list.
  The target used Powerful Hand five times and took four Prizes; after the
  opponent rebuilt a Mist-Energy wall, the last three attacks placed zero
  counters and the target ultimately decked out.  Recycle/refill was unavailable
  and correctly should not fire.  Exact v3 and stage-up were identical for all
  81 target callbacks.
- These two losses make the submitted score clearly weak, but neither by
  itself changes the repeated mirror-specific evidence for recycle-before-
  refill.  Their exact tactical diagnoses remain qualitative-review inputs.

## Deck-theory context (not causal proof)

Current list includes 1 Fezandipiti ex, 1 Genesect, 1 Psyduck, 1 Shaymin, 3
Lucky Helmet and 4 Battle Cage, while using only 3 Alakazam, 3 Rare Candy, 3
Dunsparce, 2 Dudunsparce, 1 Night Stretcher and 2 Basic Psychic Energy.

Two complete historical Alakazam agents in the anti-overfitting population
independently share a core-dense shell: 4/4/4 Abra-Kadabra-Alakazam, 4 Rare
Candy, 4 Dunsparce, 3 Dudunsparce, 4 Hammer, 3 Night Stretcher, 3 Basic Psychic,
3 Boss, 1 Lana's Aid and 1 Battle Cage, with no Fez/Genesect/Psyduck/Shaymin or
Lucky Helmet.  The live mirror opponent independently used 4 Alakazam, 4 Rare
Candy, 4 Dunsparce and 4 Dudunsparce.  Coincidence across these sources supports
core-density as deck theory, but does not authorize copying or claim causality.

## Candidate families for one isolated selection

1. **Core-density restoration (deck-only):** keep exact v3 policy and replace
   low-frequency tech/Tool/Stadium slots with a thicker attacker, draw-engine,
   energy and recovery core.  The chosen 60 must be derived explicitly from
   roles and verified independently; it may coincide with a historical list
   only if the fixed evaluation selects it.
2. **Attack-continuity recovery transaction (policy-only):** when no current or
   certified next attacker exists, order `Fez if live -> Sacred Ash -> Run Away
   Draw to open capacity -> non-empty Poffin for Abra -> reserve Psychic attach`,
   and permit Boss only for immediate Prize conversion or a verified attack
   denial.  Revalidate serials, deck targets, Bench capacity and Prize clock at
   every callback; fail closed to v3.
3. **Certified Enriching escape/attack transaction (policy-only):** under a
   visible mill clock with a trapped non-attacker and a ready bench Alakazam,
   reserve and execute `Enriching attach -> draw four -> pay retreat -> promote
   ready Alakazam -> Powerful Hand/KO`, recomputing legality and terminal clock
   after each callback.  Fail closed if any certificate disappears.

The strategy judge must choose exactly one family and one precise hypothesis.
Local testing is a safety and relative-direction gate, not a demand for perfect
certainty.  Under the user's latest instruction, a safe deterministic candidate
with a clear mechanism may be submitted as an exploratory live test even when
the fixed schedule is parity, but never if illegal, invalid, known-broken,
unpackaged, or materially destructive to adjacent matchups.
