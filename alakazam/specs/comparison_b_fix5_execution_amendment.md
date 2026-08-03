# Comparison B fix5 execution amendment

## Scope

This amendment records the executable panel layout for
`comparison_b_v0_vs_v1_runtime_certified_fix5_immutable_spec.md`.
It does not change either policy, the common 60-card deck, the engine,
opponents, seeds, seats, game count, maximum step count, interpretation, or
hard gates in that immutable specification.

Comparison B may start only after the fresh fix5 700-game formal safety suite
has completed and the root has independently verified every prerequisite hard
gate from raw rows.

## Checked-runner invocation

Each of the 35 `(seed_base, opponent)` cells must use the checked
`tools/run_seeded_paired_suite.py`. The opponent must be supplied as one exact
argument:

```text
--opponent <label>=<path>
```

Each cell contains one opponent, one seed base, ten games per seat, both
seats, baseline control A, baseline control B, and candidate. The expected
canonical output is 20 paired rows and 6 manifest rows per cell.

No output directory may be overwritten. If an attempt fails, preserve it and
retry the identical command in a new `attempt_N` directory, up to three total
attempts. Seeds, agents, opponent, seats, game count, and maximum steps may not
change between attempts. The first attempt with `report.valid == true` is the
only canonical attempt. If any cell lacks a valid attempt, the whole comparison
is blocked and no partial win result may be used.

## Combination and audit

Only the 35 canonical checked-runner outputs may be passed to
`tools/combine_staged_panel_results.py`. Combination must produce exactly:

- 700 unique paired rows;
- 210 manifest rows;
- 2,100 child summaries;
- the paired and manifest schedule hashes frozen in the immutable
  specification.

The Sol-Ultra numerical evaluator must recompute the required comparison from
the completed raw rows. The root must independently recompute schedule
equality, duplicate controls, baseline and candidate wins, discordant pairs,
seat and opponent splits, safety totals, and exact sign-test evidence before
using the result.

No failed attempt, earlier fix output, formal-safety row, or partial panel may
be pooled into Comparison B.
