# CALIBRATION_USED

The earlier MVP smoke roots and the first V2 smoke roots have already been
observed.  They are retained for unit, integration, parity, and runtime
calibration only.  They are not fresh discovery roots, not fresh holdout
roots, and cannot contribute to bootstrap or adoption decisions.

Recorded calibration outputs:

- `run_spread100_discovery_2worlds`: 14 root-world rows, `ROOT_VALID=14/14`,
  action errors 0, invalid 0.
- `run_spread100_holdout_2worlds`: 14 root-world rows, `ROOT_VALID=14/14`,
  action errors 0, invalid 0.

The V2.1 extractor accepts these manifests through `--exclude-manifest` and
deduplicates by normalized public observation, semantic option set, and parent
semantic action.  It never silently reuses a calibration root as fresh data.
