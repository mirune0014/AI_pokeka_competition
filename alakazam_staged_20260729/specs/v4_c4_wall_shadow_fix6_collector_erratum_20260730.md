# C4 wall-shadow FIX6 collector erratum

Date: 2026-07-30

This erratum changes only the classification of complete fail-closed
`NO_LIVE_PROTECTED_LINE` callback records. It does not change the C4 policy,
the raw games, the immutable schedule, the C5 reach thresholds, or any action.

## Preserved evidence

- C4 candidate closure:
  `FA46897E4762CB1B55C9DED36EC3A06CA9CF4F9FE7C4233BE8414CC25D86DF4E`
- Frozen collector:
  `verification/c4_sidecar_collector.py`
- Frozen collector SHA-256:
  `770EA508AF3CCFEC549C1C543EB8D04041553236B11C6D5C3CBBA8FF30344BEE`
- Frozen collector full-union attempt:
  `metrics/formal_v4_c4_wall_shadow_fix6_union_audit_attempt1`
- Frozen input-manifest SHA-256:
  `AE798D009472D123324E49C3993DF72227DB2134E62F20BE045AE9464F7FD8E9`

The frozen collector is retained unchanged. Its attempt remains the formal
record of the schema mismatch.

## Cause

The analyzer deliberately emits a complete negative record when it recognizes
a C4 prompt but cannot certify one unique live Alakazam line. Such records
have `protected_line=null`, choose the exact parent fallback, apply no
candidate action, and are not wall evidence.

The frozen collector nevertheless required `protected_line` to be a dictionary
for every recognized prompt. It also rejected a diagnostic duplication where
`NO_LIVE_PROTECTED_LINE` appears exactly twice in a rejected reusable or
sacrifice row. The full 900-game frozen run therefore reported a schema
failure even though action identity, callback pairing, closures, raw binding,
and metric execution remained intact.

## Versioned correction

- Amended collector:
  `verification/c4_sidecar_collector_v2.py`
- Amended collector SHA-256:
  `3CF552929ACE62CA87455795C6C7D912DD7E5B276A50A0B597C4AD1996EC4F81`
- Regression test:
  `test_v4_c4_sidecar_collector_v2.py`
- Regression-test SHA-256:
  `DBB9C8B9927B34814C930AF6C76324F99B80715EA5F6229A633D23527983F58A`

The amended collector permits the negative-only branch only when all of the
following hold:

1. `protected_line=null`, importance is unknown, and both distance fields are
   null.
2. `NO_LIVE_PROTECTED_LINE` is present in the trace rejection and unsupported
   diagnostics.
3. Pair material and expose projection both bind the protected line to null.
4. No candidate row is `STRICT`.
5. Reusable and sacrifice rows are `REJECTED` or `UNAVAILABLE`.
6. A `PRESERVE_CHANCE` row, if present, is Run Away only and passes the normal
   row schema.
7. Parent, proposed, and applied actions agree; arbitration chooses the exact
   parent fallback; wall projection has `chosen=null`; outcome is
   counterfactual.
8. The only tolerated duplicate is exactly two
   `NO_LIVE_PROTECTED_LINE` entries in a rejected reusable or sacrifice row.

The collector validates all normal required fields, closures, raw-state
binding, fingerprints, callback order, action identity, metric exceptions,
and candidate-application faults before exclusion. It does not edit the raw
JSONL. Qualifying records are excluded from pair classes, reach, agreements,
and outcomes and are retained in a negative-only collision map.

Any collision, missing field, other duplicate, wall `PRESERVE_CHANCE` row,
`STRICT` row, projection fault, raw-binding fault, action fault, or closure
fault remains fatal.

## Monotonicity and C5

This correction can only remove records from evidence. In particular, Run Away
`PRESERVE_CHANCE` rows attached to a null protected line are not promoted into
reach. C5 thresholds and the rule that `PRESERVE_CHANCE` never changes action
remain unchanged.

The amended collector must run once over exactly these complete roots:

1. `formal_v4_c4_wall_shadow_fix6_trace_a`
2. `formal_v4_c4_wall_shadow_fix6_trace_b_rocket_retry2`
3. `formal_v4_c4_wall_shadow_fix6_trace_b_kangaskhan_retry2`
4. `formal_v4_c4_wall_shadow_fix6_trace_c`
5. `formal_v4_c4_wall_shadow_fix6_megalucario_reach1`

The incomplete original metric-B root is not an input.

An A+C-only regression over the 500 games that exposed the mismatch produced
exactly 705 exclusions and 732 duplicate diagnostics, with zero residual
schema faults, 166 valid chance states, zero strict states, integrity `PASS`,
and overall `INSUFFICIENT_EVIDENCE`. Its summary SHA-256 is
`26D54A25F06E04BEC3FFAED178313A1666BC2A0654F3880A5959663F155871FF`.

## Completed amended union

Output:
`metrics/formal_v4_c4_wall_shadow_fix6_union_audit_attempt2`

The amended collector processed exactly 900 sidecars and 55,514 paired
callbacks from the unchanged input-manifest SHA-256
`AE798D009472D123324E49C3993DF72227DB2134E62F20BE045AE9464F7FD8E9`.

Results:

- negative-only exclusions: `983`;
- duplicate diagnostic rows retained in raw evidence: `1014`;
- negative-only internal or valid-pair collisions: `0`;
- sparse, raw-binding, closure, action-identity, metric-exception, and
  candidate-applied faults: `0`;
- valid `STRICT` unique states: `0`;
- valid `PRESERVE_CHANCE` unique states: `246`;
- natural parent agreements: `0`;
- trace-complete observed wall outcomes: `0`;
- integrity gate: `PASS`;
- reach and overall gate: `INSUFFICIENT_EVIDENCE`.

Output hashes:

| File | SHA-256 |
|---|---|
| `c4_callback_audit_rows.jsonl` | `E6A786676650926AB91E9AB76A4CEECC5E91E3BDCD4C298AD4CD6F67CD3713B8` |
| `c4_mechanical_summary.json` | `584CE6F0CD0682C12374811EE668892C7E2C42EA23B5817F534315FBCB378EBB` |
| `root_independent_metric_audit.json` | `BF4EAB586378E796E5C637254213E59992AA1F93588D98B5F4B330046790C8B2` |
| `tools/audit_v4_c4_metric_root.py` | `5C3E7E1AF1872E6A7FB7A6EC97B85105ADA25E91BFCC12D53642ABC15430F79B` |

The root audit independently reconstructed all 90 blocks, 900 games,
55,514 callback pairs, 983 exclusions, 246 valid chance states, and zero
strict states. Its status is `PASS` with zero errors.

Therefore C5 is a documented no-op. The generalized wall rule remains
shadow-only; no `PRESERVE_CHANCE` record changes an action.
