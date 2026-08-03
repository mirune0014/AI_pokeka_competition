# v4 C1 invalid-attempt recovery amendment

Date: 2026-07-30

## Scope

Two first attempts created empty directories before the checked paired runner
could produce a report:

- `202608500_marnie/attempt_1`
- `202608510_direct_frozen/attempt_1`

Before this amendment, each directory contained zero files and therefore no
battle rows, manifest, summary, or checked-runner report.

## Recovery rule

A minimal `report.json` was added to each directory with
`valid=false`.  It records only that the checked runner produced no report or
battle result and that the attempt is excluded from all numerical evidence.
It does not invent a battle aggregate, result row, or runner success.

The checked combiner remains unchanged.  It may now retain both failed attempts
in provenance while selecting each panel's later first attempt whose report has
boolean `valid=true`.

## Numerical authority

Only the selected report-valid attempts, their raw paired rows, manifests, and
referenced game summaries may contribute to the C1 comparison.
