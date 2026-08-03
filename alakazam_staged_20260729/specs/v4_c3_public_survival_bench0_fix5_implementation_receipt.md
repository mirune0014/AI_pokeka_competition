# v4 C3 public-survival bench-0 FIX5 implementation receipt

Date: 2026-07-30

## Immutable inputs

- Parent candidate:
  `alakazam_staged_20260729/versions/alakazam_newdeck_v4_next_attacker_distance_shadow_fix4b`
- Verified parent policy closure:
  `29084BC13CB74236ABE557B57A9E633A8F9E88FA83FF22D131C835293E987157`
- Destination:
  `alakazam_staged_20260729/versions/alakazam_newdeck_v4_public_survival_bench0_fix5`
- Immutable C3 spec SHA-256:
  `1585C9FC7BEB326E2F496AC8B35D99E5B75A976F0F69C7A8B7492671E7B73B5F`
- Power Pro stacking/engine amendment SHA-256:
  `7C48B4D830D009BE9128DDA137FBAA25B2F5CDCE2022BB163ACA6F94E9979344`
- Strategy-judge binding amendment SHA-256:
  `C33EBED6B5C945924F0ED4AFAC1C0029C9B129D870EE4FE583D3612948CD70B6`
- Preimplementation strategy judgment SHA-256:
  `529FC4EA36BC7766B77648700B2356FC9854A71D4593582DFE44292F20CF557B`
- Replay `C:/Users/amuam/Downloads/88843743.json` SHA-256:
  `B0B8752CA10D9319C667A5482323BF8A780A3038FFDD50AF7DCF588EDA882948`

## Files changed

Production:

| File | Bytes | SHA-256 |
|---|---:|---|
| `main.py` | 10512 | `F10CD675F0FCF9DA89E2D80D26CA330B521E934685F492C69085457CD75CFB44` |
| `planner_public_damage_continuity.py` | 40709 | `AD14F84C80FC92B95ACB7C585D492910BD46883528CE2F99158AF046EDDAE201` |
| `planner_public_survival_bench0.py` | 43629 | `C9E86FFDBD054476E562313808DD08E35E05176F30BE083E1862A370229E3AEC` |

Tests and candidate-local verification:

| File | Bytes | SHA-256 |
|---|---:|---|
| `test_v4_public_damage_continuity_fix5.py` | 19259 | `50FD1F56D434B5428E1C84B996AE26D36F7BFC14ABBF2D18F4573C3B50154AB5` |
| `test_v4_public_survival_bench0_fix5.py` | 21765 | `6499FC41865E573BCE24B468DA1F3C9469C5226004CB91418B0E23AD7CDBEA8B` |
| `test_v4_c3_sidecar_collector.py` | 12827 | `6F23C31FCBCD414D3FC1A459457AA4E2F3E42E26EDB208AB962DFA0BF3102E46` |
| `test_v4_next_attacker_distance_shadow_fix4b.py` | 26367 | `C9C5ECD8AAA9D8F1A284FEFAFCE244CBB372B42751BADEEE840A5FEE91E359AB` |
| `verification/c3_sidecar_collector.py` | 20443 | `45F611F121D757AF18C5D501892E743BBF3FFF7ABBC4C362C087DCC885A9249D` |
| `verification/run_c3_replay_probe.py` | 5605 | `B858E5598039B65A9793F6FA85E923074E48B726DB133ACC4656910C8ED6E29E` |

The inherited C2 test was changed only to expect the new outer C3 trace rule;
its C2 behavior assertions remain intact. Relative to the parent, no other
non-cache files were modified or removed. The parent directory was not edited.

## Behavioral intent

The complete FIX4B parent remains the default policy. C3 changes an action only
in normal MAIN with exactly one Active, Bench 0, a parent `ATTACK` or `END`,
and a supported public floor or cap board-out threat. It then benches only one
independently justified low-cost Basic while preserving current deterministic
attack and prize outcomes.

The implementation:

- uses only raw/parsed current observations, public zones and logs, current
  options, static engine metadata, and a match-lifetime public serial ledger;
- requires at least three distinct public Fighting-family marker IDs including
  Solrock `676`, and strictly validates all revealed/committed/unavailable
  Power Pro physical serial sets and their four-copy union;
- supports the frozen Fighting family `673`-`678` and attacks `976`-`983`;
- models Premium Power Pro `1141` with physical-serial deduplication, a four-copy
  limit, committed floor, revealed/archetype-common cap, discard, recovery, and
  current/future stack separation;
- permits a current-turn committed serial to leave the unavailable set after
  exact public recovery, while retaining nonnegative, revealed-subset, and
  four-copy union validation;
- ranks only the spec-supported Basic roles: Shaymin `343`, Abra `741`, and
  Dudunsparce `305`;
- recalculates Powerful Hand after benching and rejects KO or terminal outcome
  degradation;
- reports the maximum residual supported threat damage after base damage,
  modifiers, and weakness/resistance as both policy and safety cap; removes
  only the parent-defeated Active threat before reselecting a residual Bench
  threat;
- classifies all four continuity states, including Hariyama self-KO and
  explicit inactive/unsupported public attack shadow rows, without counting
  those rows as supported threats;
- snapshots the complete delegate state, semantically rebinds duplicate and
  reordered callbacks, verifies the exact Basic move, performs one full parent
  re-entry, and rolls back on every failed linkage;
- fingerprints normalized ledger/log evidence, enforces cross-zone serial
  uniqueness including own Hand, and overwrites inherited C2 action identity
  whenever C3 returns a different action;
- preserves the deck callback and resets the complete parent, integrated, V1,
  trace, duplicate, transaction, and C3 state at the game boundary.

The candidate-local collector counts supported-threat, guard-class,
promotion/removal, and continuity reach once per decision. It prefers the
original `PROPOSED`/`ARMED` state for each `decision_id`, with full game key
plus observation fingerprint as the fallback key when a decision ID is
missing. Repeated `DUPLICATE_REBIND` and `COMPLETED` callbacks therefore do not
inflate reach. Structural integrity, action identity, transaction faults,
stage faults, and all other `CALL_END` checks still inspect every callback.

Trace identity:

- schema version: `5`
- rule version: `V4_PUBLIC_SURVIVAL_BENCH0_FIX5`
- parent closure:
  `29084BC13CB74236ABE557B57A9E633A8F9E88FA83FF22D131C835293E987157`
- candidate closure:
  `5C1BAD6C505358BFF7550A89F167D3DE19B0D2540C6C54ED85324F961A37E134`
- closure layout: 34 top-level non-test Python files plus `runtime/main.py`
  and `deck.csv`, 36 entries total.

## Verification

All test commands used:

```powershell
$env:PYTHONPATH='C:\Users\amuam\project\AI_pokeka_competition\analysis_outputs\cynthia_v9_vs_v11_poffin_role_selection_20260713\seeded_engine'
$env:PYTHONIOENCODING='utf-8'
```

Focused C3 suite, from the candidate:

```powershell
..\..\..\.venv-rl\Scripts\python.exe -B -m unittest -v test_v4_public_damage_continuity_fix5.py test_v4_public_survival_bench0_fix5.py test_v4_c3_sidecar_collector.py
```

Result: exit `0`; `Ran 54 tests`; `OK`.

Complete candidate regression:

```powershell
..\..\..\.venv-rl\Scripts\python.exe -B -m unittest discover -v
```

Result: exit `0`; `Ran 246 tests`; `OK`.

Complete unchanged-parent regression, from the FIX4B parent:

```powershell
..\..\..\.venv-rl\Scripts\python.exe -B -m unittest discover -v
```

Result: exit `0`; `Ran 192 tests in 2.249s`; `OK`.

Changed-Python compile:

```powershell
..\..\..\.venv-rl\Scripts\python.exe -B -m py_compile main.py planner_public_damage_continuity.py planner_public_survival_bench0.py test_v4_public_damage_continuity_fix5.py test_v4_public_survival_bench0_fix5.py test_v4_c3_sidecar_collector.py test_v4_next_attacker_distance_shadow_fix4b.py verification\c3_sidecar_collector.py verification\run_c3_replay_probe.py
```

Result: exit `0`, no stderr.

Exact replay probe:

```powershell
..\..\..\.venv-rl\Scripts\python.exe -B verification\run_c3_replay_probe.py --replay C:\Users\amuam\Downloads\88843743.json
```

Result: exit `0`, `"pass":true`. It retained obs22/23/24 as
`[2]`/`[0]`/`[3]`, changed obs27 to `[2]` selecting Shaymin `343` serial
`81`, semantically rebound the reordered duplicate, returned attack `1071`
after the verified Basic move, and computed the supported Solrock cap as 160.

Deck checks:

- `deck.csv`: 60 nonblank rows; SHA-256
  `F598F5E578D0440C96DC0492EAECF2E19739B7A23225BE57114A724EF7D0FB94`
- `runtime/deck.csv`: 60 nonblank rows; same SHA-256
- parent `deck.csv`: same SHA-256

Known transaction faults, unsupported action changes, metric exceptions, and
replay-probe failures observed by these checks: `0`.

## Formal runner and collector template

The root/evaluation runner must replace only the schedule and fresh output
placeholders with the immutable C3 execution specification:

```powershell
& .\.venv-rl\Scripts\python.exe -B .\tools\run_alakazam_staged_metric_suite.py `
  --engine-dir analysis_outputs/cynthia_v9_vs_v11_poffin_role_selection_20260713/seeded_engine `
  --version c3=alakazam_staged_20260729/versions/alakazam_newdeck_v4_public_survival_bench0_fix5 `
  <immutable-opponent-and-seed-arguments> `
  --games-per-block 10 `
  --max-steps 1000 `
  --watchdog-seconds 180 `
  --output-dir <fresh-c3-suite-dir>

& .\.venv-rl\Scripts\python.exe -B `
  .\alakazam_staged_20260729\versions\alakazam_newdeck_v4_public_survival_bench0_fix5\verification\c3_sidecar_collector.py `
  <fresh-c3-suite-dir> `
  --candidate-closure 5C1BAD6C505358BFF7550A89F167D3DE19B0D2540C6C54ED85324F961A37E134 `
  --rows-out <fresh-c3-suite-dir>\c3_callback_audit_rows.jsonl `
  --summary-out <fresh-c3-suite-dir>\c3_mechanical_summary.json
```

The collector mechanically checks trace identity, raw action identity,
mechanism linkage, integrity, decision-deduplicated reach, all four continuity
classes, at least ten decision-deduplicated promotion/removal contexts, seats,
opponents, and unique callbacks. Unsupported and inactive shadow rows do not
increase the 30-state supported-threat count. All `CALL_END` callbacks remain
subject to integrity and stage-fault checks. It does not aggregate or interpret
wins.

Conflict detection compares observation fingerprints only at the originating
`PROPOSED` / `ARMED` state and its exact `DUPLICATE_REBIND`. A normal
`COMPLETED` or `ABORTED` callback is a post-action observation and is therefore
excluded from origin-state conflict comparison. A dedicated fixture confirms
that a changed post-Basic fingerprint remains valid, while two different
origin fingerprints for one decision still fail integrity.

## Known tradeoffs and evaluator obligations

The guard deliberately fails closed for ambiguous game boundaries or public
serial moves, raw/parsed disagreement, unsupported attack/effect/stadium
damage, unknown weakness/resistance or ownership, absent Fighting family or
Power Pro evidence, copy-limit violations, unsupported Active/Bench shapes,
parent transactions in progress, projection uncertainty, and any failed
transaction/re-entry linkage. Cap-only protection is intentionally limited to
the three named Basic roles and exact public evidence; this trades reach for
zero unsupported action changes.

The evaluator must test the immutable both-seat schedule and verify raw
completeness, unique schedule keys, zero execution/action/transaction/metric
faults, zero unsupported action changes, exact action type/order identity for
no-change callbacks, both guard classes, all four continuity classes, at least
30 supported threat states, at least 10 promotion/removal contexts, both
seats, at least three opponents including two non-mirrors, and the spec's
absolute/paired/matchup floors. Counterfactual outcomes must remain labeled
unobserved rather than inferred from replay results.

No archive was created. No formal 700-game suite, Kaggle API, upload,
submission replacement, Notebook/Discussion publication, or Codex
configuration change was performed.
