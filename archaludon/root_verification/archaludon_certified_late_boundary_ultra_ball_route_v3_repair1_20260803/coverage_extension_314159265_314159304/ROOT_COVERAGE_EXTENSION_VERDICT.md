# Rule3 v3 coverage extension: root verdict

## Scope

This report closes the frozen natural-coverage extension for
`archaludon_certified_late_boundary_ultra_ball_route_v3_repair1`.
It does not authorize packaging, Kaggle submission, fixed760 execution, or use
of this candidate as the accepted Silver-series parent.

## Frozen identities

- Candidate `main.py` SHA-256:
  `3D95357E75E0B00CB679C1A31F6612AD1FA0EF44914E8ECA8C272CE9220027C3`
- Exact comparison parent `main.py` SHA-256:
  `4287A616E1611F5697964D9F4065978EED1CEA72CDB48C9F63F1430D69106C35`
- Deck SHA-256:
  `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`
- Coverage specification SHA-256:
  `3E1F38C096F32E316F013D6D00F887BCDBBBAD0426B127C2E70D2648E8442651`
- Coverage runner SHA-256:
  `0A40C62185B26794768947EE7904E77E3FCF624080E524E3325B45742EBA691B`
- Immutable schedule document SHA-256:
  `974AF84E02D65EDFA348ABB94E8FC64A470508096205616DD410106BA832B42C`

## Fixed160 evidence carried into this decision

- Unique paired keys: `160/160`.
- Parent wins: `100/160`.
- Candidate wins: `100/160`.
- Paired gains / regressions: `0 / 0`.
- Seat 0: `47/80` for both.
- Seat 1: `53/80` for both.
- Historical-Silver / Arch Peak / Alakazam / Marnie cells:
  `20/40`, `20/40`, `29/40`, `31/40` for both.
- Action errors, start faults, irreversible faults, max-step hits, and duplicate
  mismatches: all `0`.
- Natural v3 starts and completions: `2 / 2`, one per seat.
- Both starts were `ACTIVE_EX_FUEL_ROUTE + R3_WIN_NOW`.
- Neither start replaced an `ATTACK` or `END`; both replaced a deferred setup
  action.
- Natural Turbo starts: `0`.

Independent numerical audit:
`INDEPENDENT_NUMERICAL_AUDIT.md`, SHA-256
`8098FEBDEBEA9519795B12261330058D75D586E6531A3CF055A246818A5472D1`.

## Frozen extension result

The extension executed seeds `314159265..314159304`, both seats, against
Historical-Silver, Arch Peak, Alakazam, and Marnie in the frozen order.

- Executed primary keys: `320/320`.
- Missing, extra, or duplicate keys: `0`.
- Manifest or outcome mismatches: `0`.
- Action errors, irreversible faults, max-step hits, and duplicate mismatches:
  all `0`.
- New v3 starts / completions / faults: `0 / 0 / 0`.
- Cumulative starts / completions: `2 / 2`.
- Active-ex family naturally completed: yes.
- Turbo family naturally completed: no.
- Parent `ATTACK/END` to candidate Ultra Ball first difference: no.
- Coverage stop condition reached: no.
- Frozen cap exhausted: yes.

Raw completion hashes:

- `coverage_status.json`:
  `8550F27C57130FA95F5A0362666D29FA3E7D20CFA7FE7A20837796DAF40F7B07`
- `extension_manifest.jsonl`:
  `94FB4735674CC7400ED03F36E5235C60C77581573A68BC19EF418253F0042B81`
- `RUN_COMPLETE.json`:
  `728805BD5A48DD5E087A7D2C9AC2F412CF1ABD814CEFD1A55E8FABC4863BAC51`

## Nine trace differences

Root recomputation found nine raw trace differences but zero outcome differences.
They are four distinct local states repeated across opponents. All occur after
Historical-Silver itself selected Ultra Ball. The v2 parent retained ownership
of that parent-selected transaction, while v3 correctly declined to claim it
without a dominance certificate and returned subsequent decisions to Silver.

1. Seed `314159278`, seat 0, Historical-Silver and Arch Peak:
   v2 evolved immediately; v3 first played Duraludon. The lines fully
   reconverged before the attack, including board and Energy state.
2. Seed `314159282`, seat 1, Historical-Silver, Arch Peak, and Marnie:
   the same two physical Metal serials were selected in opposite order. All
   following snapshots and actions were identical.
3. Seed `314159294`, seat 1, Historical-Silver and Arch Peak:
   v2 selected one Alloy Metal; v3/Silver selected two and put the additional
   Metal on a Bench Duraludon. The candidate had better temporary backup
   readiness. Both results remained the same loss and the final state
   reconverged.
4. Seed `314159302`, seat 1, Historical-Silver and Arch Peak:
   the lines selected different but functionally identical Basic Metal serials.
   All subsequent snapshots and actions were identical.

Classification: all nine are intentional removal of v2 non-dominance ownership;
none is a v3 start, v3 leakage, post-commit fallback, implementation fault, or
clearly harmful first difference.

Evidence:

- `MISMATCH_FIRST_DIFFERENCES.csv` SHA-256:
  `FC96916FD973CAC4585336475B1B8A245E9082998B1CEF7AE97F06A8DB4B8241`
- Diagnostic manifest SHA-256:
  `847116388E37B146C3F02EF882FDAA3D58981D2808B67CB9D1F120573B81B638`
- Root recompute SHA-256 at closure:
  `B85DCF4C138BA8BCA45A070EA51B97983AB343A7AF5CE722263FC092C2AEA696`

## Final decision

**DEFER the combined v3 candidate.**

The implementation is not broken. The Active-ex Fuel subfamily has two-seat,
100%-completion, zero-fault natural evidence and is retained as a frozen,
provisionally validated artifact. The combined candidate is not accepted as an
implementation-only parent because its Turbo behavior and its principal
late-boundary `ATTACK/END -> Ultra Ball` replacement were never naturally
exercised, even after the precommitted coverage cap.

Consequences:

- Do not run fixed760 for this combined candidate.
- Do not package or submit it.
- Do not use it as the accepted Silver-series parent.
- Do not keep searching beyond the frozen cap under the same contract.
- Preserve the candidate, fixtures, fixed160 evidence, extension, and mismatch
  diagnostics unchanged.

The smallest honest successor, only under a new versioned amendment, is an
Active-ex-only candidate with Turbo removed or made unreachable. That successor
must define whether `ATTACK/END` natural coverage remains mandatory and must be
evaluated as a new isolated candidate. No such successor is authorized by this
closure report.

