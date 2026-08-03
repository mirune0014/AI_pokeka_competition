# fix4 multi-Energy fault replay execution amendment

The fix4 140-game smoke uses seed base `202608500`; it cannot contain the two
fix3 formal positions that occurred under seed bases `202608510` and
`202608520`.

Before the complete fix4 formal safety suite, run a fresh targeted Marnie-only
diagnostic with:

- candidate:
  `alakazam_staged_20260729/eval_adapters/alakazam_newdeck_v1_package_runtime_certified_fix4`
- opponent:
  `meta_agents/marnie_sota_live_85033057_simple`
- seed bases: `202608510`, `202608520`
- games per block: `10`
- seats: both
- max steps: `1000`
- output:
  `alakazam_staged_20260729/metrics/targeted_fix4_multi_energy_fault_replay_202608510_520`

This is a 40-game diagnostic gate, not win-rate evidence. It must reproduce and
complete at least these exact rows without `V1_IRREVERSIBLE_ABORT_FAULT`:

- seed `202608512`, policy seat `1`, game `2`;
- seed `202608526`, policy seat `0`, game `6`.

For both rows, root must inspect the Alakazam transaction through evolution,
ability, attack, and post-attack verification. The six-Energy and two-Energy KO
movement must match the engine's reversed Energy order. All 40 diagnostic games
must also retain zero invalid action, exception, timeout, max-step, structural
invalidity, transaction abort/fault, unknown removed-card status, and
candidate-owned generic or first-legal fallback.

Only after this targeted gate passes may the 700-game formal safety suite begin.
