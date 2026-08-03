# Root implementation verification

Verified: 2026-07-30 03:45 JST

## Frozen source

- Candidate:
  `autonomous_gold_20260715/candidates/archaludon_cumulative_public_hierarchy_after_search_aware_v1`
- `main.py` SHA-256:
  `BE8C67E387CE4F36344A4B0DE610CAB9976BB07EE49200997D35CCC6C5DBF18A`
- `deck.csv` SHA-256:
  `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`
- Exact historical-Silver parent SHA-256:
  `F4B578453C9D953BE94885144DD50E05DBA4510DF3340BE27ADE07495896046E`
- Runtime files: 12.
- Candidate and implementation cache entries after Root cleanup: 0.

The Root independently confirmed that every admitted source hash matched the
pre-implementation ledger. Only accepted H3 v2, H4 v3, H5 v2, and H6 v2
versions are present; rejected siblings are absent.

## Focused and collision execution

An initial Root command accidentally used the PowerShell-default Python 3.9
and stopped before test logic with the language-level error
`unsupported operand type(s) for |`. This was an execution-environment error,
not candidate evidence. The Root then explicitly used Python 3.11.

Final Python 3.11 executions:

| Test | Exit |
|---|---:|
| `test_h2_component.py` | 0 |
| `test_search_aware_component.py` | 0 |
| `test_h1_component.py` | 0 |
| `test_h5v2_component.py` | 0 |
| `test_h4v3_component.py` | 0 |
| `test_h6v2_component.py` | 0 |
| `test_hero_component.py` | 0 |
| `test_h3v2_component.py` | 0 |
| `test_collision_registry.py` | 0 |

The collision result SHA-256 is
`1F8E50F9662FEDFA916B8817E58F3EBC355F1C7D9016FC76399C2BA138516695`.
Root directly checked:

- 28 unordered pairs;
- 112 order-permuted both-seat clear cases;
- 448 directed active-owner pair cases;
- 64 all-eight owner cases;
- all-eight clear winner H2 with seven suppressed clear rules;
- parent rank-1 override;
- unknown and equal-rank fail-closed behavior;
- one parent computation across the initial callback and identical retry.

## Root full union replay rerun

The Root separately reran `run_union_replay_shadow.py` against the frozen
candidate with Python 3.11.

- Root stdout:
  `ROOT_UNION_RERUN_STDOUT.txt`
- Root stderr: empty.
- Replays: 261.
- Callbacks: 14,464.
- Integrated-versus-parent action differences: 28 in 23 replay files.
- Each of eight isolated rules was compared at every callback:
  115,712 eligibility/action/full-certificate comparisons.
- Isolated mismatches: 0.
- Transaction starts: 34.
- Normal clears: 33.
- Explicit real deck-request EOF boundary clear: 1.
- Identical-owner retry checks: 49.
- Invalid actions: 0.
- Parent-cache retry errors: 0.
- Outer/component exceptions: 0.
- Emergency fallbacks: 0.
- Unknown collisions: 0.
- Two-owner states: 0.
- Owner switches: 0.
- Stale owners: 0.
- Max-step hits: 0.

The final union summary SHA-256 is
`E91E12FC8B5E4344884EF6D07C61C92B99EF8B839BFB6CDE24BAE1567BFB11D4`.

All eight rules received natural single-rule attribution somewhere in the
frozen replay union. No natural simultaneous eligible collision occurred, so
live collision causality remains an experimental question; synthetic
collision safety is complete.

## Structural rerun and cache handling

The Root background shadow was initially launched without
`PYTHONDONTWRITEBYTECODE`, creating only `__pycache__` trees under the exact
candidate and implementation destinations. `validate_structure.py` correctly
rejected those temporary caches. After the shadow completed, Root verified
the three resolved cache targets were within those two destinations, removed
only those generated cache directories, and reran the structural validator
with Python 3.11 and bytecode disabled.

Final structural result:

- exit 0;
- candidate `main.py` hash unchanged;
- 12 runtime files;
- 60 cards and one ACE SPEC;
- one loader-last/loader-only `agent`;
- all non-`main.py` members parent-identical;
- cache entries 0.

## Root conclusion before fixed evaluation

The cumulative implementation passes the frozen destructive source,
component, collision, replay-shadow, attribution, and structural gates.
This is not yet Kaggle authorization. The exact fixed-760 schedule, Root
numerical recomputation, independent numerical audit, final rule-level
judgment, and Root-built package remain required.
