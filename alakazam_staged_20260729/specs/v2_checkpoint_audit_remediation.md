# V2 checkpoint audit remediation

## Status

The checkpoint with policy closure
`9E4E587A05BFE30B97516D7A10362ED6ACA869A11B4E77FB1222C331713A3FB9`
is **NO-GO for Comparison C**.

It passed its unit tests but does not satisfy the immutable
`V2_CERTIFIED_H1_CONTINUITY` contract. This remediation is mandatory when the
v2 change is rebased onto the accepted v1 compliance candidate.

Audited files:

- contract:
  `3696B8FC36916977328D8C9C13E7823DEE7EAA14D2E715BC3B2BBFEA5BA9E93A`;
- planner:
  `B3E8941F384B4716473A034585A21FAFBF40D7E6A90B66820949CF6F5B7E40B7`;
- model:
  `6759806E020943E231B2E782AACDD8382851C3E5EE203A3A176A45EF321A3BFD`;
- tests:
  `582E7C9E0D91DFD4F77F74125A433D4D65E27FBBF4A6F4F545557C57F70067E5`.

## Hard contradictions

1. POST_KO recovery can reuse the frozen H0 Alakazam serial. The checkpoint
   test treats discarded H0 serial `700` as a valid Stretcher recovery target.
   H0 top, stack, and Energy must never be counted as H1 or recovery resources.
2. POST_KO calls the generic prep search and can irreversibly bench a new Abra
   or normally evolve Abra to Kadabra without first proving a same-turn final
   Powerful Hand attack.
3. The Rare Candy path binds the later Alakazam Ability prompt to the Candy
   row instead of the evolved Alakazam row.
4. Several aborts after an irreversible v2 action leave
   `irreversible_abort_fault` false.

## Mandatory implementation corrections

1. Store the frozen H0 top, all evolution-stack serials, and all attached
   Energy serials in one `excluded_serials` set. Apply it to every H1
   certificate, hand reservation, discard recovery, Hilda result, promotion,
   retreat, and final attacker.
2. Before the first irreversible POST_KO action, prove one complete and unique
   route through the final Powerful Hand action. Remove new-Abra placement and
   normal Abra-to-Kadabra evolution from POST_KO candidates.
3. Preserve all recovered, searched, and reserved physical serials
   cumulatively through Stretcher, Lana, and Hilda children. Do not replace the
   reservation with only the latest candidate. Compare complete routes by
   total self-action count and choose the unique shortest route.
4. Bind the Rare Candy Ability child to the evolved Alakazam row. Add a full
   Candy-to-target-Abra-to-Alakazam-to-Ability-to-Energy-if-needed-to-Powerful
   Hand fixture.
5. On Telepath, Candy, recovery, retreat, payment, and promotion children,
   verify context, select type, effect, contextCard, area, player, min/max,
   stable option key, and physical serial. Reapply the deck clock after a
   Telepath search.
6. Verify the exact runtime deck totals for Abra, Kadabra, Alakazam, Rare
   Candy, Basic Psychic, and Telepath Psychic. Test `deck_lb=0` and `deck_lb=1`
   separately for Hilda's Alakazam and both eligible Psychic Energy groups.
7. Every abort after any irreversible v2 action must set
   `irreversible_abort_fault=True`. No such abort may be counted as a legal
   fallback for promotion.
8. Preserve the complete Boss terminal and Xerosic play/child/verify prefixes.
   Test real v1 action, trace, transaction, duplicate cache, and parent mutable
   state equality on v2 nonfire.
9. Cover all four unsafe-Active-743 certificate shapes end to end:
   intercept unsafe active evolution, perform the certified prep, return to
   the same frozen H0 evolution/attack route, and use Powerful Hand.
10. Add full prompt-chain fixtures for ready Alakazam, Kadabra evolution,
    Candy evolution, Basic/Telepath Energy, Stretcher, Lana, Hilda, retreat,
    payment, and promotion, plus structurally impossible negative states.

## Priority correction

An in-progress v2 transaction must be handled before rechecking terminal Boss
or Xerosic ownership. The original contract's owner order remains
authoritative.

## Required pre-evaluation result

Comparison C remains blocked until all of the following hold:

- the rebased v1 compliance tests pass unchanged;
- all v2 full-chain fixtures pass;
- frozen H0 serial reuse tests are negative;
- all irreversible-abort fault tests pass;
- nonfire state equality is verified with the real v1 compliance delegate;
- the rebased v2 deck is byte-identical to the accepted v1 compliance deck;
- a fresh policy closure and changed-file hashes are recorded.
