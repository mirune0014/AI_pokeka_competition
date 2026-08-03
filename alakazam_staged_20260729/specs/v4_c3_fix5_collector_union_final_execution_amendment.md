# v4 C3 fix5 collector union final execution amendment

Date: 2026-07-30

## Scope

This amendment binds the final post-execution C3 sidecar collector used for
formal multi-shard evidence. It changes no production-policy file, deck,
adapter, engine, opponent, seat, seed, game count, or raw execution output.

The governing formal execution specification remains:

```text
v4_c3_public_survival_bench0_fix5_formal_execution_spec.md
SHA-256 B0E7ED5FE726BFB55E20A535BCD0D58E7BCA550D8C5F7A9D56635015DACCFA4A
```

The earlier origin-state amendment remains part of the audit history:

```text
v4_c3_fix5_collector_origin_state_execution_amendment.md
SHA-256 709F7BA89558FD1E12150DE2F6C3296C81C8F4D1ED0679E59F9BEDA28E877A08
```

For collector and collector-test identity only, this amendment supersedes the
older hashes wherever recorded by the governing formal execution
specification, the earlier origin-state amendment, and the implementation
receipt. It supersedes no production-policy or raw-execution identity.

Production closure remains:

```text
5C1BAD6C505358BFF7550A89F167D3DE19B0D2540C6C54ED85324F961A37E134
```

## Final collector identity

```text
verification/c3_sidecar_collector.py
SHA-256 597D84E8D0913B49AE037D6633B412627DB7CEF52699007F612D9679A7A30F92

test_v4_c3_sidecar_collector.py
SHA-256 FF1ADD6CBE2BACEB8EE37D5508C58B0D0F588088FDBBA2AED99356F1F62AA603
```

## Final union semantics

The collector accepts one or more complete raw metric-suite directories and
processes their sidecars in one union before calculating reach.

- callback pairing and transaction lifecycle are source-file-local and
  qualified by version, opponent, seat, seed base, seed, game, and callback
  ordinal;
- a separate logical-key check rejects complete duplicate callbacks across
  input sources;
- every requested suite must contain sidecars, and every sidecar must contain
  at least one locally paired callback;
- event identity must be typed, non-null, path-consistent, and satisfy
  `seed == seed_base + game`;
- only live (`result == -1`) origin states
  (`PROPOSED`, `ARMED`, `DUPLICATE_REBIND`) enter reach;
- completed, aborted, terminal, and non-origin fallback rows cannot inflate
  reach;
- lifecycle instances remain distinct across games, while the same certified
  public decision state is deduplicated globally by `decision_id`;
- a canonical mechanism-evidence comparison rejects the same `decision_id`
  when guard, selected Basic, projections, continuity, promotion/removal,
  Power Pro multiplicity, damage caps, or outcome linkage disagree;
- seat and opponent coverage, continuity, and promotion/removal counts are
  derived only from states whose guard is
  `FLOOR_BOARDOUT_AVOIDANCE` or
  `CAP_LOW_COST_BOARDOUT_AVOIDANCE`;
- the input manifest digest is a portable, input-order-invariant multiset of
  relative path, file SHA-256, and byte count;
- integrity failure returns process exit code `2`; intact raw evidence with
  insufficient mechanism reach returns `0` and
  `INSUFFICIENT_EVIDENCE`.

## Verification

Using the checked Python environment and frozen engine path:

```text
collector focused: 14 / 14
candidate full regression: 254 / 254
py_compile: exit 0
production closure: unchanged
```

The collector does not aggregate wins, scores, paired deltas, or promotion
decisions. Those remain the responsibility of the checked paired combiner,
the independent numerical evaluator, and the root verification.
