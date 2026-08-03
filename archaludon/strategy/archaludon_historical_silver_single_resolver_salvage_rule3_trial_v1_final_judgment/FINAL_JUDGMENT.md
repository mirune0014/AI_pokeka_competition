# Rule 3 final judgment

## Verdict

**REJECT** `SILVER_DECLARED_ULTRA_BALL_TWO_ROUTE_TRANSACTION_V1` under the frozen stage gate. Do not integrate, patch, widen, or run fixed760. Restore the accepted Rule 1 parent.

## Verified facts used

- Frozen Rule 1 parent `main.py`: `153D8461FB66927DB9731CBE614B71FF5398B8EAE8980AE0BB4D46ADD0E8792A`.
- Rule 3 trial `main.py`: `3F05F353B868307E91A38FA62ED460D4BFB9A82B85400E2D98B3DBB5CE67A0FC`; helper: `2015A4E589D2AE428A151AF50520C160CED7E1B1926D5599A2B35EB0CC6CEA61`.
- The root-verified 160 unique schedule keys recompute to Rule 1 `100/160` and Rule 3 `99/160`, with gains/regressions/ties `0/1/159`.
- Primary anchor: Historical-Silver mirror `20/40 -> 20/40`. Adjacent buckets: Arch Peak `20/40 -> 19/40`; Alakazam `29/40 -> 29/40`; Marnie `31/40 -> 31/40`. Seats: seat 0 `47/80 -> 46/80`; seat 1 `53/80 -> 53/80`.
- All 18 commands exited `0`; action errors, start faults, max-step hits, duplicate keys, and duplicate-control mismatches were all `0`.
- There were three action-observable starts, all at seed `271958318`, seat 0, across the three adjacent opponents, and zero completed declared transactions.
- The sole result flip was Arch Peak, seat 0, seed `271958318`: Rule 1 won in 133 steps and Rule 3 lost in 131. The first Rule 3 difference altered the Ultra Ball route, changed the searched option and later deck-dependent Explorer reveal, but did not continue through the declared immediate evolution/Energy/attack transaction.
- The independent numerical audit hash is `AE47A4291228018681C19490AC9CB9F34E14828DADFBE723DC5970650332B3EE` and agrees with the root recomputation.

## Failed gates and reasoning

- Observable activation makes `DEFER-DORMANT` inapplicable.
- `paired gains >= paired regressions` fails mechanically: `0 < 1`.
- Zero clearly harmful first differences fails: the only outcome regression is mechanism-first.
- Declared-complete route behavior fails: `0/3` observable starts completed evolution, Energy preparation, and preserved attack.

Mechanical safety and the three-win seat/opponent floors pass, but they cannot override the failed adoption gates. Rule 3 supplies no demonstrated setup, board-formation, attacker/backup-readiness, Energy/hand/deck-management, attack-continuity, prize-exchange, finishing, or disruption benefit. Its observed mechanism instead perturbs deck order before abandoning the promised transaction, creating downstream resource variance and one adjacent-population loss. The evidence is concentrated in one seed and seat, which limits generalization claims but does not create decision uncertainty because the frozen gate is deterministic and already falsified.

## Exact evidence needed next

None for this Rule 3 trial: the rejection is final under the frozen contract. Preserve it only as a rejected implementation record, return to Rule 1, and proceed to Rule 4 as a separate one-rule experiment. No further Rule 3 diagnostic, fixed760 run, patch, or trigger widening is justified.
