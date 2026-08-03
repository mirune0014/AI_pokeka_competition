# Rule 3 v3 ranking clarification

Date: 2026-08-03 JST

This amendment resolves one internal ordering contradiction in the supplied
GPT Pro consultation.  Section 5.2 places manual-attachment preservation
before discard class, while section 6.5 and the final `select_best_plan`
pseudocode place non-recoverable card loss before manual-attachment use.

The controlling deterministic order is:

```text
1. dominance certificate:
   WIN_NOW -> PRIZE_GAIN_NOW -> ATTACK_COMPLETION
   -> SAME_ATTACK_PLUS_CONTINUITY
2. ascending sorted discard cost-class tuple
3. no manual attachment before a plan that consumes the manual attachment
4. source Ultra Ball physical serial
5. cost card IDs and physical serials
6. Alloy and manual Metal physical serials
7. route kind only as the final deterministic tie-break
```

Rationale: discard cost class measures an irreversible resource loss, whereas
manual-attachment use is a same-turn opportunity cost.  Rule 3 must not throw
away a less replaceable utility or protected role merely to preserve the
manual attachment.  Within equal discard-loss classes, preserving the manual
attachment remains preferred so Silver may still use it in the productive
prefix.

This clarification does not alter route eligibility, reservations, the exact
Energy equation, certificate semantics, owner priority, or any other rule.
