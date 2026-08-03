# Root record: first-Turbo census attempt 1

Status: `FAILED_BEFORE_RAW_CSV_COMPLETION`

The deterministic execution operator verified and ran the frozen command once.
The process exited with code `1` after about 2.013 seconds with:

`duplicate semantic first-Turbo callback key`

Bound artifacts:

- execution specification SHA-256: `3DE92E1B0461E4396D2FE5B502FCBD7D945B727E48D3553715BC7CE66F18DF21`
- executed runner SHA-256: `42243ED174DFF40D80BD6DBD7004E81B339FBE22576CFAE7ED2D408E20B075F1`
- copied `source_manifest.json` SHA-256: `90A512D5C9AE5EAD8DF92F370C32716959EC0929F9465451E7BB0926DBEB5A68`

No callback, transaction, difference, or summary CSV/JSON was completed. The
attempt-1 destination is preserved and must not be overwritten or interpreted.

Root diagnosis: the strategy contract requires deduplication by
`(replay_sha256, seat, stage, snapshot_sha256)`. The attempt-1 runner instead
treated a repeated engine presentation of such a snapshot as fatal. A retry is
permitted only in a new runner and new immutable destination. It must collapse
an identical retry only after proving that parent semantics, contract semantics,
owners, classification, and error state agree with the first presentation; any
disagreement remains fatal and is not silently deduplicated.

