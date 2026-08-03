# v1 runtime live-smoke fix3 amendment

## Failed fix2 smoke evidence

The immutable fix2 smoke evidence root is
`alakazam_staged_20260729/metrics/smoke_v1_runtime_certified_fix2_seed202608500`.
Its `suite_manifest.json` SHA-256 is
`7237BEF57B8D9DA15409E2204B702E2DC0CA10178EE82B34418F589988B22859`.

All 14 blocks and 140 games completed with exit code zero. Root recomputation
found 9,056 `CALL_START` and 9,056 `CALL_END` records, 95 candidate
transaction starts, 93 completions, and two irreversible verification faults.
Both faults were
`V1_HAMMER_UNIQUE_SPECIAL_ENERGY_CURRENT_KO` against the
`kangaskhan_crustle` opponent. No action error, structural-invalid action,
uncaught exception, timeout, max-step hit, unknown removed-card
classification, first-legal fallback, or generic candidate-owned fallback was
observed.

The two faulting physical transitions were:

- target `345/73`, Energy `18/85`: HP/maxHP `140/170` to `120/150`;
- target `345/74`, Energy `18/83`: HP/maxHP `170/170` to `150/150`.

In each case the Energy move log, action-count delta, Hammer discard, target
serial, and all non-target public invariants matched. The first false
postcondition was target fingerprint equality because fix2 removed the Energy
unit/card from its expected fingerprint without also revoking the exact
20-HP modifier supplied by physical card ID 18, Grow Grass Energy.

The fix2 candidate and smoke remain immutable and are classified
`SUPERSEDED_LIVE_RUNTIME_FAULT`.

## Evidence-bound semantic correction

The isolated fix3 destination is
`alakazam_staged_20260729/versions/alakazam_newdeck_v1_package_runtime_certified_fix3`.
Its evaluation adapter is
`alakazam_staged_20260729/eval_adapters/alakazam_newdeck_v1_package_runtime_certified_fix3`.
The immutable source is fix2 closure
`10A92A25FCDDEAE1792701B8B8013C835311D460A27A400618129618090CC6D7`.

Only the Hammer postcondition fingerprint changes. When the exact selected
physical Energy row has card ID 18, the expected transition removes its
aligned Energy unit and physical card and subtracts exactly 20 from current HP
and maximum HP, preserving damage. A non-ID-18 Energy removal must preserve HP
exactly. Malformed fingerprints, misaligned indices or physical serials,
invalid HP ranges, and a transition that would leave non-positive in-play HP
fail closed. KO resolution is not inferred.

This is a strict engine-semantics completion. It does not change a candidate
predicate, candidate ordering, Hammer mode, action choice, another card rule,
the v0 delegate, or the 60-card deck.

## Bound candidate

- fix3 policy closure SHA-256:
  `356C3E40EDC1654FA6E707D55E5C10CB57B42E58C6C817BE165C9DC61DF267A7`
- fix3 planner SHA-256:
  `6C0D8EF09EAA85E5596888D6A42025DC5E53E312FDA6A4AD20960FE0B5B65D69`
- deck SHA-256:
  `F598F5E578D0440C96DC0492EAECF2E19739B7A23225BE57114A724EF7D0FB94`
- normalized deck hash:
  `4414e8995e50c7a00d4b6aa7d9229f63c1dff5261643ec7cd86c4e329113ed69`
- unit tests:
  `131/131`

No simulation or archive was created while authoring this amendment.
