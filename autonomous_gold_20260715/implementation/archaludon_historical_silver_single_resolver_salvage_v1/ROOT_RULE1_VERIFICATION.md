# Root Rule 1 implementation and shadow verification

Date: 2026-08-03 JST
Decision before fixed160: PASS

## Frozen identity

- Candidate `main.py`: `153D8461FB66927DB9731CBE614B71FF5398B8EAE8980AE0BB4D46ADD0E8792A`
- Exact Silver parent: `F4B578453C9D953BE94885144DD50E05DBA4510DF3340BE27ADE07495896046E`
- Exact deck: `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`
- Worker report: `2D57409A7E9A5FBAFF110BD42E71314CB95E519FF57C8C693461C589D571A59F`
- Shadow raw tree digest: `9EB63F22196AA02AAFC263D195EB1ACBF9E1ABBEA484B9EE444F2EBD78719C0C`

The candidate stores the exact Silver source as
`_historical_silver_parent.py`. Root byte comparison found no difference.
Candidate AST has one top-level final `agent`, one `_resolve`, and one static
call to `_parent.agent` in the final agent. Silver `score_option` and
`choose_options` therefore remain only in the exact parent.

## Focused and structural verification

Root reran all 13 focused groups with Python 3.11 and bytecode disabled. All
passed. The suite covers both seats, one/multiple Duraludon, minimum-serial
choice, option reversal, identical and reversed retry, no replacement serial,
Active Duraludon/Relicanth/unknown, malformed binding, count bounds, visible or
full Bench, turn/seat/result mismatch, parent identity outside the one setup
surface, proposal shape, last-callable loading, and one parent call.

Compile/import, legal 60 cards, one ACE SPEC, one-game checked-engine smoke,
and cache-free gates passed. Smoke completed in 77 steps with zero action
errors and no max-step hit.

## Replay shadow root recomputation

- Frozen corpus snapshot: `B88C25BC8F26F959F85D00D27FD7B148D22034D71B2588DF73AAF8C8E0B15004`
- 77 readable replay reports plus one preserved malformed-input record.
- 4,262 callbacks recomputed by root.
- Zero invalid actions and zero wrapper exceptions.
- Nine first differences: seat 0 four, seat 1 five; at most one per replay.

All nine differences satisfy every required boundary:

- turn 0 and `SETUP_BENCH_POKEMON` only;
- parent exact `[]`;
- candidate exactly one own-hand Duraludon `169`;
- selected serial is the minimum visible Duraludon serial;
- setup Active ledger is exact Cinderace `666`;
- no transaction owner;
- telemetry parent call count is one.

No Active-Duraludon setup difference, non-setup difference, multiple-Bench
selection, invalid action, or exception occurred. The behavior is therefore
safe and attributable enough to advance to the immutable fixed160 gate. This
report does not interpret win rates and does not adopt the rule.
