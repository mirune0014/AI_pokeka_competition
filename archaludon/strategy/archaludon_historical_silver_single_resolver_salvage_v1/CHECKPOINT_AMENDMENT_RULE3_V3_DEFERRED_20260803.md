# Checkpoint amendment: Rule3 certified late-boundary v3 deferred

## Invariants

- Silver scorer is unchanged.
- No wrapper was added to an accepted parent.
- The resolver remains single-owner.
- Unknown or incomparable states return Historical-Silver.
- Existing artifacts remain read-only.
- No Kaggle write is authorized by this checkpoint.

## Candidate

- Name: `archaludon_certified_late_boundary_ultra_ball_route_v3_repair1`
- `main.py` SHA-256:
  `3D95357E75E0B00CB679C1A31F6612AD1FA0EF44914E8ECA8C272CE9220027C3`
- Exact comparison parent SHA-256:
  `4287A616E1611F5697964D9F4065978EED1CEA72CDB48C9F63F1430D69106C35`

## Status

`DEFERRED_COMBINED_CONTRACT_NOT_NATURALLY_COVERED`

- Focused implementation and engine gates passed.
- The sole natural committed fault was repaired as an ownership bug.
- Fixed160 was tied `100-100`, gains/regressions `0/0`, faults `0`.
- Two Active-ex Fuel `R3_WIN_NOW` routes completed, one per seat.
- Frozen 320-key extension produced no additional v3 starts.
- Turbo and `ATTACK/END -> Ultra Ball` remained naturally unexercised.
- Nine v2/v3 trace differences were benign removal of v2 ownership; no harmful
  v3 difference was found.

## Decision

- The combined v3 candidate is not accepted and must not become the parent.
- The Active-ex Fuel subfamily and evidence are retained provisionally.
- No fixed760, package, or submission follows.
- Do not widen conditions or continue schedule hunting under this contract.

## Next authorized work

None. A future Active-ex-only successor requires a separate versioned
requirements amendment and an explicit new implementation decision.

Authoritative closure report:
`root_verification/archaludon_certified_late_boundary_ultra_ball_route_v3_repair1_20260803/coverage_extension_314159265_314159304/ROOT_COVERAGE_EXTENSION_VERDICT.md`.
