# v4 C3 fix5 collector origin-state execution amendment

Date: 2026-07-30

## Scope

This amendment changes only the candidate-local, post-execution sidecar
collector and its tests. It does not change the production policy, deck,
adapters, engine, opponents, seeds, seats, game counts, or output paths in the
formal execution specification.

Formal execution specification before this amendment:

```text
v4_c3_public_survival_bench0_fix5_formal_execution_spec.md
SHA-256 B0E7ED5FE726BFB55E20A535BCD0D58E7BCA550D8C5F7A9D56635015DACCFA4A
```

Production closure remains:

```text
5C1BAD6C505358BFF7550A89F167D3DE19B0D2540C6C54ED85324F961A37E134
```

Raw paired and metric executions started under the formal specification remain
eligible because neither runner imports or executes the post-hoc collector.

## Corrected collector

```text
verification/c3_sidecar_collector.py
SHA-256 45F611F121D757AF18C5D501892E743BBF3FFF7ABBC4C362C087DCC885A9249D

test_v4_c3_sidecar_collector.py
SHA-256 6F23C31FCBCD414D3FC1A459457AA4E2F3E42E26EDB208AB962DFA0BF3102E46

implementation receipt
SHA-256 67FD6D2A35A7B8EB749EEDFFC8D50BB6B00F1B16D39CA4CF75A6F6384346426A
```

## Correction

Reach remains deduplicated by originating decision. Callback-level integrity
still checks every `CALL_END`.

Observation-fingerprint conflict detection now compares only origin-state
callbacks:

```text
PROPOSED
ARMED
DUPLICATE_REBIND
```

A normal `COMPLETED` or `ABORTED` callback is observed after the Basic move or
rollback and may legitimately have a different observation fingerprint. Such
post-action callbacks are excluded from origin-state conflict comparison.

The focused fixture proves both directions:

- one `ARMED` decision plus its post-Basic `COMPLETED` observation is valid;
- two different origin fingerprints for one decision fail integrity.

## Root verification

Using the checked Python environment and engine path:

```text
collector focused: 6 / 6
C3 focused: 54 / 54
candidate full regression: 246 / 246
py_compile: exit 0
```

The collector continues to aggregate no wins, scores, or paired deltas.
