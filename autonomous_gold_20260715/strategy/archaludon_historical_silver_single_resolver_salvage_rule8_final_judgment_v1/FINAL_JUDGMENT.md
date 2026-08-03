# Rule 8 Final Judgment

Decision: **DEFER-DORMANT**.

## Evidence

- Candidate `main.py`: `B0BD42D71617EEA041AFCF54F84B9C92FD894A2A3A6BD1CCAD95645CD1952507`.
- Deck: `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`.
- Focused/inherited checks: 32/32 passed.
- Replay shadow: 30,977 callbacks, zero starts, zero differences.
- Frozen fixed160: Rule 5 `100/160`, Rule 8 `100/160`, G/R/T
  `0/0/160`, exact 160-key schedule, and byte-identical candidate/baseline
  traces in all 160 games.
- Invalid actions, exceptions, action errors, max-step hits, schedule faults,
  and duplicate mismatches: zero.
- Independent numerical audit:
  `71A6D30E58BE79A244F6700C6DCCC38D788FADCA2C079EB2E9DDE59AD43C875F`.
- Root recomputation:
  `0364F3767E91098CA40DDA15407C02BAB57B5A1819864E31F3C9B179532F24F5`.

The runner did not persist a dedicated internal Rule 8 counter. However, the
frozen source can start Rule 8 only by changing the emitted same-Active attack
from `223` to `224`. Byte-identical traces therefore prove zero observable
fixed160 starts. Together with shadow, the natural-start count is zero.

## Controlling instruction

- Keep the implementation and evidence as a dormant record.
- Do not widen, repair, integrate, promote, or run fixed760 for Rule 8.
- Rule 5 `D966E455E5110F9D5616195AEAAC8663E6A92F310DAFC4B7F79E4D37149A9C62`
  remains the sole parent for Rule 9.
