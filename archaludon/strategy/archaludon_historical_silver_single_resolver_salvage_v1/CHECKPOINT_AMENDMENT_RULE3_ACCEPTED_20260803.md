# CHECKPOINT amendment: Rule 3 accepted

Date: 2026-08-03 JST

This file supersedes only the Rule 3 status and accepted-parent entry in
`CHECKPOINT.md`. All other rule statuses and invariants remain unchanged.

## Invariants

- Silver scorer unchanged.
- One final agent, one resolver, one active transaction.
- UNKNOWN returns Historical-Silver.
- Existing artifacts remain read-only.
- No Rule 3 failure is hidden by another rule.

## Current accepted parent

- Candidate:
  `autonomous_gold_20260715/candidates/archaludon_historical_silver_single_resolver_salvage_rule3_repair_v2`
- `main.py`:
  `4287A616E1611F5697964D9F4065978EED1CEA72CDB48C9F63F1430D69106C35`
- `deck.csv`:
  `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`
- Accepted rules: 1, 3, 4, and 5.

## Rule 3 corrected status

- Status: **ACCEPTED AS NON-DESTRUCTIVE**.
- Focused: `276/276`; inherited Rule 1/4/5: `28/28`.
- Fixed160: `100=100`, `G/R/T 0/0/160`, trace `160/160`.
- Fixed760: `480=480`, `G/R/T 0/0/760`; all seats/opponents equal and all
  execution/duplicate faults zero.
- Lifecycle: 10 committed routes, `10/10` completed, zero aborts. One clean
  pre-commit provisional release returned the exact parent action.
- Five changed traces were inspected: no clear harmful first difference.
- Strengthened threshold: not passed (`480 < 486`); do not call it stronger.

## Next action

The user requested Rule 3 only. Stop here after recording and publishing this
accepted repair. Do not begin another rule, package, or Kaggle submission in
this task.

Authoritative verification:
`autonomous_gold_20260715/root_verification/archaludon_historical_silver_single_resolver_salvage_rule3_parent_prefix_v1_20260803/ROOT_FINAL_RULE3_VERIFICATION.md`.
