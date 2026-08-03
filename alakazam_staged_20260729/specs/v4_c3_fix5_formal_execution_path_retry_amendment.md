# v4 C3 fix5 formal execution path and retry amendment

Date: 2026-07-30

## Scope

This amendment records the paths actually used by the completed C3 formal
execution. It changes no production policy, adapter, deck, engine, opponent,
seat, seed, game count, raw game row, or adoption threshold.

The governing execution specification is:

```text
v4_c3_public_survival_bench0_fix5_formal_execution_spec.md
SHA-256 B0E7ED5FE726BFB55E20A535BCD0D58E7BCA550D8C5F7A9D56635015DACCFA4A
```

The final collector semantics are:

```text
v4_c3_fix5_collector_union_final_execution_amendment.md
SHA-256 6618E5C8AAC1AF3D51E1AD562F2FB5CCBA94CDEBD01E31178A68D3F0C9A3B991
```

## Paired execution

All 35 panels completed in their first valid attempt:

```text
alakazam_staged_20260729/evaluations/
  v4_c3_public_survival_bench0_fix5_panels/
    <seed_base>_<opponent>/attempt_1/
```

The checked combiner output is:

```text
alakazam_staged_20260729/evaluations/
  v4_c3_public_survival_bench0_fix5_combined_attempt1/
```

The combined evidence contains 700 unique baseline rows and 700 unique
candidate rows over identical `(opponent, policy_seat, seed)` keys.

## Metric execution paths

The original Shard A output is incomplete and is excluded from every formal
reach or integrity calculation:

```text
metrics/formal_v4_c3_public_survival_bench0_fix5_trace_a
```

It contains only 2 completed blocks. Its retained files are audit history, not
formal evidence.

Shard A was rerun from a fresh directory in one checked invocation with all
three opponents and all five seed bases:

```text
metrics/formal_v4_c3_public_survival_bench0_fix5_trace_a_retry1
```

The following path deviation is accepted for Shard B. The directory is under
`alakazam_staged_20260729/metrics` rather than repository-root `metrics`:

```text
alakazam_staged_20260729/metrics/
  formal_v4_c3_public_survival_bench0_fix5_trace_b
```

The auxiliary `file_hashes.csv` in Shard B was created after execution. It is
excluded from the raw evidence set and from the collector input-manifest
digest.

The remaining complete suites are:

```text
metrics/formal_v4_c3_public_survival_bench0_fix5_trace_c
metrics/formal_v4_c3_public_survival_bench0_fix5_megalucario_reach1
```

The four accepted suites total 90 complete blocks and 900 games:

| Suite | Blocks | Games |
| --- | ---: | ---: |
| Shard A retry1 | 30 | 300 |
| Shard B | 20 | 200 |
| Shard C | 20 | 200 |
| Mega Lucario reach | 20 | 200 |

## Frozen execution-file hashes

| Suite | `suite_manifest.json` | `block_ledger.jsonl` | `suite_execution_summary.json` |
| --- | --- | --- | --- |
| Shard A retry1 | `6C21260BA2D3E1D2BE64246330FD5642A1D2BCDE6930B88270FCAD70DEAF29B2` | `D47166280394D06CA88F9628F7A7B2CA778F3B61DD53CA0F41DABF0984210135` | `F21FA7B6218E3AF44254F771422D8F5687B186843043C994DF1229B8574AE344` |
| Shard B | `157105FD0249DA63C6748E68ED0E4640B5FB0376AFE6EB76FB6630658B8971DC` | `5BBB7C85075B1153C735768761EE31717C23C1E648E09CCAEF16A709B8D72818` | `ABA204D8B31FB06B31531729FD9DB10BDA7528507236A9196F17E9C81292793C` |
| Shard C | `DAE3FB9DE5CDDE024FB3A83368385F2086D78A085A2D7B17FB8ABDB6B1FB4A00` | `AC74EC0934ADA81F684D93D23C8478E041ECB7CE4B9BA5BA099A4C764328DAF3` | `BD2F3C90AD565B2C67231BC8D49948F95D1314ECFA07CD94F718018F44EF432A` |
| Mega Lucario reach | `15514F80157DC0CCD59CF489FEAB454CE3A2F8141ADE3C9396A8651520DF17F4` | `A01166BDBB51754FE2DD0F1EBD3C5DFD80EAD429BA0E5AE02B158D73042ADA95` | `B26F55F3E0CDE2CAD6E15385F2826CDA64622ADE802AF3F1BE864EB4EF07E214` |

## Union collector output

The final collector was run once over the four accepted complete suites:

```text
alakazam_staged_20260729/metrics/
  formal_v4_c3_public_survival_bench0_fix5_union_audit/
```

Frozen outputs:

```text
c3_callback_audit_rows.jsonl
SHA-256 D191973FD7967F1E48E2773C8BC51FE1834E0D51122247E9C88F4619784933BE

c3_mechanical_summary.json
SHA-256 95155FE090A6CFCF8A5DD3FBA79505E10A368BD051F8A02AC3B3B2D191C15E97

input_manifest_sha256
3FB626031AF16A0F61098DAFC38A7554AEBE9F7C69DC0F0E223DA6F57A3B02E6
```

The collector paired 55,514 callback starts with 55,514 callback ends. Raw
integrity passed. No supported threat/action decision state was observed, so
mechanism reach is `INSUFFICIENT_EVIDENCE`.

## Interpretation boundary

This amendment records execution provenance only. It does not promote or
reject the C3 action rule. Adoption remains governed by the immutable numeric
and mechanism gates and by the root and Sol-Ultra reviews of the frozen raw
rows.
