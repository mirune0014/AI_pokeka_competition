# C4 wall-shadow FIX6 final implementation receipt

Date: 2026-07-30

## Status

The first and all intermediate FIX6 snapshots are rejected and superseded.
The only frozen implementation is:

`versions/alakazam_newdeck_v4_wall_shadow_fix6`

Policy closure:

`FA46897E4762CB1B55C9DED36EC3A06CA9CF4F9FE7C4233BE8414CC25D86DF4E`

C4 is shadow-only. It returns the exact action object produced by the adopted
C2 parent and does not yet authorize an action-changing wall rule.

## Final files

| File | SHA-256 |
|---|---|
| `main.py` | `09E6406CEDC6939A38FCE86524814171D5E7FFF7197D1FAC4CF3C776EBC0ABA9` |
| `_c4_action_parent.py` | `CB35C27EF291B627F2299DF8B5B5EF26046BC92F4E16A60BC9ECC3382E34F71F` |
| `planner_wall_shadow_fix6.py` | `772ADF9A37DB572FA0CF1B219A387EC1063CD6FD10CD5268A6DBDC29E9652D75` |
| `planner_public_damage_continuity.py` | `AD14F84C80FC92B95ACB7C585D492910BD46883528CE2F99158AF046EDDAE201` |
| `verification/c4_sidecar_collector.py` | `770EA508AF3CCFEC549C1C543EB8D04041553236B11C6D5C3CBBA8FF30344BEE` |
| `test_v4_wall_shadow_fix6.py` | `EF3F9112CED2E090EF29B74BB8A792072D955DA89A4D97F8B2DEEE8DCBA5B4AE` |
| `test_v4_c4_sidecar_collector.py` | `D7349318F1F97251A4517865C9FFA67369B8BDE28F14CADA2A1521691516197D` |
| `deck.csv` | `F598F5E578D0440C96DC0492EAECF2E19739B7A23225BE57114A724EF7D0FB94` |

The copied action parent is byte-identical to the adopted C2 `main.py`. The
candidate deck and runtime entrypoint are byte-identical to C2.

## Implemented model

- `RUN_AWAY_ACCELERATION`, `CERTIFIED_REUSABLE_WALL`,
  `CERTIFIED_SACRIFICE_WALL`, and `NO_WALL_OR_UNKNOWN` are evaluated
  separately.
- `STRICT` requires complete structural input, supported public damage floor
  and maximum payable cap, repeatable continuity where required, exact
  line importance, refusal progress, safe release, prize continuity, and no
  public gust/snipe bypass.
- `PRESERVE_CHANCE` records strategically plausible but uncertified lines.
- Opponent hidden hand contents are never inspected.
- Power Protein uses current public availability and the physical four-copy
  limit.
- Powerful Hand is treated as damage-counter placement, without
  Weakness/Resistance, and respects public board-wide blockers such as
  Repelling Veil.
- Run Away draw count is `min(3, deck_count)`; anonymous draw identities never
  certify an otherwise unknown line.
- B always compares Run Away with holding the wall, regardless of which action
  C2 selected.
- Trading Places pending state is game-, prompt-, serial-, and structure-bound.
- Delay-one sacrifice projects two distinct timelines:
  attack and exact wall KO/Prize/forced promotion, or refusal and later Trading
  release.
- Opponent attack effects, mandatory draws, and cumulative Energy attachment
  opportunities across every intervening opponent turn are included
  conservatively.
- Deadlines are fixed at wall entry and never roll forward.
- EXPOSE and WALL projections contain reconstructable public board/resource
  material and fingerprints.

## Collector guarantees

- checked-writer ordinal zero and file-local callback pairing;
- typed path identity, seat and seed formula checks;
- raw `CALL_START.observation` to canonical trace binding;
- canonical pair-ID recomputation and reverse one-to-one state binding;
- multi-suite, order-independent manifests with source hashes;
- certification-specific type, value, and arithmetic checks;
- verified parent/proposed semantic equality for natural agreements;
- same-game, same-wall, ordered outcome completeness;
- refusal, gust/snipe, unsafe release, protected-not-ready, and opponent
  continuity counterexamples block reach success;
- integrity failure exits 2; intact reach shortfall exits 0 as
  `INSUFFICIENT_EVIDENCE`.

## Verification

- production tests: **56/56 PASS**;
- collector tests: **18/18 PASS**;
- full candidate regression: **266/266 PASS**;
- unchanged C2 regression: **192/192 PASS**;
- runtime/package regression: **54/54 PASS**;
- durable collector fixtures: **4/4 PASS**;
- 700-callback action-identity probe: zero mismatches, identity faults, or
  metric exceptions;
- compilation: 48 Python files PASS;
- both deck copies: exactly 60 rows and byte-identical.

Independent production and collector reviewers both returned PASS on the final
hashes. Formal battle evaluation had not begun when this receipt was frozen.

## Governing inputs

| Input | SHA-256 |
|---|---|
| `v4_c4_wall_shadow_fix6_immutable_spec.md` | `F6BFEA318FC245543BDB8043D4FF0E8D60CD9A476403FA3E52993EF35CB2859B` |
| `v4_c4_wall_shadow_fix6_binding_amendment.md` | `924EFC7B7BEAA660AFA3BC46667A1C7A52EE2E708C8BF1D0880FB4446A604C95` |
| `v4_wall_value_integrated_design_20260730.md` | `80971002EB53419FEE21B8D755F791A3E3829749F535320A64032B4F65B6325C` |
| `v4_c4_fix6_preimplementation_strategy_judgment.md` | `9E92FA025DC3091BD09515CB6572F4E9679F42C7E044F61932D985A0EF087853` |

The formal schedule is frozen separately in
`v4_c4_wall_shadow_fix6_formal_execution_spec.md`.
