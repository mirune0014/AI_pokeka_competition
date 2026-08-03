# v4 C2 fix4b shard C command retry amendment

Date: 2026-07-30

The corrected FIX4B shard A completed its runner and collector successfully.
The first subsequent attempt to start shard C failed at argument parsing
because the operator command omitted both required `--opponent` arguments.

## Failed command status

- exit code: `1`
- elapsed time: approximately `0.4` seconds
- engine battles started: `0`
- game rows produced: `0`
- shard C evidence accepted: `0`

The failure was an execution-command construction error, not a policy,
engine, or collector result. It does not alter shard A.

The originally named shard C destination is excluded from evidence:

```text
alakazam_staged_20260729/metrics/
  formal_v4_c2_next_attacker_distance_shadow_fix4b_retry1_shard_c
```

## Selected retry

Run the unchanged shard C schedule into the new fresh destination:

```text
alakazam_staged_20260729/metrics/
  formal_v4_c2_next_attacker_distance_shadow_fix4b_retry1_shard_c_retry2
```

Required opponent arguments:

```text
--opponent historical_silver=analysis_outputs/reference_agents/historical_silver_archaludon_54495224
--opponent direct_frozen=alakazam_staged_20260729/eval_adapters/alakazam_800_frozen
```

All other candidate, engine, seat, seed-base, games-per-cell, max-step, and
watchdog values remain exactly those in
`v4_c2_next_attacker_distance_shadow_fix4b_retry_execution_spec.md`.

Only the completed `shard_c_retry2` runner and collector outputs may
participate in the 700-game union. The failed command contributes no row,
callback, fingerprint, or count.
