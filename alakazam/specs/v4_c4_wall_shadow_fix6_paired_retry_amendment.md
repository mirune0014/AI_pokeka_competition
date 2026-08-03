# C4 paired-run retry amendment

Date: 2026-07-30

The first execution commands for two cells failed in argument parsing before
the battle runner created any game row:

- `202608500_rocket_mewtwo_spidops_proxy/attempt_1`
- `202608500_historical_silver/attempt_1`

The failed commands passed a bare opponent path instead of the required single
`NAME=PATH` token and exited 2. No battle began and no `paired_results.csv`,
manifest, or valid runner report was created.

The raw failed attempt directories and stderr evidence are preserved.
To make the checked combiner's immutable-attempt enumeration machine-readable,
the root added one `report.json` to each failed attempt. Each report contains
`valid: false`, the exact preflight failure class, exit code 2, and zero result
rows. These reports do not repair, replace, or select the failed attempts.

Corrected commands used:

- `attempt_2` for the two cells above;
- `attempt_1` for every other cell;
- a single literal `NAME=PATH` opponent token in every corrected command.

The checked combiner must select the first report-valid attempt and retain both
failed attempt records in `combination_provenance.json`.
