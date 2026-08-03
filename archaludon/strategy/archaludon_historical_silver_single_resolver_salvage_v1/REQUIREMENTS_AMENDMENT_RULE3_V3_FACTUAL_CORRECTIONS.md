# Rule 3 v3 factual corrections

Status: CONTROLLING FACTUAL CORRECTION
Date: 2026-08-03 JST

This file corrects repository facts in
`REQUIREMENTS_AMENDMENT_RULE3_CERTIFIED_LATE_BOUNDARY_V3.md` and the attached
GPT Pro consultation. It does not change the selected strategy.

## Deck count correction

The frozen `deck.csv` contains **12**, not 11, Basic Metal Energy cards with
card ID `8`.

Root recount:

```text
169 x4
190 x4
666 x4
840 x2
1121 x4
1244 x3
8 x12
```

All guaranteed-deck lower bounds, focused fixtures, and telemetry must use the
actual frozen deck count of 12. Prefer one audited deck-count registry rather
than repeated literals.

## Existing-code boundary corrections

1. Existing Rule 1 is setup-context-only. It is not a normal-MAIN board-out
   rule and must remain unchanged.
2. The current owner-free MAIN resolver order is exact direct terminal, Rule 4
   materialization, Rule 5 Boss, Rule 3, then Silver.
3. The current source has no Rule3-to-Rule5 atomic owner handoff during a
   productive prefix. If v3 implements this required behavior, it must do so
   inside the new Rule 3 transaction without changing owner-free Rule 5.
4. Current `_r3_abort` clears the Rule 3 owner even after an irreversible
   action. That behavior does not satisfy v3. V3 requires a latched fault owner,
   containment action, and a run-level failure signal.
5. Current combat helpers do not provide a complete Turbo Flare certificate.
   V3 must use an exact Turbo Flare metadata fingerprint and same-attack
   identity rather than pretending the existing registry already covers it.
6. The existing state machine assumes that the searched Archaludon ex becomes
   the evolution card. `ACTIVE_EX_FUEL_ROUTE` needs a distinct binding for the
   pre-existing hand Archaludon ex and an optional, core-independent search
   result.

