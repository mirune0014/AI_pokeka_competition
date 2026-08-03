# v4 C2 FIX4B root verification and adoption

Date: 2026-07-30

## Decision

`alakazam_newdeck_v4_next_attacker_distance_shadow_fix4b` is accepted as a
validated, action-identical analysis parent for C3 and C4.

It is not credited with a win-rate improvement. C2 is a shadow-only metric
stage and returned the exact parent action on every observed callback.

## Frozen inputs

- B0 action parent:
  `alakazam_newdeck_v3_exact_evolution_ko_fix2`
- B0 closure:
  `DC90205DE06AE3E2E41ADC661577096BB02EE5B42AB9F4366FC1A01154745B47`
- C2 FIX4B closure:
  `29084BC13CB74236ABE557B57A9E633A8F9E88FA83FF22D131C835293E987157`
- C2 rule:
  `V4_NEXT_ATTACKER_DISTANCE_SHADOW_FIX4B`
- C1 Poffin fix3:
  rejected and not inherited

Only these successful retry shards were used:

1. `formal_v4_c2_next_attacker_distance_shadow_fix4b_retry1_shard_a`
2. `formal_v4_c2_next_attacker_distance_shadow_fix4b_retry1_shard_b`
3. `formal_v4_c2_next_attacker_distance_shadow_fix4b_retry1_shard_c_retry2`

The failed FIX4 attempt and the failed first C-shard command were excluded.

## Root recomputation

The root audit was run with:

```text
node tools/audit_v4_c2_fix4b_union_root.mjs .
```

The script reads the raw block ledgers, game summaries, battle traces, and all
sidecars. It does not use the per-shard collector verdict as its decision
input.

Results:

| Check | Result |
|---|---:|
| Complete blocks | 70 / 70 |
| Unique games | 700 / 700 |
| Missing or unexpected game keys | 0 |
| Cross-shard game-key overlap | 0 |
| Nonzero exits / timeouts | 0 / 0 |
| Action errors / max-step hits / invalid results | 0 / 0 / 0 |
| Nonempty sidecars / battle traces | 700 / 700 |
| `CALL_START` / `CALL_END` | 45,446 / 45,446 |
| Duplicate or unmatched callback keys | 0 |
| Action value/type/order/object-identity faults | 0 |
| Wrapper exceptions / structural invalids | 0 / 0 |
| Metric exceptions / missing or wrong traces | 0 / 0 |
| Wrong parent/candidate closure in trace | 0 / 0 |
| Unique observation fingerprints | 42,315 |
| Fingerprint payload conflicts | 0 |
| `CERTIFIED` unique states | 11,298 |
| `POSSIBLE` unique states | 22,450 |
| `IMPOSSIBLE` unique states | 9,308 |
| `UNKNOWN` unique states | 28,995 |

The candidate closure was independently recomputed from the checked policy
closure and matched the frozen value.

## Independent numerical audit

The Sol-Ultra audit independently regenerated 238,044 collector rows from the
raw sidecars. It found zero missing, extra, or content-mismatched rows and zero
critical-summary mismatches. Its counts matched the root recomputation
exactly.

- Report:
  `reports/v4_c2_fix4b_union_sol_ultra_audit.md`
- Report SHA-256:
  `BC8C54CE617FEDBE2D3DE81A3E051F307576D9A47212250D88121B490A57EC3F`
- JSON:
  `reports/v4_c2_fix4b_union_sol_ultra_audit.json`
- JSON SHA-256:
  `ECBDB6E864E8F21C8FBC72D612D774E51DCF585C90F7C69CB15F8E57FD503BCC`

## Adoption boundary

C2 may be inherited only as:

- a side-effect-free next-attacker distance analyzer;
- a source of `CERTIFIED`, `POSSIBLE`, `IMPOSSIBLE`, and `UNKNOWN`;
- an exact removal-recalculation input for `UNIQUE` and `IMPORTANT`;
- trace evidence for later C3/C4 decisions.

C2 may not:

- change an action;
- convert `POSSIBLE` or `UNKNOWN` into a safety certificate;
- infer hidden hand, deck, prize, seed, opponent name, or replay action;
- be cited as evidence that the policy's game strength improved.

The next implementation parent is therefore FIX4B, whose action behavior is
still exactly B0.
