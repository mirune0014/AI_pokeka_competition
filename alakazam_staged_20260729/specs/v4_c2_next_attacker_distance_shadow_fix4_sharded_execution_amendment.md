# v4 C2 next-attacker-distance shadow fix4 sharded execution amendment

Date: 2026-07-30

Parent execution specification:

- `v4_c2_next_attacker_distance_shadow_fix4_formal_execution_spec.md`
- SHA-256:
  `4BBEF1F21B9D6373357AB84FB039CBBA590F2F8989EC28992EB7A48BCED88FF6`

## Reason

The first single-process invocation was valid but processed the 70 independent
blocks serially.  It is stopped without deleting or overwriting its partial
output.  No row from that partial attempt is used in C2 coverage or integrity
evidence.

Preserved, excluded attempt:

```text
alakazam_staged_20260729/metrics/
  formal_v4_c2_next_attacker_distance_shadow_fix4_7opp_50seed/
```

The immutable 700-game schedule is partitioned by opponent into three
disjoint shards.  Policy, engine, seeds, seats, games per block, max steps,
watchdog, and every game key remain unchanged.

## Shards

### Shard A

```text
marnie
cynthia
alakazam_mirror
```

- expected blocks: 30
- expected games: 300
- output:
  `formal_v4_c2_next_attacker_distance_shadow_fix4_shard_a`

### Shard B

```text
rocket_mewtwo_spidops_proxy
kangaskhan_crustle
```

- expected blocks: 20
- expected games: 200
- output:
  `formal_v4_c2_next_attacker_distance_shadow_fix4_shard_b`

### Shard C

```text
historical_silver
direct_frozen
```

- expected blocks: 20
- expected games: 200
- output:
  `formal_v4_c2_next_attacker_distance_shadow_fix4_shard_c`

Every shard uses all seed bases:

```text
202608500
202608510
202608520
202608530
202608540
```

and both seats with 10 games per cell.

## Union requirements

The three selected shard outputs are accepted only if:

- each shard begins at a fresh output directory and completes every expected
  block;
- game-key intersection across shards is empty;
- the union contains exactly 700 unique
  `(opponent, policy_seat, seed_base, game, seed)` rows;
- opponent, seat, seed, and game distributions exactly match the parent
  specification;
- all parent integrity and reachability gates are recomputed over the union;
- sidecar inventories and hashes are retained per shard;
- duplicate observation fingerprints across shards are deduplicated only for
  reachability, and conflicting route classes for one fingerprint fail closed.

Run the frozen candidate-local collector separately on each shard.  The
Sol-Ultra evaluator and root independently union the three callback row files.
No game-score aggregate is produced.

## Failed-attempt handling

The excluded serial attempt is provenance only.  Its partial ledger, traces,
and sidecars are not copied into a shard, are not repaired, and do not
contribute to any count.  A shard failure is similarly preserved and retried
only into a new suffixed output directory.
