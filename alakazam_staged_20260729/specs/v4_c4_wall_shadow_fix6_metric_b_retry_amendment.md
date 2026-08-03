# C4 metric-B retry amendment

Date: 2026-07-30

The original metric-B command was terminated by its outer 1200-second process
limit before the checked suite runner completed all 20 blocks.

Incomplete evidence is preserved at:

`metrics/formal_v4_c4_wall_shadow_fix6_trace_b`

It is not an authorized input to the C4 collector. At termination its
`block_ledger.jsonl` SHA-256 was
`DC589F37F5623904E9B1DCDE667568DB6D17B1FEC0C679104200C6B1D3BA8C2C`.

To avoid another outer timeout without changing games, seats, seeds, agents,
or checked runner, metric B is split into two complete suites:

1. `formal_v4_c4_wall_shadow_fix6_trace_b_rocket_retry2`
   - opponent `rocket_mewtwo_spidops_proxy`
   - both seats
   - seed bases `202608500, 202608510, 202608520, 202608530, 202608540`
   - ten games per block
   - 10 blocks / 100 games
2. `formal_v4_c4_wall_shadow_fix6_trace_b_kangaskhan_retry2`
   - opponent `kangaskhan_crustle`
   - the same seats, seed bases, and games
   - 10 blocks / 100 games

The two complete replacement suites exactly partition the original metric-B
schedule. Only the replacement roots are included in the formal collector
union. The incomplete original root remains raw failure evidence.
