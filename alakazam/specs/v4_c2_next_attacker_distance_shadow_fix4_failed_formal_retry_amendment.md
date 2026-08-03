# v4 C2 next-attacker-distance shadow fix4 formal failure and retry amendment

Date: 2026-07-30

This amendment records the first formal C2 execution as a rejected
implementation attempt. It does not change the intended distance semantics in
the frozen C2 specification.

## Governing specifications

- `v4_c2_next_attacker_distance_shadow_fix4_immutable_spec.md`
- `v4_c2_next_attacker_distance_shadow_fix4_formal_execution_spec.md`
- `v4_c2_next_attacker_distance_shadow_fix4_sharded_execution_amendment.md`
- `v4_c2_c5_strategy_judge_binding_amendment.md`

Failed candidate:

```text
alakazam_staged_20260729/versions/
  alakazam_newdeck_v4_next_attacker_distance_shadow_fix4
```

Candidate closure:

```text
802A1DD3344287EFE5EAC16F1B07DF79FF2727CF6767359EB3747470D09D4C38
```

## Preserved failed evidence

Shard A completed all 30 blocks and 300 games. Shard B completed all 20
blocks and 200 games. Root independently confirmed:

- exactly 500 unique game keys;
- no intersection between the two shards;
- exact agreement with the frozen opponent, seat, seed-base, game, and seed
  schedule;
- zero nonzero block exits, timeouts, action errors, max-step hits, and
  unstarted games;
- zero action-identity failures, wrapper exceptions, and structural-invalid
  callbacks.

The attempt is nevertheless rejected because a shadow metric must have zero
normal exceptions and a stable decision fingerprint.

### Shard A

```text
metric_exception_count = 197
fingerprint_trace_conflict_count = 1
action_identity_failure_count = 0
```

Evidence:

```text
block_ledger.jsonl
88861F8C380C9110897919A89A7C09A6A48A89E8F67248145AF528BDB3287D27

c2_callback_audit_rows.jsonl
F629B2CBA1812C22FDC3D4C2F0B1B3EE25BD6C1C41FC1E2C94468FABB9BA9205

c2_mechanical_summary.json
4A528D962E0560B9BC1CA7B4D55A5082960790F84E55AEE43F182B738C220362
```

### Shard B

```text
metric_exception_count = 123
fingerprint_trace_conflict_count = 0
action_identity_failure_count = 0
```

Evidence:

```text
block_ledger.jsonl
D16B5CABF70C6805F21CF072E225661095E92790A41AF8CF0F605C66B599E698

c2_shadow_rows.jsonl
B8CE89CDD54DE8D07CB71201103165E348A3D7CE15557E100032F6367B411066

c2_shadow_summary.json
D868B298A4F5522E3C4739B1B73661AC59B115EC1384BE0B4121707D8C66D606
```

Shard C was not started after the mandatory metric gate had already failed.
The earlier partial serial attempt and these two failed shards remain
provenance only. No row from them may be used as formal C2 reachability
evidence.

## Failure 1: face-down setup Active

All 320 metric exceptions are `AttributeError`. Root joined each failing
`CALL_END` to its preceding `CALL_START` and confirmed that every occurrence
is in setup context `2` or `38`, before a public own Active identity exists.

The parsed `PlayerState.active` may contain `None` for a face-down Pokémon.
The implementation validates the zone, then iterates the zone and reads
`pokemon.id` without first handling this permitted `None` value. A face-down
identity is unavailable public information and must not be inferred.

Required correction:

1. Detect any face-down or otherwise non-object Active/Bench entry before
   enumerating attack lines.
2. Return a normal fail-closed `UNKNOWN` trace with an explicit reason such as
   `FACE_DOWN_IN_PLAY_IDENTITY_UNKNOWN`.
3. Do not report a metric exception.
4. Return the exact parent action object unchanged.

Required fixtures:

- empty pre-setup Active;
- `active=[None]` while choosing additional Basics;
- `active=[None]` in the numbered setup selection;
- duplicate callback and reordered setup options;
- all must produce stable `UNKNOWN`, zero exception, and exact action
  identity.

## Failure 2: fingerprint omitted policy transaction state

The single conflicting fingerprint is:

```text
75F113FC56DF7F101F296913D90C90568C9FB8AE26338B84CBC9482FBFF9B86A
```

The callback-visible public board was the same in the two observations, but
one delegate had an active parent transaction. The analyzer therefore added
`PARENT_TRANSACTION_IN_PROGRESS` and correctly changed its route result to
`UNKNOWN`. The fingerprint covered the public board but omitted the two
transaction-active flags that directly affect the metric.

Required correction:

1. Define the C2 decision fingerprint over the public observation plus only
   the normalized parent-transaction flags consumed by the analyzer:
   `integrated_transaction_active` and `v1_transaction_active`.
2. Do not add opponent name, seat, seed, game, callback ordinal, hidden
   information, or mutable object identity.
3. Equivalent absent and explicit-false flags must canonicalize identically.
4. A true flag must produce a different decision fingerprint from both false
   flags.

Required fixtures:

- identical public observation with both flags false or absent: same
  fingerprint and same trace;
- identical public observation with either flag true: distinct fingerprint,
  `PARENT_TRANSACTION_IN_PROGRESS`, and `UNKNOWN`;
- option reordering remains fingerprint-stable.

## Retry contract

The correction must be implemented in a new immutable candidate directory.
The failed candidate must not be edited in place.

Before another formal execution:

- focused tests, corrected-candidate full regression, failed-parent full
  regression, and changed-source compilation must pass;
- a replay of representative failed callbacks must show zero metric
  exceptions;
- the 700-callback identity probe must still show exact action identity;
- the collector must expect the corrected trace rule version and closure.

The corrected candidate must then be executed into fresh shard directories
over the complete original 700-game schedule. No failed-attempt row may be
copied, repaired, or counted.
