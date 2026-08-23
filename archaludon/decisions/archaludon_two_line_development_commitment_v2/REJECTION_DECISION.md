# Archaludon Two-Line Development Commitment V2 rejection

## Decision

`REJECT_POLICY_HYPOTHESIS_TWO_LINE_DEVELOPMENT`

## Evidence

- Fixed160 runtime screen: parent `100/160` -> candidate `94/160`.
- Fixed760: parent `501/760` -> candidate `469/760` (19 gains, 51 regressions, net `-32`).
- Fresh640: parent `477/640` -> candidate `452/640` (8 gains, 33 regressions, net `-25`).
- Combined formal comparison (fixed760 + fresh640): parent `978/1400` -> candidate `921/1400`, net `-57` (27 gains, 84 regressions, 1,289 ties).
- Fixed760 seat 0 net: `-16`; seat 1 net: `-16`.
- Runtime faults: `0`.
- Invalid actions: `0`.
- Max-step hits: `0`.

## Interpretation

The candidate behaved mechanically as designed. The broad policy that a
non-terminal turn should generally establish a minimally developed second
Archaludon line before following the accepted parent is rejected. This does not
establish that every Bench, evolution, or Bench-energy action is individually
harmful; those action families require a trace-preserving first-difference
decomposition before any narrower successor experiment.

## Status

- Not accepted.
- Not submitted.
- Not a development parent.
- Candidate source and deck remain unchanged and are preserved as a diagnostic archive.
