# Mismatch diagnostic wrapper path repair

The first diagnostic execution stopped before game 1 because the local-only
v2 wrapper resolved the repository root one parent too high. The failed raw
directory is preserved as `mismatch_diagnostics_raw` and must not be reused.

Repair1 changes only:

- `HERE.parents[5]` to `HERE.parents[4]` in the diagnostic wrapper;
- the destination to the new refusal-protected
  `mismatch_diagnostics_raw_repair1` directory.

No comparison policy, deck, engine, opponent, seed, seat, or max-step setting
changes. The repaired wrapper imports the exact Rule 3 v2 target successfully
before rerun.
