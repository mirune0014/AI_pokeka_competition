# Archaludon Tempo Commitment V1 rejection

## Decision

`REJECT_POLICY_HYPOTHESIS_BROAD_TEMPO`

## Evidence

- Fixed160: parent `100/160` -> candidate `88/160` (2 gains, 14 regressions).
- Fixed760: parent `501/760` -> candidate `466/760` (18 gains, 53 regressions, net `-35`).
- Seat 0 net: `-18`; seat 1 net: `-17`.
- Runtime faults: `0`.
- Invalid actions: `0`.
- Max-step hits: `0`.

## Interpretation

The implementation behaved mechanically as designed, but the broad policy that a
legal positive-damage attack should generally preempt search, development,
recovery, hand refresh, and non-terminal Boss actions is rejected. The result is
diagnostic evidence only; it does not justify an opponent-specific Tempo guard.

## Status

- Not accepted.
- Not submitted.
- Not a development parent.
- Candidate source remains unchanged and is preserved as a diagnostic archive.
