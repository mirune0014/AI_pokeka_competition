# Root fixed-760 recomputation

Decision:
`NUMERICAL_GATE_PASS__MECHANISM_DORMANT`

This is Root's independent recomputation from physical CSV, manifests,
summaries, and preserved traces. It is not packaging, live-write, or
formal-parent authorization.

## Frozen output identity

- output root:
  `implementation/archaludon_persistent_public_boss_access_ledger_last_copy_guard_v1/fixed760_raw_20260730_0620`
- combined CSV SHA-256:
  `90F539FEC2BB6C040446BF43C08CC2309C1B770CE54F943594F3208C49E856A8`
- execution manifest SHA-256:
  `B7C207B4F75E81DE633644EB17896BEEE909B60D7ADB7F3E13429A223683EA48`
- historical paired CSV SHA-256:
  `67C378D38405D01599C41B42F10D9435D94D7CBBD1D1710AFC091880A0EE6F94`
- adjacent paired CSV SHA-256:
  `A9CF18B5164943D08B7AFDFC9FCC7D0502E4D545F50320B6DC172115962BD78A`

The execution manifest binds candidate
`AACAC0B2E47C495A971A6CFCA91A393DBAC4A567291F849DB7912E9F26E9D3A3`
and records exit codes `[0, 0]`.

## Schedule and result recomputation

- physical rows: 760
- unique `(panel, opponent, seat, seed)` keys: 760
- exact expected schedule equality: pass
- result-to-win flag disagreements: zero
- baseline wins: 478/760
- candidate wins: 478/760
- paired gains/regressions: `0/0`
- result differences: zero
- step-count differences: zero

Panel and seat totals:

| Slice | Baseline | Candidate | Games |
|---|---:|---:|---:|
| historical-Silver | 100 | 100 | 200 |
| adjacent population | 378 | 378 | 560 |
| seat 0 | 243 | 243 | 380 |
| seat 1 | 235 | 235 | 380 |

Root checked aggregate, panel, opponent, and panel/opponent/seat slices. No
slice regressed.

## Execution and duplicate controls

- runner role processes: 48
- nonzero exits: zero
- candidate games started: 760/760
- candidate action errors: zero
- candidate max-step hits: zero
- baseline-A versus baseline-B summary mismatches: zero
- baseline-A versus baseline-B byte-trace mismatches: zero

## Candidate trace comparison

Root read every preserved trace.

- baseline versus candidate summary mismatches: zero
- baseline versus candidate byte-trace mismatches: zero

Thus the candidate's Boss ledger and discard guard did not fire anywhere in
this fixed schedule. The schedule proves no local regression in the tested
population, but it supplies no causal strength or match-conversion evidence
for the new mechanism. The exact source engine fixture and one natural replay
remain the mechanism evidence.

Under the user's cumulative policy, this outcome permits retaining the
contract-correct component as a dormant rank-11 rule after collision-safe
integration. It does not permit making the isolated candidate the formal
parent or submitting it as a separate strength claim.

