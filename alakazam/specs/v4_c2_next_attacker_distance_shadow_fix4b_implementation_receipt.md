# v4 C2 next-attacker-distance shadow fix4b implementation receipt

Date: 2026-07-30

## Identity

- Failed formal source, retained read-only:
  `alakazam_staged_20260729/versions/alakazam_newdeck_v4_next_attacker_distance_shadow_fix4`
- New corrected candidate:
  `alakazam_staged_20260729/versions/alakazam_newdeck_v4_next_attacker_distance_shadow_fix4b`
- Trace rule:
  `V4_NEXT_ATTACKER_DISTANCE_SHADOW_FIX4B`
- Failed FIX4 policy closure, 34 files:
  `802A1DD3344287EFE5EAC16F1B07DF79FF2727CF6767359EB3747470D09D4C38`
- Corrected FIX4B policy closure, 34 files:
  `29084BC13CB74236ABE557B57A9E633A8F9E88FA83FF22D131C835293E987157`
- Inherited frozen v3 parent closure retained in the trace:
  `DC90205DE06AE3E2E41ADC661577096BB02EE5B42AB9F4366FC1A01154745B47`

Governing inputs:

- immutable C2 specification:
  `096AC9F8C968A5BE645ECE87119241B1965C9110433E4872721881F16956FFE9`
- formal execution specification:
  `4BBEF1F21B9D6373357AB84FB039CBBA590F2F8989EC28992EB7A48BCED88FF6`
- sharded execution amendment:
  `4FEE860E542151B9EAB20E00F451EA7F1659B77132005F2900D2E3944AE450AD`
- C2-C5 strategy-judge binding amendment:
  `C33EBED6B5C945924F0ED4AFAC1C0029C9B129D870EE4FE583D3612948CD70B6`
- failed-formal retry amendment:
  `7BA5A67FDB084F70DF954DF9C0DBDC8467924D7DCCE2B1D1D5112DA9ED7D51D3`
- FIX4B retry execution specification:
  `19FFB4DC039EF20961A4AA806AB56CFF4C399FEBB80375CCD7EB9E37D24423E1`

## Files changed relative to failed FIX4

Production:

- `main.py`
  - bytes: `9171`
  - SHA-256:
    `CB35C27EF291B627F2299DF8B5B5EF26046BC92F4E16A60BC9ECC3382E34F71F`
- `planner_next_attacker_distance_shadow.py`
  - bytes: `69153`
  - SHA-256:
    `4659D12318465049AC45CFB807A0541B6F2F4048D653F6DFF04752C7C1999220`

Focused tests:

- `test_v4_next_attacker_distance_shadow_fix4.py` was replaced by the
  FIX4B-specific
  `test_v4_next_attacker_distance_shadow_fix4b.py`
  - bytes: `26221`
  - SHA-256:
    `4644EFFF367BE6F2278496F241D887D66DF9F7A5616DD5FE1997F486DC2ED5F8`
- `test_v4_c2_sidecar_collector.py`
  - bytes: `9485`
  - SHA-256:
    `15FF18D808C9A3DC9C38011B0AC3CB3A115CBF7C60FEC1FDEDC9BEB6FD1B1160`

Candidate-local verification:

- `verification/c2_sidecar_collector.py`
  - bytes: `17749`
  - SHA-256:
    `3DECCF354939D00EE2F6AFB6CF83A18259163EA800D9B55997A58C8584AB76F9`
- `verification/run_c2_action_identity_probe.py`
  - bytes: `9828`
  - SHA-256:
    `5B34520002803E5E8E127290A5D946ECABF56FAD33D30917162A9F25FE2E014D`
- retained probe result,
  `verification/c2_action_identity_probe.json`
  - bytes: `646`
  - SHA-256:
    `CD718C01C9ADB2E51927BEF2A819B19943261796750710EB297D528CF3D8BE3D`

The complete non-cache manifest comparison found no other differences.
`runtime/main.py` remains byte-identical to FIX4:
`5100355E5756C16B4E38276DA79551A7F9D1F47D62B863C295D9302B06AE4A24`.
The inherited parent delegate, all C2 distance semantics, and the rejected C1
exclusion are unchanged.

## Behavioral intent

1. Parsed own Active or Bench entries that are `None` or otherwise have no
   object identity now return an ordinary global fail-closed `UNKNOWN` with
   `FACE_DOWN_IN_PLAY_IDENTITY_UNKNOWN`. They no longer reach line enumeration
   or become a metric exception. An empty Active in setup contexts `2` and
   `38` similarly fails closed with
   `PRE_SETUP_ACTIVE_IDENTITY_UNKNOWN`.
2. The decision fingerprint now adds exactly the normalized flags
   `integrated_transaction_active` and `v1_transaction_active`. Absent and
   false normalize to the same payload. Either true value changes the
   fingerprint and supplies `PARENT_TRANSACTION_IN_PROGRESS` to the analyzer.
   Transaction kind/stage and any opponent, seat, seed, hidden-data, callback,
   or object-identity metadata are not added to the fingerprint.
3. The analyzer, root fallback trace, candidate-local collector, and identity
   probe consistently require
   `V4_NEXT_ATTACKER_DISTANCE_SHADOW_FIX4B`.
4. C2 remains post-action and shadow-only. The exact object returned by the
   parent delegate is returned unchanged on normal analysis, setup fail-closed
   analysis, and forced analyzer exceptions.

No exception-detail schema was broadened.

## Verification

All Python checks used the repository virtual environment. Test commands used:

```text
PYTHONPATH=C:\Users\amuam\project\AI_pokeka_competition\analysis_outputs\cynthia_v9_vs_v11_poffin_role_selection_20260713\seeded_engine
PYTHONIOENCODING=utf-8
```

### Focused suite

Final command, from the FIX4B candidate:

```text
..\..\..\.venv-rl\Scripts\python.exe -B -m unittest -v test_v4_next_attacker_distance_shadow_fix4b.py test_v4_c2_sidecar_collector.py
```

Result: `26/26 OK`, exit code `0`.

The first pre-final invocation of this same command exposed that an empty
pre-setup Active still reduced to `POSSIBLE`: `25/26` passed, exit code `1`.
The setup-only empty-Active fail-closed case was then made explicit and the
entire focused suite was rerun to the final passing result above.

The final suite covers:

- empty pre-setup Active;
- parsed `active=[None]` in setup contexts `2` and `38`;
- duplicate callback and reordered setup options;
- exact parent action object identity for setup fail-closed cases;
- absent, explicit-false, integrated-true, and v1-true fingerprint flags;
- ignored transaction metadata including synthetic opponent/seat/seed/hidden
  values;
- the known failed FIX4 conflict class
  `75F113FC56DF7F101F296913D90C90568C9FB8AE26338B84CBC9482FBFF9B86A`;
- unchanged C2 distance, reduction, Run Away, episode, transaction, collector,
  runtime, and forced-exception fixtures.

The failed formal amendment states that all 320 prior normal metric exceptions
were the same parsed face-down setup shape in context `2` or `38`. Both
contexts, the empty pre-setup boundary, duplicate callback, and reordered
option variants are therefore all represented by focused fixtures. Every
represented setup shape returns `UNKNOWN`, has `metric_exception=None`, and
preserves exact action identity.

### Corrected-candidate full regression

Command, from the FIX4B candidate:

```text
..\..\..\.venv-rl\Scripts\python.exe -B -m unittest discover -v
```

Result: `192/192 OK`, exit code `0`.

### Failed-parent full regression

Command, from the unchanged failed FIX4 directory:

```text
..\..\..\.venv-rl\Scripts\python.exe -B -m unittest discover -v
```

Result: `186/186 OK`, exit code `0`.

Its policy closure recomputed after the run as the frozen
`802A1DD3344287EFE5EAC16F1B07DF79FF2727CF6767359EB3747470D09D4C38`.

### Changed-source compilation

Command, from the FIX4B candidate:

```text
..\..\..\.venv-rl\Scripts\python.exe -B -m py_compile planner_next_attacker_distance_shadow.py main.py verification/c2_sidecar_collector.py verification/run_c2_action_identity_probe.py test_v4_next_attacker_distance_shadow_fix4b.py test_v4_c2_sidecar_collector.py
```

Result: all `6/6` changed Python files compiled, exit code `0`.

### 700-callback action-identity probe

Command, from the FIX4B candidate:

```text
..\..\..\.venv-rl\Scripts\python.exe -B verification/run_c2_action_identity_probe.py --repo-root ..\..\.. --output verification/c2_action_identity_probe.json
```

Result: exit code `0`, `pass=true`.

```text
callbacks = 700
action_mismatch_count = 0
candidate_trace_action_identity_failures = 0
candidate_metric_exceptions = 0
forced_exception action_equal = true
forced_exception type_equal = true
forced_exception metric_exception = RuntimeError
```

### Representative retry smoke

A no-file inline Python smoke reran:

- context `2`, face-down Active, original and reordered options;
- context `38`, face-down Active, original and reordered options;
- context `2`, empty Active;
- absent, false, integrated-true, and v1-true transaction states.

Result: all assertions passed, exit code `0`. Every setup row was `UNKNOWN`
with no metric exception. Reordered options retained the same fingerprint in
each context:

```text
context 2 = 3E9AE6D8DF69255514176BA639B5A4902E654F97AE6242859D1DCC2192453F30
context 38 = D0A48205F6EE9BBBA1803548CAB387D0BA2AB5AC04C9977F0DB0FCFCA9A914F4
empty context 2 = C7B0A3FA0B62070030AE0B0FA0C748B1425A477E0E7E697DD35147878D29A0A6
```

For one identical public observation, the known transaction-state conflict
class now separates as required:

```text
absent = false = 2D95D010BBB670EBFA1D4E7E3757B8BB53627681781523C8173FCDA2362BA34A
integrated true = 6F9EE2088A42B248DB027FB855B30A91F473281DA4013E5F007EB751F79EFC86
v1 true = 10D8D7DF02AE813C202EA5AC416FC3EEF01F320036728F24770A68502630CA23
```

Both true cases were `UNKNOWN` with
`PARENT_TRANSACTION_IN_PROGRESS`; absent and false retained the same
`CERTIFIED` route trace.

### Deck and closure

- `deck.csv`: `60` rows,
  `F598F5E578D0440C96DC0492EAECF2E19739B7A23225BE57114A724EF7D0FB94`
- `runtime/deck.csv`: `60` rows, same hash
- failed FIX4 `deck.csv`: same hash
- deck changed: `NO`

Closure algorithm: top-level non-test Python, top-level `deck.csv`, and
`runtime/main.py`; relative paths sorted lexically; each row is
`path + NUL + uppercase file SHA-256 + NUL + byte size + LF`.

The direct closure recomputation and a fresh analyzer import both returned:

```text
candidate_closure_sha256 =
29084BC13CB74236ABE557B57A9E633A8F9E88FA83FF22D131C835293E987157
```

## Archive and external actions

No archive was created. No formal battle suite, Kaggle API, package upload,
submission, Notebook, Discussion, or Codex-configuration action was run.

## Known tradeoffs and evaluator checks

- The setup replay is represented by exact failed-shape fixtures and the
  no-file smoke, not by copied or repaired failed formal rows. The evaluator
  must still confirm zero normal metric exceptions over the fresh complete
  700-game retry.
- This is an isolated analyzer-integrity correction. It supplies no game-score
  or win-rate evidence and makes no adoption claim.
- Unknown public identity remains deliberately fail-closed and is never
  inferred from hidden setup state.
- The fingerprint includes only public C2 observation material already used by
  FIX4 plus the two normalized transaction booleans. No external run metadata
  was introduced.

The evaluator must use the fresh shard destinations in
`v4_c2_next_attacker_distance_shadow_fix4b_retry_execution_spec.md`, run this
candidate's collector separately on every completed shard, and test:

1. exact candidate closure and `FIX4B` trace/collector identity;
2. zero setup and other normal metric exceptions;
3. zero action-identity failures, including contexts `2` and `38`;
4. zero fingerprint trace conflicts;
5. absent/false transaction equivalence and true-state separation in collected
   callbacks;
6. the complete frozen schedule, reachability floors, and all remaining
   integrity gates without using any failed FIX4 row.
