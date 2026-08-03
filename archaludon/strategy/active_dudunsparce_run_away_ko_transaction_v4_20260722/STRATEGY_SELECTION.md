# Active Dudunsparce Run Away KO transaction v4

## Decision

Implement one fail-closed hypothesis directly over the current live formal
parent `alakazam_psychic_readiness_parent_continuation_v3` (policy SHA
`6AEF53400B9413037FB79DDCB9BE752A632FF4E0803B1D00EE84F188C44EDB6C`):
retain the v1 Run Away-to-immediate-KO transaction only inside an affirmative
public **no-effect envelope**. V1, v2, and v3 are rejected implementation
ancestors, never formal parents.

## Why v4 is needed

- V1 admitted Survival Brace.
- V2 admitted benched Spiritomb's Spiteful Swirl.
- V3 admitted Lucky Helmet and other on-damage/on-KO effects.

These are structural continuation failures. The fix is not another list of
dangerous words; every admitted public effect must be proven inert during the
frozen Run Away, promotion, attack, KO resolution, and Prize handoff.

## Exact admissible envelope

All existing v3 transaction, duplicate, rollback, target-fingerprint, attack,
KO, and Prize gates remain. Add all of the following:

1. The opponent Active has no Tool.
2. Every opponent visible Pokemon (Active and Bench) has either no printed
   skills or only skills whose normalized text contains exact
   `once during your turn`. These are owner-turn actions and cannot react during
   our attack. Any other printed skill rejects the start.
3. Every opponent visible Pokemon has no Tool. Its attached Energy must be an
   inert Basic Energy with no skills, or exact Telepath Psychic Energy `19` with
   its frozen provide-Psychic/on-attach-search text. Any other attachment
   rejects the start.
4. The Stadium is empty or exact Battle Cage `1264` with its frozen Benched
   counter-prevention text. Any other Stadium rejects the start.
5. The promoted Kadabra/Alakazam has no Tool. Its Energy is exact Basic Psychic
   Energy `5`, or exact Telepath Psychic Energy `19` with the frozen text above.
   Any other attachment rejects the start.
6. Preserve the existing lingering-opponent-attack and exact damage/KO checks.
   Unknown card metadata, missing rows, extra skills, or text mismatch reject.

The legal-pool audit must show that admitted `once during your turn` skills are
owner-turn actions only. Do not allow replay IDs, opponent identity, deck labels,
history reconstruction, or hidden information.

## Mandatory retained natural starts

- `87411430 / seat 0 / step 53`: target Kadabra `742` with Basic Psychic `5`;
  opponent Bench includes Abra with Telepath Psychic `19`.
- `87411965 / seat 0 / step 39`: target Budew `235`; two Dusclops `132`, two
  Drakloak `120`, and Battle Cage `1264` are public owner-turn/inert effects.
- `87416244 / seat 1 / step 47`: target Kyogre `721` with Basic Water `3`;
  promoted Alakazam uses Telepath Psychic `19`.

## Mandatory negatives

Exact submitted parent must select END and v4 must delegate without latching for:

- Budew plus Survival Brace;
- Budew plus Lucky Helmet;
- target-local reactive damage counter;
- Dark Gastly plus benched Spiritomb;
- at least one printed on-KO Pokemon effect (for example Gengar Infinite
  Shadow);
- at least one reactive Tool/attachment effect other than Lucky Helmet;
- unknown or non-whitelisted special Energy, Tool, Stadium, or skill text.

## Breakage-only release gate

- compile/import; 60 legal cards; one ACE SPEC; sole/last `agent`; zero caches;
- all focused positives and negatives in both semantic seats where applicable;
- exact full transaction for `87416244` in both seats;
- callback-complete current-35 shadow from episode CSV SHA
  `E76F116518BE1259F2F2FCA621F68C8475B0B68597989E59A0CD7173DAAF0382`;
- historical 186 / 11,866 callback shadow;
- deterministic duplicate/latch controls and both-seat engine smoke.

Weak win rate or no new natural exposure is nonblocking. Any invalid action,
unclassified difference, known legal consequence treated as stale, or other
structural continuation failure blocks packaging and submission.
