# Comparison B fix3 execution amendment

## Scope

This amendment corrects one launcher-argument formatting error. It does not
change a policy, deck, engine, opponent, seed, seat, game count, max-step
limit, comparison interpretation, or hard gate in
`comparison_b_v0_vs_v1_runtime_certified_fix3_immutable_spec.md`.

The immutable specification SHA-256 is
`32A55F10E5A79E535D3C7FBBFF25AA353C0C3FC7161DEAC3E8B407A2A49DE5B2`.

## Preserved failed attempt

The first launch for cell `202608500_marnie` used an opponent path without the
checked runner's required `NAME=` prefix. Argument parsing stopped before any
game was executed.

The raw failed attempt is preserved at
`alakazam_staged_20260729/evaluations/comparison_b_runtime_certified_fix3_panels/202608500_marnie/attempt_1`.

- exit code: `2`
- `stdout.txt` SHA-256:
  `E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855`
- `stderr.txt` SHA-256:
  `CD6E9135788C00A99B734ADB3F61E1630F63BA52195A352FEACA22020CBF074B`
- checked report: absent
- paired rows: `0`
- games started: `0`

This attempt is an execution-format failure, not policy evidence, and must
never be pooled.

## Authorized correction

Every checked-runner invocation must pass the opponent as one exact argument:

```text
--opponent <label>=<path>
```

The corrected `202608500_marnie` cell must use `attempt_2`. The other 34
cells, which have not yet been attempted, must use `attempt_1`. No directory
may be overwritten. The fixed schedule and all other command arguments remain
exactly as specified.

The execution ledger must retain the failed attempt and the 35 corrected
schedule cells. Combination must select the first checked
`report_valid == true` attempt for each cell, so only
`202608500_marnie/attempt_2` can supersede its parse-only attempt.
