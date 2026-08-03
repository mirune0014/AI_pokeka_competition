# v1 runtime live-smoke fix2 amendment

## Failed smoke evidence

The failed full-smoke evidence root is
`alakazam_staged_20260729/metrics/smoke_v1_runtime_certified_seed202608500`.
Its `suite_manifest.json` SHA-256 is
`B5F800A35622B63291D13AF2C7219A4B42688E57C5C576D7457A535D3699866B`.

At that root, the candidate emitted 9,032 `CALL_END` records and 36
irreversible runtime faults. The fault split is 35 Enhanced Hammer child
prompts and one Alakazam attack-resolution verification. All 35 Hammer faults
reported `SELECT_REMAIN_ENERGY`. Structural-invalid actions, callback
exceptions, and unknown removed-rule classifications were all zero.

## Evidence-bound semantic corrections

The fix2 destination is
`alakazam_staged_20260729/versions/alakazam_newdeck_v1_package_runtime_certified_fix2`.
Its evaluation adapter is
`alakazam_staged_20260729/eval_adapters/alakazam_newdeck_v1_package_runtime_certified_fix2`.
The source remains the read-only closure
`B8E4F9C50B41AE9B62FA726E7BD124E44E0A36252E80C0182576BFEB9EE2BFEF`.

Only two live-runtime verification semantics change:

1. `await_hammer_child` requires `remainEnergyCost == 1`, matching the engine
   API meaning of the remaining required Energy count. Every other select
   envelope continues to require exact zero.
2. Exact KO physical movement proof uses the engine's observed order: top
   Pokemon, `preEvolution` in reverse stack order, Energy, then tools. The live
   Alakazam example is serial order `72, 69, 65, 119`; the former forward-stack
   order is rejected.

These are verification corrections for engine-shaped child prompts and logs.
They do not add a decision rule, change a candidate predicate, alter a route or
priority chain, change an action choice, or modify the 60-card deck. The nine
candidate-function ASTs and both priority chains remain source-equivalent.

No simulation was run and no archive was created for this amendment.