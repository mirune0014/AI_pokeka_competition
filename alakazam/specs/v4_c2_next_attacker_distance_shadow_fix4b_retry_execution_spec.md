# v4 C2 next-attacker-distance shadow fix4b retry execution specification

Date: 2026-07-30

This specification applies only after the corrected candidate passes its
focused, full-regression, compile, and callback-identity checks.

## Inputs

Corrected candidate:

```text
alakazam_staged_20260729/versions/
  alakazam_newdeck_v4_next_attacker_distance_shadow_fix4b
```

Engine:

```text
analysis_outputs/cynthia_v9_vs_v11_poffin_role_selection_20260713/
  seeded_engine
```

The candidate closure and member hashes are supplied by the implementation
receipt and must be checked again immediately before execution.

The governing behavior, integrity, reachability, and fail-closed requirements
remain those in:

- `v4_c2_next_attacker_distance_shadow_fix4_immutable_spec.md`
- `v4_c2_next_attacker_distance_shadow_fix4_formal_execution_spec.md`
- `v4_c2_next_attacker_distance_shadow_fix4_sharded_execution_amendment.md`
- `v4_c2_c5_strategy_judge_binding_amendment.md`
- `v4_c2_next_attacker_distance_shadow_fix4_failed_formal_retry_amendment.md`

## Immutable schedule

Use both policy seats, 10 games per cell, `max_steps=1000`, and watchdog 180
seconds.

Seed bases:

```text
202608500
202608510
202608520
202608530
202608540
```

### Shard A

Opponents:

```text
marnie
cynthia
alakazam_mirror
```

Expected: 30 blocks and 300 games.

Fresh output:

```text
alakazam_staged_20260729/metrics/
  formal_v4_c2_next_attacker_distance_shadow_fix4b_retry1_shard_a
```

### Shard B

Opponents:

```text
rocket_mewtwo_spidops_proxy
kangaskhan_crustle
```

Expected: 20 blocks and 200 games.

Fresh output:

```text
alakazam_staged_20260729/metrics/
  formal_v4_c2_next_attacker_distance_shadow_fix4b_retry1_shard_b
```

### Shard C

Opponents:

```text
historical_silver
direct_frozen
```

Expected: 20 blocks and 200 games.

Fresh output:

```text
alakazam_staged_20260729/metrics/
  formal_v4_c2_next_attacker_distance_shadow_fix4b_retry1_shard_c
```

## Execution and collection

Use the checked repository metric-suite runner. Run the corrected
candidate-local sidecar collector independently on each completed shard.
Neither the runner nor collector may interpret game scores.

If a shard runner fails, preserve it and stop that execution chain. If a
collector reports an integrity failure, preserve the output and do not start a
dependent shard. Never overwrite or repair a failed output directory.

## Union audit

The Sol-Ultra numerical auditor and root independently verify:

- exactly 70 complete blocks and 700 unique game keys;
- exact schedule equality and empty cross-shard intersections;
- 700 nonempty sidecars and battle traces;
- zero nonzero exits, timeouts, action errors, max-step hits, invalid results,
  duplicate callbacks, wrapper exceptions, structural invalids, normal metric
  exceptions, missing traces, and fingerprint conflicts;
- exact action value, Python type, and element-order identity;
- exact closure and trace-rule identity;
- at least 50 unique decision fingerprints;
- both seats and all seven opponents;
- at least five unique states in each of `CERTIFIED`, `POSSIBLE`,
  `UNKNOWN`, and `IMPOSSIBLE`.

No row from the failed serial attempt or failed fix4 shards is included.
