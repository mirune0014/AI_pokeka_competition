# V2 stratified multiworld diagnostic

The V2.1 harness implements the GPT PRO-directed next experiment without
changing the accepted agent.  `stratified_roots.py` records the primary
action transformation (`T1`--`T13`) and independent public context tags, then
writes a deterministic discovery/holdout/reserve split.  `run_v2.py` executes
each root in a diagnostic bank of engine-only worlds consistent with the
public counts, while the parent callback receives only the target public
observation.

The operating minimum is 32 discovery roots and 16 fresh holdout roots, with
shortfalls reported rather than fabricated.  Existing smoke roots are marked
`CALIBRATION_USED` and excluded.  Use `--split discovery` and `--split
holdout` as separate runs; the holdout must remain untouched until a
hypothesis contract is frozen and an isolated candidate is implemented.

Example (paths are illustrative):

```powershell
python stratified_roots.py `
  --replay replay.json `
  --parent-agent ..\..\candidates\archaludon_historical_silver_replay_repair_alakazam_lillie_v1 `
  --output _local_generated\v2\roots.jsonl

python run_v2.py `
  --root-manifest _local_generated\v2\roots.jsonl `
  --split discovery `
  --output _local_generated\v2\discovery
```

Terminal result is the only primary comparison.  Prize/board/next-attack
fields are retained as diagnostics.  Root-family aggregates are kept
separate from root-world rows, and formal multiworld eligibility is fail
closed when public zone mirrors are absent.  The report never promotes a rule
or creates a Kaggle package.
