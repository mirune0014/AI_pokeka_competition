# Decision - reject Iono Voltorb Coated conversion v1

Timestamp: 2026-07-15 23:12 JST.

## Decision

Reject and retire
`historical_silver_iono_voltorb_coated_conversion_v1`.  Do not run retention,
package it, or submit it to Kaggle.  Preserve
`historical_silver_kc_lone_nonex_v1` as the strongest deployed parent.

## Reason

The rule correctly changes the two identified live replay choices to non-ex
Archaludon and leaves the earlier Iono and current Lucario negative controls
identical.  However, the preregistered target evaluation is completely inert:

- reference `320 -> 320`;
- disjoint fresh `632 -> 632`;
- combined `952 -> 952`, gains/regressions `0/0`, CI `[0,0]`;
- zero reason hits, zero first divergences, and zero complete Coated chains in
  960 paired keys and 1,920 traces.

The local Iono duplicate was not double-counted.  All source hashes, schedules,
errors, duplicate controls, and raw rows are clean.  Root and independent
Sol-xhigh recomputations agree, and the final Sol-Ultra judgment is
`REJECT / RETIRE`.

Root verification is in
`evaluations/iono_voltorb_coated_conversion_v1/ROOT_PHASE_A_VERIFICATION.md`.
No Kaggle slot was consumed.
