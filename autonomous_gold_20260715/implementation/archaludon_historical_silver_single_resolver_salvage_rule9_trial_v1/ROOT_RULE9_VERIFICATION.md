# Root verification: Rule 9

Decision before fixed160: **PASS TO FROZEN FIXED160**.

This is permission to execute the required immutable schedule, not acceptance.

## Frozen identity

- Rule 5 parent `main.py`: `D966E455E5110F9D5616195AEAAC8663E6A92F310DAFC4B7F79E4D37149A9C62`.
- Rule 9 candidate `main.py`: `FC2ACC8F1AA08AC32D85B20001E420D9D036853B117FF11539D985D99B7395D0`.
- Deck: `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`.
- Strategy: `E34153B3B3886BCC074EA597A8741A6A100C9E18E59780B60797AA8820BE11FD`.

## Independent source review

Only `main.py` differs from Rule 5. The diff adds exact Gear/Explorer metadata,
Rule 9 owner telemetry, one Gear admission certificate, and the bounded
Gear->Boss->target->attack transaction. It does not alter the
Historical-Silver scorer, deck, existing Rules 1/4/5, or public interface.
Rules 7 and 8 are absent.

Rule 9 never turns a non-Gear parent action into Gear. Its entry action is the
byte-identical Rule 5 Gear action and only arms the existing sole owner when a
unique same-attack terminal Bench target is already public. Reveal handling
chooses the lowest-serial Boss or legal `[]`; Explorer and Lillie are not
selected. Boss acquisition is followed only by the bound Boss, target, and
re-proven terminal attack. Every uncertainty or owner/ledger drift clears to
the callback's Rule 5 action.

Resolver order remains owner continuation, setup, Rule 5 current win, Rule 4,
Rule 5 Boss, Rule 9 Gear admission, Rule 5 fallback. The final agent calls the
parent exactly once.

## Root-executed checks

- Focused and inherited suite: 35/35 passed.
- Compile/import/layout verifier: passed.
- Top-level/final `agent`: one; `_resolve`: one; owner variable: one; static
  parent call in `agent`: one.
- Deck: 60 cards; ACE SPEC: one; cache paths: zero.
- Full two-seat shadow rerun: 46 current plus 207 historical paths, 252
  readable replays, 30,977 callbacks, zero invalid actions, exceptions,
  starts, Boss hits, misses, Boss plays, targets, terminal attack emissions,
  confirmations, irreversible aborts, or action differences.
- The known source replay `89287701` remains malformed at its existing JSON
  truncation and is not interpreted.
- Both-seat checked-engine smoke terminated below 1,000 steps with zero action
  errors.

## Fixed160 gate

Run exactly Rule 5 versus Rule 9 on the frozen 160 keys. A natural start is not
enough: at least one complete non-fixture Gear->Boss->target->same-attack
transaction is required. Inspect every first difference, especially any
unsupported reveal forced to `[]`. Any fault, unclassified/harmful difference,
zero start, or zero natural Boss-hit completion prevents integration. Do not
widen the boundary.
