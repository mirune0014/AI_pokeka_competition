# v4 C2 next-attacker distance shadow fix4 implementation receipt

## Identity

- Immutable C2 specification SHA-256:
  `096AC9F8C968A5BE645ECE87119241B1965C9110433E4872721881F16956FFE9`
- Binding C2-C5 amendment SHA-256:
  `C33EBED6B5C945924F0ED4AFAC1C0029C9B129D870EE4FE583D3612948CD70B6`
- Frozen parent:
  `alakazam_staged_20260729/versions/alakazam_newdeck_v3_exact_evolution_ko_fix2`
- Candidate:
  `alakazam_staged_20260729/versions/alakazam_newdeck_v4_next_attacker_distance_shadow_fix4`

The C1 candidate was rejected. This candidate was copied from the frozen v3
parent and does not inherit C1. The inherited
`planner_deck_adaptation_v1.py` is byte-identical to the parent.

## Changed files

Production:

- `planner_next_attacker_distance_shadow.py`
  - SHA-256:
    `B4784B7804602188D8253B41D0033F553C0A59DD5B7F34D5C2CA60E368266405`
  - bytes: `67882`
- `main.py`
  - SHA-256:
    `B2E354952ACEE44F7D0E40B44C83CA7A9B8379619FC3E13D98B8C33E894B7C4F`
  - bytes: `9170`
- `runtime/main.py`
  - SHA-256:
    `5100355E5756C16B4E38276DA79551A7F9D1F47D62B863C295D9302B06AE4A24`
  - bytes: `1251`

Focused tests:

- `test_v4_next_attacker_distance_shadow_fix4.py`
  - SHA-256:
    `D53FAC19DAE9FFB1FB92663C0E197A6D51D66EA374E0A45AE362368B50C45CFB`
  - bytes: `17769`
- `test_v4_c2_sidecar_collector.py`
  - SHA-256:
    `0AF90C64D4E5CD159A8D591BD51A438706DFA0E28A2DCBB7BD69136F62BA00DF`
  - bytes: `9316`

Verification tools and retained raw report:

- `verification/c2_sidecar_collector.py`
  - SHA-256:
    `67F19C955E83E99FECB21C148E9EF49AB63BC03062B0A7163E37A4951DC96289`
  - bytes: `17748`
- `verification/run_c2_action_identity_probe.py`
  - SHA-256:
    `979355DD36FDF30603938B4524BCD802F967D0406D391DD31B019CC3FE5F615E`
  - bytes: `9826`
- `verification/c2_action_identity_probe.json`
  - SHA-256:
    `AF11D60FB765F0C70500CF1A22B3FD19C9127C6EE250C57E0BE21973DE06B728`
  - bytes: `645`

Relative to the frozen parent, the only modified inherited files are
`main.py` and `runtime/main.py`. The analyzer, focused tests, collector,
probe, and probe report are new. Every other non-cache parent file is
byte-identical in the candidate.

## Behavioral intent

- Preserve the v3 parent's returned Python action object exactly. C2 is a
  post-action, side-effect-free shadow analyzer and never selects or changes an
  action.
- Replace the two-valued `second_attacker_ready` diagnostic with deterministic
  route rows for each live Abra/Kadabra/Alakazam line, plus a reconstruction
  route when supported by public evidence.
- Report primary Powerful Hand distance and fallback Kadabra damaging-attack
  distance as
  `(route_class, turn_delay, main_actions, forced_prompts, witness)`.
- Reduce routes with the binding order: any `CERTIFIED`, else any `POSSIBLE`,
  else unresolved `UNKNOWN`, else exhaustively proven `IMPOSSIBLE`.
- Model exact public evolution timing, attachment, retreat/switch, forced
  promotion, Run Away, line stack identity, status, energy, and legal-option
  semantics. Unsupported or ambiguous inputs fail closed to `UNKNOWN`.
- Treat successful Run Away with deck size at least three as exact draw three
  and exact Powerful Hand damage delta `+60`; unknown drawn identities cannot
  certify evolution, search, or switch components.
- Exclude option positions from witnesses so semantically equivalent option
  reorderings have one stable observation fingerprint and route trace.
- Recompute line-removal importance as `UNIQUE`, `IMPORTANT`, `REDUNDANT`, or
  fail-closed `UNKNOWN_IMPORTANCE`.
- Emit the complete `V4_NEXT_ATTACKER_DISTANCE_SHADOW_FIX4` trace through the
  root `LAST_STAGED_POLICY_TRACE` mapping and the runtime wrapper. The trace
  includes raw/applied action identity, parent/candidate closures, route rows,
  primary/fallback reductions, amendment fields, transaction state, stable
  fingerprint, unsupported reasons, and `metric_exception`.
- Catch every analyzer exception after the parent action is obtained, return
  that exact parent object, and record only the metric exception.
- Collect coverage directly from checked raw sidecar JSONL rather than the
  existing summary path, which omits the version trace. The collector records
  input hashes, callback and unique-state rows, route class, seat, opponent,
  action identity, metric exception, trace/fingerprint conflicts, duplicate
  controls, and mechanical gates. It intentionally does not aggregate game
  scores or win rates.

## Verification

All Python commands used the repository virtual environment. Tests also used:

```text
PYTHONPATH=C:\Users\amuam\project\AI_pokeka_competition\analysis_outputs\cynthia_v9_vs_v11_poffin_role_selection_20260713\seeded_engine
PYTHONIOENCODING=utf-8
```

1. Focused C2 and raw-sidecar collector suite, run from the candidate:

```text
..\..\..\.venv-rl\Scripts\python.exe -B -m unittest -v test_v4_next_attacker_distance_shadow_fix4.py test_v4_c2_sidecar_collector.py
```

Result: `20/20 OK`, exit code `0`.

This covers active/bench readiness, exact Run Away draw and damage, evolution
and attachment, one/two-turn maturation, reconstruction, possible/impossible/
unknown reduction, malformed public state, option reorder, duplicate callback,
transaction preservation, forced analyzer exception, line importance, runtime
and root trace exposure, episode `88844273`'s four fixed observations, episode
`88843743`'s checked Run Away observations, deterministic raw-row collection,
duplicate exclusion, and all mechanical coverage gates.

2. Candidate full regression, run after the final implementation change:

```text
..\..\..\.venv-rl\Scripts\python.exe -B -m unittest discover -v
```

Result: `186/186 OK`, exit code `0`.

3. Frozen-parent full regression, run from the parent directory:

```text
..\..\..\.venv-rl\Scripts\python.exe -B -m unittest discover -v
```

Result: `166/166 OK`, exit code `0`.

4. Changed-source compile:

```text
..\..\..\.venv-rl\Scripts\python.exe -B -m py_compile planner_next_attacker_distance_shadow.py main.py runtime/main.py verification/c2_sidecar_collector.py verification/run_c2_action_identity_probe.py test_v4_next_attacker_distance_shadow_fix4.py test_v4_c2_sidecar_collector.py
```

Result: `7/7` files compiled, exit code `0`.

5. Deterministic parent/candidate action-identity probe:

```text
..\..\..\.venv-rl\Scripts\python.exe -B verification/run_c2_action_identity_probe.py --repo-root ..\..\.. --output verification/c2_action_identity_probe.json
```

Final result: exit code `0`, `700` callbacks, action mismatch count `0`,
candidate trace action-identity failures `0`, normal metric exceptions `0`,
and overall `pass: true`.

The separate forced analyzer-exception check returned the same action value
and type (`builtins.list`) as the ordinary call and recorded
`metric_exception: RuntimeError`.

The first invocation of this probe exited `1` before writing its report because
the probe's in-process exception fixture had not placed the checked engine on
`sys.path` (`ModuleNotFoundError: cg`). The subprocess parent/candidate rows had
already run. The probe harness was corrected to use the same checked-engine
path for the exception fixture, then the full 700-callback probe was rerun from
scratch and produced the passing retained report above.

6. Deck validation:

- candidate `deck.csv`: exactly `60` rows
- candidate `runtime/deck.csv`: exactly `60` rows
- both SHA-256:
  `F598F5E578D0440C96DC0492EAECF2E19739B7A23225BE57114A724EF7D0FB94`
- frozen parent deck SHA-256:
  `F598F5E578D0440C96DC0492EAECF2E19739B7A23225BE57114A724EF7D0FB94`
- unchanged from parent: `YES`

7. Closure and parent invariance:

Closure algorithm: top-level non-test Python, top-level `deck.csv`, and
`runtime/main.py`; relative paths sorted lexically; each row is
`path + NUL + uppercase file SHA-256 + NUL + byte size + LF`.

- Frozen parent policy closure, `33` files:
  `DC90205DE06AE3E2E41ADC661577096BB02EE5B42AB9F4366FC1A01154745B47`
- Frozen parent planner and inherited candidate planner:
  `255FD9E1303E8E6DFB286952023A7F086CD233B4E5D5030EDBE06313A40697B7`
- Candidate policy closure, `34` files:
  `802A1DD3344287EFE5EAC16F1B07DF79FF2727CF6767359EB3747470D09D4C38`

A fresh analyzer import reported the same parent and candidate closure values.
The frozen parent's closure remained unchanged.

## Archive

No archive was created. Packaging and every external submission action remain
with the parent agent.

## Known tradeoffs and evaluator checks

- This is intentionally shadow-only. It supplies no local win-rate evidence
  and makes no adoption claim.
- `CERTIFIED` is limited to supported public routes. Unknown identities,
  special status/cost semantics, unsupported stadium/effect interactions,
  ambiguous options, malformed ownership/serial data, and in-flight parent
  transactions remain `UNKNOWN`.
- Reconstruction certifies only deterministic physical cards and public legal
  steps. Ordinary unknown draw/search contents remain `POSSIBLE`.
- C3-C5 projection and wall fields are present but remain `None` or empty at
  this C2 boundary, except C2's exact Run Away draw fields.
- Cache artifacts produced by imports/compile are excluded from the policy
  closure and must not be included in any future archive.

The evaluator must run the checked immutable schedule and retain raw sidecars.
Then run:

```text
python verification/c2_sidecar_collector.py <suite_dir> --rows-out <raw_rows.jsonl> --summary-out <mechanical_summary.json>
```

The evaluator must independently verify:

- at least `50` unique observation fingerprints;
- both seats;
- at least three opponents, including at least two non-mirrors;
- at least five unique states in each of
  `CERTIFIED/POSSIBLE/IMPOSSIBLE/UNKNOWN`;
- `100%` raw/applied parent action value, type, and order identity;
- zero metric exceptions, action errors, trace/fingerprint conflicts,
  unmatched callbacks, and duplicate callback keys;
- duplicate decisions excluded from unique-state coverage;
- all required root `version_trace` fields preserved in raw `CALL_END` rows.

The collector's deterministic summary is mechanical evidence only:
`win_rate_aggregated` is always `false`. Numerical results and any adoption
decision remain for the Sol-Ultra evaluator and parent.
