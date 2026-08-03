# v4 C2 FIX4B retry-union Sol-Ultra audit

**Decision: PASS — C2 may be inherited by C3 as the side-effect-free analyzer.**

This is a shadow integrity/reachability audit, not a strength or promotion
comparison. I did not aggregate game results or interpret win rate. No
simulation was run during the audit.

## Frozen binding and inputs

The candidate closure independently recomputes to
`29084BC13CB74236ABE557B57A9E633A8F9E88FA83FF22D131C835293E987157`
over 34 closure members. The frozen v3 parent independently recomputes to
`DC90205DE06AE3E2E41ADC661577096BB02EE5B42AB9F4366FC1A01154745B47`
over 33 members. Every completed callback carries those exact hashes and
`V4_NEXT_ATTACKER_DISTANCE_SHADOW_FIX4B`.

All governing documents matched their frozen hashes, including the retry
execution specification
`19FFB4DC039EF20961A4AA806AB56CFF4C399FEBB80375CCD7EB9E37D24423E1`,
the binding amendment
`C33EBED6B5C945924F0ED4AFAC1C0029C9B129D870EE4FE583D3612948CD70B6`,
the failed-retry amendment
`7BA5A67FDB084F70DF954DF9C0DBDC8467924D7DCCE2B1D1D5112DA9ED7D51D3`,
and the shard-C retry amendment
`65F236319CA755C5D128517CDF07E45DC504537D1F8C602C52F53A81788E9BC5`.

Only these completed outputs entered the union:

| Shard | Approved output | Blocks / games | Rows SHA-256 | Ledger SHA-256 |
|---|---|---:|---|---|
| A | `metrics/formal_v4_c2_next_attacker_distance_shadow_fix4b_retry1_shard_a` | 30 / 300 | `A465F0CD…D9324` | `A441F1FB…C1411` |
| B | `metrics/formal_v4_c2_next_attacker_distance_shadow_fix4b_retry1_shard_b` | 20 / 200 | `92291A08…4522` | `AA4D57AB…A2FD` |
| C | `metrics/formal_v4_c2_next_attacker_distance_shadow_fix4b_retry1_shard_c_retry2` | 20 / 200 | `252AD8DE…78A2` | `5B8EDE9B…1B44` |

The failed serial attempt, failed FIX4 shards, and zero-game original shard-C
command failure were excluded.

## Independent raw recomputation

The union is exactly the immutable schedule:

- 70/70 unique complete block keys and 700/700 unique game keys;
- schedule symmetric difference 0 and duplicate game keys 0;
- cross-shard game intersections A/B, A/C, and B/C all 0;
- 100 games for each of seven opponents and 350 games in each policy seat;
- 140 games per seed base, 50 distinct actual seeds, 14 games per actual seed;
- 700 nonempty sidecars and 700 nonempty battle traces.

Policy mapping was explicit throughout: seat 0 placed the C2 wrapper at
agent A/player 0; seat 1 placed it at agent B/player 1. No seat-result
comparison was made.

The raw callback recomputation found 45,446 `CALL_START` and 45,446
`CALL_END` rows, 45,446 unique callback keys, no duplicates, and no unmatched
row. Every game sidecar alternated consecutive start/end ordinals. Every
selected action also matched the candidate-player action in the corresponding
battle trace.

For all 45,446 completed callbacks:

- `raw_parent_action == applied_action == CALL_END.selected_action`;
- the recorded Python-type, value, element-order, and returned-parent-object
  identity flags all pass;
- exact top-level trace schema, rule, parent closure, and candidate closure
  all match;
- metric exception, wrapper exception, structural invalid, missing/wrong
  trace, and fingerprint-format counts are all zero.

Runner faults are also all zero: nonzero exit, timeout, incomplete block,
unstarted game, action error, max-step hit, invalid result, nonempty stderr,
and ledger/file-hash mismatch.

## Fingerprint and reach evidence

After global deduplication there are **42,315 unique decision fingerprints**;
3,131 repeated decisions were excluded from unique-state coverage. Cross-shard
fingerprint overlaps were A/B 689, A/C 786, and B/C 632, and were deduplicated.

| Route class | Unique fingerprints | Required |
|---|---:|---:|
| `CERTIFIED` | 11,298 | 5 |
| `POSSIBLE` | 22,450 | 5 |
| `IMPOSSIBLE` | 9,308 | 5 |
| `UNKNOWN` | 28,995 | 5 |

These are multi-label counts: one decision fingerprint is counted once in each
route class present among its line/distance rows. They are not intended to sum
to 42,315.

Both seats and all seven opponents are reached. Canonical route/best-route/
unsupported-reason payload conflicts are 0 across the full union. Normalized
transaction-flag conflicts are also 0; the raw suite reached 951 callbacks
with the integrated transaction active and 764 with the v1 transaction
active.

## Collector cross-check versus raw authority

I regenerated every collector row directly from the approved sidecars,
including source path/hash/line, action identity, fingerprint, line,
distance kind, route class, and distance tuple fields. All **238,044** rows
matched the three checked row files exactly; missing, differing, and extra
rows were 0. Every critical field in each collector summary also agreed with
the independent recomputation.

This distinction matters: shard A's collector summary reports `PASS`, while B
and C individually report `INSUFFICIENT_EVIDENCE` because a shard is not the
approved seven-opponent union. The inheritance decision above comes from the
independently recomputed union, not from combining those prose/status labels.

Recomputed manifests:

- sidecar union:
  `09BD69E85DD9F4B06BE811B04DDD4CB444BAEFAAFC17179ABAC6A4678A91FC19`;
- battle-trace union:
  `4CBDC8CD12B6B75218B2C9518C727F0E55E3EFF0B1A5675224AFCED45A587537`.

The per-shard manifest and raw-file hashes are recorded in the companion JSON.

## Gate decision and assumptions

Integrity is `PASS`; reachability is `PASS`; therefore C2 inheritance is
`PASS`. The positive result means only that the FIX4B analyzer is
side-effect-free, internally consistent, and sufficiently reached under the
frozen schedule. It is not evidence of policy strength.

The frozen parent action is the control for this shadow stage. Consequently,
the exact per-callback parent/applied identity check replaces a separate
baseline-versus-candidate W-L duplicate-control matrix. Win/loss rates,
paired intervals, practical effect size, seat-result deltas, and regressions
are intentionally inapplicable and were not computed.

Reproduction used:

1. the closure algorithm from the FIX4B receipt (`path + NUL + uppercase
   file-SHA + NUL + byte-size + LF`, lexical relative-path order);
2. exact expected block/game set construction from opponent × seat × seed
   base × game, with `seed = seed_base + game`;
3. direct JSONL parsing of all ledgers, summaries, sidecars, and battle
   traces;
4. callback key
   `(version, opponent, seat, seed_base, seed, game, callback_ordinal)`;
5. canonical sorted-key JSON payload comparison per observation fingerprint;
6. global fingerprint/class deduplication; and
7. direct regeneration and ordered equality comparison of all collector rows.
