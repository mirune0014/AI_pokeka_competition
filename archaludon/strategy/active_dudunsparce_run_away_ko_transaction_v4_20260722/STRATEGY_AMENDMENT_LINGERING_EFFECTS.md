# V4 controlling amendment: non-board lingering effects

This amendment is controlling after `STRATEGY_AMENDMENT_FLYGON.md`. It closes
the remaining public but non-board effects that can invalidate the frozen
Run Away, promotion, attack, KO, and Prize continuation.

## Root-verified engine facts

1. Iron Defender `1140` writes `players[target].nextTurn.metalDamageChange=-30`.
   The value is applied to attack damage against Metal Pokemon on the next
   turn, but it is not serialized in `ToJson.h`. It can make Kadabra's exact
   30-damage Super Psy Bolt fail to KO a Metal target. Powerful Hand places
   damage counters and is not changed by this flag.
2. Walrein `943` / Frigid Fangs `1353` writes the player-wide
   `cannotAttackLessEqualEnergy2` flag for the next turn. The flag includes
   newly promoted Pokemon and is not serialized in `ToJson.h`; therefore it
   can stop both frozen attackers, which carry exactly one Energy.
3. Slowking `163` / Seek Inspiration `213` can copy any attack of the
   non-Rule-Box Pokemon it discards from the top of its deck. Scanning only
   Slowking's printed attacks therefore cannot certify the copied effect. A
   copied Walrein remains publicly visible in the opponent discard. A visible
   Slowking can also copy effects such as Dig that protect that Slowking from
   both damage and effects of attacks.
4. Acerola's Mischief `1228` is the only other legal Trainer in the audited
   pool that writes a relevant next-turn protection. It protects only against
   Pokemon ex. Kadabra `742` and Alakazam `743` are exact non-ex attackers, so
   it is inert for this transaction.

The verified engine sources are `CardImpl.h` SHA-256
`286A51820D36F9B60B5B13C58BC2EDFF352EB4050581DDADF1960F13FD6F21A9`,
`EffectInstant.h` SHA-256
`31DA884F26F9D7820D37770DFAA9A54229CD15D1185B41E20D718437FED3F217`,
`PlayerState.h` SHA-256
`269E7C4A2C1522245FC2DDC1E89CF83412D1B00F1DEED4B673F3275906A412A1`,
`SetProperty.h` SHA-256
`A563762C4A8F6C1F9C77048B89F770CD2E7A5D4801CD29256196DDA9E40FCB81`,
and `ToJson.h` SHA-256
`84EE63939863493520EBE29E8CA717217EBF90191829EA80D1349942AA867602`.

## Additional exact start gates

All earlier v4 gates remain. Before starting the transaction, also require:

1. No opponent Active or Benched Pokemon has card ID `163` (Slowking).
   Rejecting every visible Slowking is deliberate and fail-closed; do not try
   to infer which top-deck attack it used.
2. The exact public opponent discard contains no card ID `943` (Walrein).
   A visible Walrein is already rejected by the printed lingering-attack scan.
   The discard guard covers Seek Inspiration's public copied source and a
   Walrein that leaves play at Pokemon Checkup after using Frigid Fangs.
3. If the frozen attack is Super Psy Bolt `1071`, the exact target Pokemon
   metadata energy type must not be Metal. Missing or inconsistent type
   metadata rejects. This type-wide exclusion is intentionally stronger than
   trying to infer whether Iron Defender was played.

Do not inspect replay identity, opponent identity, deck labels, hidden cards,
or reconstruct prior turns. These gates use only the exact current public
board and public discard.

## Required controls

The focused matrix must prove, in both semantic seats where applicable:

- visible Slowking `163` delegates the exact parent END with no latch;
- opponent public discard containing Walrein `943` delegates the exact parent
  END with no latch for a one-Energy ready attacker;
- a Metal one-prize target on the Super Psy Bolt route delegates the exact
  parent END with no latch;
- a Metal one-prize target on an otherwise certified Powerful Hand route is
  not rejected solely by the Iron Defender guard, because damage counters are
  not attack damage;
- all three frozen natural positives remain first-change-equivalent and reach
  their exact immediate KO and parent-owned Prize continuation.

Any unclassified player-wide next-turn combat flag or copied-attack route found
after this amendment is a structural blocker. Do not weaken these exclusions
to make a natural-start count or local result pass.
