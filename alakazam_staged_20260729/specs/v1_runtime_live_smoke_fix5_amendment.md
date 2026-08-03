# v1 runtime live-smoke fix5 amendment

## Superseded parent

`alakazam_newdeck_v1_package_runtime_certified_fix4` is classified as
`SUPERSEDED_FORMAL_RUNTIME_FAULT`.

Its complete 700-game formal safety run finished all scheduled games and had no
runner, action, timeout, max-step, structural, unknown-route, or
candidate-owned fallback fault. Exact raw auditing nevertheless found nine
irreversible transaction faults:

- seven Enhanced Hammer faults caused by applying Grow Grass Energy's HP
  removal to non-Grass Mega Kangaskhan ex;
- two Boss's Orders faults caused by omitting Team Rocket's Articuno's
  Repelling Veil field effect.

No fix4 partial or completed result may be pooled with fix5 or interpreted as
Comparison B evidence.

## Authorized fix5

The authoritative implementation contract is
`v1_runtime_fix5_semantic_certificate_contract.md`, SHA-256
`5270AD22162ADDD81963E99CF459F40FE1C1D62259E501BB199D53A547CE8D20`.

Fix5 makes exactly two pre-commit certificate corrections:

1. Enhanced Hammer stores the exact target before/expected-after fingerprints
   before PLAY and applies Grow Grass's HP delta only to an exact Grass target.
2. Every v1 Powerful Hand KO certificate applies a local, target-owner-only,
   tri-state Repelling Veil guard.

The exact attack-resolution verifier, candidate priority, agent entrypoint,
unrelated candidates, deck, runtime, and inherited parent remain unchanged.

## Frozen fix5 identity

- Destination:
  `alakazam_staged_20260729/versions/alakazam_newdeck_v1_package_runtime_certified_fix5`
- Policy closure file count: `33`
- Policy closure SHA-256:
  `5FFA8776CA95E16C7030C55B5682DE42BA21C06964C790A3D6312B60FBAA5009`
- Planner SHA-256:
  `80A9B0F88A04591D4174B21AFCC5C9019A4EFCEC02E8F9C2D1576DCFC0FC044B`
- Runtime-test SHA-256:
  `4CC19F2592AD6D3CAC61AFCB8E2D3C837B4E08BFD4697C5F3D85FD9237B35D61`
- Fix5 semantic-test SHA-256:
  `948617F2847C67991747EB32F23BC70E53A97A78AE4FFC3D133B2B557FCFAB5B`
- Raw deck SHA-256:
  `F598F5E578D0440C96DC0492EAECF2E19739B7A23225BE57114A724EF7D0FB94`
- Normalized deck hash:
  `4414e8995e50c7a00d4b6aa7d9229f63c1dff5261643ec7cd86c4e329113ed69`
- Evaluation adapter `main.py` SHA-256:
  `426F1BBB71583A691CBF39A07FA8A042CB0AB0600EB43F22F9E4DBD247E5AAEC`
- Evaluation adapter `deck.csv` SHA-256:
  `F598F5E578D0440C96DC0492EAECF2E19739B7A23225BE57114A724EF7D0FB94`
- Unit tests: `146/146`
- `agent`, priority chain, unrelated candidates, and exact attack-resolution
  verifier AST equality versus fix4: true

## Fresh execution order

No existing directory may be overwritten or reused.

1. Hammer known-fault replay:
   `alakazam_staged_20260729/metrics/targeted_fix5_hammer_fault_replay_202608510_530_540`
2. Boss known-fault replay:
   `alakazam_staged_20260729/metrics/targeted_fix5_boss_repelling_veil_202608540`
3. Seven-opponent 140-game smoke:
   `alakazam_staged_20260729/metrics/smoke_v1_runtime_certified_fix5_seed202608500`
4. Seven-opponent 700-game formal safety:
   `alakazam_staged_20260729/metrics/formal_v1_runtime_certified_fix5_7opp_50seed`
5. Formal summary, only after checked Comparison B rows exist:
   `alakazam_staged_20260729/metrics/formal_v1_runtime_certified_fix5_7opp_50seed_summary`

The exact targeted schedules are frozen in
`fix5_known_fault_replay_execution_amendment.md`.

## Hard gates

Every stage requires:

- all scheduled blocks and games complete;
- callback starts equal callback ends;
- transaction starts equal transaction completes;
- zero invalid action, exception, timeout, max-step, structural fault,
  duplicate-control fault, unknown removed-card route, first-legal fallback,
  candidate-owned fallback, transaction abort, and irreversible fault.

The targeted Hammer cases must complete with stored non-Grass fingerprints.
The targeted protected Boss positions must not start a Boss transaction.
Hammer, Boss, and Alakazam candidates must still occur elsewhere when their
exact certificates are satisfied.

The complete fresh 700-game formal safety run must pass before any Comparison B
panel starts. Partial results are not evidence.
